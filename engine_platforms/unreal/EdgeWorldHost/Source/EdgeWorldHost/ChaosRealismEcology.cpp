#include "ChaosRealismEcology.h"

#include "ChaosRealismTerrain.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
	uint32 Mix(uint32 X)
	{
		X ^= X >> 16;
		X *= 0x7feb352dU;
		X ^= X >> 15;
		X *= 0x846ca68bU;
		return X ^ (X >> 16);
	}

	float Unit(uint32 X) { return (Mix(X) & 0xffffffU) / 16777216.0f; }

	void AddZone(TArray<FChaosRealismPlant>& OutPlants, int32 MinX, int32 MaxX,
		int32 MinY, int32 MaxY, int32 Spacing, uint32 Salt, EChaosRealismPlantKind Primary,
		EChaosRealismPlantKind Alternate)
	{
		for (int32 X = MinX; X < MaxX; X += Spacing)
		{
			for (int32 Y = MinY; Y < MaxY; Y += Spacing)
			{
				const uint32 Cell = Mix(static_cast<uint32>(X) * 73856093U
					^ static_cast<uint32>(Y) * 19349663U ^ Salt ^ 7U);
				const FVector2D XY(X + Spacing * (0.2 + 0.6 * Unit(Cell)),
					Y + Spacing * (0.2 + 0.6 * Unit(Cell ^ 0xa5a5a5a5U)));
				const FChaosRealismSurfaceSample Surface = FChaosRealismTerrain::Sample(XY);
				if (!Surface.bInsideSample || Surface.Slope > 0.5) continue;
				const bool bMarsh = Primary == EChaosRealismPlantKind::MarshReed;
				const bool bCoast = Primary == EChaosRealismPlantKind::CoastalScrub;
				if ((!bMarsh && Surface.WaterMask > (bCoast ? 0.55 : 0.22))
					|| (bMarsh && (Surface.WaterMask < 0.2 || Surface.WaterMask > 0.85))) continue;
				const float Keep = bMarsh ? 0.8f : bCoast ? 0.34f : 0.72f;
				if (Unit(Cell ^ 0x9e3779b9U) > Keep) continue;
				FChaosRealismPlant& Plant = OutPlants.AddDefaulted_GetRef();
				Plant.Kind = Unit(Cell ^ 0x31415926U) < 0.22f ? Alternate : Primary;
				Plant.Location = FVector(XY, Surface.HeightCm);
				Plant.Scale = 0.7f + 0.6f * Unit(Cell ^ 0x27182818U);
			}
		}
	}

	void Configure(UHierarchicalInstancedStaticMeshComponent* Component,
		const TCHAR* MeshPath, const FLinearColor& Color)
	{
		if (UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, MeshPath)) Component->SetStaticMesh(Mesh);
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
		{
			if (UMaterialInstanceDynamic* Instance = UMaterialInstanceDynamic::Create(Base, Component))
			{
				Instance->SetVectorParameterValue(TEXT("Color"), Color);
				Component->SetMaterial(0, Instance);
			}
		}
	}
}

void FChaosRealismEcologyLayout::Generate(TArray<FChaosRealismPlant>& OutPlants)
{
	OutPlants.Reset();
	AddZone(OutPlants, 30000, 59000, 31000, 59000, 1100, 0x1001,
		EChaosRealismPlantKind::Conifer, EChaosRealismPlantKind::Broadleaf);
	AddZone(OutPlants, 52000, 69000, 31000, 49000, 650, 0x2002,
		EChaosRealismPlantKind::MarshReed, EChaosRealismPlantKind::CoastalScrub);
	AddZone(OutPlants, 69000, 80000, 21000, 64000, 1800, 0x3003,
		EChaosRealismPlantKind::CoastalScrub, EChaosRealismPlantKind::MarshReed);
}

AChaosRealismEcology::AChaosRealismEcology()
{
	PrimaryActorTick.bCanEverTick = false;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("EcologyRoot"));
	RootComponent = SceneRoot;
	auto MakeCluster = [this](const TCHAR* Name)
	{
		UHierarchicalInstancedStaticMeshComponent* Cluster = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(Name);
		Cluster->SetupAttachment(SceneRoot);
		Cluster->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		return Cluster;
	};
	Trunks = MakeCluster(TEXT("TreeTrunks"));
	Conifers = MakeCluster(TEXT("ConiferCrowns"));
	BroadleafCrowns = MakeCluster(TEXT("BroadleafCrowns"));
	Reeds = MakeCluster(TEXT("MarshReeds"));
	CoastalScrubs = MakeCluster(TEXT("CoastalScrubs"));
}

bool AChaosRealismEcology::Build(FString& OutError)
{
	if (bBuilt) return true;
	Configure(Trunks, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"), FLinearColor(0.19f, 0.12f, 0.06f));
	Configure(Conifers, TEXT("/Engine/BasicShapes/Cone.Cone"), FLinearColor(0.07f, 0.22f, 0.08f));
	Configure(BroadleafCrowns, TEXT("/Engine/BasicShapes/Sphere.Sphere"), FLinearColor(0.11f, 0.30f, 0.09f));
	Configure(Reeds, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"), FLinearColor(0.33f, 0.36f, 0.09f));
	Configure(CoastalScrubs, TEXT("/Engine/BasicShapes/Sphere.Sphere"), FLinearColor(0.24f, 0.30f, 0.13f));
	if (!Trunks->GetStaticMesh() || !Conifers->GetStaticMesh() || !BroadleafCrowns->GetStaticMesh()
		|| !Reeds->GetStaticMesh() || !CoastalScrubs->GetStaticMesh())
	{
		OutError = TEXT("UE built-in plant proxy meshes are unavailable");
		return false;
	}
	TArray<FChaosRealismPlant> Plants;
	FChaosRealismEcologyLayout::Generate(Plants);
	for (const FChaosRealismPlant& Plant : Plants)
	{
		const float Size = Plant.Scale;
		if (Plant.Kind == EChaosRealismPlantKind::Conifer || Plant.Kind == EChaosRealismPlantKind::Broadleaf)
		{
			Trunks->AddInstance(FTransform(FRotator::ZeroRotator, Plant.Location + FVector(0, 0, 190 * Size),
				FVector(0.35f * Size, 0.35f * Size, 3.8f * Size)));
			UHierarchicalInstancedStaticMeshComponent* Crown = Plant.Kind == EChaosRealismPlantKind::Conifer
				? Conifers.Get() : BroadleafCrowns.Get();
			Crown->AddInstance(FTransform(FRotator::ZeroRotator, Plant.Location + FVector(0, 0, 530 * Size),
				FVector(5.0f * Size, 5.0f * Size, 6.0f * Size)));
		}
		else
		{
			UHierarchicalInstancedStaticMeshComponent* Cluster = Plant.Kind == EChaosRealismPlantKind::MarshReed
				? Reeds.Get() : CoastalScrubs.Get();
			const FVector Scale = Plant.Kind == EChaosRealismPlantKind::MarshReed
				? FVector(0.12f * Size, 0.12f * Size, 2.3f * Size)
				: FVector(1.8f * Size, 1.8f * Size, 0.8f * Size);
			Cluster->AddInstance(FTransform(FRotator::ZeroRotator, Plant.Location + FVector(0, 0, 80 * Size), Scale));
		}
	}
	PlantCount = Plants.Num();
	bBuilt = true;
	UE_LOG(LogTemp, Display, TEXT("ChaosRealismEcology built deterministic HISM layout plants=%d"), PlantCount);
	return true;
}

AChaosRealismEcology* AChaosRealismEcology::EnsureInWorld(UWorld* World, FString& OutError)
{
	if (!World) { OutError = TEXT("No world"); return nullptr; }
	TActorIterator<AChaosRealismEcology> Existing(World);
	if (Existing)
	{
		AChaosRealismEcology* Actor = *Existing;
		return Actor->Build(OutError) ? Actor : nullptr;
	}
	AChaosRealismEcology* Actor = World->SpawnActor<AChaosRealismEcology>();
	return Actor && Actor->Build(OutError) ? Actor : nullptr;
}
