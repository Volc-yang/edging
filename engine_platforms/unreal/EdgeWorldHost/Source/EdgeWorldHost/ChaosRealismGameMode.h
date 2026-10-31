#pragma once

#include "ChaosObservationGameMode.h"
#include "ChaosRealismGameMode.generated.h"

/** Opt-in forest–marsh–coast projection of the committed Chaos world. */
UCLASS()
class EDGEWORLDHOST_API AChaosRealismGameMode : public AChaosObservationGameMode
{
	GENERATED_BODY()
public:
	virtual void StartPlay() override;
};
