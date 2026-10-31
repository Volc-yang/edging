#include "ChaosRealismTerrain.h"

#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/DirectionalLight.h"
#include "Components/DirectionalLightComponent.h"
#include "EngineUtils.h"
#include "Math/RotationMatrix.h"
#include "Misc/CommandLine.h"
#include "TimerManager.h"
#include "UnrealClient.h"

namespace
{
	constexpr double MinX = 25000.0;
	constexpr double MaxX = 90000.0;
	constexpr double MinY = 20000.0;
	constexpr double MaxY = 65000.0;
	constexpr double GridCm = 500.0;
	constexpr double WaterZ = 35.0;

	double Smooth01(double Value)
	{
		const double T = FMath::Clamp(Value, 0.0, 1.0);
		return T * T * (3.0 - 2.0 * T);
	}

	double SegmentDistance(const FVector2D& Point, const FVector2D& A, const FVector2D& B)
	{
		const FVector2D Delta = B - A;
		const double LengthSq = Delta.SizeSquared();
		const double T = LengthSq > 0.0 ? FMath::Clamp(FVector2D::DotProduct(Point - A, Delta) / LengthSq, 0.0, 1.0) : 0.0;
		return FVector2D::Distance(Point, A + T * Delta);
	}

	double RiverDistance(const FVector2D& XY)
	{
		const FVector2D A(40000.0, 55000.0);
		const FVector2D B(60000.0, 40000.0);
		const FVector2D C(80000.0, 40000.0);
		return FMath::Min(SegmentDistance(XY, A, B), SegmentDistance(XY, B, C));
	}

	struct FSection
	{
		TArray<FVector> Vertices;
		TArray<int32> Triangles;
		TArray<FVector> Normals;
		TArray<FVector2D> UVs;
		TArray<FLinearColor> Colors;
		TArray<FProcMeshTangent> Tangents;

		void Quad(const FVector& A, const FVector& B, const FVector& C, const FVector& D,
			const FVector& NA, const FVector& NB, const FVector& NC, const FVector& ND)
		{
			const int32 Index = Vertices.Num();
			Vertices.Append({A, B, C, D});
			Normals.Append({NA, NB, NC, ND});
			UVs.Append({FVector2D(0, 0), FVector2D(1, 0), FVector2D(1, 1), FVector2D(0, 1)});
			Colors.Append({FLinearColor::White, FLinearColor::White, FLinearColor::White, FLinearColor::White});
			Tangents.Append({FProcMeshTangent(1, 0, 0), FProcMeshTangent(1, 0, 0),
				FProcMeshTangent(1, 0, 0), FProcMeshTangent(1, 0, 0)});
			// ProceduralMeshComponent treats this winding as the visible top face in UE.
			Triangles.Append({Index, Index + 2, Index + 1, Index, Index + 3, Index + 2});
		}

		void Submit(UProceduralMeshComponent* Mesh, int32 SectionIndex, const FLinearColor& Color)
		{
			if (Vertices.IsEmpty()) return;
			Mesh->CreateMeshSection_LinearColor(SectionIndex, Vertices, Triangles, Normals, UVs, Colors, Tangents, false);
			if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr,
				TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
			{
				if (UMaterialInstanceDynamic* Instance = UMaterialInstanceDynamic::Create(Base, Mesh))
				{
					Instance->SetVectorParameterValue(TEXT("Color"), Color);
					Mesh->SetMaterial(SectionIndex, Instance);
				}
			}
		}
	};

	void Ribbon(FSection& Section, const FVector2D& A, const FVector2D& B,
		double HalfWidth, double HeightOffset, bool bFollowTerrain)
	{
		const FVector2D Along = (B - A).GetSafeNormal();
		const FVector2D Side(-Along.Y, Along.X);
		const FVector2D P0 = A - Side * HalfWidth;
		const FVector2D P1 = B - Side * HalfWidth;
		const FVector2D P2 = B + Side * HalfWidth;
		const FVector2D P3 = A + Side * HalfWidth;
		auto Z = [bFollowTerrain, HeightOffset](const FVector2D& P)
		{
			return bFollowTerrain ? FChaosRealismTerrain::HeightAt(P) + HeightOffset : HeightOffset;
		};
		Section.Quad(FVector(P0, Z(P0)), FVector(P1, Z(P1)), FVector(P2, Z(P2)), FVector(P3, Z(P3)),
			FVector::UpVector, FVector::UpVector, FVector::UpVector, FVector::UpVector);
	}
}

bool FChaosRealismTerrain::Contains(const FVector2D& XY)
{
	return XY.X >= MinX && XY.X <= MaxX && XY.Y >= MinY && XY.Y <= MaxY;
}

double FChaosRealismTerrain::HeightAt(const FVector2D& XY)
{
	const double Broad = FMath::PerlinNoise2D(FVector2D(XY.X / 19000.0, XY.Y / 19000.0));
	const double Fine = FMath::PerlinNoise2D(FVector2D(XY.X / 6300.0, XY.Y / 6300.0));
	const double Coast = Smooth01((XY.X - 66500.0) / 11500.0);
	double Height = 320.0 + 430.0 * Broad + 90.0 * Fine - 570.0 * Coast;
	const double Marsh = Smooth01(1.0 - FVector2D::Distance(XY, FVector2D(61000.0, 40000.0)) / 12500.0);
	Height = FMath::Lerp(Height, 12.0 + 25.0 * Fine, Marsh * 0.82);
	const double River = Smooth01(1.0 - RiverDistance(XY) / 1500.0);
	Height = FMath::Lerp(Height, WaterZ - 125.0, River);
	return Height;
}

FVector FChaosRealismTerrain::NormalAt(const FVector2D& XY)
{
	const double Step = 100.0;
	return FVector(HeightAt(XY - FVector2D(Step, 0)) - HeightAt(XY + FVector2D(Step, 0)),
		HeightAt(XY - FVector2D(0, Step)) - HeightAt(XY + FVector2D(0, Step)), 2.0 * Step).GetSafeNormal();
}

double FChaosRealismTerrain::WaterMaskAt(const FVector2D& XY)
{
	const double Ocean = Smooth01((XY.X - 68500.0) / 8500.0);
	const double River = Smooth01(1.0 - RiverDistance(XY) / 1800.0);
	const double Marsh = Smooth01(1.0 - FVector2D::Distance(XY, FVector2D(61000.0, 40000.0)) / 9500.0);
	return FMath::Max3(Ocean, River, Marsh * 0.55);
}

double FChaosRealismTerrain::SlopeAt(const FVector2D& XY)
{
	const FVector Normal = NormalAt(XY);
	return FMath::Sqrt(Normal.X * Normal.X + Normal.Y * Normal.Y) / FMath::Max(Normal.Z, 0.001);
}

FChaosRealismSurfaceSample FChaosRealismTerrain::Sample(const FVector2D& XY)
{
	FChaosRealismSurfaceSample Result;
	Result.bInsideSample = Contains(XY);
	if (Result.bInsideSample)
	{
		Result.HeightCm = HeightAt(XY);
		Result.Normal = NormalAt(XY);
		Result.WaterMask = WaterMaskAt(XY);
		Result.Slope = SlopeAt(XY);
	}
	return Result;
}

AChaosRealismTerrainActor::AChaosRealismTerrainActor()
{
	PrimaryActorTick.bCanEverTick = false;
	TerrainMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("RealismTerrain"));
	RootComponent = TerrainMesh;
	WaterMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("RealismWater"));
	WaterMesh->SetupAttachment(TerrainMesh);
	RouteMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("RealismRoute"));
	RouteMesh->SetupAttachment(TerrainMesh);
	TerrainMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	WaterMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	RouteMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

bool AChaosRealismTerrainActor::Build(FString& OutError)
{
	if (bBuilt) { OutError = TEXT("Realism terrain already built"); return false; }
	if (!TerrainMesh || !WaterMesh || !RouteMesh)
	{
		OutError = TEXT("ProceduralMeshComponent unavailable"); return false;
	}
	FSection Land[4];
	for (int32 Xi = 0; Xi < 130; ++Xi)
	{
		for (int32 Yi = 0; Yi < 90; ++Yi)
		{
			const double X = MinX + Xi * GridCm;
			const double Y = MinY + Yi * GridCm;
			const FVector2D Center(X + GridCm * 0.5, Y + GridCm * 0.5);
			const double Mask = FChaosRealismTerrain::WaterMaskAt(Center);
			const int32 Section = Center.X >= 74000.0 ? 3 : Mask >= 0.42 ? 2 : Center.X >= 66000.0 ? 1 : 0;
			const FVector2D P[4] = {FVector2D(X, Y), FVector2D(X + GridCm, Y),
				FVector2D(X + GridCm, Y + GridCm), FVector2D(X, Y + GridCm)};
			Land[Section].Quad(FVector(P[0], FChaosRealismTerrain::HeightAt(P[0])),
				FVector(P[1], FChaosRealismTerrain::HeightAt(P[1])),
				FVector(P[2], FChaosRealismTerrain::HeightAt(P[2])),
				FVector(P[3], FChaosRealismTerrain::HeightAt(P[3])),
				FChaosRealismTerrain::NormalAt(P[0]), FChaosRealismTerrain::NormalAt(P[1]),
				FChaosRealismTerrain::NormalAt(P[2]), FChaosRealismTerrain::NormalAt(P[3]));
		}
	}
	Land[0].Submit(TerrainMesh, 0, FLinearColor(0.17f, 0.27f, 0.14f));
	Land[1].Submit(TerrainMesh, 1, FLinearColor(0.55f, 0.44f, 0.28f));
	Land[2].Submit(TerrainMesh, 2, FLinearColor(0.17f, 0.26f, 0.20f));
	Land[3].Submit(TerrainMesh, 3, FLinearColor(0.31f, 0.39f, 0.41f));

	FSection Ocean;
	Ocean.Quad(FVector(70000, MinY, WaterZ), FVector(MaxX, MinY, WaterZ),
		FVector(MaxX, MaxY, WaterZ), FVector(70000, MaxY, WaterZ),
		FVector::UpVector, FVector::UpVector, FVector::UpVector, FVector::UpVector);
	Ocean.Submit(WaterMesh, 0, FLinearColor(0.025f, 0.19f, 0.27f));
	FSection River;
	Ribbon(River, FVector2D(40000, 55000), FVector2D(60000, 40000), 650.0, WaterZ + 4.0, false);
	Ribbon(River, FVector2D(60000, 40000), FVector2D(80000, 40000), 650.0, WaterZ + 4.0, false);
	River.Submit(WaterMesh, 1, FLinearColor(0.04f, 0.24f, 0.31f));
	FSection Marsh;
	Marsh.Quad(FVector(54500, 34000, WaterZ + 5), FVector(67500, 34000, WaterZ + 5),
		FVector(67500, 46000, WaterZ + 5), FVector(54500, 46000, WaterZ + 5),
		FVector::UpVector, FVector::UpVector, FVector::UpVector, FVector::UpVector);
	Marsh.Submit(WaterMesh, 2, FLinearColor(0.075f, 0.25f, 0.23f));
	FSection Route;
	const FVector2D Points[] = {FVector2D(25000, 20500), FVector2D(35000, 22000),
		FVector2D(45000, 40000), FVector2D(60000, 40000), FVector2D(80000, 40000)};
	for (int32 Index = 1; Index < UE_ARRAY_COUNT(Points); ++Index)
	{
		Ribbon(Route, Points[Index - 1], Points[Index], 280.0, 35.0, true);
	}
	Route.Submit(RouteMesh, 0, FLinearColor(0.34f, 0.27f, 0.18f));
	bBuilt = true;
	UE_LOG(LogTemp, Display, TEXT("Chaos realism terrain built: bounds=(25000,20000)-(90000,65000) grid=500cm, land_vertices=%d, water_sections=3, route_segments=4"),
		Land[0].Vertices.Num() + Land[1].Vertices.Num() + Land[2].Vertices.Num() + Land[3].Vertices.Num());
	return true;
}

void AChaosRealismTerrainPreviewGameMode::StartPlay()
{
	Super::StartPlay();
	UWorld* World = GetWorld();
	if (!World) return;
	// The installed OpenWorld template has its own Landscape, unrelated to seed-7 geography.
	const FString MapPackage = World->GetOutermost()->GetName();
	if (MapPackage == TEXT("/Engine/Maps/Templates/OpenWorld"))
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (It->GetClass()->GetPathName().StartsWith(TEXT("/Script/Landscape.Landscape")))
			{
				It->SetActorHiddenInGame(true);
				It->SetActorEnableCollision(false);
			}
		}
	}
	AChaosRealismTerrainActor* Terrain = World->SpawnActor<AChaosRealismTerrainActor>();
	FString Error;
	if (!Terrain || !Terrain->Build(Error))
	{
		UE_LOG(LogTemp, Error, TEXT("Chaos realism terrain preview failed: %s"), *Error);
		return;
	}
	if (ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>())
	{
		Sun->SetActorRotation(FRotator(-55.0f, -35.0f, 0.0f));
		Sun->GetLightComponent()->SetIntensity(7.0f);
	}
	ACameraActor* Camera = World->SpawnActor<ACameraActor>(FVector(50000.0, 8000.0, 23000.0), FRotator::ZeroRotator);
	if (Camera)
	{
		const FVector Focus(62000.0, 41000.0, 0.0);
		Camera->SetActorRotation(FRotationMatrix::MakeFromX(Focus - Camera->GetActorLocation()).Rotator());
		Camera->GetCameraComponent()->SetFieldOfView(55.0f);
		if (APlayerController* Controller = World->GetFirstPlayerController()) Controller->SetViewTarget(Camera);
	}
	UE_LOG(LogTemp, Display, TEXT("Chaos realism terrain preview ready: world=%s camera=(50000,8000,23000)"), *World->GetName());
	FString BeforeScreenshot;
	FString ScreenshotArgument;
	if (FString(FCommandLine::Get()).Split(TEXT("-RealismScreenshot="), &BeforeScreenshot, &ScreenshotArgument))
	{
		FString ScreenshotPath;
		if (!ScreenshotArgument.Split(TEXT(" "), &ScreenshotPath, nullptr)) ScreenshotPath = ScreenshotArgument;
		FTimerHandle ScreenshotTimer;
		World->GetTimerManager().SetTimer(ScreenshotTimer, [ScreenshotPath]()
		{
			FScreenshotRequest::RequestScreenshot(ScreenshotPath, false, false);
			UE_LOG(LogTemp, Display, TEXT("Chaos realism screenshot requested: %s"), *ScreenshotPath);
		}, 2.0f, false);
	}
}
