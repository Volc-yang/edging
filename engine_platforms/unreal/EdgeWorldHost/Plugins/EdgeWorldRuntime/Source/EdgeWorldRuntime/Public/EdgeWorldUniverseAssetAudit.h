#pragma once
#include "CoreMinimal.h"

#if WITH_EDITOR
/** Installation evidence only: never an authority writer or a shipping/license approval. */
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseAssetAuditResult
{
 FString AuditJson;
 FString CandidateJson;
 FString CandidateDigest;
 bool bResolved = false;
 int32 AssetCount = 0;
 int32 NativeTerminalCount = 0;
 int32 GapCount = 0;
 int64 ObservedFileBytes = 0;
};
class EDGEWORLDRUNTIME_API FEdgeWorldUniverseAssetAudit
{
public:
 // Run explicitly after editor initialization. Reads installed content/Registry;
 // returns audit bytes in memory and never visits authority storage or loads assets.
 static bool Collect(const FString& WorldId, FEdgeWorldUniverseAssetAuditResult& Out, FString& Error);
};
#endif
