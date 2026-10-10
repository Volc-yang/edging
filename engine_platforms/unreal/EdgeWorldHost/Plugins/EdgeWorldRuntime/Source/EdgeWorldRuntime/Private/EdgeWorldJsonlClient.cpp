#include "EdgeWorldJsonlClient.h"

#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

void FEdgeWorldUnavailableTransport::SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler)
{
	Async(EAsyncExecution::ThreadPool, [Request = MoveTemp(Request), Handler = MoveTemp(Handler)]() mutable
	{
		FEdgeWorldResponse Response;
		Response.RequestId = Request.RequestId;
		Response.ErrorCode = TEXT("worker_unavailable");
		Response.ErrorMessage = TEXT("No edgeWorld JSONL worker transport is configured.");
		Handler(MoveTemp(Response));
	});
}

FEdgeWorldJsonlClient::FEdgeWorldJsonlClient(TSharedRef<IEdgeWorldJsonlTransport, ESPMode::ThreadSafe> InTransport)
	: Transport(MoveTemp(InTransport))
{
}

void FEdgeWorldJsonlClient::Status(const FString& WorldId, FEdgeWorldResponseHandler Handler) const
{
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("world_id"), WorldId);
	SendOperation(TEXT("status"), Payload, MoveTemp(Handler));
}

void FEdgeWorldJsonlClient::Advance(const FString& WorldId, int64 ExpectedRevision, int64 TargetTick,
	const FString& CommandId, FEdgeWorldResponseHandler Handler) const
{
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("world_id"), WorldId);
	Payload->SetNumberField(TEXT("expected_revision"), static_cast<double>(ExpectedRevision));
	Payload->SetNumberField(TEXT("target_tick"), static_cast<double>(TargetTick));
	Payload->SetStringField(TEXT("command_id"), CommandId);
	SendOperation(TEXT("advance"), Payload, MoveTemp(Handler));
}

void FEdgeWorldJsonlClient::Observe(const FString& WorldId, int64 LogicalTick, const FString& ViewSpecJson,
	FEdgeWorldResponseHandler Handler) const
{
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("world_id"), WorldId);
	Payload->SetNumberField(TEXT("logical_tick"), static_cast<double>(LogicalTick));
	TSharedPtr<FJsonObject> ViewSpec;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ViewSpecJson);
	if (FJsonSerializer::Deserialize(Reader, ViewSpec) && ViewSpec.IsValid())
	{
		Payload->SetObjectField(TEXT("view_spec"), ViewSpec.ToSharedRef());
	}
	else
	{
		Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.ErrorCode = TEXT("invalid_view_spec");
			Response.ErrorMessage = TEXT("view_spec must be a valid JSON object.");
			Handler(MoveTemp(Response));
		});
		return;
	}
	SendOperation(TEXT("observe"), Payload, MoveTemp(Handler));
}

void FEdgeWorldJsonlClient::SendOperation(const FString& Operation, TSharedRef<FJsonObject> Payload,
	FEdgeWorldResponseHandler Handler) const
{
	const FString RequestId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
	Payload->SetNumberField(TEXT("protocol_version"), 1);
	Payload->SetStringField(TEXT("request_id"), RequestId);
	Payload->SetStringField(TEXT("operation"), Operation);

	FString JsonLine;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonLine);
	if (!FJsonSerializer::Serialize(Payload, Writer))
	{
		Async(EAsyncExecution::ThreadPool, [RequestId, Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.RequestId = RequestId;
			Response.ErrorCode = TEXT("request_serialization_failed");
			Response.ErrorMessage = TEXT("Could not serialize the JSONL request.");
			Handler(MoveTemp(Response));
		});
		return;
	}
	JsonLine.AppendChar(TEXT('\n'));
	Transport->SendJsonLine({RequestId, Operation, MoveTemp(JsonLine)}, MoveTemp(Handler));
}
