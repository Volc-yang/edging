#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EdgeWorldCausalObservation.h"
#include "EdgeWorldCausalActor.generated.h"

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldCausalActor : public AActor
{
	GENERATED_BODY()
public:
	AEdgeWorldCausalActor();
	void ApplyObservation(const FEdgeWorldCausalObservation& Observation);
private:
	UPROPERTY()
	TArray<TObjectPtr<AActor>> Proxies;
};
