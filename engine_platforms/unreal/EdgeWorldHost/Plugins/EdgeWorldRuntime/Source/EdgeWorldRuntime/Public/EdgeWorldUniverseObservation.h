#pragma once

#include "CoreMinimal.h"

/** Public pins obtained from the owner launcher, never from an Observe response. */
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseContext
{
 FString WorldId, AuthorityRoot, TrustAlgorithm, TrustAnchor, ArtifactClass, ExpectedBuild, ExpectedOptions;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseHeadBinding
{
 FEdgeWorldUniverseContext Context;
 FString Head, Domain, Version, Profile, StorageState;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseExpectation
{
 FEdgeWorldUniverseContext Context;
 FEdgeWorldUniverseHeadBinding TrustedHead;
 FString RequestId;
 int64 Tick = 0, Revision = 0, Watermark = 0;
 // Must be explicitly supplied by a fixture harness. Runtime defaults reject synthetic records.
 bool bFixtureOnly = false;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseBody
{
 FString PhysicalId;
 FVector3d PositionM, LinearVelocityMS, AngularVelocityRadS;
 // Genesis WXYZ order retained; no implicit handedness conversion.
 FVector4d QuaternionWXYZ;
 double MassKg = 0;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseContact
{
 FVector3d PositionM, ForceOnDynamicN;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniversePoint { int64 X = 0, Y = 0; };
struct EDGEWORLDRUNTIME_API FEdgeWorldUniversePlace
{
 FString PlaceId, PlaceKind, ExistenceDigest;
 int64 ElevationCm = 0;
 TArray<FEdgeWorldUniversePoint> FootprintCm;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseRoute
{
 FString Id;
 TArray<FString> PlaceIds;
 TArray<FEdgeWorldUniversePoint> PolylineCm;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseAsset
{
 FString AssetId, Uri, Sha256;
 int64 ByteCount = 0;
 TArray<FString> Dependencies;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseDecoration
{
 FString InstanceId, PlaceId, AssetId;
 int64 PositionCm[3] = {}, ScaleMilli[3] = {};
};
/** Immutable-by-value verified record; CanonicalJson is ASCII C(record). */
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseRecord
{
 FString Digest, Kind, Id, CanonicalJson;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseObservation
{
 FString WorldId, Manifest, State, Event, StorageState, ArtifactClass;
 int64 WireBytes = 0;
 TOptional<FInt64Point> PriorSelection; // X=tick, Y=revision, verified immediate prior.
 int64 Tick = 0, Revision = 0, Watermark = 0, Budget = 0, RandomCursor = 0, PhysicalStepCount = 0;
 TOptional<int64> DevelopmentMm;
 FVector3d OriginCm;
 double Scale = 100, DevelopmentCmPerMm = 0;
 TArray<FEdgeWorldUniverseBody> Bodies, PriorBodies;
 TArray<FEdgeWorldUniverseContact> Contacts;
 FString WorldManifest, Snapshot, Config, Binding, Build, Options, Transform, AssetDependencyStatus;
 TArray<FEdgeWorldUniversePlace> Places;
 TArray<FEdgeWorldUniverseRoute> Routes;
 TArray<FEdgeWorldUniversePoint> WatercourseCm;
 TArray<FEdgeWorldUniverseAsset> Assets;
 TArray<FEdgeWorldUniverseDecoration> Decorations;
 // Full validated world/geography/assets/config/binding/snapshot and immediate-prior dependencies.
 // Omitted history refs are deliberately absent. This is a selected membership proof, not recovery.
 TArray<FEdgeWorldUniverseRecord> SelectedRecords;
};
class EDGEWORLDRUNTIME_API FEdgeWorldUniverseObservationParser
{
public:
 static bool Verify(TArrayView<const uint8> RawJsonl, const FEdgeWorldUniverseExpectation& Expected,
                    FEdgeWorldUniverseObservation& Out, FString& Error);
 // Independent strict codec entry point for golden verification; does not grant membership/trust.
 static bool CanonicalRecord(TArrayView<const uint8> RawJson, FString& Canonical, FString& Digest, FString& Error);
 static bool ExactInfluence(uint64 PreviousBits, uint64 CurrentBits, int64& Millimetres);
};

/** Public launch hints never authorize an action or initialize. */
struct EDGEWORLDRUNTIME_API FEdgeWorldUniversePublicPins
{
 FEdgeWorldUniverseContext Context;
 FString Principal;
 TArray<FString> AllowedActions;
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseControlExpectation
{
 FEdgeWorldUniversePublicPins Pins;
 FString RequestId, Operation;
 FString ProposalJson, IntentJson, ApprovalId, CommandRecordId, CommandDigest;
 bool bFixtureOnly=false; // C++ test harness only; no runtime/CLI fake mode.
};
struct EDGEWORLDRUNTIME_API FEdgeWorldUniverseControl
{
 bool bSuccess=false;
 FEdgeWorldUniverseHeadBinding Head;
 int64 Tick=0, Revision=0, Watermark=0;
 FString State, Event, Manifest, CommandRecordsJson, CommandDigest, CommittedResultJson;
 FString ErrorCode, CommitStatus;
};
class EDGEWORLDRUNTIME_API FEdgeWorldUniverseControlParser
{
public:
 static bool PublicPins(TArrayView<const uint8> CanonicalAscii,const FString& ExpectedSha256,
                        FEdgeWorldUniversePublicPins& Out,FString& Error,bool bFixtureOnly=false);
 static bool Verify(TArrayView<const uint8> Raw,const FEdgeWorldUniverseControlExpectation& Expected,
                    FEdgeWorldUniverseControl& Out,FString& Error);
 static bool Request(const FString& Operation,const FString& RequestId,const FString& PayloadJson,
                     FString& OutJsonl,FString& Error);
 static bool BuildPrepare(const FEdgeWorldUniversePublicPins& Pins,const FEdgeWorldUniverseObservation& Current,
                          const FString& CommandId,const FString& Action,const FString& Case,
                          FString& OutPayload,FString& OutProposal,FString& OutIntent,FString& Error);
};
