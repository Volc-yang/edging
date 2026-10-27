#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "ChaosGameMode.generated.h"

class ACameraActor;
class AChaosWorldActor;

/** Standalone entrypoint. Select with ?game=/Script/EdgeWorldHost.ChaosGameMode. */
UCLASS()
class EDGEWORLDHOST_API AChaosGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	virtual void StartPlay() override;

protected:
	/** D4 can subclass this mode and use its world projection without editing the tree demo. */
	UPROPERTY(Transient)
	TObjectPtr<AChaosWorldActor> ChaosWorld;
	UPROPERTY(Transient)
	TObjectPtr<ACameraActor> OverviewCamera;
};
