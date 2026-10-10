#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EdgeWorldObservationActor.generated.h"

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
};
