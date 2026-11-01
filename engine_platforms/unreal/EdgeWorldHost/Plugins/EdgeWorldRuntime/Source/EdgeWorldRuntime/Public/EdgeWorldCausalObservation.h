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
	TArray<FEdgeWorldCausalNode> Nodes;
	TArray<FEdgeWorldCausalEdge> Edges;
};

/** Strict parser for the abstract-seed-genesis.v1 Observe result. */
EDGEWORLDRUNTIME_API bool EdgeWorldParseCausalObservation(const FEdgeWorldResponse& Response,
	const FString& ExpectedWorldId, int64 ExpectedTick, int64 ExpectedWatermark,
	FEdgeWorldCausalObservation& Out, FString& OutError);
