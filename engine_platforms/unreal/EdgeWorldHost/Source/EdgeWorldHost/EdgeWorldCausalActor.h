#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EdgeWorldCausalObservation.h"
#include "EdgeWorldCausalActor.generated.h"

class AEdgeWorldCausalEnvironment;

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldCausalActor : public AActor
{
	GENERATED_BODY()
public:
	AEdgeWorldCausalActor();
	virtual void BeginPlay() override;
	void ApplyObservation(const FEdgeWorldCausalObservation& Observation);
private:
	UPROPERTY()
	TObjectPtr<AEdgeWorldCausalEnvironment> Environment;
	UPROPERTY()
	TArray<TObjectPtr<AActor>> Proxies;
};
