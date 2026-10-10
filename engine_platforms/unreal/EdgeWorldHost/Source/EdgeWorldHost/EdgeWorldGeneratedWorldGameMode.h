#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "EdgeWorldGeneratedWorldGameMode.generated.h"

class ACameraActor;
class AEdgeWorldObservationActor;
class FEdgeWorldJsonlClient;
class FEdgeWorldProcessTransport;

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldGeneratedWorldGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AEdgeWorldGeneratedWorldGameMode();
	virtual ~AEdgeWorldGeneratedWorldGameMode() override;
	virtual void StartPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	void AdvanceOneTick();

private:
	void SpawnGeneratedWorld();
	void StartWorkerObservation();
	void ObserveAt(int64 Tick, int64 Watermark);

	UPROPERTY()
	TObjectPtr<AEdgeWorldObservationActor> ObservationActor;

	UPROPERTY()
	TObjectPtr<ACameraActor> ObservationCamera;

	TSharedPtr<FEdgeWorldProcessTransport, ESPMode::ThreadSafe> WorkerTransport;
	TSharedPtr<FEdgeWorldJsonlClient> WorkerClient;
	FString WorldId;
	FString RulesetVersion;
	int64 LogicalTick = 0;
	int64 StateRevision = 0;
	bool bRequestInFlight = false;
};

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldGeneratedWorldPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	virtual void SetupInputComponent() override;

private:
	void AdvanceOneTick();
};
