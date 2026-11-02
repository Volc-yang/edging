#include "EdgeWorldUniverseDiagnostics.h"
#include "HAL/PlatformMisc.h"
#include "Serialization/JsonSerializer.h"
namespace
{
bool Token(const FString& S,int32 Max)
{
 if(S.IsEmpty()||S.Len()>Max)return false;
 for(TCHAR C:S)if(!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||(C>='0'&&C<='9')||C=='-'||C=='_'))return false;
 return true;
}
}
FEdgeWorldUniverseDiagnosticConfig FEdgeWorldUniverseDiagnosticConfig::Parse(const FString& Enable,const FString& Run,const FString& Source,const FString& Mode,const FString& Scope)
{
 FEdgeWorldUniverseDiagnosticConfig C;
 if(Enable!=TEXT("1")||!Token(Run,128)||Source.Len()!=40||(Mode!=TEXT("initialize")&&Mode!=TEXT("existing")))return C;
 for(TCHAR X:Source)if(!((X>='0'&&X<='9')||(X>='a'&&X<='f')))return C;
 if(!Scope.IsEmpty()&&(Scope!=TEXT("readonly-probe")||Mode!=TEXT("existing")))return C;
 C.Scope=Scope;C.bEnabled=true;C.RunId=Run;C.SourceSha=Source;C.Session=Mode;return C;
}
FEdgeWorldUniverseDiagnosticConfig FEdgeWorldUniverseDiagnosticConfig::Environment()
{
 return Parse(FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_DIAGNOSTICS_V1")),
              FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_DIAGNOSTIC_RUN_ID")),
              FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_DIAGNOSTIC_SOURCE_SHA")),
              FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_DIAGNOSTIC_SESSION")),
              FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_DIAGNOSTIC_SCOPE")));
}
void FEdgeWorldUniverseDiagnostics::AuthorizeReadonlyProbe(bool Initialize,bool EmptyActions)
{
 bReadonlyProbeAuthorized=Config.bEnabled&&Config.Scope==TEXT("readonly-probe")&&Config.Session==TEXT("existing")&&!Initialize&&EmptyActions;
 if(Config.Scope==TEXT("readonly-probe")&&!bReadonlyProbeAuthorized)Config.bEnabled=false;
}
FString FEdgeWorldUniverseDiagnostics::LogicalAction()const
{
 return Action.StartsWith(TEXT("p1."))?TEXT("s1.")+Action.Mid(3):Action;
}
bool FEdgeWorldUniverseDiagnostics::IsAction(const FString& StandardId)const
{
 return Action==StandardId||(bReadonlyProbeAuthorized&&LogicalAction()==StandardId);
}
void FEdgeWorldUniverseDiagnostics::Invalidate(uint64 NewEpoch)
{
 if(Epoch!=NewEpoch)bIdentityFaulted=false;
 Epoch=NewEpoch;Generation=0;WorkerPid=0;Disarm();LastSpaceInput.Reset();LastRetainInput.Reset();
}
bool FEdgeWorldUniverseDiagnostics::ConfirmVerified(uint64 ActualEpoch,uint32 ActualWorker,uint64 ActualGeneration)
{
 if(!Config.bEnabled||ActualWorker==0||ActualGeneration==0)return false;
 if(Epoch!=ActualEpoch)Invalidate(ActualEpoch);
 if(bIdentityFaulted)return false;
 if(WorkerPid!=0&&(WorkerPid!=ActualWorker||Generation!=ActualGeneration)){Invalidate(ActualEpoch);bIdentityFaulted=true;return false;}
 WorkerPid=ActualWorker;Generation=ActualGeneration;return true;
}
bool FEdgeWorldUniverseDiagnostics::Ready(uint64 ActualEpoch)const
{
 return Config.bEnabled&&!bIdentityFaulted&&Epoch==ActualEpoch&&WorkerPid>0&&Generation>0;
}
TArray<FString> FEdgeWorldUniverseDiagnostics::Stages(const FString& Id)
{
 if(Id.StartsWith(TEXT("p1.")))return Stages(TEXT("s1.")+Id.Mid(3));
 if(Id==TEXT("s1.probe")||Id==TEXT("s2.probe"))return {TEXT("png_and_guard")};
 if(Id==TEXT("s1.camera"))return {TEXT("before"),TEXT("moved"),TEXT("restored")};
 if(Id==TEXT("s1.visibility"))return {TEXT("before"),TEXT("hidden"),TEXT("restored")};
 if(Id==TEXT("s1.framerate"))return {TEXT("before"),TEXT("changed"),TEXT("restored")};
 if(Id==TEXT("s1.pause"))return {TEXT("before"),TEXT("paused"),TEXT("restored")};
 if(Id==TEXT("s1.history_write_rejected"))return {TEXT("space_rejected"),TEXT("retain_rejected"),TEXT("released")};
 if(Id==TEXT("s1.held_input"))return {TEXT("held_history"),TEXT("held_current"),TEXT("released")};
 if(Id==TEXT("s1.final")||Id==TEXT("s2.final"))return {TEXT("released_and_restored")};
 return {};
}
bool FEdgeWorldUniverseDiagnostics::Arm(const FString& Id)
{
 const bool Initial=Config.Session==TEXT("initialize");
 const bool ScopeMatches=Config.Scope==TEXT("readonly-probe")?
  (bReadonlyProbeAuthorized&&Id.StartsWith(TEXT("p1."))):Id.StartsWith(Initial?TEXT("s1."):TEXT("s2."));
 if(!Ready(Epoch)||!Action.IsEmpty()||Stages(Id).IsEmpty()||!ScopeMatches)return false;
 Action=Id;StageIndex=0;bHeldLatestRequested=false;LastSpaceInput.Reset();LastRetainInput.Reset();return true;
}
void FEdgeWorldUniverseDiagnostics::Disarm(){Action.Reset();StageIndex=0;bHeldLatestRequested=false;}
void FEdgeWorldUniverseDiagnostics::RecordInput(bool bSpace,bool bRejected,const FString& Reason)
{
 if(!Config.bEnabled)return;
 uint64& Count=bSpace?SpaceCount:RetainCount;
 if(Count>=9007199254740990ULL){Invalidate(Epoch);Config.bEnabled=false;return;}
 auto E=MakeShared<FJsonObject>();
 E->SetStringField(TEXT("key"),bSpace?TEXT("Space"):TEXT("R"));E->SetStringField(TEXT("event"),TEXT("pressed"));
 E->SetStringField(TEXT("handler"),bSpace?TEXT("SpacePressed"):TEXT("Retain"));E->SetBoolField(TEXT("handled"),true);
 E->SetBoolField(TEXT("rejected"),bRejected);E->SetStringField(TEXT("reason"),Reason);
 E->SetNumberField(TEXT("counter_before"),double(Count));E->SetNumberField(TEXT("counter_after"),double(++Count));
 (bSpace?LastSpaceInput:LastRetainInput)=E;
}
bool FEdgeWorldUniverseDiagnostics::IsNext(const FString& Stage)const
{
 const auto All=Stages(Action);return All.IsValidIndex(StageIndex)&&All[StageIndex]==Stage;
}
FString FEdgeWorldUniverseDiagnostics::Marker(const FString& Stage,const FString& Origin,const TSharedRef<FJsonObject>& Binding,
                                             const TSharedRef<FJsonObject>& Trusted,const TSharedRef<FJsonObject>& Selected,
                                             const TSharedRef<FJsonObject>& State)
{
 if(!Ready(Epoch)||!IsNext(Stage)||EventSerial>=256||!(Origin==TEXT("query")||Origin==TEXT("input")||Origin==TEXT("verified_observation")||Origin==TEXT("release")))return {};
 auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("format"),Config.Scope==TEXT("readonly-probe")?TEXT("universe-i15-probe-readback.v1"):TEXT("universe-i14-readback.v1"));
 V->SetObjectField(TEXT("binding"),Binding);V->SetStringField(TEXT("action_id"),Action);V->SetStringField(TEXT("stage"),Stage);
 V->SetObjectField(TEXT("trusted_head"),Trusted);V->SetObjectField(TEXT("selected_observation"),Selected);V->SetObjectField(TEXT("state"),State);
 V->SetNumberField(TEXT("event_serial"),double(EventSerial+1));V->SetStringField(TEXT("origin"),Origin);
 FString Json;FJsonSerializer::Serialize(V,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
 if(FTCHARToUTF8(*Json).Length()>65536)return {};
 ++EventSerial;++StageIndex;return Json;
}
