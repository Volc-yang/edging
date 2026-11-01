#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "EdgeWorldCausalHud.generated.h"

struct FEdgeWorldCausalObservation;

/** Visitor-facing labels for an already validated causal observation. */
UCLASS()
class EDGEWORLDHOST_API AEdgeWorldCausalHud : public AHUD
{
	GENERATED_BODY()
public:
	virtual void DrawHUD() override;
	void PresentValidated(const FEdgeWorldCausalObservation& Sample, int64 LatestTick, int64 LatestRevision);

private:
	bool bHasValidatedSample = false;
	FString WorldId;
	int64 ObservedTick = 0;
	int64 HeadTick = 0;
	int64 HeadRevision = 0;
	int64 ProbeInfluenceMm = 0;
	bool bHasProbeInfluence = false;
};
