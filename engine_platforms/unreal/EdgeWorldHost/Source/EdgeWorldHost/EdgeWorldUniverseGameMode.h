#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "EdgeWorldUniverseObservation.h"
#include "EdgeWorldUniverseGameMode.generated.h"

class FEdgeWorldProcessTransport;
class AEdgeWorldUniverseActor;
class ACameraActor;
struct FEdgeWorldResponse;
struct FEdgeWorldTraceBudget;

enum class EUniverseClientPhase { Stopped, AwaitStatus, AwaitObserve, Latest, History, Preparing, Advancing, Unknown, ReadOnly, Rejected };
struct FUniverseRequestToken { uint64 Epoch=0, Serial=0, Generation=0; };
/** No world/transport access: deterministic gate exercised by protocol tests. */
struct FEdgeWorldUniverseSession
{
 uint64 Epoch=1, Serial=0, Generation=0;
 bool bBusy=false, bUnknown=false, bHistory=false, bHasObservation=false, bAssetsValidated=false, bSpaceHeld=false, bFocusNeedsRelease=false;
 EUniverseClientPhase Phase=EUniverseClientPhase::Stopped;
 FEdgeWorldUniverseHeadBinding Head;
 int64 HeadTick=0, HeadRevision=0;
 int32 DerivedInstances=0;
 FString LastCommandRecords,LastCommandDigest;
 FString SelectedCase=TEXT("weak"), PendingPrepare, Proposal, Intent, ApprovalId, CommandRecordId, CommandRecords, CommandDigest;
 FEdgeWorldUniverseObservation Observation;
 FUniverseRequestToken Begin(EUniverseClientPhase P) { bBusy=true;Phase=P;return {Epoch,++Serial,Generation}; }
 bool Accept(const FUniverseRequestToken& T,uint64 ProcessGeneration)
 {
  if(T.Epoch!=Epoch||T.Serial!=Serial||!bBusy)return false;
  if(ProcessGeneration==0||(T.Generation!=0&&T.Generation!=ProcessGeneration))return false;
  Generation=ProcessGeneration;bBusy=false;return true;
 }
 bool CanWrite() const { return !bFocusNeedsRelease&&!bBusy&&!bUnknown&&!bHistory&&bHasObservation&&bAssetsValidated&&Phase==EUniverseClientPhase::Latest&&Head.StorageState==TEXT("ready")&&Observation.Manifest==Head.Head; }
 bool CanRetryLast()const{return CanWrite()&&!LastCommandRecords.IsEmpty()&&!LastCommandDigest.IsEmpty();}
 bool CanSelectExact(int64 Tick,int64 Revision,int64 Watermark)const{return !bBusy&&!Head.Head.IsEmpty()&&Tick>=0&&Revision>=0&&Watermark==Revision&&Tick<=HeadTick&&Revision<=HeadRevision&&Revision<=9007199254740991LL;}
 bool SpacePressed(){if(bFocusNeedsRelease||bSpaceHeld)return false;bSpaceHeld=true;return CanWrite();}
 void SpaceReleased(){bSpaceHeld=false;}
 void FocusLost(){bFocusNeedsRelease=true;bSpaceHeld=true;}
 void ResumeReleased(){bFocusNeedsRelease=false;bSpaceHeld=false;}
 void Invalidate(){++Epoch;++Serial;Generation=0;bBusy=false;bHasObservation=false;bAssetsValidated=false;bSpaceHeld=true;Phase=EUniverseClientPhase::Stopped;}
 void ClearPending(){PendingPrepare.Reset();Proposal.Reset();Intent.Reset();ApprovalId.Reset();CommandRecordId.Reset();CommandRecords.Reset();CommandDigest.Reset();bUnknown=false;}
 void ClassifyView(){Phase=bUnknown?EUniverseClientPhase::Unknown:Head.StorageState!=TEXT("ready")?EUniverseClientPhase::ReadOnly:bHistory?EUniverseClientPhase::History:EUniverseClientPhase::Latest;}
};

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldUniverseGameMode : public AGameModeBase
{
 GENERATED_BODY()
public:
 AEdgeWorldUniverseGameMode();
 virtual ~AEdgeWorldUniverseGameMode() override;
 virtual void StartPlay() override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 void SelectCase(const FString& Case);
 void SpacePressed();
 void SpaceReleased(){Session.SpaceReleased();}
 void FocusLost(){Session.FocusLost();}
 bool FocusNeedsRelease()const{return Session.bFocusNeedsRelease;}
 void ResumeReleased(){Session.ResumeReleased();}
 void Retain();
 void Advance();
 void RetryLastCommitted();
 void ObserveExact(int64 Tick,int64 Revision,int64 Watermark);
 void ProjectionVisible(bool Visible);
 void Previous();
 void Latest();
 void Reconnect();
 void RetryExact();
 void MoveCamera(const FVector& Offset,const FRotator& Turn);
 const FEdgeWorldUniverseSession& View()const{return Session;}
private:
 bool Configure();
 void OpenTransport();
 void RefreshHead();
 void Observe(int64 Tick,int64 Revision);
 void Prepare(const FString& Action);
 void ExecutePrepared();
 void SendControl(const FString& Op,const FString& Payload,EUniverseClientPhase Phase);
 void OnControl(const FString& Op,const FUniverseRequestToken& Token,const FEdgeWorldUniverseControlExpectation& Expected,FEdgeWorldResponse&& Response);
 void Reject(const FString& Error,bool Unknown);
 void ChannelFailed(const FString& Error);
 void Present();
 bool ValidateAssets(const FEdgeWorldUniverseObservation& Observation,FString& Error);
 FEdgeWorldUniverseControlExpectation Expectation(const FString& Op,const FString& RequestId)const;
 FString BasePayload()const;
 FEdgeWorldUniversePublicPins Pins;
 FEdgeWorldUniverseSession Session;
 FString Python,Worker,OwnerConfig,TraceDirectory;
 TSharedPtr<FEdgeWorldTraceBudget,ESPMode::ThreadSafe> TraceBudget;
 bool bExplicitInitialize=false, bInitializeSent=false;
 TSharedPtr<FEdgeWorldProcessTransport,ESPMode::ThreadSafe> Transport;
 UPROPERTY() TObjectPtr<AEdgeWorldUniverseActor> Projection;
 UPROPERTY() TObjectPtr<ACameraActor> Camera;
};

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldUniverseController : public APlayerController
{
 GENERATED_BODY()
public:
 AEdgeWorldUniverseController();
 virtual void SetupInputComponent()override;
 virtual void PlayerTick(float Delta)override;
 UFUNCTION(Exec) void UniverseRetry();
 UFUNCTION(Exec) void UniverseRefresh();
 UFUNCTION(Exec) void UniverseRetryLastCommitted();
 UFUNCTION(Exec) void UniverseObserveExact(int64 Tick,int64 Revision,int64 Watermark);
 UFUNCTION(Exec) void UniverseRetain();
 UFUNCTION(Exec) void UniverseAdvance();
 UFUNCTION(Exec) void UniverseProjectionVisible(bool Visible=true);
 UFUNCTION(Exec) void UniverseCamera(float Yaw=0,float Pitch=0);
private:
 AEdgeWorldUniverseGameMode* Mode()const;
 void Weak();void Strong();void Advance();void Release();void Retain();void Previous();void Latest();
};
