#include "EdgeWorldCausalHud.h"

#include "EdgeWorldCausalObservation.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"

void AEdgeWorldCausalHud::PresentValidated(const FEdgeWorldCausalObservation& Sample,
	int64 LatestTick, int64 LatestRevision)
{
	WorldId = Sample.WorldId;
	ObservedTick = Sample.Tick;
	HeadTick = LatestTick;
	HeadRevision = LatestRevision;
	bHasProbeInfluence = Sample.Nodes.Num() > 1;
	ProbeInfluenceMm = bHasProbeInfluence ? Sample.Nodes.Last().InfluenceMm : 0;
	bHasValidatedSample = true;
}

void AEdgeWorldCausalHud::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas) return;
	const float Width = FMath::Min(625.0f, Canvas->SizeX - 32.0f);
	DrawRect(FLinearColor(0.01f, 0.025f, 0.045f, 0.78f), 16.0f, 16.0f, Width, 154.0f);
	UFont* Font = GEngine ? GEngine->GetSmallFont() : nullptr;
	const FLinearColor Main(0.82f, 0.95f, 1.0f);
	const FLinearColor Muted(0.55f, 0.75f, 0.82f);
	DrawText(TEXT("EDGEWORLD / Causal Observatory"), Main, 28.0f, 26.0f, Font, 1.25f);
	if (!bHasValidatedSample)
	{
		DrawText(TEXT("Connecting to the world; no validated observation yet"), Muted, 28.0f, 52.0f, Font);
	}
	else
	{
		DrawText(FString::Printf(TEXT("World %s  |  head tick %lld / revision %lld"), *WorldId,
			static_cast<long long>(HeadTick), static_cast<long long>(HeadRevision)), Main, 28.0f, 52.0f, Font);
		DrawText(FString::Printf(TEXT("Viewing tick %lld%s"), static_cast<long long>(ObservedTick),
			ObservedTick == HeadTick ? TEXT(" (current)") : TEXT(" (history, read only)")), Main, 28.0f, 74.0f, Font);
		const FString Probe = bHasProbeInfluence
			? FString::Printf(TEXT("Genesis engineering probe influence: %lld mm"), static_cast<long long>(ProbeInfluenceMm))
			: TEXT("Genesis engineering probe: initial state");
		DrawText(Probe, Muted, 28.0f, 96.0f, Font);
	}
	DrawText(TEXT("Space advance  |  0/1/2 history  |  H head  |  R refresh"), Muted, 28.0f, 122.0f, Font);
	DrawText(TEXT("WASD / Q E move  |  Arrow keys look"), Muted, 28.0f, 142.0f, Font);
}
