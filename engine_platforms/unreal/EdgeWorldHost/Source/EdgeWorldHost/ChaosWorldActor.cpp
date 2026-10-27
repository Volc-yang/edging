#include "ChaosWorldActor.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	constexpr TCHAR FixtureHash[] = TEXT("75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3");
	constexpr TCHAR FixtureJson[] = TEXT(R"chaos({
"schema_version":"edgeworld.chaos-origin.v1","world_id":"chaos-demo","world_seed":7,
"generator_version":"chaos-geography-exp-v1","ruleset_version":"chaos-o1-exp-v1",
"logical_tick":0,"state_revision":0,"phase":"CHAOS",
"random_stream":{"algorithm":"sha256-counter","version":1,"cursor":0},
"extent_cm":[0,0,100000,100000],
"places":[
{"place_id":"city-1","kind":"city","footprint_cm":[[10000,10000],[20000,10000],[20000,20000],[10000,20000],[10000,10000]],"elevation_cm":200,"potential":{"civilization":8000}},
{"place_id":"wildland-1","kind":"wildland","footprint_cm":[[5000,70000],[30000,70000],[30000,90000],[5000,90000],[5000,70000]],"elevation_cm":600,"potential":{"ecology":4000}},
{"place_id":"plain-1","kind":"plain","footprint_cm":[[20000,10000],[50000,10000],[50000,30000],[20000,30000],[20000,10000]],"elevation_cm":150,"potential":{"ecology":6000}},
{"place_id":"forest-1","kind":"forest","footprint_cm":[[30000,30000],[60000,30000],[60000,60000],[30000,60000],[30000,30000]],"elevation_cm":350,"potential":{"ecology":9000}},
{"place_id":"river-marsh-1","kind":"river_marsh","footprint_cm":[[50000,30000],[70000,30000],[70000,50000],[50000,50000],[50000,30000]],"elevation_cm":50,"potential":{"wetness":9500}},
{"place_id":"ocean-1","kind":"ocean","footprint_cm":[[70000,0],[100000,0],[100000,100000],[70000,100000],[70000,0]],"elevation_cm":0,"potential":{"wetness":10000}}],
"watercourses":[{"watercourse_id":"river-1","polyline_cm":[[40000,55000],[60000,40000],[80000,40000]],"marsh_place_id":"river-marsh-1","outlet_place_id":"ocean-1"}],
"routes":[{"route_id":"origin-route-1","polyline_cm":[[15000,15000],[35000,20000],[45000,40000],[60000,40000],[80000,40000]],"place_ids":["city-1","plain-1","forest-1","river-marsh-1","ocean-1"]}],
"world_spirit_id":null,"event_watermark":0
})chaos");

	bool ReadPoint(const TSharedPtr<FJsonValue>& Value, FVector2D& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Coordinates = nullptr;
		if (!Value.IsValid() || !Value->TryGetArray(Coordinates) || !Coordinates || Coordinates->Num() != 2)
		{
			return false;
		}
		double X = 0.0;
		double Y = 0.0;
		if (!(*Coordinates)[0]->TryGetNumber(X) || !(*Coordinates)[1]->TryGetNumber(Y)
			|| !FMath::IsFinite(X) || !FMath::IsFinite(Y)
			|| FMath::Abs(X) > static_cast<double>((1LL << 53) - 1)
			|| FMath::Abs(Y) > static_cast<double>((1LL << 53) - 1)
			|| FMath::FloorToDouble(X) != X || FMath::FloorToDouble(Y) != Y)
		{
			return false;
		}
		Out = FVector2D(X, Y);
		return true;
	}

	bool ReadExactInteger(const TSharedPtr<FJsonValue>& Value, int64& Out)
	{
		double Number = 0.0;
		if (!Value.IsValid() || !Value->TryGetNumber(Number) || !FMath::IsFinite(Number)
			|| FMath::Abs(Number) > static_cast<double>((1LL << 53) - 1)
			|| FMath::FloorToDouble(Number) != Number)
		{
			return false;
		}
		Out = static_cast<int64>(Number);
		return true;
	}

	bool ReadLine(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, TArray<FVector2D>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (!Object.IsValid() || !Object->TryGetArrayField(Field, Values) || !Values || Values->Num() < 2)
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& Value : *Values)
		{
			FVector2D Point;
			if (!ReadPoint(Value, Point)) return false;
			Out.Add(Point);
		}
		return true;
	}

	FLinearColor PlaceColor(const FString& Kind)
	{
		if (Kind == TEXT("city")) return FLinearColor(0.60f, 0.47f, 0.34f);
		if (Kind == TEXT("wildland")) return FLinearColor(0.43f, 0.30f, 0.22f);
		if (Kind == TEXT("plain")) return FLinearColor(0.65f, 0.66f, 0.30f);
		if (Kind == TEXT("forest")) return FLinearColor(0.08f, 0.34f, 0.15f);
		if (Kind == TEXT("river_marsh")) return FLinearColor(0.18f, 0.48f, 0.42f);
		return FLinearColor(0.04f, 0.32f, 0.61f);
	}
}

AChaosWorldActor::AChaosWorldActor()
{
	PrimaryActorTick.bCanEverTick = false;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("ChaosSceneRoot"));
	RootComponent = SceneRoot;
}

void AChaosWorldActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (LevelAddedHandle.IsValid())
	{
		FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
		LevelAddedHandle.Reset();
	}
	Super::EndPlay(EndPlayReason);
}

bool AChaosWorldActor::HideLandscapeActor(AActor* Actor, const TCHAR* Source)
{
	if (!Actor || Actor == this) return false;
	const FString ClassPath = Actor->GetClass()->GetPathName();
	if (!ClassPath.StartsWith(TEXT("/Script/Landscape.Landscape"))) return false;
	Actor->SetActorHiddenInGame(true);
	Actor->SetActorEnableCollision(false);
	UE_LOG(LogTemp, Display, TEXT("Chaos template landscape hidden: source=%s actor=%s class=%s"),
		Source, *Actor->GetName(), *ClassPath);
	return true;
}

void AChaosWorldActor::OnLevelAdded(ULevel* Level, UWorld* World)
{
	if (World != GetWorld() || !Level) return;
	int32 HiddenCount = 0;
	for (AActor* Actor : Level->Actors)
	{
		if (HideLandscapeActor(Actor, TEXT("streamed-level"))) ++HiddenCount;
	}
	if (HiddenCount > 0)
	{
		UE_LOG(LogTemp, Display, TEXT("Chaos streamed template landscape hide: count=%d"), HiddenCount);
	}
}

void AChaosWorldActor::HideTemplateLandscape()
{
	UWorld* World = GetWorld();
	if (!World) return;
	const FString MapPackage = World->GetOutermost()->GetName();
	if (!MapPackage.StartsWith(TEXT("/Engine/Maps/Templates/")) || !MapPackage.EndsWith(TEXT("OpenWorld")))
	{
		UE_LOG(LogTemp, Display, TEXT("Chaos template landscape hide skipped: map=%s"), *MapPackage);
		return;
	}
	if (!LevelAddedHandle.IsValid())
	{
		LevelAddedHandle = FWorldDelegates::LevelAddedToWorld.AddUObject(this, &AChaosWorldActor::OnLevelAdded);
	}
	int32 HiddenCount = 0;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (HideLandscapeActor(*It, TEXT("initial-level"))) ++HiddenCount;
	}
	UE_LOG(LogTemp, Display, TEXT("Chaos template landscape hide complete: map=%s count=%d"),
		*MapPackage, HiddenCount);
}

UStaticMeshComponent* AChaosWorldActor::AddShape(UStaticMesh* Mesh, const FVector& CenterCm,
	const FVector& SizeCm, const FLinearColor& Color, const FString& Label)
{
	if (!Mesh) return nullptr;
	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(this);
	Component->SetStaticMesh(Mesh);
	Component->SetMobility(EComponentMobility::Movable);
	Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component->SetupAttachment(SceneRoot);
	AddInstanceComponent(Component);
	Component->RegisterComponent();
	Component->SetWorldLocation(CenterCm);
	Component->SetWorldScale3D(SizeCm / 100.0f);
	Component->ComponentTags.Add(FName(*Label));
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
	{
		if (UMaterialInstanceDynamic* Instance = UMaterialInstanceDynamic::Create(Base, Component))
		{
			Instance->SetVectorParameterValue(TEXT("Color"), Color);
			Component->SetMaterial(0, Instance);
		}
	}
	return Component;
}

void AChaosWorldActor::AddSegment(UStaticMesh* Mesh, const FVector& Start, const FVector& End,
	float WidthCm, float HeightCm, const FLinearColor& Color, const FString& Label)
{
	const FVector Delta = End - Start;
	const float Length = Delta.Size2D();
	if (Length < 1.0f) return;
	if (UStaticMeshComponent* Segment = AddShape(Mesh, (Start + End) * 0.5f,
		FVector(Length, WidthCm, HeightCm), Color, Label))
	{
		Segment->SetWorldRotation(FRotator(0.0f, FMath::RadiansToDegrees(FMath::Atan2(Delta.Y, Delta.X)), 0.0f));
	}
}

bool AChaosWorldActor::BuildContractFixture(FString& OutError)
{
	return BuildFromInitialWorldJson(FixtureJson, FixtureHash, OutError);
}

bool AChaosWorldActor::BuildFromInitialWorldJson(const FString& Json,
	const FString& ExpectedInitialHash, FString& OutError)
{
	if (bBuilt)
	{
		OutError = TEXT("Chaos world projection already built");
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	FString Schema;
	FString Phase;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid()
		|| !Root->TryGetStringField(TEXT("schema_version"), Schema)
		|| !Root->TryGetStringField(TEXT("phase"), Phase)
		|| Schema != TEXT("edgeworld.chaos-origin.v1") || Phase != TEXT("CHAOS"))
	{
		OutError = TEXT("Invalid chaos InitialWorld JSON/schema/phase");
		return false;
	}
	FString ParsedWorldId;
	if (!Root->TryGetStringField(TEXT("world_id"), ParsedWorldId) || ParsedWorldId.IsEmpty())
	{
		OutError = TEXT("InitialWorld requires world_id");
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>* Extent = nullptr;
	const TArray<TSharedPtr<FJsonValue>>* Places = nullptr;
	const TArray<TSharedPtr<FJsonValue>>* Watercourses = nullptr;
	const TArray<TSharedPtr<FJsonValue>>* Routes = nullptr;
	if (!Root->TryGetArrayField(TEXT("extent_cm"), Extent) || !Extent || Extent->Num() != 4
		|| !Root->TryGetArrayField(TEXT("places"), Places) || !Places
		|| !Root->TryGetArrayField(TEXT("watercourses"), Watercourses) || !Watercourses || Watercourses->IsEmpty()
		|| !Root->TryGetArrayField(TEXT("routes"), Routes) || !Routes || Routes->IsEmpty())
	{
		OutError = TEXT("InitialWorld lacks extent, places, watercourses or routes");
		return false;
	}
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Cone = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cone.Cone"));
	UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (!Cube || !Cone || !Cylinder)
	{
		OutError = TEXT("UE Engine BasicShapes are unavailable");
		return false;
	}
	int64 ExtentIntegers[4] = {};
	for (int32 Index = 0; Index < 4; ++Index)
	{
		if (!ReadExactInteger((*Extent)[Index], ExtentIntegers[Index]))
		{
			OutError = TEXT("Invalid InitialWorld extent coordinate");
			return false;
		}
	}
	const float MinX = static_cast<float>(ExtentIntegers[0]);
	const float MinY = static_cast<float>(ExtentIntegers[1]);
	const float MaxX = static_cast<float>(ExtentIntegers[2]);
	const float MaxY = static_cast<float>(ExtentIntegers[3]);
	if (!(MinX < MaxX && MinY < MaxY) || MaxX - MinX > 5000000.0f || MaxY - MinY > 5000000.0f)
	{
		OutError = TEXT("Invalid InitialWorld extent");
		return false;
	}
	HideTemplateLandscape();
	AddShape(Cube, FVector((MinX + MaxX) * 0.5f, (MinY + MaxY) * 0.5f, -110.0f),
		FVector(MaxX - MinX, MaxY - MinY, 200.0f), FLinearColor(0.32f, 0.35f, 0.25f), TEXT("continuous-ground"));

	TSet<FString> Kinds;
	for (const TSharedPtr<FJsonValue>& Entry : *Places)
	{
		const TSharedPtr<FJsonObject> Place = Entry.IsValid() ? Entry->AsObject() : nullptr;
		if (!Place.IsValid()) { OutError = TEXT("Invalid place entry"); return false; }
		FString Id, Kind;
		if (!Place->TryGetStringField(TEXT("place_id"), Id) || Id.IsEmpty()
			|| !Place->TryGetStringField(TEXT("kind"), Kind))
		{
			OutError = TEXT("Place lacks identity/kind"); return false;
		}
		if (Kind != TEXT("city") && Kind != TEXT("wildland") && Kind != TEXT("plain")
			&& Kind != TEXT("forest") && Kind != TEXT("river_marsh") && Kind != TEXT("ocean"))
		{
			OutError = FString::Printf(TEXT("Unsupported place kind: %s"), *Kind); return false;
		}
		TArray<FVector2D> Polygon;
		if (!ReadLine(Place, TEXT("footprint_cm"), Polygon) || Polygon.Num() < 4 || Polygon[0] != Polygon.Last())
		{
			OutError = FString::Printf(TEXT("Invalid footprint: %s"), *Id); return false;
		}
		FBox2D Bounds(Polygon);
		if (!Bounds.bIsValid || Bounds.Min.X < MinX || Bounds.Min.Y < MinY
			|| Bounds.Max.X > MaxX || Bounds.Max.Y > MaxY)
		{
			OutError = FString::Printf(TEXT("Footprint outside extent: %s"), *Id); return false;
		}
		Kinds.Add(Kind);
		const FVector2D Center = Bounds.GetCenter();
		const FVector2D Size = Bounds.GetSize();
		const FLinearColor Color = PlaceColor(Kind);
		AddShape(Cube, FVector(Center.X, Center.Y, 3.0f), FVector(Size.X, Size.Y, 6.0f), Color, Id);
		// Bright footprint edges stay readable in both the overview and local review cameras.
		for (int32 Index = 1; Index < Polygon.Num(); ++Index)
		{
			AddSegment(Cube, FVector(Polygon[Index - 1], 42.0f), FVector(Polygon[Index], 42.0f),
				180.0f, 45.0f, Color * 1.6f, Id + TEXT("-edge"));
		}
		UE_LOG(LogTemp, Display, TEXT("Chaos place projection: id=%s kind=%s center_cm=(%.0f,%.0f) extent_cm=(%.0f,%.0f)"),
			*Id, *Kind, Center.X, Center.Y, Size.X, Size.Y);

		if (Kind == TEXT("city"))
		{
			for (int32 X = 0; X < 4; ++X) for (int32 Y = 0; Y < 4; ++Y)
			{
				const float Height = 650.0f + 170.0f * ((X + 2 * Y) % 4);
				AddShape(Cube, FVector(Bounds.Min.X + (X + 0.5f) * Size.X / 4.0f,
					Bounds.Min.Y + (Y + 0.5f) * Size.Y / 4.0f, Height * 0.5f + 7.0f),
					FVector(950.0f, 950.0f, Height), FLinearColor(0.64f, 0.58f, 0.48f), TEXT("city-building"));
			}
			AddShape(Cylinder, FVector(Center.X, Center.Y, 1850.0f), FVector(500.0f, 500.0f, 3700.0f),
				FLinearColor(0.86f, 0.72f, 0.48f), Id + TEXT("-landmark"));
			AddShape(Cone, FVector(Center.X, Center.Y, 4200.0f), FVector(1200.0f, 1200.0f, 1000.0f),
				FLinearColor(0.96f, 0.83f, 0.52f), Id + TEXT("-roof"));
		}
		else if (Kind == TEXT("forest"))
		{
			for (int32 X = 0; X < 7; ++X) for (int32 Y = 0; Y < 7; ++Y)
			{
				const float Px = Bounds.Min.X + (X + 0.5f) * Size.X / 7.0f;
				const float Py = Bounds.Min.Y + (Y + 0.5f) * Size.Y / 7.0f;
				AddShape(Cylinder, FVector(Px, Py, 275.0f), FVector(130.0f, 130.0f, 550.0f),
					FLinearColor(0.23f, 0.13f, 0.07f), TEXT("forest-trunk"));
				AddShape(Cone, FVector(Px, Py, 930.0f), FVector(730.0f, 730.0f, 1250.0f),
					FLinearColor(0.08f, 0.29f, 0.09f), TEXT("forest-canopy"));
			}
		}
		else if (Kind == TEXT("wildland"))
		{
			for (int32 Index = 0; Index < 12; ++Index)
			{
				const float Px = Bounds.Min.X + (Index % 4 + 0.5f) * Size.X / 4.0f;
				const float Py = Bounds.Min.Y + (Index / 4 + 0.5f) * Size.Y / 3.0f;
				AddShape(Cone, FVector(Px, Py, 400.0f), FVector(850.0f, 850.0f, 800.0f),
					FLinearColor(0.35f, 0.30f, 0.25f), TEXT("wildland-rock"));
			}
			AddShape(Cone, FVector(Center.X, Center.Y, 2300.0f), FVector(5200.0f, 5200.0f, 4600.0f),
				FLinearColor(0.58f, 0.45f, 0.34f), Id + TEXT("-landmark"));
		}
		else if (Kind == TEXT("plain"))
		{
			for (int32 Index = 0; Index < 5; ++Index)
			{
				const float Px = Bounds.Min.X + (Index + 0.5f) * Size.X / 5.0f;
				AddShape(Cube, FVector(Px, Center.Y, 120.0f), FVector(1100.0f, Size.Y * 0.56f, 220.0f),
					FLinearColor(0.79f, 0.71f, 0.31f), Id + TEXT("-field"));
			}
		}
		else if (Kind == TEXT("river_marsh"))
		{
			for (int32 Index = 0; Index < 15; ++Index)
			{
				const float Px = Bounds.Min.X + (Index % 5 + 0.5f) * Size.X / 5.0f;
				const float Py = Bounds.Min.Y + (Index / 5 + 0.5f) * Size.Y / 3.0f;
				AddShape(Cylinder, FVector(Px, Py, 180.0f), FVector(75.0f, 75.0f, 350.0f),
					FLinearColor(0.48f, 0.50f, 0.21f), TEXT("marsh-reed"));
			}
			for (int32 Index = 0; Index < 5; ++Index)
			{
				const float Px = Bounds.Min.X + (Index + 0.5f) * Size.X / 5.0f;
				AddShape(Cylinder, FVector(Px, Center.Y + (Index % 2 ? 1800.0f : -1800.0f), 280.0f),
					FVector(850.0f, 850.0f, 550.0f), FLinearColor(0.76f, 0.72f, 0.31f), Id + TEXT("-reed-island"));
			}
		}
		if (Kind == TEXT("ocean") || Kind == TEXT("river_marsh"))
		{
			AddShape(Cube, FVector(Center.X, Center.Y, 10.0f), FVector(Size.X, Size.Y, 8.0f),
				Kind == TEXT("ocean") ? FLinearColor(0.04f, 0.31f, 0.66f) : FLinearColor(0.08f, 0.43f, 0.55f),
				Id + TEXT("-surface-water"));
			if (Kind == TEXT("ocean"))
			{
				for (int32 Index = 1; Index <= 4; ++Index)
				{
					const float X = Bounds.Min.X + Index * Size.X / 5.0f;
					AddShape(Cube, FVector(X, Center.Y, 18.0f), FVector(140.0f, Size.Y * 0.78f, 6.0f),
						FLinearColor(0.44f, 0.73f, 0.81f), Id + TEXT("-wave"));
				}
			}
		}
	}
	if (Kinds.Num() != 6)
	{
		OutError = TEXT("InitialWorld must contain all six place kinds"); return false;
	}
	for (const TSharedPtr<FJsonValue>& Entry : *Watercourses)
	{
		const TSharedPtr<FJsonObject> Water = Entry.IsValid() ? Entry->AsObject() : nullptr;
		TArray<FVector2D> Points;
		if (!ReadLine(Water, TEXT("polyline_cm"), Points))
		{
			OutError = TEXT("Invalid watercourse"); return false;
		}
		FString WaterId;
		if (!Water->TryGetStringField(TEXT("watercourse_id"), WaterId) || WaterId.IsEmpty())
		{
			OutError = TEXT("Watercourse lacks identity"); return false;
		}
		UE_LOG(LogTemp, Display, TEXT("Chaos watercourse projection: id=%s points=%d start_cm=(%.0f,%.0f) end_cm=(%.0f,%.0f)"),
			*WaterId, Points.Num(), Points[0].X, Points[0].Y, Points.Last().X, Points.Last().Y);
		for (int32 Index = 1; Index < Points.Num(); ++Index)
		{
			AddSegment(Cube, FVector(Points[Index - 1], 26.0f), FVector(Points[Index], 26.0f),
				1800.0f, 20.0f, FLinearColor(0.05f, 0.46f, 0.67f), WaterId + TEXT("-channel"));
			AddSegment(Cube, FVector(Points[Index - 1], 40.0f), FVector(Points[Index], 40.0f),
				900.0f, 8.0f, FLinearColor(0.42f, 0.74f, 0.82f), WaterId + TEXT("-surface"));
		}
	}
	for (const TSharedPtr<FJsonValue>& Entry : *Routes)
	{
		const TSharedPtr<FJsonObject> Route = Entry.IsValid() ? Entry->AsObject() : nullptr;
		TArray<FVector2D> Points;
		if (!ReadLine(Route, TEXT("polyline_cm"), Points))
		{
			OutError = TEXT("Invalid route"); return false;
		}
		FString RouteId;
		if (!Route->TryGetStringField(TEXT("route_id"), RouteId) || RouteId.IsEmpty())
		{
			OutError = TEXT("Route lacks identity"); return false;
		}
		UE_LOG(LogTemp, Display, TEXT("Chaos route projection: id=%s points=%d start_cm=(%.0f,%.0f) end_cm=(%.0f,%.0f)"),
			*RouteId, Points.Num(), Points[0].X, Points[0].Y, Points.Last().X, Points.Last().Y);
		for (int32 Index = 1; Index < Points.Num(); ++Index)
		{
			AddSegment(Cube, FVector(Points[Index - 1], 57.0f), FVector(Points[Index], 57.0f),
				950.0f, 20.0f, FLinearColor(0.20f, 0.18f, 0.12f), RouteId + TEXT("-edge"));
			AddSegment(Cube, FVector(Points[Index - 1], 73.0f), FVector(Points[Index], 73.0f),
				580.0f, 9.0f, FLinearColor(0.94f, 0.72f, 0.25f), RouteId + TEXT("-surface"));
		}
	}
	const float BorderZ = 150.0f;
	const FLinearColor BorderColor(0.16f, 0.79f, 0.69f);
	const FVector Corners[] = { FVector(MinX, MinY, BorderZ), FVector(MaxX, MinY, BorderZ),
		FVector(MaxX, MaxY, BorderZ), FVector(MinX, MaxY, BorderZ) };
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const FVector Start = Corners[Index];
		const FVector End = Corners[(Index + 1) % 4];
		const FVector Delta = End - Start;
		if (UStaticMeshComponent* Border = AddShape(Cube, (Start + End) * 0.5f,
			FVector(Delta.Size(), 120.0f, 180.0f), BorderColor, TEXT("world-spirit-boundary")))
		{
			Border->SetWorldRotation(FRotator(0.0f, FMath::RadiansToDegrees(FMath::Atan2(Delta.Y, Delta.X)), 0.0f));
			Border->SetVisibility(false);
			SpiritBoundary.Add(Border);
		}
	}
	WorldId = ParsedWorldId;
	InitialManifestHash = ExpectedInitialHash;
	bBuilt = true;
	UE_LOG(LogTemp, Display, TEXT("ChaosWorld projection built: world=%s, places=%d, hash=%s"),
		*WorldId, Places->Num(), InitialManifestHash.IsEmpty() ? TEXT("unverified") : *InitialManifestHash);
	return true;
}

void AChaosWorldActor::SetWorldSpiritVisible(bool bVisible)
{
	for (UStaticMeshComponent* Border : SpiritBoundary)
	{
		if (Border) Border->SetVisibility(bVisible);
	}
}
