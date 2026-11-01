#pragma once

#include "CoreMinimal.h"
#include "EdgeWorldJsonlClient.h"

struct EDGEWORLDRUNTIME_API FEdgeWorldCausalNode
{
	FString Id;
	int64 Tick = 0;
	int64 InfluenceMm = 0;
	bool bInitial = false;
	FString PhysicsHash;
};

struct EDGEWORLDRUNTIME_API FEdgeWorldCausalEdge
{
	FString Id;
	FString From;
	FString To;
	FString PhysicsHash;
};

struct EDGEWORLDRUNTIME_API FEdgeWorldCausalObservation
{
	FString WorldId;
	int64 Tick = 0;
	int64 Revision = 0;
	FString StateHash;
	FString EventHash;
	FString GenesisConfigHash;
	FString CheckpointHash;
	TArray<FEdgeWorldCausalNode> Nodes;
	TArray<FEdgeWorldCausalEdge> Edges;
};

/** A worker head is staged until its same-revision Observe sample is validated. */
struct EDGEWORLDRUNTIME_API FEdgeWorldCausalHeadGate
{
	int64 LatestTick = 0;
	int64 LatestRevision = 0;
	bool bHasValidatedHead = false;
	FString LatestConfigHash;
	FString LatestCheckpointHash;
	FString LatestStateHash;
	FString LatestEventHash;
	bool bPending = false;
	int64 PendingTick = 0;
	int64 PendingRevision = 0;
	FString PendingConfigHash;
	FString PendingCheckpointHash;
	FString PendingStateHash;
	FString PendingEventHash;

	void Stage(int64 Tick, int64 Revision, const FString& ConfigHash, const FString& CheckpointHash,
		const FString& StateHash, const FString& EventHash);
	bool Accept(const FEdgeWorldCausalObservation& Sample);
	bool CheckHistory(const FEdgeWorldCausalObservation& Sample) const;
	bool CanAdvance() const { return bHasValidatedHead && !bPending; }
};

/** Strict parser for the abstract-seed-genesis.v1 Observe result. */
EDGEWORLDRUNTIME_API bool EdgeWorldParseCausalObservation(const FEdgeWorldResponse& Response,
	const FString& ExpectedWorldId, int64 ExpectedTick, int64 ExpectedWatermark,
	FEdgeWorldCausalObservation& Out, FString& OutError);
