#if WITH_DEV_AUTOMATION_TESTS

#include "EdgeWorldJsonlClient.h"
#include "EdgeWorldObservationActor.h"

#include "Async/Async.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
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

namespace
{
	FEdgeWorldResponse MakeTreeObservationFixture(int64 Tick, int64 Watermark, const TCHAR* Stage,
		const TCHAR* TreeIdJson, const TCHAR* PhaseJson, double Biomass)
	{
		FEdgeWorldResponse Response;
		Response.bSuccess = true;
		Response.JsonLine = FString::Printf(
			TEXT("{\"protocol_version\":1,\"request_id\":\"fixture\",\"ok\":true,\"result\":{\"world_id\":\"seed-tree-demo\",\"logical_tick\":%lld,\"source_revision\":%lld,\"watermark\":%lld,\"sample\":{\"seed_id\":\"seed-7\",\"tree_id\":%s,\"stage\":\"%s\",\"health\":0.8,\"biomass\":%.3f,\"water_reserve\":0.4,\"phase\":%s,\"ruleset_version\":\"experimental.seed-tree.v1\"},\"projection_version\":\"stylized-tree-ue-v1\",\"state_hash\":\"state-%lld\",\"event_hash\":\"event-%lld\",\"view_spec\":{\"watermark\":%lld,\"region\":\"single-tree-world\"}}}"),
			static_cast<long long>(Tick), static_cast<long long>(Watermark), static_cast<long long>(Watermark),
			TreeIdJson, Stage, Biomass, PhaseJson, static_cast<long long>(Tick),
			static_cast<long long>(Tick), static_cast<long long>(Watermark));
		return Response;
	}

	class FRecordingTreeTransport final : public IEdgeWorldJsonlTransport
	{
	public:
		FEdgeWorldRequest LastRequest;

		virtual void SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler) override
		{
			LastRequest = MoveTemp(Request);
			Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
			{
				FEdgeWorldResponse Response;
				Response.ErrorCode = TEXT("fixture_complete");
				Handler(MoveTemp(Response));
			});
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldTreeObserveFixtureTest,
	"edgeWorld.TreeObservation.ExactTimeSeedSeedlingAndMatureFixtures",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FEdgeWorldTreeObserveFixtureTest::RunTest(const FString& Parameters)
{
	struct FFixtureCase
	{
		int64 Tick;
		int64 Watermark;
		const TCHAR* Stage;
		const TCHAR* TreeIdJson;
		const TCHAR* PhaseJson;
		double Biomass;
	};
	const FFixtureCase Fixtures[] = {
		{ 0, 0, TEXT("seed"), TEXT("null"), TEXT("null"), 0.0 },
		{ 3, 3, TEXT("seedling"), TEXT("\"tree-7\""), TEXT("\"shaoyang\""), 0.3 },
		{ 8, 8, TEXT("mature"), TEXT("\"tree-7\""), TEXT("\"taiyang\""), 0.8 }
	};

	FEdgeWorldTreeObservation MatureObservation;
	for (const FFixtureCase& Fixture : Fixtures)
	{
		const FEdgeWorldResponse Response = MakeTreeObservationFixture(Fixture.Tick, Fixture.Watermark,
			Fixture.Stage, Fixture.TreeIdJson, Fixture.PhaseJson, Fixture.Biomass);
		FEdgeWorldTreeObservation Parsed;
		FString Error;
		const bool bParsed = EdgeWorldParseTreeObservation(Response, TEXT("seed-tree-demo"), Fixture.Tick,
			Fixture.Watermark, TEXT("experimental.seed-tree.v1"), TEXT("stylized-tree-ue-v1"), Parsed, Error);
		TestTrue(FString::Printf(TEXT("Fixture tick %lld parses: %s"), static_cast<long long>(Fixture.Tick), *Error), bParsed);
		if (bParsed)
		{
			TestEqual(TEXT("Parser preserves requested logical tick"), Parsed.LogicalTick, Fixture.Tick);
			TestEqual(TEXT("Parser preserves exact source watermark"), Parsed.SourceRevision, Fixture.Watermark);
			TestEqual(TEXT("Parser preserves lifecycle stage"), Parsed.Stage, FString(Fixture.Stage));
			TestEqual(TEXT("Parser preserves biomass"), Parsed.Biomass, Fixture.Biomass);
			if (Fixture.Tick == 8)
			{
				MatureObservation = Parsed;
			}
		}
	}

	FString Error;
	FEdgeWorldTreeObservation Rejected;
	const FEdgeWorldResponse Mature = MakeTreeObservationFixture(8, 8, TEXT("mature"), TEXT("\"tree-7\""), TEXT("\"taiyang\""), 0.8);
	TestFalse(TEXT("A response for a different requested tick is rejected"),
		EdgeWorldParseTreeObservation(Mature, TEXT("seed-tree-demo"), 7, 8, TEXT("experimental.seed-tree.v1"),
			TEXT("stylized-tree-ue-v1"), Rejected, Error));
	TestFalse(TEXT("A response with a mismatched watermark is rejected"),
		EdgeWorldParseTreeObservation(Mature, TEXT("seed-tree-demo"), 8, 7, TEXT("experimental.seed-tree.v1"),
			TEXT("stylized-tree-ue-v1"), Rejected, Error));
	TestFalse(TEXT("An unrecognized projection version is rejected"),
		EdgeWorldParseTreeObservation(Mature, TEXT("seed-tree-demo"), 8, 8, TEXT("experimental.seed-tree.v1"),
			TEXT("other-projection"), Rejected, Error));

	UWorld* TestWorld = UWorld::CreateWorld(EWorldType::Game, false);
	if (TestNotNull(TEXT("Transient world is created for presentation verification"), TestWorld))
	{
		AEdgeWorldObservationActor* TreeActor = TestWorld->SpawnActor<AEdgeWorldObservationActor>();
		if (TestNotNull(TEXT("Tree observation actor is spawned"), TreeActor))
		{
			TestFalse(TEXT("Tree observation actor has no enabled tick"), TreeActor->IsActorTickEnabled());
			TestTrue(TEXT("A mature fixed-time sample applies"), TreeActor->ApplyTreeObservation(MatureObservation, 8, 8, Error));
			TArray<UStaticMeshComponent*> Components;
			TreeActor->GetComponents<UStaticMeshComponent>(Components);
			TArray<FTransform> FirstTransforms;
			TArray<bool> FirstVisibility;
			for (const UStaticMeshComponent* Component : Components)
			{
				FirstTransforms.Add(Component->GetRelativeTransform());
				FirstVisibility.Add(Component->IsVisible());
			}
			TestTrue(TEXT("Repeating the same fixed sample applies"), TreeActor->ApplyTreeObservation(MatureObservation, 8, 8, Error));
			TestEqual(TEXT("Proxy component count is fixed"), Components.Num(), FirstTransforms.Num());
			for (int32 Index = 0; Index < Components.Num(); ++Index)
			{
				TestTrue(TEXT("Repeated sample produces identical component transform"), Components[Index]->GetRelativeTransform().Equals(FirstTransforms[Index]));
				TestEqual(TEXT("Repeated sample preserves component visibility"), Components[Index]->IsVisible(), FirstVisibility[Index]);
			}
		}
		TestWorld->DestroyWorld(false);
	}

	TSharedRef<FRecordingTreeTransport, ESPMode::ThreadSafe> RecordingTransport =
		MakeShared<FRecordingTreeTransport, ESPMode::ThreadSafe>();
	FEdgeWorldJsonlClient Client(RecordingTransport);
	const TOptional<FEdgeWorldResponse> AdvanceResponse = WaitForResponse(*this,
		[&Client](FEdgeWorldResponseHandler Handler)
		{
			Client.Advance(TEXT("seed-tree-demo"), 3, 4, TEXT("cmd-4"),
				TEXT("{\"phase\":\"taiyang\",\"moisture\":0.8,\"light\":0.7}"), MoveTemp(Handler));
		});
	TestTrue(TEXT("Environment advance reaches the transport"), RecordingTransport->LastRequest.JsonLine.Contains(TEXT("\"environment\"")));
	TestTrue(TEXT("Environment phase is serialized explicitly"), RecordingTransport->LastRequest.JsonLine.Contains(TEXT("\"phase\":\"taiyang\"")));
	TestTrue(TEXT("Advance request retains the exact target tick"), RecordingTransport->LastRequest.JsonLine.Contains(TEXT("\"target_tick\":4")));

	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
