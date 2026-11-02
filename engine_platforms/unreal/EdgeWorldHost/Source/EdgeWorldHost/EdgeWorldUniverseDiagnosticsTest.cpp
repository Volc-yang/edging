#include "EdgeWorldUniverseDiagnostics.h"
#include "Misc/AutomationTest.h"
#include "HAL/PlatformProcess.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "GameFramework/WorldSettings.h"
#include "GameFramework/PlayerState.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/JsonSerializer.h"

#if WITH_DEV_AUTOMATION_TESTS
namespace
{
FEdgeWorldUniverseDiagnostics SyntheticDiagnostics()
{
 FEdgeWorldUniverseDiagnostics D;
 D.Config=FEdgeWorldUniverseDiagnosticConfig::Parse(TEXT("1"),TEXT("synthetic-native-only"),FString::ChrN(40,'a'),TEXT("initialize"));
 D.ConfirmVerified(1,123,1);return D;
}
TSharedRef<FJsonObject> SyntheticHead()
{
 auto H=MakeShared<FJsonObject>();H->SetNumberField(TEXT("tick"),1);H->SetNumberField(TEXT("revision"),2);H->SetNumberField(TEXT("watermark"),2);return H;
}
TSharedRef<FJsonObject> SyntheticBinding()
{
 auto B=MakeShared<FJsonObject>();B->SetStringField(TEXT("run_id"),TEXT("synthetic-native-only"));
 B->SetNumberField(TEXT("host_pid"),FPlatformProcess::GetCurrentProcessId());B->SetNumberField(TEXT("worker_pid"),123);
 B->SetStringField(TEXT("source_sha"),FString::ChrN(40,'a'));B->SetStringField(TEXT("session"),TEXT("initialize"));
 B->SetStringField(TEXT("world_id"),TEXT("synthetic"));B->SetStringField(TEXT("authority_root"),TEXT("/synthetic"));B->SetNumberField(TEXT("generation"),1);return B;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUniverseDiagnosticsIdentityTest,"edgeWorld.UniverseHost.Diagnostics.IdentityAndDefaultOff",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FUniverseDiagnosticsIdentityTest::RunTest(const FString& Parameters)
{
 FEdgeWorldUniverseDiagnostics Off;
 TestFalse(TEXT("default disabled"),Off.Config.bEnabled);TestFalse(TEXT("no default identity"),Off.ConfirmVerified(1,123,1));
 TestFalse(TEXT("no default arm"),Off.Arm(TEXT("s1.pause")));
 TestFalse(TEXT("bad source disables"),FEdgeWorldUniverseDiagnosticConfig::Parse(TEXT("1"),TEXT("run"),TEXT("HEAD"),TEXT("initialize")).bEnabled);
 TestFalse(TEXT("bad session disables"),FEdgeWorldUniverseDiagnosticConfig::Parse(TEXT("1"),TEXT("run"),FString::ChrN(40,'a'),TEXT("repair")).bEnabled);
 TestFalse(TEXT("enable must be exact"),FEdgeWorldUniverseDiagnosticConfig::Parse(TEXT("true"),TEXT("run"),FString::ChrN(40,'a'),TEXT("initialize")).bEnabled);
 auto D=SyntheticDiagnostics();TestTrue(TEXT("accepted callback identity"),D.Ready(1));TestFalse(TEXT("wrong epoch"),D.Ready(2));
 TestFalse(TEXT("different worker rejected"),D.ConfirmVerified(1,124,1));TestFalse(TEXT("same epoch stays faulted"),D.ConfirmVerified(1,124,1));
 D.Invalidate(2);TestFalse(TEXT("invalidate removes ready"),D.Ready(2));
 TestTrue(TEXT("new epoch verified callback rebinds"),D.ConfirmVerified(2,124,1));
 TestFalse(TEXT("wrong session action"),D.Arm(TEXT("s2.pause")));TestFalse(TEXT("unknown stage/action"),D.Arm(TEXT("arbitrary")));
 return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUniverseDiagnosticsInputTest,"edgeWorld.UniverseHost.Diagnostics.HandledInputAndOrder",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FUniverseDiagnosticsInputTest::RunTest(const FString& Parameters)
{
 auto D=SyntheticDiagnostics();TestTrue(TEXT("arm actual history observer"),D.Arm(TEXT("s1.history_write_rejected")));
 TestEqual(TEXT("arm/query do not invent Space event"),D.SpaceCount,uint64(0));TestFalse(TEXT("no synthetic input from arm"),D.LastSpaceInput.IsValid());
 D.RecordInput(true,true,TEXT("history_read_only"));
 TestEqual(TEXT("actual handler count increments"),D.SpaceCount,uint64(1));TestTrue(TEXT("actual event handled"),D.LastSpaceInput->GetBoolField(TEXT("handled")));
 TestTrue(TEXT("actual event rejected"),D.LastSpaceInput->GetBoolField(TEXT("rejected")));TestEqual(TEXT("actual reason preserved"),D.LastSpaceInput->GetStringField(TEXT("reason")),FString(TEXT("history_read_only")));
 auto State=MakeShared<FJsonObject>();
 TestTrue(TEXT("wrong stage cannot manufacture marker"),D.Marker(TEXT("retain_rejected"),TEXT("release"),SyntheticBinding(),SyntheticHead(),SyntheticHead(),State).IsEmpty());
 TestFalse(TEXT("ordered real event can serialize"),D.Marker(TEXT("space_rejected"),TEXT("release"),SyntheticBinding(),SyntheticHead(),SyntheticHead(),State).IsEmpty());
 TestTrue(TEXT("stage cannot replay"),D.Marker(TEXT("space_rejected"),TEXT("release"),SyntheticBinding(),SyntheticHead(),SyntheticHead(),State).IsEmpty());
 D.RecordInput(false,true,TEXT("busy"));TestEqual(TEXT("other rejection not relabeled history"),D.LastRetainInput->GetStringField(TEXT("reason")),FString(TEXT("busy")));
 D.Disarm();D.Arm(TEXT("s1.held_input"));TestFalse(TEXT("no H transition manufactured"),D.bHeldLatestRequested);
 TestTrue(TEXT("early release cannot skip held stages"),D.Marker(TEXT("released"),TEXT("release"),SyntheticBinding(),SyntheticHead(),SyntheticHead(),State).IsEmpty());
 return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUniverseReadonlyProbeScopeTest,"edgeWorld.UniverseHost.Diagnostics.ReadonlyProbeScope",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FUniverseReadonlyProbeScopeTest::RunTest(const FString& Parameters)
{
 auto Existing=[](){FEdgeWorldUniverseDiagnostics D;D.Config=FEdgeWorldUniverseDiagnosticConfig::Parse(TEXT("1"),TEXT("synthetic-probe-only"),FString::ChrN(40,'a'),TEXT("existing"),TEXT("readonly-probe"));D.ConfirmVerified(1,123,1);return D;};
 auto NoPins=Existing();TestFalse(TEXT("probe not armed without validated empty grants"),NoPins.Arm(TEXT("p1.camera")));
 auto Writes=Existing();Writes.AuthorizeReadonlyProbe(false,false);TestFalse(TEXT("nonempty grants disable probe"),Writes.Arm(TEXT("p1.camera")));
 auto Init=Existing();Init.AuthorizeReadonlyProbe(true,true);TestFalse(TEXT("initialize flag disables probe"),Init.Arm(TEXT("p1.camera")));
 TestFalse(TEXT("initialize session cannot request scope"),FEdgeWorldUniverseDiagnosticConfig::Parse(TEXT("1"),TEXT("run"),FString::ChrN(40,'a'),TEXT("initialize"),TEXT("readonly-probe")).bEnabled);
 auto D=Existing();D.AuthorizeReadonlyProbe(false,true);TestTrue(TEXT("actual existing empty grants permit alias"),D.Arm(TEXT("p1.camera")));
 TestTrue(TEXT("alias maps readonly getter only"),D.IsAction(TEXT("s1.camera")));TestEqual(TEXT("original session remains existing"),D.Config.Session,FString(TEXT("existing")));
 D.Disarm();TestFalse(TEXT("standard names not smuggled into probe"),D.Arm(TEXT("s1.camera")));
 auto Standard=SyntheticDiagnostics();TestFalse(TEXT("default scope never permits p1"),Standard.Arm(TEXT("p1.camera")));
 return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUniverseDiagnosticsPauseTest,"edgeWorld.UniverseHost.Diagnostics.PauseReadWithoutTick",
 EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FUniverseDiagnosticsPauseTest::RunTest(const FString& Parameters)
{
 // Synthetic local world only: no GameMode/transport/StartPlay/solver and no Tick call.
 if(!GEngine){AddError(TEXT("engine required for world-context query"));return false;}
 UWorld::InitializationValues IV;
 IV.AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
 UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,false,ERHIFeatureLevel::Num,&IV);
 if(!World){AddError(TEXT("synthetic world allocation failed"));return false;}
 AWorldSettings* Settings=World->GetWorldSettings();APlayerState* Pauser=World->SpawnActor<APlayerState>();
 if(!Settings||!Pauser){World->DestroyWorld(false);AddError(TEXT("synthetic pause fixtures unavailable"));return false;}
 auto D=SyntheticDiagnostics();D.Arm(TEXT("s1.pause"));
 const TArray<FString> Stages={TEXT("before"),TEXT("paused"),TEXT("restored")};
 for(int32 I=0;I<3;++I)
 {
  Settings->SetPauserPlayerState(I==1?Pauser:nullptr);
  const bool Actual=UGameplayStatics::IsGamePaused(World);TestEqual(TEXT("actual pause query without Tick"),Actual,I==1);
  auto State=MakeShared<FJsonObject>();State->SetBoolField(TEXT("paused"),Actual);
  const FString Marker=D.Marker(Stages[I],TEXT("query"),SyntheticBinding(),SyntheticHead(),SyntheticHead(),State);
  TestFalse(TEXT("synchronous query marker without Tick"),Marker.IsEmpty());
 }
 World->DestroyWorld(false);return true;
}
#endif
