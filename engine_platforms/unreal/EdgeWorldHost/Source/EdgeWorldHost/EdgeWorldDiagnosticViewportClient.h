#pragma once

#include "Engine/GameViewportClient.h"
#include "EdgeWorldDiagnosticViewportClient.generated.h"

class SWindow;

void EdgeWorldPreflushViewportRenderWork(bool bEnabled);

UCLASS()
class UEdgeWorldDiagnosticViewportClient : public UGameViewportClient
{
	GENERATED_BODY()

public:
	virtual void Init(FWorldContext& WorldContext, UGameInstance* OwningGameInstance,
		bool bCreateNewAudioDevice = true) override;
	virtual void BeginDestroy() override;

private:
	void OnWindowBeingDestroyed(const SWindow& Window);
	FDelegateHandle WindowDestroyHandle;
	bool bPreflushEnabled = false;
};
