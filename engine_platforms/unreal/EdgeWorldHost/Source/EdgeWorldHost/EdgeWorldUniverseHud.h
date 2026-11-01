#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "EdgeWorldUniverseHud.generated.h"
struct FEdgeWorldUniverseSession;
UCLASS()
class EDGEWORLDHOST_API AEdgeWorldUniverseHud : public AHUD
{
 GENERATED_BODY()
public:
 void Present(const FEdgeWorldUniverseSession& State);
 virtual void DrawHUD()override;
private:
 FString Watermarks=TEXT("No verified observation"),Controls=TEXT("Connecting"),Value;
};
