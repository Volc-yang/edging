#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Diagnostic metadata is a launch declaration; external receipts authenticate source/run. */
struct FEdgeWorldUniverseDiagnosticConfig
{
 bool bEnabled=false;
 FString RunId,SourceSha,Session,Scope;
 static FEdgeWorldUniverseDiagnosticConfig Parse(const FString& Enable,const FString& Run,
                                                 const FString& Source,const FString& Mode,const FString& Scope=FString());
 static FEdgeWorldUniverseDiagnosticConfig Environment();
};

/** Read-only diagnostic state only. No transport, authority, input injection or world mutation. */
struct FEdgeWorldUniverseDiagnostics
{
 FEdgeWorldUniverseDiagnosticConfig Config;
 uint64 Epoch=0,Generation=0,EventSerial=0,SpaceCount=0,RetainCount=0;
 uint32 WorkerPid=0;
 FString Action;
 int32 StageIndex=0;
 bool bHeldLatestRequested=false,bIdentityFaulted=false,bReadonlyProbeAuthorized=false;
 TSharedPtr<FJsonObject> LastSpaceInput,LastRetainInput;

 void AuthorizeReadonlyProbe(bool bExplicitInitialize,bool bEmptyAllowedActions);
 FString LogicalAction()const;
 bool IsAction(const FString& StandardId)const;
 void Invalidate(uint64 NewEpoch);
 bool ConfirmVerified(uint64 ActualEpoch,uint32 ActualWorker,uint64 ActualGeneration);
 bool Ready(uint64 ActualEpoch)const;
 bool Arm(const FString& Id);
 void Disarm();
 void RecordInput(bool bSpace,bool bRejected,const FString& Reason);
 bool IsNext(const FString& Stage)const;
 FString Marker(const FString& Stage,const FString& Origin,const TSharedRef<FJsonObject>& Binding,
                const TSharedRef<FJsonObject>& Trusted,const TSharedRef<FJsonObject>& Selected,
                const TSharedRef<FJsonObject>& State);
 static TArray<FString> Stages(const FString& Id);
};
