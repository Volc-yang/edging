#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"

class AChaosObservationGameMode;

/** Opt-in local JSON command file used only by the chaos evidence run. */
class FChaosValidationControl
{
public:
	FChaosValidationControl(AChaosObservationGameMode* InMode, FString InCommandPath, FString InAckPath);
	~FChaosValidationControl();
private:
	bool Poll(float DeltaTime);
	TWeakObjectPtr<AChaosObservationGameMode> Mode;
	FString CommandPath;
	FString AckPath;
	int64 LastSequence = -1;
	FTSTicker::FDelegateHandle TickerHandle;
};
