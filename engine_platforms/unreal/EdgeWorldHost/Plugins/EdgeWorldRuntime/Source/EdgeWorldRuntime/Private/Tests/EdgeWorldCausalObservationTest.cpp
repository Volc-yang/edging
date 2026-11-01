#include "EdgeWorldCausalObservation.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldCausalObservationTest,
	"edgeWorld.CausalObservation.StrictIdentity", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FEdgeWorldCausalObservationTest::RunTest(const FString& Parameters)
{
	FString Json = TEXT(R"json({"protocol_version":1,"request_id":"fixture-1","ok":true,"result":{
"world_id":"stg-demo","schema_version":"abstract-seed-genesis.v1","logical_tick":1,
"source_revision":1,"watermark":1,"state_hash":"@H@","event_hash":"@H@","checkpoint_sha256":"@H@",
"projection_version":"causal-graph-ue.v1","seed_identity":{"seed_id":"stg-demo:seed:0","initial_state_hash":"@H@"},
"development_structure":{"root_id":"stg-demo:node:0","structure_hash":"@H@","nodes":[
{"node_id":"stg-demo:node:0","tick":0,"influence_mm":null,"physics_candidate_hash":null},
{"node_id":"stg-demo:node:1","tick":1,"influence_mm":-7,"physics_candidate_hash":"@H@"}],
"edges":[{"edge_id":"stg-demo:edge:1","from_node_id":"stg-demo:node:0","to_node_id":"stg-demo:node:1","command_id":"tick-1","physics_candidate_hash":"@H@"}]},
"physics_sample":{"physical_probe_id":"stg-demo:physical:0","position":[0,0,0.9928],"velocity":[0,0,-0.16,0,0,0],"phase":"shaoyang","physics_candidate_hash":"@H@","genesis_config_hash":"@H@"},
"view_spec":{"watermark":1,"region":"causal-fragment-v1","observer":"ue-causal-camera-v1","resolution":"causal-graph-proxy-v1","error_budget":{"semantic_state":"exact","visual_geometry":"unmeasured-proxy"},"rules":{"evolution":"abstract-causal-probe.v1","projection":"causal-graph-ue.v1"}}
}})json");
	Json.ReplaceInline(TEXT("@H@"), *FString::ChrN(64, TEXT('a')));
	FEdgeWorldResponse Response;
	Response.bSuccess = true;
	Response.RequestId = TEXT("fixture-1");
	Response.JsonLine = Json;
	FEdgeWorldCausalObservation Sample;
	FString Error;
	TestTrue(TEXT("valid exact observation"), EdgeWorldParseCausalObservation(Response, TEXT("stg-demo"), 1, 1, Sample, Error));
	TestEqual(TEXT("one causal edge"), Sample.Edges.Num(), 1);
	TestEqual(TEXT("derived influence"), Sample.Nodes.Last().InfluenceMm, int64(-7));
	FEdgeWorldCausalHeadGate Gate;
	Gate.Stage(1, 1, Sample.GenesisConfigHash, Sample.CheckpointHash, Sample.StateHash, Sample.EventHash);
	FEdgeWorldCausalObservation Wrong = Sample;
	Wrong.GenesisConfigHash = FString::ChrN(64, TEXT('b'));
	TestFalse(TEXT("wrong config does not publish head"), Gate.Accept(Wrong));
	TestEqual(TEXT("validated tick remains zero"), Gate.LatestTick, int64(0));
	TestFalse(TEXT("pending head blocks another advance"), Gate.CanAdvance());
	Wrong = Sample;
	Wrong.CheckpointHash = FString::ChrN(64, TEXT('b'));
	TestFalse(TEXT("wrong checkpoint does not publish head"), Gate.Accept(Wrong));
	TestEqual(TEXT("validated revision remains zero"), Gate.LatestRevision, int64(0));
	Wrong = Sample;
	Wrong.StateHash = FString::ChrN(64, TEXT('b'));
	TestFalse(TEXT("wrong state hash does not publish head"), Gate.Accept(Wrong));
	Wrong = Sample;
	Wrong.EventHash = FString::ChrN(64, TEXT('b'));
	TestFalse(TEXT("wrong event head does not publish head"), Gate.Accept(Wrong));
	TestTrue(TEXT("matching observation publishes head"), Gate.Accept(Sample));
	TestEqual(TEXT("validated tick advances after observation"), Gate.LatestTick, int64(1));
	TestTrue(TEXT("published head allows advance"), Gate.CanAdvance());
	TestFalse(TEXT("wrong world rejected"), EdgeWorldParseCausalObservation(Response, TEXT("other"), 1, 1, Sample, Error));
	TestFalse(TEXT("wrong watermark rejected"), EdgeWorldParseCausalObservation(Response, TEXT("stg-demo"), 1, 2, Sample, Error));
	Response.JsonLine = Json.Replace(TEXT("stg-demo:edge:1"), TEXT("stg-demo:edge:2"));
	TestFalse(TEXT("wrong causal edge rejected"), EdgeWorldParseCausalObservation(Response, TEXT("stg-demo"), 1, 1, Sample, Error));
	Response.JsonLine = Json.Replace(TEXT("\"influence_mm\":-7"), TEXT("\"influence_mm\":1001"));
	TestFalse(TEXT("out of range influence rejected"), EdgeWorldParseCausalObservation(Response, TEXT("stg-demo"), 1, 1, Sample, Error));
	Response.JsonLine = Json.Replace(TEXT("\"phase\":\"shaoyang\""), TEXT("\"phase\":\"unknown\""));
	TestFalse(TEXT("unknown phase rejected"), EdgeWorldParseCausalObservation(Response, TEXT("stg-demo"), 1, 1, Sample, Error));
	Response.JsonLine = Json.Replace(TEXT("\"physics_candidate_hash\":\""), TEXT("\"physics_candidate_hash\":\"b"));
	TestFalse(TEXT("malformed physics hash rejected"), EdgeWorldParseCausalObservation(Response, TEXT("stg-demo"), 1, 1, Sample, Error));
	return true;
}
#endif
