#pragma once

#include "CoreMinimal.h"

/** One JSON Lines request. RequestId must be unique among in-flight requests. */
struct EDGEWORLDRUNTIME_API FEdgeWorldRequest
{
	FString RequestId;
	FString Operation;
	FString JsonLine;
};

struct EDGEWORLDRUNTIME_API FEdgeWorldResponse
{
	bool bSuccess = false;
	FString RequestId;
	FString JsonLine;
	FString ErrorCode;
	FString ErrorMessage;
};

using FEdgeWorldResponseHandler = TFunction<void(FEdgeWorldResponse&&)>;

/**
 * Transport contract: SendJsonLine must return immediately and invoke the
 * handler asynchronously exactly once. Implementations correlate responses by
 * request_id and must report missing/unavailable workers explicitly.
 */
class EDGEWORLDRUNTIME_API IEdgeWorldJsonlTransport
{
public:
	virtual ~IEdgeWorldJsonlTransport() = default;
	virtual void SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler) = 0;
};

/** Honest placeholder used until a worker process/pipe lifecycle is supplied. */
class EDGEWORLDRUNTIME_API FEdgeWorldUnavailableTransport final : public IEdgeWorldJsonlTransport
{
public:
	virtual void SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler) override;
};

/** Small request builder for the prototype operations; it does not own state. */
class EDGEWORLDRUNTIME_API FEdgeWorldJsonlClient
{
public:
	explicit FEdgeWorldJsonlClient(TSharedRef<IEdgeWorldJsonlTransport, ESPMode::ThreadSafe> InTransport);

	void Status(const FString& WorldId, FEdgeWorldResponseHandler Handler) const;
	void Advance(const FString& WorldId, int64 ExpectedRevision, int64 TargetTick,
		const FString& CommandId, FEdgeWorldResponseHandler Handler) const;
	void Observe(const FString& WorldId, int64 LogicalTick, const FString& ViewSpecJson,
		FEdgeWorldResponseHandler Handler) const;

private:
	void SendOperation(const FString& Operation, TSharedRef<FJsonObject> Payload,
		FEdgeWorldResponseHandler Handler) const;
	TSharedRef<IEdgeWorldJsonlTransport, ESPMode::ThreadSafe> Transport;
};
