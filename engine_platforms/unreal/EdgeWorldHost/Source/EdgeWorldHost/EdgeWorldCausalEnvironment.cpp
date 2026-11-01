#include "EdgeWorldCausalEnvironment.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

AEdgeWorldCausalEnvironment::AEdgeWorldCausalEnvironment()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("ObservatoryRoot"));
}

void AEdgeWorldCausalEnvironment::AddShape(UStaticMesh* Mesh, UMaterialInterface* BaseMaterial,
	const TCHAR* Name, const FVector& Location, const FVector& Scale,
	const FLinearColor& Color, const FRotator& Rotation)
{
	if (!Mesh || !BaseMaterial) return;
	UStaticMeshComponent* Shape = NewObject<UStaticMeshComponent>(this, Name);
	Shape->SetMobility(EComponentMobility::Movable);
	Shape->SetupAttachment(RootComponent);
	Shape->SetStaticMesh(Mesh);
	Shape->SetRelativeLocationAndRotation(Location, Rotation);
	Shape->SetRelativeScale3D(Scale);
	Shape->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Shape->SetMaterial(0, BaseMaterial);
	AddInstanceComponent(Shape);
	Shape->RegisterComponent();
	if (UMaterialInstanceDynamic* Material = Shape->CreateAndSetMaterialInstanceDynamic(0))
		Material->SetVectorParameterValue(TEXT("Color"), Color);
	Shapes.Add(Shape);
}

void AEdgeWorldCausalEnvironment::BeginPlay()
{
	Super::BeginPlay();
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	if (!Cube || !Cylinder || !Material)
	{
		UE_LOG(LogTemp, Warning, TEXT("Causal observatory: UE BasicShapes unavailable"));
		return;
	}

	// This floor and its landmarks are visual coordinates; they do not model world state.
	AddShape(Cube, Material, TEXT("Floor"), FVector(200, 0, -145), FVector(12, 10, 0.10),
		FLinearColor(0.035f, 0.055f, 0.075f));
	AddShape(Cube, Material, TEXT("CentralWalkway"), FVector(200, -150, -138), FVector(9, 1.2, 0.025),
		FLinearColor(0.12f, 0.16f, 0.19f));
	AddShape(Cube, Material, TEXT("FarWall"), FVector(200, 510, 45), FVector(12, 0.10, 4.0),
		FLinearColor(0.055f, 0.095f, 0.13f));
	AddShape(Cube, Material, TEXT("LeftWall"), FVector(-395, 0, 45), FVector(0.10, 10, 4.0),
		FLinearColor(0.055f, 0.095f, 0.13f));
	AddShape(Cube, Material, TEXT("RightWall"), FVector(795, 0, 45), FVector(0.10, 10, 4.0),
		FLinearColor(0.055f, 0.095f, 0.13f));
	for (int32 Tick = 0; Tick != 3; ++Tick)
	{
		const double X = 200.0 * Tick;
		const FString PedestalName = FString::Printf(TEXT("Tick%dPedestal"), Tick);
		AddShape(Cylinder, Material, *PedestalName, FVector(X, 0, -80), FVector(0.85, 0.85, 1.25),
			FLinearColor(0.11f, 0.16f, 0.20f));
		const FString RingName = FString::Printf(TEXT("Tick%dRing"), Tick);
		AddShape(Cylinder, Material, *RingName, FVector(X, 0, -14), FVector(0.92, 0.92, 0.07),
			Tick == 0 ? FLinearColor(0.02f, 0.36f, 0.48f) : FLinearColor(0.38f, 0.23f, 0.08f));
		const FString MarkerName = FString::Printf(TEXT("Tick%dMarker"), Tick);
		AddShape(Cube, Material, *MarkerName, FVector(X, -155, -127), FVector(0.08, 0.8, 0.06),
			FLinearColor(0.20f, 0.55f, 0.60f));
	}
	for (int32 Side = -1; Side <= 1; Side += 2)
	{
		const FString RailName = FString::Printf(TEXT("WalkwayRail%d"), Side);
		AddShape(Cube, Material, *RailName, FVector(200, -150 + Side * 68, -115), FVector(9, 0.04, 0.35),
			FLinearColor(0.16f, 0.28f, 0.31f));
	}
}
