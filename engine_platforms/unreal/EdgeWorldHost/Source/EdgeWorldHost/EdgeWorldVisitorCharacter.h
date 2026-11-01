#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "EdgeWorldVisitorCharacter.generated.h"

class UCameraComponent;

UCLASS()
class EDGEWORLDHOST_API AEdgeWorldVisitorCharacter : public ACharacter
{
	GENERATED_BODY()
public:
	AEdgeWorldVisitorCharacter();
	virtual void Tick(float DeltaSeconds) override;
	bool ReturnToEntry();
	static FVector EntryLocation();
	void LogVisitorStatus() const;
	void TraceMovement(float Seconds);
private:
	UFUNCTION() void OnVisitorHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit);
	UPROPERTY() TObjectPtr<UCameraComponent> VisitorCamera;
	double TraceUntil = 0;
	double NextTrace = 0;
};
