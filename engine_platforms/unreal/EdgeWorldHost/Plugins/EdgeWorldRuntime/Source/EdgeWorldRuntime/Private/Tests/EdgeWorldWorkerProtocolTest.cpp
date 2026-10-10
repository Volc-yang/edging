#if WITH_DEV_AUTOMATION_TESTS

#include "EdgeWorldJsonlClient.h"

#include "HAL/PlatformProcess.h"
#include "Dom/JsonObject.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeLock.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	struct FEdgeWorldWaitState
	{
		FEvent* Event = FPlatformProcess::GetSynchEventFromPool(true);
		TOptional<FEdgeWorldResponse> Response;
		FCriticalSection Mutex;

		~FEdgeWorldWaitState()
		{
			FPlatformProcess::ReturnSynchEventToPool(Event);
		}
	};

	TOptional<FEdgeWorldResponse> WaitForResponse(
		FAutomationTestBase& Test,
		TFunction<void(FEdgeWorldResponseHandler)> Submit)
	{
		TSharedRef<FEdgeWorldWaitState, ESPMode::ThreadSafe> State = MakeShared<FEdgeWorldWaitState, ESPMode::ThreadSafe>();
		Submit([State](FEdgeWorldResponse&& InResponse)
		{
			{
				FScopeLock Lock(&State->Mutex);
				State->Response.Emplace(MoveTemp(InResponse));
			}
			State->Event->Trigger();
		});
		if (!State->Event->Wait(120000))
		{
			Test.AddError(TEXT("Timed out waiting for the asynchronous worker response."));
			return {}; // State remains alive until a late callback completes.
		}
		FScopeLock Lock(&State->Mutex);
		return State->Response;
	}

	TSharedPtr<FJsonObject> ParseResponse(const FEdgeWorldResponse& Response)
	{
		TSharedPtr<FJsonObject> Root;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response.JsonLine);
		FJsonSerializer::Deserialize(Reader, Root);
		return Root;
	}

	TSharedPtr<FJsonObject> ResultObject(const FEdgeWorldResponse& Response)
	{
		const TSharedPtr<FJsonObject> Root = ParseResponse(Response);
		const TSharedPtr<FJsonObject>* Result = nullptr;
		return Root.IsValid() && Root->TryGetObjectField(TEXT("result"), Result) && Result
			? *Result : nullptr;
	}

	bool TestResponseSucceeded(FAutomationTestBase& Test,
		const TOptional<FEdgeWorldResponse>& Response, const TCHAR* Description)
	{
		if (!Response.IsSet())
		{
			Test.AddError(FString::Printf(TEXT("%s: no response was delivered."), Description));
			return false;
		}
		if (!Response->bSuccess)
		{
			Test.AddError(FString::Printf(TEXT("%s failed: %s - %s. Reply: %s"), Description,
				*Response->ErrorCode, *Response->ErrorMessage, *Response->JsonLine));
			return false;
		}
		return true;
	}

	double NumberField(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field)
	{
		double Value = -1.0;
		if (Object.IsValid())
		{
			Object->TryGetNumberField(Field, Value);
		}
		return Value;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldWorkerProtocolTest,
	"edgeWorld.WorkerProtocol.ProcessRoundTripRecoveryAndReadOnlyObserve",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FEdgeWorldWorkerProtocolTest::RunTest(const FString& Parameters)
{
	const FString Python = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_TEST_PYTHON"));
	const FString Script = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_TEST_WORKER"));
	if (Python.IsEmpty() || Script.IsEmpty())
	{
		AddWarning(TEXT("Set EDGEWORLD_TEST_PYTHON and EDGEWORLD_TEST_WORKER to run the live Genesis worker integration check."));
		return true;
	}

	const FString WorldId = FString::Printf(TEXT("ue-probe-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
	const FString StateDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EdgeWorldWorkerTests"), WorldId);
	FEdgeWorldWorkerLaunchConfig Config;
	Config.PythonExecutable = Python;
	Config.WorkerScript = Script;
	Config.StateDirectory = StateDirectory;
	Config.WorldId = WorldId;
	Config.PhysicalStepsPerTick = 2;
	Config.RequestTimeoutSeconds = 120.0;

	FString InitialManifest;
	{
		TSharedRef<FEdgeWorldProcessTransport, ESPMode::ThreadSafe> Transport =
			MakeShared<FEdgeWorldProcessTransport, ESPMode::ThreadSafe>(Config);
		FEdgeWorldJsonlClient Client(Transport);

		const TOptional<FEdgeWorldResponse> InitialStatus = WaitForResponse(*this,
			[&Client, &WorldId](FEdgeWorldResponseHandler Handler) { Client.Status(WorldId, MoveTemp(Handler)); });
		if (!TestResponseSucceeded(*this, InitialStatus, TEXT("Initial status"))) return false;
		const TSharedPtr<FJsonObject> InitialHead = ResultObject(*InitialStatus);
		TestEqual(TEXT("New world starts at logical tick 0"), NumberField(InitialHead, TEXT("logical_tick")), 0.0);
		TestEqual(TEXT("New world starts at revision 0"), NumberField(InitialHead, TEXT("state_revision")), 0.0);

		const FString CommandId = FString::Printf(TEXT("ue-advance-%s"), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
		const TOptional<FEdgeWorldResponse> Advanced = WaitForResponse(*this,
			[&Client, &WorldId, &CommandId](FEdgeWorldResponseHandler Handler)
			{
				Client.Advance(WorldId, 0, 1, CommandId, MoveTemp(Handler));
			});
		if (!TestResponseSucceeded(*this, Advanced, TEXT("Advance request"))) return false;
		const TSharedPtr<FJsonObject> AdvancedHead = ResultObject(*Advanced);
		TestEqual(TEXT("Advance commits tick 1"), NumberField(AdvancedHead, TEXT("logical_tick")), 1.0);
		TestEqual(TEXT("Advance commits revision 1"), NumberField(AdvancedHead, TEXT("state_revision")), 1.0);

		const TOptional<FEdgeWorldResponse> DuplicateAdvance = WaitForResponse(*this,
			[&Client, &WorldId, &CommandId](FEdgeWorldResponseHandler Handler)
			{
				Client.Advance(WorldId, 0, 1, CommandId, MoveTemp(Handler));
			});
		if (!TestResponseSucceeded(*this, DuplicateAdvance, TEXT("Repeated command"))) return false;
		TestEqual(TEXT("Repeated command does not advance twice"),
			NumberField(ResultObject(*DuplicateAdvance), TEXT("logical_tick")), 1.0);

		const FString ManifestPath = FPaths::Combine(StateDirectory, TEXT("world.json"));
		if (!TestTrue(TEXT("Committed worker manifest can be read"), FFileHelper::LoadFileToString(InitialManifest, *ManifestPath))) return false;
		for (int32 ObserveIndex = 0; ObserveIndex < 2; ++ObserveIndex)
		{
			const TOptional<FEdgeWorldResponse> Observation = WaitForResponse(*this,
				[&Client, &WorldId](FEdgeWorldResponseHandler Handler)
				{
					Client.Observe(WorldId, 1, TEXT("{}"), MoveTemp(Handler));
				});
			if (!TestResponseSucceeded(*this, Observation, TEXT("Historical observation"))) return false;
			const TSharedPtr<FJsonObject> ObserveResult = ResultObject(*Observation);
			TestEqual(TEXT("Observation reads the requested logical tick"), NumberField(ObserveResult, TEXT("logical_tick")), 1.0);
			TestEqual(TEXT("Observation reports committed source revision"), NumberField(ObserveResult, TEXT("source_revision")), 1.0);
			FString ManifestAfterObserve;
			if (!TestTrue(TEXT("Manifest remains readable after observation"), FFileHelper::LoadFileToString(ManifestAfterObserve, *ManifestPath))) return false;
			TestEqual(TEXT("Observe is read-only"), ManifestAfterObserve, InitialManifest);
		}
		Transport->Shutdown();
	}

	// A second process must recover the same committed head from disk.
	{
		TSharedRef<FEdgeWorldProcessTransport, ESPMode::ThreadSafe> Transport =
			MakeShared<FEdgeWorldProcessTransport, ESPMode::ThreadSafe>(Config);
		FEdgeWorldJsonlClient Client(Transport);
		const TOptional<FEdgeWorldResponse> RecoveredStatus = WaitForResponse(*this,
			[&Client, &WorldId](FEdgeWorldResponseHandler Handler) { Client.Status(WorldId, MoveTemp(Handler)); });
		if (!TestResponseSucceeded(*this, RecoveredStatus, TEXT("Restarted worker status"))) return false;
		TestEqual(TEXT("Restart preserves logical tick 1"), NumberField(ResultObject(*RecoveredStatus), TEXT("logical_tick")), 1.0);
		TestEqual(TEXT("Restart preserves revision 1"), NumberField(ResultObject(*RecoveredStatus), TEXT("state_revision")), 1.0);
		Transport->Shutdown();
	}
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
