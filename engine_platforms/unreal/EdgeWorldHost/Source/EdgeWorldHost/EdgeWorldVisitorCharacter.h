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
private:
	UPROPERTY() TObjectPtr<UCameraComponent> VisitorCamera;
};
