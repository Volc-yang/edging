#pragma once

#include "ChaosObservationGameMode.h"
#include "ChaosRealismGameMode.generated.h"

/** Local camera navigation; it never sends a command to the Chaos Worker. */
UCLASS()
class EDGEWORLDHOST_API AChaosRealismPlayerController : public AChaosObservationPlayerController
{
	GENERATED_BODY()
public:
	virtual void PlayerTick(float DeltaTime) override;
};

/** Opt-in forest–marsh–coast projection of the committed Chaos world. */
UCLASS()
class EDGEWORLDHOST_API AChaosRealismGameMode : public AChaosObservationGameMode
{
	GENERATED_BODY()
public:
	AChaosRealismGameMode();
	virtual void StartPlay() override;
};
