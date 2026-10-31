#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ChaosRealismEcology.generated.h"

class UHierarchicalInstancedStaticMeshComponent;

enum class EChaosRealismPlantKind : uint8
{
	Conifer,
	Broadleaf,
	MarshReed,
	CoastalScrub
};

struct FChaosRealismPlant
{
	EChaosRealismPlantKind Kind = EChaosRealismPlantKind::Conifer;
	FVector Location = FVector::ZeroVector;
	float Scale = 1.0f;
};

/** Deterministic presentation layout; reads only the T1 terrain sampler. */
struct EDGEWORLDHOST_API FChaosRealismEcologyLayout
{
	static void Generate(TArray<FChaosRealismPlant>& OutPlants);
};

/** Built-in mesh stand-ins, kept separate from authoritative world state. */
UCLASS()
class EDGEWORLDHOST_API AChaosRealismEcology : public AActor
{
	GENERATED_BODY()
public:
	AChaosRealismEcology();
	static AChaosRealismEcology* EnsureInWorld(UWorld* World, FString& OutError);
	bool Build(FString& OutError);
	int32 GetPlantCount() const { return PlantCount; }

private:
	UPROPERTY()
	TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY()
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Trunks;
	UPROPERTY()
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Conifers;
	UPROPERTY()
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> BroadleafCrowns;
	UPROPERTY()
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> Reeds;
	UPROPERTY()
	TObjectPtr<UHierarchicalInstancedStaticMeshComponent> CoastalScrubs;
	bool bBuilt = false;
	int32 PlantCount = 0;
};
