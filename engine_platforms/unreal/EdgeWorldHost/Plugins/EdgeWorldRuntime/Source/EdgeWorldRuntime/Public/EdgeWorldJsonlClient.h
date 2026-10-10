#pragma once

#include "CoreMinimal.h"

struct FEdgeWorldTreeObservation;

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

/** Honest placeholder for projects that have not configured a worker process. */
class EDGEWORLDRUNTIME_API FEdgeWorldUnavailableTransport final : public IEdgeWorldJsonlTransport
{
public:
	virtual void SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler) override;
};

/** Launch configuration for the single-world Python worker process. */
struct EDGEWORLDRUNTIME_API FEdgeWorldWorkerLaunchConfig
{
	FString PythonExecutable;
	FString WorkerScript;
	FString StateDirectory;
	FString WorldId;
	double DeltaTime = 0.01;
	int32 PhysicalStepsPerTick = 8;
	int32 Seed = 7;
	double RequestTimeoutSeconds = 30.0;
};

/**
 * Asynchronous, serialized JSONL transport backed by one child worker process.
 * The process is started lazily, reused for requests, and shut down with the
 * transport. One transport must own one world/state directory.
 */
class EDGEWORLDRUNTIME_API FEdgeWorldProcessTransport final
	: public IEdgeWorldJsonlTransport
	, public TSharedFromThis<FEdgeWorldProcessTransport, ESPMode::ThreadSafe>
{
public:
	explicit FEdgeWorldProcessTransport(FEdgeWorldWorkerLaunchConfig InConfig);
	virtual ~FEdgeWorldProcessTransport();

	virtual void SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler) override;
	void Shutdown();

private:
	bool EnsureStarted(FString& OutError);
	FEdgeWorldResponse Exchange(const FEdgeWorldRequest& Request);
	void StopProcess(bool bTerminate);

	FEdgeWorldWorkerLaunchConfig Config;
	FCriticalSection RequestMutex;
	FProcHandle ProcessHandle;
	void* StdoutReadPipe = nullptr;
	void* StdinWritePipe = nullptr;
	void* StderrReadPipe = nullptr;
	FString PendingStdout;
	bool bShutdown = false;
};

/** Small request builder for the prototype operations; it does not own state. */
class EDGEWORLDRUNTIME_API FEdgeWorldJsonlClient
{
public:
	explicit FEdgeWorldJsonlClient(TSharedRef<IEdgeWorldJsonlTransport, ESPMode::ThreadSafe> InTransport);

	void Status(const FString& WorldId, FEdgeWorldResponseHandler Handler) const;
	void Advance(const FString& WorldId, int64 ExpectedRevision, int64 TargetTick,
		const FString& CommandId, FEdgeWorldResponseHandler Handler) const;
	void Advance(const FString& WorldId, int64 ExpectedRevision, int64 TargetTick,
		const FString& CommandId, const FString& EnvironmentJson, FEdgeWorldResponseHandler Handler) const;
	void Observe(const FString& WorldId, int64 LogicalTick, const FString& ViewSpecJson,
		FEdgeWorldResponseHandler Handler) const;

private:
	void SendOperation(const FString& Operation, TSharedRef<FJsonObject> Payload,
		FEdgeWorldResponseHandler Handler) const;
	TSharedRef<IEdgeWorldJsonlTransport, ESPMode::ThreadSafe> Transport;
};

/** Parse and validate one exact-tick tree Observe response against its query. */
EDGEWORLDRUNTIME_API bool EdgeWorldParseTreeObservation(const FEdgeWorldResponse& Response,
	const FString& ExpectedWorldId, int64 ExpectedTick, int64 ExpectedWatermark,
	const FString& ExpectedRulesetVersion, const FString& ExpectedProjectionVersion,
	FEdgeWorldTreeObservation& OutObservation, FString& OutError);
