#pragma once

#include "ChaosGameMode.h"
#include "GameFramework/PlayerController.h"
#include "ChaosObservationGameMode.generated.h"

/** P0 canonical SHA-256 over the supported integer/ASCII InitialWorld JSON. */
EDGEWORLDHOST_API bool ChaosCanonicalInitialWorldHash(const FString& Json, FString& OutHash, FString& OutError);

class FEdgeWorldJsonlClient;
class FEdgeWorldProcessTransport;

/** Worker-backed origin demo. Only explicit input can commit O1. */
UCLASS()
class EDGEWORLDHOST_API AChaosObservationGameMode : public AChaosGameMode
{
	GENERATED_BODY()
public:
	AChaosObservationGameMode();
	virtual ~AChaosObservationGameMode() override;
	virtual void StartPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	void RevealWorldSpirit();
	void ObserveHistoricalTick(int64 Tick);
private:
	void ObserveAt(int64 Tick);
	TSharedPtr<FEdgeWorldProcessTransport, ESPMode::ThreadSafe> Transport;
	TSharedPtr<FEdgeWorldJsonlClient> Client;
	FString WorldId;
	FString InitialHash;
	int64 HeadTick = 0;
	int64 HeadRevision = 0;
	bool bRequestInFlight = false;
};

UCLASS()
class EDGEWORLDHOST_API AChaosObservationPlayerController : public APlayerController
{
	GENERATED_BODY()
public:
	virtual void SetupInputComponent() override;
private:
	void RevealWorldSpirit();
	void ObserveChaos();
	void ObserveOne();
};
