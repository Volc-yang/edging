#include "EdgeWorldUniverseGameMode.h"
#include "EdgeWorldUniverseActor.h"
#include "EdgeWorldUniverseHud.h"
#include "EdgeWorldJsonlClient.h"
#include "EdgeWorldUniverseAssetAudit.h"
#include "Async/Async.h"
#include "Camera/CameraActor.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/DirectionalLight.h"
#include "Components/DirectionalLightComponent.h"
#include "HAL/PlatformMisc.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "InputCoreTypes.h"
#include "Framework/Application/SlateApplication.h"
#if PLATFORM_MAC
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#endif
namespace
{
FString Quote(const FString& S){TSharedRef<FJsonObject> X=MakeShared<FJsonObject>();X->SetStringField(TEXT("x"),S);FString T;FJsonSerializer::Serialize(X,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&T));return T.Mid(5,T.Len()-6);}
FString RequestId(){return TEXT("u-")+FGuid::NewGuid().ToString(EGuidFormats::Digits);}
bool ReadPins(const FString& Path,TArray<uint8>& Out)
{
#if PLATFORM_MAC
 if(FPaths::IsRelative(Path))return false;FTCHARToUTF8 U(*Path),P(*FPaths::GetPath(Path));struct stat Dir,St;
 if(lstat(P.Get(),&Dir)||!S_ISDIR(Dir.st_mode)||(Dir.st_mode&0777)!=0700||Dir.st_uid!=getuid())return false;
 int Fd=open(U.Get(),O_RDONLY|O_NOFOLLOW);if(Fd<0)return false;
 bool OK=fstat(Fd,&St)==0&&S_ISREG(St.st_mode)&&St.st_uid==getuid()&&(St.st_mode&0777)==0600&&St.st_nlink==1&&St.st_size>0&&St.st_size<=16384;
 if(OK){Out.SetNumUninitialized(int32(St.st_size));int64 Done=0;while(Done<St.st_size){ssize_t N=read(Fd,Out.GetData()+Done,St.st_size-Done);if(N<=0){OK=false;break;}Done+=N;}uint8 Extra;if(OK)OK=read(Fd,&Extra,1)==0;}close(Fd);if(!OK)Out.Reset();return OK;
#else
 return false;
#endif
}
}
AEdgeWorldUniverseGameMode::AEdgeWorldUniverseGameMode(){PlayerControllerClass=AEdgeWorldUniverseController::StaticClass();HUDClass=AEdgeWorldUniverseHud::StaticClass();DefaultPawnClass=nullptr;}
AEdgeWorldUniverseGameMode::~AEdgeWorldUniverseGameMode()=default;
void AEdgeWorldUniverseGameMode::StartPlay()
{
 Super::StartPlay();if(!Configure()){Reject(TEXT("trusted public launch pins unavailable"),false);return;}
 if(auto* Light=GetWorld()->SpawnActor<ADirectionalLight>(FVector(0,0,500),FRotator(-45,-35,0))){Light->GetLightComponent()->SetMobility(EComponentMobility::Movable);Light->GetLightComponent()->SetIntensity(10.f);}
 Projection=GetWorld()->SpawnActor<AEdgeWorldUniverseActor>();Camera=GetWorld()->SpawnActor<ACameraActor>(FVector(700,-900,650),FRotator(-25,45,0));
 if(APlayerController* C=GetWorld()->GetFirstPlayerController()){C->SetViewTarget(Camera);C->SetInputMode(FInputModeGameOnly());}
 OpenTransport();RefreshHead();UE_LOG(LogTemp,Display,TEXT("Universe world: 1 weak; 2 strong; Space physical; R retain; [ prior; H latest; UniverseRefresh/UniverseRetry explicit."));
}
void AEdgeWorldUniverseGameMode::EndPlay(const EEndPlayReason::Type Reason){Session.Invalidate();if(Transport)Transport->Shutdown();Transport.Reset();Super::EndPlay(Reason);}
bool AEdgeWorldUniverseGameMode::Configure()
{
 Python=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_PYTHON"));Worker=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_WORKER"));OwnerConfig=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_OWNER_CONFIG"));
 FString PinsPath=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_PINS")),Hash=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_PINS_SHA256"));TArray<uint8> Raw;FString Error;
 TraceDirectory=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_TRACE"));TraceBudget=MakeShared<FEdgeWorldTraceBudget,ESPMode::ThreadSafe>();
 bExplicitInitialize=FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_UNIVERSE_INITIALIZE"))==TEXT("1");
 return !FPaths::IsRelative(Python)&&!FPaths::IsRelative(Worker)&&!FPaths::IsRelative(OwnerConfig)&&FPaths::FileExists(Python)&&FPaths::FileExists(Worker)&&ReadPins(PinsPath,Raw)&&FEdgeWorldUniverseControlParser::PublicPins(Raw,Hash,Pins,Error);
}
void AEdgeWorldUniverseGameMode::OpenTransport()
{
 FEdgeWorldWorkerLaunchConfig C;C.LaunchMode=EEdgeWorldWorkerLaunchMode::Universe;C.PythonExecutable=Python;C.WorkerScript=Worker;C.OwnerConfigPath=OwnerConfig;C.TraceDirectory=TraceDirectory;C.TraceBudget=TraceBudget;C.WorldId=Pins.Context.WorldId;C.RequestTimeoutSeconds=60.;Transport=MakeShared<FEdgeWorldProcessTransport,ESPMode::ThreadSafe>(MoveTemp(C));
}
FString AEdgeWorldUniverseGameMode::BasePayload()const{return TEXT("\"domain\":\"edgeworld.universe.authority\",\"version\":\"0.2\",\"world_id\":")+Quote(Pins.Context.WorldId);}
FEdgeWorldUniverseControlExpectation AEdgeWorldUniverseGameMode::Expectation(const FString& Op,const FString& Id)const
{
 FEdgeWorldUniverseControlExpectation E;E.Pins=Pins;E.RequestId=Id;E.Operation=Op;E.ProposalJson=Session.Proposal;E.IntentJson=Session.Intent;E.ApprovalId=Session.ApprovalId;E.CommandRecordId=Session.CommandRecordId;E.CommandDigest=Session.CommandDigest;return E;
}
void AEdgeWorldUniverseGameMode::SendControl(const FString& Op,const FString& Payload,EUniverseClientPhase Phase)
{
 if(!Transport||Session.bBusy)return;FString Id=RequestId(),Line,Error;if(!FEdgeWorldUniverseControlParser::Request(Op,Id,Payload,Line,Error)){Reject(Error,false);return;}
 auto E=Expectation(Op,Id);auto Token=Session.Begin(Phase);TWeakObjectPtr<AEdgeWorldUniverseGameMode> Weak(this);
 Transport->SendJsonLine({Id,Op,Line},[Weak,Token,E,Op](FEdgeWorldResponse&& R){AsyncTask(ENamedThreads::GameThread,[Weak,Token,E,Op,R=MoveTemp(R)]()mutable{if(Weak.IsValid())Weak->OnControl(Op,Token,E,MoveTemp(R));});});Present();
}
void AEdgeWorldUniverseGameMode::RefreshHead(){SendControl(TEXT("status"),TEXT("{")+BasePayload()+TEXT("}"),EUniverseClientPhase::AwaitStatus);}
void AEdgeWorldUniverseGameMode::ChannelFailed(const FString& Error)
{
 bool Unknown=!Session.PendingPrepare.IsEmpty()||!Session.CommandRecords.IsEmpty();Session.Invalidate();if(Transport)Transport->Shutdown();Transport.Reset();Reject(Error,Unknown);
}
void AEdgeWorldUniverseGameMode::Reject(const FString& Error,bool Unknown)
{
 Session.bBusy=false;Session.bUnknown|=Unknown;Session.Phase=Session.bUnknown?EUniverseClientPhase::Unknown:EUniverseClientPhase::Rejected;UE_LOG(LogTemp,Error,TEXT("Universe rejected: %s; unknown=%d"),*Error,Session.bUnknown);Present();
}
void AEdgeWorldUniverseGameMode::OnControl(const FString& Op,const FUniverseRequestToken& Token,const FEdgeWorldUniverseControlExpectation& E,FEdgeWorldResponse&& R)
{
 if(Token.Epoch!=Session.Epoch||Token.Serial!=Session.Serial||!Session.bBusy)return;
 if(R.WorkerPid==0||!Session.Accept(Token,R.ProcessGeneration)){ChannelFailed(TEXT("worker generation unavailable/changed; explicit reconnect required"));return;}
 FEdgeWorldUniverseControl C;FString Error;
 if(R.RawJsonl.IsEmpty()||!FEdgeWorldUniverseControlParser::Verify(R.RawJsonl,E,C,Error)){ChannelFailed(R.RawJsonl.IsEmpty()?R.ErrorCode:Error);return;}
 if(!C.bSuccess)
 {
  if(Op==TEXT("status")&&Session.CanInitialize(C.ErrorCode,bExplicitInitialize,bInitializeSent))
  {bInitializeSent=true;SendControl(TEXT("initialize"),TEXT("{")+BasePayload()+TEXT(",\"test_profile\":\"composite-rigid-support.v0.2\"}"),EUniverseClientPhase::AwaitStatus);return;}
  bool Unknown=C.CommitStatus!=TEXT("not_attempted")||Session.bUnknown;if(!Unknown&&Op!=TEXT("status"))Session.ClearPending();Reject(C.ErrorCode,Unknown);return;
 }
 if(Op==TEXT("status"))
 {
  Session.Head=C.Head;Session.HeadTick=C.Tick;Session.HeadRevision=C.Revision;Observe(C.Tick,C.Revision);return;
 }
 // Commit/prepare bindings are checked, but only a fresh owned-channel status publishes a trusted HEAD.
 if(Op==TEXT("prepare"))
 {
  Session.CommandRecords=C.CommandRecordsJson;Session.CommandDigest=C.CommandDigest;
  if(!C.CommittedResultJson.IsEmpty()){Session.LastCommandRecords=Session.CommandRecords;Session.LastCommandDigest=Session.CommandDigest;Session.ClearPending();RefreshHead();return;}
  ExecutePrepared();return;
 }
 if(Op==TEXT("advance")||Op==TEXT("initialize")){if(Op==TEXT("advance")){Session.LastCommandRecords=Session.CommandRecords;Session.LastCommandDigest=Session.CommandDigest;}Session.ClearPending();RefreshHead();}
}
void AEdgeWorldUniverseGameMode::Observe(int64 Tick,int64 Revision)
{
 if(Session.bBusy||!Transport)return;FString Id=RequestId(),Line,Error;FString Payload=TEXT("{")+BasePayload()+FString::Printf(TEXT(",\"tick\":%lld,\"revision\":%lld,\"watermark\":%lld}"),(long long)Tick,(long long)Revision,(long long)Revision);
 if(!FEdgeWorldUniverseControlParser::Request(TEXT("observe"),Id,Payload,Line,Error)){Reject(Error,false);return;}
 FEdgeWorldUniverseExpectation E;E.Context=Pins.Context;E.TrustedHead=Session.Head;E.RequestId=Id;E.Tick=Tick;E.Revision=Revision;E.Watermark=Revision;auto Token=Session.Begin(EUniverseClientPhase::AwaitObserve);TWeakObjectPtr<AEdgeWorldUniverseGameMode> Weak(this);
 Transport->SendJsonLine({Id,TEXT("observe"),Line},[Weak,Token,E](FEdgeWorldResponse&& R){AsyncTask(ENamedThreads::GameThread,[Weak,Token,E,R=MoveTemp(R)]()mutable
 {
  if(!Weak.IsValid()||Token.Epoch!=Weak->Session.Epoch||Token.Serial!=Weak->Session.Serial||!Weak->Session.bBusy)return;
  if(R.WorkerPid==0||!Weak->Session.Accept(Token,R.ProcessGeneration)){Weak->ChannelFailed(TEXT("observe channel changed"));return;}
  FEdgeWorldUniverseObservation O;FString Error;
  if(!FEdgeWorldUniverseObservationParser::Verify(R.RawJsonl,E,O,Error)||!Weak->ValidateAssets(O,Error)){Weak->Reject(Error,false);return;}
  Weak->Session.Observation=O;Weak->Session.bHasObservation=true;Weak->Session.bAssetsValidated=true;Weak->Session.bHistory=O.Manifest!=Weak->Session.Head.Head;Weak->Session.ClassifyView();
  if(Weak->Projection&&!Weak->Projection->ApplyVerified(O,Error)){Weak->Session.bAssetsValidated=false;Weak->Reject(Error,false);return;}
  if(Weak->Projection)Weak->Session.DerivedInstances=Weak->Projection->GetDerivedInstanceCount();
  Weak->Present();UE_LOG(LogTemp,Display,TEXT("Universe world %s observed tick %lld, revision %lld"),*O.WorldId,(long long)O.Tick,(long long)O.Revision);
 });});Present();
}
bool AEdgeWorldUniverseGameMode::ValidateAssets(const FEdgeWorldUniverseObservation& O,FString& Error)
{
#if WITH_EDITOR
 Error=TEXT("installed asset graph mismatch");FEdgeWorldUniverseAssetAuditResult A;if(!FEdgeWorldUniverseAssetAudit::Collect(O.WorldId,A,Error)||!A.bResolved||A.GapCount!=0||O.AssetDependencyStatus!=TEXT("runtime-resolved"))return false;
 for(const auto& R:O.SelectedRecords)if(R.Kind==TEXT("asset_manifest"))return R.Id==TEXT("asset-manifest-runtime")&&R.Digest==A.CandidateDigest&&R.CanonicalJson==A.CandidateJson;
#endif
 Error=TEXT("installed asset graph mismatch or unsupported non-editor path");return false;
}
void AEdgeWorldUniverseGameMode::Prepare(const FString& Action)
{
 if(!Session.CanWrite())return;FString Id=TEXT("c-")+FGuid::NewGuid().ToString(EGuidFormats::Digits),Payload,Error;
 if(!FEdgeWorldUniverseControlParser::BuildPrepare(Pins,Session.Observation,Id,Action,Session.SelectedCase,Payload,Session.Proposal,Session.Intent,Error)){Reject(Error,false);return;}
 Session.ApprovalId=TEXT("approval-")+Id;Session.CommandRecordId=TEXT("record-")+Id;Session.PendingPrepare=Payload;SendControl(TEXT("prepare"),Payload,EUniverseClientPhase::Preparing);
}
void AEdgeWorldUniverseGameMode::ExecutePrepared()
{
 FString P=TEXT("{")+BasePayload()+TEXT(",\"principal\":")+Quote(Pins.Principal)+TEXT(",\"command_records\":")+Session.CommandRecords+TEXT(",\"command_digest\":")+Quote(Session.CommandDigest)+TEXT("}");SendControl(TEXT("advance"),P,EUniverseClientPhase::Advancing);
}
void AEdgeWorldUniverseGameMode::Advance(){Prepare(TEXT("physics_step"));}
void AEdgeWorldUniverseGameMode::RetryLastCommitted()
{
 if(!Session.CanRetryLast())return;
 Session.CommandRecords=Session.LastCommandRecords;Session.CommandDigest=Session.LastCommandDigest;ExecutePrepared();
}
void AEdgeWorldUniverseGameMode::ObserveExact(int64 Tick,int64 Revision,int64 Watermark)
{
 if(!Session.CanSelectExact(Tick,Revision,Watermark))return;Observe(Tick,Revision);
}
void AEdgeWorldUniverseGameMode::ProjectionVisible(bool Visible){if(Projection)Projection->SetProjectionVisible(Visible);}
void AEdgeWorldUniverseGameMode::SelectCase(const FString& C){if(C==TEXT("weak")||C==TEXT("strong"))Session.SelectedCase=C;Present();}
void AEdgeWorldUniverseGameMode::SpacePressed(){if(Session.SpacePressed())Advance();}
void AEdgeWorldUniverseGameMode::Retain(){Prepare(TEXT("retain_snapshot"));}
void AEdgeWorldUniverseGameMode::Previous(){if(!Session.bBusy&&Session.bHasObservation&&Session.Observation.PriorSelection.IsSet()){auto P=Session.Observation.PriorSelection.GetValue();Observe(P.X,P.Y);}}
void AEdgeWorldUniverseGameMode::Latest(){if(!Session.bBusy&&!Session.Head.Head.IsEmpty())Observe(Session.HeadTick,Session.HeadRevision);}
void AEdgeWorldUniverseGameMode::Reconnect(){if(Session.bBusy)return;Session.Invalidate();if(Transport)Transport->Shutdown();OpenTransport();RefreshHead();}
void AEdgeWorldUniverseGameMode::RetryExact()
{
 if(Session.bBusy||Session.bHistory||!Session.bUnknown||!Session.bHasObservation||Session.Generation==0||Session.Head.StorageState!=TEXT("ready"))return;
 if(!Session.CommandRecords.IsEmpty())ExecutePrepared();else if(!Session.PendingPrepare.IsEmpty())SendControl(TEXT("prepare"),Session.PendingPrepare,EUniverseClientPhase::Preparing);
}
void AEdgeWorldUniverseGameMode::Present(){if(APlayerController* C=GetWorld()?GetWorld()->GetFirstPlayerController():nullptr)if(auto* H=Cast<AEdgeWorldUniverseHud>(C->GetHUD()))H->Present(Session);}
void AEdgeWorldUniverseGameMode::MoveCamera(const FVector& Offset,const FRotator& Turn){if(Camera){Camera->AddActorWorldRotation(Turn);Camera->AddActorWorldOffset(Camera->GetActorRotation().RotateVector(Offset));}}
AEdgeWorldUniverseController::AEdgeWorldUniverseController(){bAutoManageActiveCameraTarget=false;}
AEdgeWorldUniverseGameMode* AEdgeWorldUniverseController::Mode()const{return GetWorld()?Cast<AEdgeWorldUniverseGameMode>(GetWorld()->GetAuthGameMode()):nullptr;}
void AEdgeWorldUniverseController::Weak(){if(auto* M=Mode())M->SelectCase(TEXT("weak"));}void AEdgeWorldUniverseController::Strong(){if(auto* M=Mode())M->SelectCase(TEXT("strong"));}
void AEdgeWorldUniverseController::Advance(){if(auto* M=Mode())M->SpacePressed();}void AEdgeWorldUniverseController::Release(){if(auto* M=Mode())M->SpaceReleased();}void AEdgeWorldUniverseController::Retain(){if(auto* M=Mode())M->Retain();}
void AEdgeWorldUniverseController::Previous(){if(auto* M=Mode())M->Previous();}void AEdgeWorldUniverseController::Latest(){if(auto* M=Mode())M->Latest();}void AEdgeWorldUniverseController::UniverseRetry(){if(auto* M=Mode())M->RetryExact();}void AEdgeWorldUniverseController::UniverseRefresh(){if(auto* M=Mode())M->Reconnect();}
void AEdgeWorldUniverseController::UniverseRetryLastCommitted(){if(auto* M=Mode())M->RetryLastCommitted();}
void AEdgeWorldUniverseController::UniverseObserveExact(int64 Tick,int64 Revision,int64 Watermark){if(auto* M=Mode())M->ObserveExact(Tick,Revision,Watermark);}
void AEdgeWorldUniverseController::UniverseRetain(){if(auto* M=Mode())M->Retain();}
void AEdgeWorldUniverseController::UniverseAdvance(){if(auto* M=Mode())M->Advance();}
void AEdgeWorldUniverseController::UniverseProjectionVisible(bool Visible){if(auto* M=Mode())M->ProjectionVisible(Visible);}
void AEdgeWorldUniverseController::UniverseCamera(float Yaw,float Pitch){if(FMath::IsFinite(Yaw)&&FMath::IsFinite(Pitch)&&FMath::Abs(Yaw)<=360&&FMath::Abs(Pitch)<=90)if(auto* M=Mode())M->MoveCamera(FVector::ZeroVector,FRotator(Pitch,Yaw,0));}
void AEdgeWorldUniverseController::SetupInputComponent()
{
 Super::SetupInputComponent();InputComponent->BindKey(EKeys::One,IE_Pressed,this,&AEdgeWorldUniverseController::Weak);InputComponent->BindKey(EKeys::Two,IE_Pressed,this,&AEdgeWorldUniverseController::Strong);InputComponent->BindKey(EKeys::SpaceBar,IE_Pressed,this,&AEdgeWorldUniverseController::Advance);InputComponent->BindKey(EKeys::SpaceBar,IE_Released,this,&AEdgeWorldUniverseController::Release);InputComponent->BindKey(EKeys::R,IE_Pressed,this,&AEdgeWorldUniverseController::Retain);InputComponent->BindKey(EKeys::LeftBracket,IE_Pressed,this,&AEdgeWorldUniverseController::Previous);InputComponent->BindKey(EKeys::H,IE_Pressed,this,&AEdgeWorldUniverseController::Latest);
}
void AEdgeWorldUniverseController::PlayerTick(float Delta)
{
 Super::PlayerTick(Delta);auto* M=Mode();if(!M||!IsLocalController())return;
 if(FSlateApplication::IsInitialized()&&!FSlateApplication::Get().IsActive()){M->FocusLost();return;}
 if(M->FocusNeedsRelease()){if(!IsInputKeyDown(EKeys::SpaceBar))M->ResumeReleased();return;}
 if(!IsInputKeyDown(EKeys::SpaceBar))M->SpaceReleased();
 FVector Move(float(IsInputKeyDown(EKeys::W))-float(IsInputKeyDown(EKeys::S)),float(IsInputKeyDown(EKeys::D))-float(IsInputKeyDown(EKeys::A)),float(IsInputKeyDown(EKeys::E))-float(IsInputKeyDown(EKeys::Q)));
 FRotator Turn((float(IsInputKeyDown(EKeys::Up))-float(IsInputKeyDown(EKeys::Down)))*60*Delta,(float(IsInputKeyDown(EKeys::Right))-float(IsInputKeyDown(EKeys::Left)))*60*Delta,0);M->MoveCamera(Move*500*Delta,Turn);
}
