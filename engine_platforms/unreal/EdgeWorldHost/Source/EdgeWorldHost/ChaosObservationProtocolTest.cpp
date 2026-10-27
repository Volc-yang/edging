#include "EdgeWorldJsonlClient.h"
#include "ChaosObservationGameMode.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Dom/JsonObject.h"
#include "Misc/AutomationTest.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	class FRecordingTransport final : public IEdgeWorldJsonlTransport
	{
	public:
		TArray<FEdgeWorldRequest> Requests;
		virtual void SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler) override
		{
			Requests.Add(MoveTemp(Request));
		}
	};

	TSharedPtr<FJsonObject> Decode(const FEdgeWorldRequest& Request)
	{
		TSharedPtr<FJsonObject> Object;
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Request.JsonLine), Object);
		return Object;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChaosOriginClientRequestsTest,
	"edgeWorld.Chaos.OriginClientRequests", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChaosOriginClientRequestsTest::RunTest(const FString& Parameters)
{
	const TSharedRef<FRecordingTransport, ESPMode::ThreadSafe> Recorder = MakeShared<FRecordingTransport, ESPMode::ThreadSafe>();
	FEdgeWorldJsonlClient Client(Recorder);
	auto Noop = [](FEdgeWorldResponse&&) {};
	Client.Status(TEXT("chaos-demo"), Noop);
	Client.AdvanceOrigin(TEXT("chaos-demo"), 0, 1, TEXT("origin-o1"), Noop);
	Client.Observe(TEXT("chaos-demo"), 0,
		TEXT("{\"watermark\":0,\"region\":\"origin-sample\"}"), Noop);
	TestEqual(TEXT("three origin operations"), Recorder->Requests.Num(), 3);
	if (Recorder->Requests.Num() != 3) return false;
	const TSharedPtr<FJsonObject> Advance = Decode(Recorder->Requests[1]);
	const TSharedPtr<FJsonObject> Observe = Decode(Recorder->Requests[2]);
	TestTrue(TEXT("origin request JSON"), Advance.IsValid());
	TestTrue(TEXT("observe request JSON"), Observe.IsValid());
	if (!Advance.IsValid() || !Observe.IsValid()) return false;
	TestEqual(TEXT("origin action"), Advance->GetStringField(TEXT("origin_action")), FString(TEXT("reveal_world_spirit")));
	TestEqual(TEXT("origin target"), Advance->GetIntegerField(TEXT("target_tick")), 1);
	TestEqual(TEXT("origin command"), Advance->GetStringField(TEXT("command_id")), FString(TEXT("origin-o1")));
	TestEqual(TEXT("observe tick"), Observe->GetIntegerField(TEXT("logical_tick")), 0);
	const TSharedPtr<FJsonObject>* View = nullptr;
	TestTrue(TEXT("view spec present"), Observe->TryGetObjectField(TEXT("view_spec"), View));
	TestTrue(TEXT("view spec watermark"), View && View->IsValid() && (*View)->GetIntegerField(TEXT("watermark")) == 0);
	Client.Advance(TEXT("seed-tree-demo"), 0, 1, TEXT("tree-1"),
		TEXT("{\"phase\":\"shaoyang\",\"moisture\":0.8,\"light\":0.7}"), Noop);
	TestEqual(TEXT("existing tree request retained"), Recorder->Requests.Num(), 4);
	const TSharedPtr<FJsonObject> Tree = Decode(Recorder->Requests[3]);
	TestTrue(TEXT("tree request has environment"), Tree.IsValid() && Tree->HasField(TEXT("environment")));
	TestTrue(TEXT("tree request has no origin action"), Tree.IsValid() && !Tree->HasField(TEXT("origin_action")));
	const FString InitialPath = FPaths::ConvertRelativePathToFull(
		FPaths::Combine(FPaths::ProjectDir(), TEXT("../../../models/chaos/initial_world_seed7.json")));
	FString InitialJson, Hash, Error;
	TestTrue(TEXT("golden InitialWorld readable"), FFileHelper::LoadFileToString(InitialJson, *InitialPath));
	TestTrue(TEXT("golden canonical hash computed"), ChaosCanonicalInitialWorldHash(InitialJson, Hash, Error));
	TestEqual(TEXT("golden canonical hash"), Hash,
		FString(TEXT("75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3")));
	FString Changed = InitialJson.Replace(TEXT("city-1"), TEXT("city-2"));
	FString ChangedHash;
	TestTrue(TEXT("changed InitialWorld hash computed"), ChaosCanonicalInitialWorldHash(Changed, ChangedHash, Error));
	TestNotEqual(TEXT("changed content rejected by golden comparison"), ChangedHash, Hash);
	return true;
}
#endif
