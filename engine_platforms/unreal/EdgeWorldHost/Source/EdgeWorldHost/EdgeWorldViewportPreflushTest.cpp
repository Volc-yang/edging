#include "EdgeWorldDiagnosticViewportClient.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "HAL/Event.h"
#include "HAL/PlatformProcess.h"
#include "Misc/AutomationTest.h"
#include "RenderingThread.h"
#include "Templates/Atomic.h"

namespace
{
	struct FViewportLifetimeProbe
	{
		TAtomic<bool>& Destroyed;
		TAtomic<bool>& DestroyedOnGameThread;

		~FViewportLifetimeProbe()
		{
			DestroyedOnGameThread.Store(IsInGameThread());
			Destroyed.Store(true);
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldViewportPreflushLifetimeTest,
	"edgeWorld.ViewportPreflush.DrainBeforeGameThreadOwnerRelease",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FEdgeWorldViewportPreflushLifetimeTest::RunTest(const FString& Parameters)
{
	if (!GIsThreadedRendering)
	{
		AddError(TEXT("This lifetime test requires the default rendering thread."));
		return false;
	}
	TAtomic<bool> Destroyed(false);
	TAtomic<bool> DestroyedOnGameThread(false);
	TAtomic<bool> RenderReferenceReleased(false);
	TSharedPtr<FViewportLifetimeProbe, ESPMode::ThreadSafe> GameOwner =
		MakeShared<FViewportLifetimeProbe, ESPMode::ThreadSafe>(Destroyed, DestroyedOnGameThread);
	FEvent* Started = FPlatformProcess::GetSynchEventFromPool(true);
	FEvent* Release = FPlatformProcess::GetSynchEventFromPool(true);
	ENQUEUE_RENDER_COMMAND(EdgeWorldRetainViewportProbe)(
		[RenderOwner = GameOwner, Started, Release, &RenderReferenceReleased](FRHICommandListImmediate&) mutable
		{
			Started->Trigger();
			Release->Wait();
			RenderOwner.Reset();
			RenderReferenceReleased.Store(true);
		});
	const bool bStarted = Started->Wait(5000);
	TestTrue(TEXT("The rendering thread holds its reference"), bStarted);
	EdgeWorldPreflushViewportRenderWork(false);
	TestFalse(TEXT("Disabled arm does not drain queued work"), RenderReferenceReleased.Load());
	TestFalse(TEXT("The game-thread owner keeps the object alive"), Destroyed.Load());
	Release->Trigger();
	EdgeWorldPreflushViewportRenderWork(true);
	TestTrue(TEXT("Enabled arm drains the rendering reference before owner release"), RenderReferenceReleased.Load());
	TestEqual(TEXT("Only the game-thread owner remains"), GameOwner.GetSharedReferenceCount(), 1);
	GameOwner.Reset();
	TestTrue(TEXT("The probe was destroyed"), Destroyed.Load());
	TestTrue(TEXT("Final destruction happened on GameThread"), DestroyedOnGameThread.Load());
	FPlatformProcess::ReturnSynchEventToPool(Started);
	FPlatformProcess::ReturnSynchEventToPool(Release);
	return bStarted;
}

#endif
