#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EdgeWorldObservationActor.generated.h"

/** Fixed-time, read-only tree sample supplied by the authoritative worker. */
USTRUCT(BlueprintType)
struct EDGEWORLDRUNTIME_API FEdgeWorldTreeObservation
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString SeedId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString TreeId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString Stage;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	double Biomass = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	double Health = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	double WaterReserve = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString Phase;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString RulesetVersion;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString ProjectionVersion;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	int64 LogicalTick = INDEX_NONE;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	int64 SourceRevision = INDEX_NONE;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	int64 Watermark = INDEX_NONE;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString StateHash;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString EventHash;
};

/** Presentation-only projection target. It never advances or owns world state. */
UCLASS()
class EDGEWORLDRUNTIME_API AEdgeWorldObservationActor : public AActor
{
	GENERATED_BODY()

public:
	AEdgeWorldObservationActor();

	/** Stable ID supplied by an observation response, retained for diagnostics. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "edgeWorld|Observation")
	FString StableEntityId;

	/** Apply committed observation fields to the normal UE transform/render path. */
	void ApplyCommittedObservation(const FString& InStableEntityId, const FVector& Position,
		const FRotator& Rotation, const FVector& Scale);

	/** Apply one validated fixed-time sample to a deterministic BasicShapes tree proxy. */
	bool ApplyTreeObservation(const FEdgeWorldTreeObservation& Observation, int64 ExpectedTick,
		int64 ExpectedWatermark, FString& OutError);

	const FEdgeWorldTreeObservation& GetLastTreeObservation() const { return LastTreeObservation; }

private:
	UPROPERTY(VisibleAnywhere, Category = "edgeWorld|Presentation")
	TObjectPtr<class USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, Category = "edgeWorld|Presentation")
	TObjectPtr<class UStaticMeshComponent> SeedMesh;

	UPROPERTY(VisibleAnywhere, Category = "edgeWorld|Presentation")
	TObjectPtr<class UStaticMeshComponent> TrunkMesh;

	UPROPERTY(VisibleAnywhere, Category = "edgeWorld|Presentation")
	TArray<TObjectPtr<class UStaticMeshComponent>> CanopyMeshes;

	UPROPERTY(VisibleAnywhere, Category = "edgeWorld|Observation")
	FEdgeWorldTreeObservation LastTreeObservation;
};
