#include "EdgeWorldObservationActor.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

AEdgeWorldObservationActor::AEdgeWorldObservationActor()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(
		TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(
		TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));

	SeedMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Seed"));
	SeedMesh->SetupAttachment(SceneRoot);
	SeedMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (SphereMesh.Succeeded())
	{
		SeedMesh->SetStaticMesh(SphereMesh.Object);
	}

	TrunkMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Trunk"));
	TrunkMesh->SetupAttachment(SceneRoot);
	TrunkMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (CylinderMesh.Succeeded())
	{
		TrunkMesh->SetStaticMesh(CylinderMesh.Object);
	}

	for (int32 Index = 0; Index < 5; ++Index)
	{
		UStaticMeshComponent* Canopy = CreateDefaultSubobject<UStaticMeshComponent>(
			*FString::Printf(TEXT("Canopy%d"), Index));
		Canopy->SetupAttachment(SceneRoot);
		Canopy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		if (SphereMesh.Succeeded())
		{
			Canopy->SetStaticMesh(SphereMesh.Object);
		}
		CanopyMeshes.Add(Canopy);
	}

	SeedMesh->SetVisibility(false);
	TrunkMesh->SetVisibility(false);
	for (UStaticMeshComponent* Canopy : CanopyMeshes)
	{
		Canopy->SetVisibility(false);
	}
}

void AEdgeWorldObservationActor::ApplyCommittedObservation(const FString& InStableEntityId,
	const FVector& Position, const FRotator& Rotation, const FVector& Scale)
{
	StableEntityId = InStableEntityId;
	SetActorTransform(FTransform(Rotation, Position, Scale), false, nullptr, ETeleportType::TeleportPhysics);
}

bool AEdgeWorldObservationActor::ApplyTreeObservation(const FEdgeWorldTreeObservation& Observation,
	int64 ExpectedTick, int64 ExpectedWatermark, FString& OutError)
{
	if (Observation.SeedId.IsEmpty())
	{
		OutError = TEXT("Tree observation is missing seed_id.");
		return false;
	}
	if (Observation.LogicalTick != ExpectedTick || Observation.Watermark != ExpectedWatermark
		|| Observation.SourceRevision != ExpectedWatermark)
	{
		OutError = TEXT("Tree observation tick, source revision, or watermark did not match the requested sample.");
		return false;
	}
	if (!FMath::IsFinite(Observation.Biomass) || Observation.Biomass < 0.0 || Observation.Biomass > 1.0
		|| !FMath::IsFinite(Observation.Health) || Observation.Health < 0.0 || Observation.Health > 1.0
		|| !FMath::IsFinite(Observation.WaterReserve) || Observation.WaterReserve < 0.0 || Observation.WaterReserve > 1.0)
	{
		OutError = TEXT("Tree observation scalar fields must be finite and within [0, 1].");
		return false;
	}
	if (Observation.StateHash.IsEmpty() || Observation.EventHash.IsEmpty()
		|| Observation.RulesetVersion.IsEmpty() || Observation.ProjectionVersion != TEXT("stylized-tree-ue-v1"))
	{
		OutError = TEXT("Tree observation is missing hashes or uses an unsupported projection version.");
		return false;
	}

	const bool bSeed = Observation.Stage == TEXT("seed");
	const bool bSeedling = Observation.Stage == TEXT("seedling");
	const bool bMature = Observation.Stage == TEXT("mature");
	const bool bDeclining = Observation.Stage == TEXT("declining");
	const bool bDead = Observation.Stage == TEXT("dead");
	if (!bSeed && !bSeedling && !bMature && !bDeclining && !bDead)
	{
		OutError = FString::Printf(TEXT("Unsupported tree stage: %s"), *Observation.Stage);
		return false;
	}
	if ((!bSeed && Observation.TreeId.IsEmpty()) || (bSeed && !Observation.TreeId.IsEmpty()))
	{
		OutError = TEXT("Tree ID nullability does not match the seed lifecycle stage.");
		return false;
	}

	// These dimensions are a deterministic presentation mapping, not botanical data.
	const double Biomass = Observation.Biomass;
	SeedMesh->SetVisibility(bSeed, true);
	SeedMesh->SetRelativeLocation(FVector(0.0, 0.0, 16.0));
	SeedMesh->SetRelativeScale3D(FVector(0.18 + Biomass * 0.05));

	const double TrunkHeight = bSeed ? 0.0 : (bSeedling ? 65.0 + Biomass * 100.0 : 220.0 + Biomass * 280.0);
	const double TrunkRadiusScale = bSeedling ? 0.08 + Biomass * 0.05 : 0.16 + Biomass * 0.12;
	TrunkMesh->SetVisibility(!bSeed, true);
	TrunkMesh->SetRelativeLocation(FVector(0.0, 0.0, TrunkHeight * 0.5));
	TrunkMesh->SetRelativeScale3D(FVector(TrunkRadiusScale, TrunkRadiusScale, TrunkHeight / 100.0));

	static const FVector CanopyOffsets[] = {
		FVector(0.0, 0.0, 0.0), FVector(-48.0, 0.0, -12.0), FVector(48.0, 0.0, -12.0),
		FVector(0.0, -46.0, -20.0), FVector(0.0, 46.0, -20.0)
	};
	const double CanopyScale = bSeed ? 0.0 : (bSeedling ? 0.16 + Biomass * 0.12 : 0.44 + Biomass * 0.46);
	const int32 VisibleCanopyCount = bSeed ? 0 : (bSeedling ? 1 : (bDeclining ? 3 : (bDead ? 0 : CanopyMeshes.Num())));
	for (int32 Index = 0; Index < CanopyMeshes.Num(); ++Index)
	{
		UStaticMeshComponent* Canopy = CanopyMeshes[Index];
		Canopy->SetVisibility(Index < VisibleCanopyCount, true);
		Canopy->SetRelativeLocation(FVector(0.0, 0.0, TrunkHeight + 30.0) + CanopyOffsets[Index]);
		Canopy->SetRelativeScale3D(FVector(CanopyScale));
	}

	StableEntityId = bSeed ? Observation.SeedId : Observation.TreeId;
	LastTreeObservation = Observation;
	OutError.Reset();
	return true;
}
