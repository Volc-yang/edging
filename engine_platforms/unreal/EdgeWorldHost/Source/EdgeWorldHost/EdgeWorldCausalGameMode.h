#pragma once

#include "CoreMinimal.h"
#include "EdgeWorldCausalObservation.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "EdgeWorldCausalGameMode.generated.h"

class ACameraActor;
class AEdgeWorldCausalActor;
class FEdgeWorldJsonlClient;
class FEdgeWorldProcessTransport;
struct FEdgeWorldResponse;

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldCausalGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	AEdgeWorldCausalGameMode();
	virtual ~AEdgeWorldCausalGameMode() override;
	virtual void StartPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	void AdvanceOneTick();
	void RefreshHead();
	void ObserveHistory(int64 Tick);
	void ObserveLatest();
	void MoveCamera(const FVector& LocalOffset, const FRotator& RotationDelta);
private:
	void StartWorker();
	void ObserveAt(int64 Tick);
	void OnHead(FEdgeWorldResponse&& Response, bool bAdvance, int64 ExpectedTick, int64 ExpectedRevision);
	UPROPERTY() TObjectPtr<AEdgeWorldCausalActor> CausalActor;
	UPROPERTY() TObjectPtr<ACameraActor> Camera;
	TSharedPtr<FEdgeWorldProcessTransport, ESPMode::ThreadSafe> Transport;
	TSharedPtr<FEdgeWorldJsonlClient> Client;
	FString WorldId = TEXT("stg-demo");
	FEdgeWorldCausalHeadGate HeadGate;
	bool bRequestInFlight = false;
};

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldCausalPlayerController : public APlayerController
{
	GENERATED_BODY()
public:
	virtual void SetupInputComponent() override;
private:
	void Advance();
	void History0();
	void History1();
	void History2();
	void Latest();
	void Refresh();
	void Forward();
	void Backward();
	void Left();
	void Right();
	void Up();
	void Down();
	void TurnLeft();
	void TurnRight();
	void LookUp();
	void LookDown();
	AEdgeWorldCausalGameMode* Mode() const;
};
