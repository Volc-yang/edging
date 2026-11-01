#include "EdgeWorldDiagnosticViewportClient.h"

#include "Framework/Application/SlateApplication.h"
#include "HAL/PlatformTime.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "RenderingThread.h"
#include "Widgets/SWindow.h"

void EdgeWorldPreflushViewportRenderWork(bool bEnabled)
{
	if (bEnabled) FlushRenderingCommands();
}

void UEdgeWorldDiagnosticViewportClient::Init(FWorldContext& WorldContext,
	UGameInstance* OwningGameInstance, bool bCreateNewAudioDevice)
{
	UnregisterWindowDestroyDelegate();
	Super::Init(WorldContext, OwningGameInstance, bCreateNewAudioDevice);
	bPreflushEnabled = FParse::Param(FCommandLine::Get(), TEXT("EWDiagPreflushViewport"));
	if (FSlateApplication::IsInitialized())
	{
		WindowDestroyHandle = FSlateApplication::Get().OnWindowBeingDestroyed().AddUObject(
			this, &UEdgeWorldDiagnosticViewportClient::OnWindowBeingDestroyed);
		UE_LOG(LogTemp, Display, TEXT("H1e viewport adapter registered: preflush=%d threaded_rendering=%d"),
			bPreflushEnabled, GIsThreadedRendering);
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("H1e viewport adapter unavailable: Slate not initialized"));
	}
}

void UEdgeWorldDiagnosticViewportClient::OnWindowBeingDestroyed(const SWindow& Window)
{
	const TSharedPtr<SWindow> GameWindow = GetWindow();
	if (!GameWindow.IsValid() || GameWindow.Get() != &Window) return;
	if (!IsInGameThread())
	{
		UE_LOG(LogTemp, Error, TEXT("H1e viewport notification rejected: not GameThread"));
		return;
	}
	FSceneViewport* const Owner = GetGameViewport();
	UE_LOG(LogTemp, Display, TEXT("H1e game window before owner release: preflush=%d threaded_rendering=%d owner=%p window=%p game_thread=1"),
		bPreflushEnabled, GIsThreadedRendering, static_cast<void*>(Owner), static_cast<const void*>(&Window));
	if (bPreflushEnabled)
	{
		const double Started = FPlatformTime::Seconds();
		UE_LOG(LogTemp, Display, TEXT("H1e preflush begin: owner=%p"), static_cast<void*>(Owner));
		EdgeWorldPreflushViewportRenderWork(true);
		UE_LOG(LogTemp, Display, TEXT("H1e preflush end: owner=%p owner_unchanged=%d elapsed_ms=%.3f"),
			static_cast<void*>(GetGameViewport()), Owner == GetGameViewport(),
			(FPlatformTime::Seconds() - Started) * 1000.0);
	}
}

void UEdgeWorldDiagnosticViewportClient::UnregisterWindowDestroyDelegate()
{
	if (WindowDestroyHandle.IsValid() && FSlateApplication::IsInitialized())
		FSlateApplication::Get().OnWindowBeingDestroyed().Remove(WindowDestroyHandle);
	WindowDestroyHandle.Reset();
}

void UEdgeWorldDiagnosticViewportClient::BeginDestroy()
{
	UnregisterWindowDestroyDelegate();
	Super::BeginDestroy();
}
