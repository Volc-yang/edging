#include "EdgeWorldCausalObservation.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	constexpr int64 SafeInteger = (1LL << 53) - 1;
	bool Integer(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, int64& Value, bool bSigned = false)
	{
		double Number = 0;
		if (!Object.IsValid() || !Object->TryGetNumberField(Name, Number) || !FMath::IsFinite(Number)
			|| Number < (bSigned ? -static_cast<double>(SafeInteger) : 0.0)
			|| Number > static_cast<double>(SafeInteger) || FMath::FloorToDouble(Number) != Number) return false;
		Value = static_cast<int64>(Number);
		return true;
	}
	bool String(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, FString& Value)
	{
		return Object.IsValid() && Object->TryGetStringField(Name, Value) && !Value.IsEmpty();
	}
	bool Hash(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, FString& Value)
	{
		if (!String(Object, Name, Value) || Value.Len() != 64) return false;
		for (TCHAR C : Value) if (!FChar::IsHexDigit(C)) return false;
		return true;
	}
	bool Object(const TSharedPtr<FJsonObject>& Parent, const TCHAR* Name, TSharedPtr<FJsonObject>& Value)
	{
		const TSharedPtr<FJsonObject>* Ptr = nullptr;
		if (!Parent.IsValid() || !Parent->TryGetObjectField(Name, Ptr) || !Ptr || !Ptr->IsValid()) return false;
		Value = *Ptr;
		return true;
	}
	bool Vector(const TSharedPtr<FJsonObject>& Parent, const TCHAR* Name, int32 Min, int32 Max)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (!Parent.IsValid() || !Parent->TryGetArrayField(Name, Values) || !Values
			|| Values->Num() < Min || Values->Num() > Max) return false;
		for (const TSharedPtr<FJsonValue>& Value : *Values)
		{
			double N = 0;
			if (!Value.IsValid() || !Value->TryGetNumber(N) || !FMath::IsFinite(N)) return false;
		}
		return true;
	}
}

bool EdgeWorldParseCausalObservation(const FEdgeWorldResponse& Response, const FString& ExpectedWorldId,
	int64 ExpectedTick, int64 ExpectedWatermark, FEdgeWorldCausalObservation& Out, FString& OutError)
{
	Out = {};
	if (!Response.bSuccess) { OutError = Response.ErrorCode + TEXT(": ") + Response.ErrorMessage; return false; }
	TSharedPtr<FJsonObject> Envelope;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response.JsonLine), Envelope) || !Envelope.IsValid())
	{ OutError = TEXT("invalid JSON envelope"); return false; }
	int64 Protocol = 0;
	FString RequestId;
	bool bOk = false;
	if (!Integer(Envelope, TEXT("protocol_version"), Protocol) || Protocol != 1
		|| !String(Envelope, TEXT("request_id"), RequestId) || RequestId != Response.RequestId
		|| !Envelope->TryGetBoolField(TEXT("ok"), bOk) || !bOk)
	{ OutError = TEXT("invalid response envelope"); return false; }
	TSharedPtr<FJsonObject> Result, Identity, Structure, Physics, View, Rules, Budget;
	FString Schema, Projection, SeedId, ProbeId, StructureHash, PhysicsHash, GenesisHash, Checkpoint;
	int64 Tick = 0, Revision = 0, Watermark = 0;
	if (!Object(Envelope, TEXT("result"), Result)
		|| !String(Result, TEXT("world_id"), Out.WorldId) || Out.WorldId != ExpectedWorldId
		|| !String(Result, TEXT("schema_version"), Schema) || Schema != TEXT("abstract-seed-genesis.v1")
		|| !Integer(Result, TEXT("logical_tick"), Tick) || Tick != ExpectedTick
		|| !Integer(Result, TEXT("source_revision"), Revision) || Revision != ExpectedWatermark
		|| !Integer(Result, TEXT("watermark"), Watermark) || Watermark != ExpectedWatermark
		|| !String(Result, TEXT("projection_version"), Projection) || Projection != TEXT("causal-graph-ue.v1")
		|| !Hash(Result, TEXT("state_hash"), Out.StateHash) || !Hash(Result, TEXT("event_hash"), Out.EventHash)
		|| !Hash(Result, TEXT("checkpoint_sha256"), Checkpoint)
		|| !Object(Result, TEXT("seed_identity"), Identity) || !String(Identity, TEXT("seed_id"), SeedId)
		|| SeedId != ExpectedWorldId + TEXT(":seed:0")
		|| !Object(Result, TEXT("development_structure"), Structure)
		|| !Hash(Structure, TEXT("structure_hash"), StructureHash)
		|| !Object(Result, TEXT("physics_sample"), Physics)
		|| !String(Physics, TEXT("physical_probe_id"), ProbeId)
		|| ProbeId != ExpectedWorldId + TEXT(":physical:0")
		|| !Hash(Physics, TEXT("physics_candidate_hash"), PhysicsHash)
		|| !Hash(Physics, TEXT("genesis_config_hash"), GenesisHash)
		|| !Vector(Physics, TEXT("position"), 3, 3)
		|| !Vector(Physics, TEXT("velocity"), 3, 6)
		|| !Object(Result, TEXT("view_spec"), View)
		|| !Object(View, TEXT("error_budget"), Budget)
		|| !Object(View, TEXT("rules"), Rules))
	{ OutError = TEXT("causal result identity or required field mismatch"); return false; }
	FString InitialHash, RootId, Region, Observer, Resolution, Evolution, ViewProjection, Phase, Semantic, Geometry;
	int64 ViewWatermark = 0;
	if (!Hash(Identity, TEXT("initial_state_hash"), InitialHash)
		|| !String(Structure, TEXT("root_id"), RootId)
		|| RootId != ExpectedWorldId + TEXT(":node:0")
		|| !Integer(View, TEXT("watermark"), ViewWatermark) || ViewWatermark != ExpectedWatermark
		|| !String(View, TEXT("region"), Region) || Region != TEXT("causal-fragment-v1")
		|| !String(View, TEXT("observer"), Observer) || Observer != TEXT("ue-causal-camera-v1")
		|| !String(View, TEXT("resolution"), Resolution) || Resolution != TEXT("causal-graph-proxy-v1")
		|| !String(Budget, TEXT("semantic_state"), Semantic) || Semantic != TEXT("exact")
		|| !String(Budget, TEXT("visual_geometry"), Geometry) || Geometry != TEXT("unmeasured-proxy")
		|| !String(Rules, TEXT("evolution"), Evolution) || Evolution != TEXT("abstract-causal-probe.v1")
		|| !String(Rules, TEXT("projection"), ViewProjection) || ViewProjection != Projection)
	{ OutError = TEXT("causal seed/root mismatch"); return false; }
	if (Tick == 0)
	{
		const TSharedPtr<FJsonValue>* Value = Physics->Values.Find(TEXT("phase"));
		if (!Value || !Value->IsValid() || (*Value)->Type != EJson::Null)
		{ OutError = TEXT("initial phase must be null"); return false; }
	}
	else if (!String(Physics, TEXT("phase"), Phase)
		|| (Phase != TEXT("shaoyang") && Phase != TEXT("taiyang")))
	{ OutError = TEXT("invalid physics phase"); return false; }
	const TArray<TSharedPtr<FJsonValue>>* Nodes = nullptr;
	const TArray<TSharedPtr<FJsonValue>>* Edges = nullptr;
	if (!Structure->TryGetArrayField(TEXT("nodes"), Nodes) || !Nodes
		|| !Structure->TryGetArrayField(TEXT("edges"), Edges) || !Edges
		|| Nodes->Num() != Tick + 1 || Edges->Num() != Tick || Tick > 10000)
	{ OutError = TEXT("causal topology length mismatch"); return false; }
	for (int32 Index = 0; Index < Nodes->Num(); ++Index)
	{
		const TSharedPtr<FJsonObject> Node = (*Nodes)[Index].IsValid() ? (*Nodes)[Index]->AsObject() : nullptr;
		FEdgeWorldCausalNode Parsed;
		if (!String(Node, TEXT("node_id"), Parsed.Id) || Parsed.Id != ExpectedWorldId + FString::Printf(TEXT(":node:%d"), Index)
			|| !Integer(Node, TEXT("tick"), Parsed.Tick) || Parsed.Tick != Index)
		{ OutError = TEXT("causal node identity mismatch"); return false; }
		if (Index == 0)
		{
			const TSharedPtr<FJsonValue>* Influence = Node->Values.Find(TEXT("influence_mm"));
			const TSharedPtr<FJsonValue>* InitialPhysics = Node->Values.Find(TEXT("physics_candidate_hash"));
			if (!Influence || !Influence->IsValid() || (*Influence)->Type != EJson::Null
				|| !InitialPhysics || !InitialPhysics->IsValid() || (*InitialPhysics)->Type != EJson::Null)
			{ OutError = TEXT("initial influence must be null"); return false; }
			Parsed.bInitial = true;
		}
		else if (!Integer(Node, TEXT("influence_mm"), Parsed.InfluenceMm, true)
			|| FMath::Abs(Parsed.InfluenceMm) > 1000
			|| !Hash(Node, TEXT("physics_candidate_hash"), Parsed.PhysicsHash))
		{ OutError = TEXT("invalid causal influence"); return false; }
		Out.Nodes.Add(MoveTemp(Parsed));
	}
	for (int32 Index = 0; Index < Edges->Num(); ++Index)
	{
		const TSharedPtr<FJsonObject> Edge = (*Edges)[Index].IsValid() ? (*Edges)[Index]->AsObject() : nullptr;
		FEdgeWorldCausalEdge Parsed;
		FString CommandId;
		if (!String(Edge, TEXT("edge_id"), Parsed.Id) || Parsed.Id != ExpectedWorldId + FString::Printf(TEXT(":edge:%d"), Index + 1)
			|| !String(Edge, TEXT("from_node_id"), Parsed.From) || Parsed.From != Out.Nodes[Index].Id
			|| !String(Edge, TEXT("to_node_id"), Parsed.To) || Parsed.To != Out.Nodes[Index + 1].Id
			|| !String(Edge, TEXT("command_id"), CommandId)
			|| !Hash(Edge, TEXT("physics_candidate_hash"), Parsed.PhysicsHash)
			|| Parsed.PhysicsHash != Out.Nodes[Index + 1].PhysicsHash)
		{ OutError = TEXT("causal edge identity mismatch"); return false; }
		Out.Edges.Add(MoveTemp(Parsed));
	}
	if (Tick > 0 && Out.Nodes.Last().PhysicsHash != PhysicsHash)
	{ OutError = TEXT("current physics candidate mismatch"); return false; }
	Out.Tick = Tick;
	Out.Revision = Revision;
	Out.GenesisConfigHash = GenesisHash;
	Out.CheckpointHash = Checkpoint;
	return true;
}

void FEdgeWorldCausalHeadGate::Stage(int64 Tick, int64 Revision, const FString& ConfigHash, const FString& CheckpointHash)
{
	bPending = true;
	PendingTick = Tick;
	PendingRevision = Revision;
	PendingConfigHash = ConfigHash;
	PendingCheckpointHash = CheckpointHash;
}

bool FEdgeWorldCausalHeadGate::Accept(const FEdgeWorldCausalObservation& Sample)
{
	if (!bPending || Sample.Tick != PendingTick || Sample.Revision != PendingRevision
		|| Sample.GenesisConfigHash != PendingConfigHash || Sample.CheckpointHash != PendingCheckpointHash)
		return false;
	LatestTick = PendingTick;
	LatestRevision = PendingRevision;
	LatestConfigHash = PendingConfigHash;
	LatestCheckpointHash = PendingCheckpointHash;
	bPending = false;
	return true;
}

bool FEdgeWorldCausalHeadGate::CheckHistory(const FEdgeWorldCausalObservation& Sample) const
{
	return !LatestConfigHash.IsEmpty() && Sample.Tick <= LatestTick
		&& Sample.GenesisConfigHash == LatestConfigHash
		&& (Sample.Tick != LatestTick || Sample.CheckpointHash == LatestCheckpointHash);
}
