#include "EdgeWorldJsonlClient.h"
#if PLATFORM_MAC
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>
#endif

#include "EdgeWorldObservationActor.h"

#include "Async/Async.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "Containers/StringConv.h"
#include "Dom/JsonObject.h"
#include "Misc/Paths.h"
#include "Misc/ScopeLock.h"
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

FEdgeWorldProcessTransport::FEdgeWorldProcessTransport(FEdgeWorldWorkerLaunchConfig InConfig)
	: Config(MoveTemp(InConfig))
{
 if(!Config.TraceDirectory.IsEmpty()&&!Config.TraceBudget)Config.TraceBudget=MakeShared<FEdgeWorldTraceBudget,ESPMode::ThreadSafe>();
}

FEdgeWorldProcessTransport::~FEdgeWorldProcessTransport()
{
	Shutdown();
}

void FEdgeWorldProcessTransport::SendJsonLine(FEdgeWorldRequest Request, FEdgeWorldResponseHandler Handler)
{
	TSharedRef<FEdgeWorldProcessTransport, ESPMode::ThreadSafe> Self = AsShared();
	Async(EAsyncExecution::ThreadPool,
		[Self = MoveTemp(Self), Request = MoveTemp(Request), Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response = Self->Exchange(Request);
			Handler(MoveTemp(Response));
		});
}

bool FEdgeWorldProcessTransport::EnsureStarted(FString& OutError)
{
	if (bShutdown)
	{
		OutError = TEXT("The edgeWorld worker transport has been shut down.");
		return false;
	}
	if (FPlatformProcess::IsProcRunning(ProcessHandle))
	{
		return true;
	}
	if (ProcessHandle.IsValid())
	{
		StopProcess(false);
	}
	if (Config.PythonExecutable.IsEmpty() || Config.WorkerScript.IsEmpty()
        || (Config.LaunchMode == EEdgeWorldWorkerLaunchMode::Universe
            ? Config.OwnerConfigPath.IsEmpty() : Config.StateDirectory.IsEmpty() || Config.WorldId.IsEmpty()))
	{
		OutError = TEXT("PythonExecutable, WorkerScript, StateDirectory, and WorldId must be configured.");
		return false;
	}
	if (Config.PythonExecutable.Contains(TEXT("\"")) || Config.WorkerScript.Contains(TEXT("\""))
		|| Config.StateDirectory.Contains(TEXT("\"")) || Config.WorldId.Contains(TEXT("\""))
		|| Config.WorldId.Contains(TEXT("\n")) || Config.WorldId.Contains(TEXT("\r"))
		|| Config.InitialWorldPath.Contains(TEXT("\""))
		|| Config.InitialWorldPath.Contains(TEXT("\n")) || Config.InitialWorldPath.Contains(TEXT("\r"))
        || Config.OwnerConfigPath.Contains(TEXT("\"")) || Config.OwnerConfigPath.Contains(TEXT("\n")) || Config.OwnerConfigPath.Contains(TEXT("\r")))
	{
		OutError = TEXT("Worker paths and world ID must not contain quotes or line breaks.");
		return false;
	}
	if (!FMath::IsFinite(Config.DeltaTime) || Config.DeltaTime <= 0.0
		|| Config.PhysicalStepsPerTick < 1 || Config.RequestTimeoutSeconds <= 0.0)
	{
		OutError = TEXT("Worker timestep, physical steps, and request timeout must be positive.");
		return false;
	}

 if(Config.LaunchMode==EEdgeWorldWorkerLaunchMode::Universe)
 {
  for(const FString& P:{Config.PythonExecutable,Config.WorkerScript,Config.OwnerConfigPath})
   if(FPaths::IsRelative(P)||P.Contains(TEXT("\n"))||P.Contains(TEXT("\r"))||P.Contains(TEXT("\\"))) {OutError=TEXT("Universe requires safe absolute launch paths");return false;}
 }
	void* StdoutChildRead = nullptr;
	void* StdoutChildWrite = nullptr;
	void* StdinChildRead = nullptr;
	void* StdinChildWrite = nullptr;
	void* StderrChildRead = nullptr;
	void* StderrChildWrite = nullptr;
	if (!FPlatformProcess::CreatePipe(StdoutChildRead, StdoutChildWrite, false)
		|| !FPlatformProcess::CreatePipe(StdinChildRead, StdinChildWrite, true)
		|| !FPlatformProcess::CreatePipe(StderrChildRead, StderrChildWrite, false))
	{
		OutError = TEXT("Could not create worker stdin/stdout/stderr pipes.");
		FPlatformProcess::ClosePipe(StdoutChildRead, StdoutChildWrite);
		FPlatformProcess::ClosePipe(StdinChildRead, StdinChildWrite);
		FPlatformProcess::ClosePipe(StderrChildRead, StderrChildWrite);
		return false;
	}

	const FString PythonPath = FPaths::ConvertRelativePathToFull(Config.PythonExecutable);
	const FString ScriptPath = FPaths::ConvertRelativePathToFull(Config.WorkerScript);
	const FString StatePath = FPaths::ConvertRelativePathToFull(Config.StateDirectory);
	FString Arguments = FString::Printf(
		TEXT("\"%s\" --state-dir \"%s\" --world-id \"%s\" --dt %.17g --physical-steps %d --seed %d"),
		*ScriptPath, *StatePath, *Config.WorldId, Config.DeltaTime,
		Config.PhysicalStepsPerTick, Config.Seed);
	if (!Config.InitialWorldPath.IsEmpty())
	{
		Arguments += FString::Printf(TEXT(" --initial-world \"%s\""),
			*FPaths::ConvertRelativePathToFull(Config.InitialWorldPath));
	}
	if (Config.LaunchMode == EEdgeWorldWorkerLaunchMode::Universe)
        Arguments = FString::Printf(TEXT("-m engine.universe_authority.worker --owner-config \"%s\""), *Config.OwnerConfigPath);
    const FString WorkingRoot=FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::GetPath(ScriptPath),TEXT("../..")));
    ProcessHandle = FPlatformProcess::CreateProc(*PythonPath, *Arguments, false, true, true,
        &WorkerPid, 0, Config.LaunchMode==EEdgeWorldWorkerLaunchMode::Universe?*WorkingRoot:nullptr, StdoutChildWrite, StdinChildRead, StderrChildWrite);

	// The parent owns only stdout/stderr read ends and the stdin write end.
	void* NullHandle = nullptr;
	FPlatformProcess::ClosePipe(StdoutChildWrite, NullHandle);
	FPlatformProcess::ClosePipe(StdinChildRead, NullHandle);
	FPlatformProcess::ClosePipe(StderrChildWrite, NullHandle);
	if (!ProcessHandle.IsValid())
	{
		FPlatformProcess::ClosePipe(StdoutChildRead, NullHandle);
		FPlatformProcess::ClosePipe(NullHandle, StdinChildWrite);
		FPlatformProcess::ClosePipe(StderrChildRead, NullHandle);
		OutError = FString::Printf(TEXT("Could not launch edgeWorld worker: %s"), *PythonPath);
		return false;
	}

	StdoutReadPipe = StdoutChildRead;
	StdinWritePipe = StdinChildWrite;
	StderrReadPipe = StderrChildRead;
	PendingStdout.Reset();
 PendingRaw.Reset(); ++Generation; bNeedsUniverseStatus=true;
	return true;
}

bool FEdgeWorldProcessTransport::TraceFileExclusive(const FString& Path,TArrayView<const uint8> Bytes)
{
#if PLATFORM_MAC
 FTCHARToUTF8 U(*Path);int Fd=open(U.Get(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(Fd<0)return false;
 bool OK=true;int64 Done=0;while(Done<Bytes.Num()){ssize_t N=write(Fd,Bytes.GetData()+Done,Bytes.Num()-Done);if(N<0&&errno==EINTR)continue;if(N<=0){OK=false;break;}Done+=N;}if(fsync(Fd))OK=false;if(close(Fd))OK=false;return OK;
#else
 return false;
#endif
}
bool FEdgeWorldProcessTransport::TraceReserve(int64 Bytes)
{
 if(Config.TraceDirectory.IsEmpty())return true;
#if PLATFORM_MAC
 FTCHARToUTF8 P(*Config.TraceDirectory);struct stat D;if(FPaths::IsRelative(Config.TraceDirectory)||lstat(P.Get(),&D)||!S_ISDIR(D.st_mode)||D.st_uid!=getuid()||(D.st_mode&0777)!=0700||!Config.TraceBudget)return false;
 FScopeLock Lock(&Config.TraceBudget->Mutex);return Config.TraceBudget->Bytes+Bytes<=64LL*1024*1024;
#else
 return false;
#endif
}
bool FEdgeWorldProcessTransport::TraceRaw(const FString& Direction,TArrayView<const uint8> Bytes,const FEdgeWorldRequest& Request,int32 Written)
{
 if(Config.TraceDirectory.IsEmpty())return true;
 if(!TraceReserve(Bytes.Num()+4096))return false;
 FScopeLock Lock(&Config.TraceBudget->Mutex);
 FString Stem=FString::Printf(TEXT("%s-%08llu"),*TracePrefix,(unsigned long long)++TraceSerial);
 auto M=MakeShared<FJsonObject>();M->SetStringField(TEXT("direction"),Direction);M->SetStringField(TEXT("utc"),FDateTime::UtcNow().ToIso8601());M->SetNumberField(TEXT("monotonic_seconds"),FPlatformTime::Seconds());M->SetStringField(TEXT("serial"),LexToString(TraceSerial));M->SetStringField(TEXT("request_serial"),LexToString(RequestSerial));M->SetStringField(TEXT("generation"),LexToString(Generation));M->SetNumberField(TEXT("worker_pid"),WorkerPid);M->SetNumberField(TEXT("host_pid"),FPlatformProcess::GetCurrentProcessId());M->SetStringField(TEXT("request_id"),Request.RequestId);M->SetStringField(TEXT("operation"),Request.Operation);M->SetStringField(TEXT("raw_file"),Stem+TEXT(".bin"));M->SetNumberField(TEXT("byte_count"),Bytes.Num());M->SetNumberField(TEXT("written_bytes"),Written);
 FString Text;FJsonSerializer::Serialize(M,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));FTCHARToUTF8 U(*Text);int64 Cost=Bytes.Num()+U.Length();if(Config.TraceBudget->Bytes+Cost>64LL*1024*1024)return false;
 // Reserve before I/O so partial trace failures cannot free/reuse budget or overwrite originals.
 Config.TraceBudget->Bytes+=Cost;
 return TraceFileExclusive(Config.TraceDirectory/(Stem+TEXT(".bin")),Bytes)&&TraceFileExclusive(Config.TraceDirectory/(Stem+TEXT(".json")),MakeArrayView(reinterpret_cast<const uint8*>(U.Get()),U.Length()));
}

FEdgeWorldResponse FEdgeWorldProcessTransport::ExchangeUniverse(const FEdgeWorldRequest& Request)
{
 FScopeLock Lock(&RequestMutex);
 LastTraceRequest=Request;
 FEdgeWorldResponse Response; Response.RequestId = Request.RequestId;
 FString Error;
 if(!TraceReserve(4*1024*1024)){Response.ErrorCode=TEXT("trace_limit_or_unsafe");return Response;}
 if (!EnsureStarted(Error)) { Response.ErrorCode=TEXT("worker_start_failed"); Response.ErrorMessage=Error; return Response; }
 Response.ProcessGeneration=Generation; Response.WorkerPid=WorkerPid; ++RequestSerial;
 // A new owned channel must first establish a status binding. Never replay a write on lazy restart.
 if (bNeedsUniverseStatus && Request.Operation != TEXT("status"))
 { Response.ErrorCode=TEXT("worker_generation_changed"); return Response; }
 FTCHARToUTF8 Input(*Request.JsonLine);
 if (Input.Length()>1048577) { Response.ErrorCode=TEXT("LIMIT"); return Response; }
 if(!TraceRaw(TEXT("request"),MakeArrayView(reinterpret_cast<const uint8*>(Input.Get()),Input.Length()),Request)){Response.ErrorCode=TEXT("trace_write_failed");StopProcess(true);return Response;}
 int32 Written=0;
 if (!FPlatformProcess::WritePipe(StdinWritePipe,reinterpret_cast<const uint8*>(Input.Get()),Input.Length(),&Written) || Written!=Input.Length())
 { TraceRaw(TEXT("write-result"),{},Request,Written);Response.ErrorCode=TEXT("worker_write_failed"); StopProcess(true); return Response; }
 if(!TraceRaw(TEXT("write-result"),{},Request,Written)){Response.ErrorCode=TEXT("trace_write_failed");StopProcess(true);return Response;}
 const double Deadline=FPlatformTime::Seconds()+Config.RequestTimeoutSeconds;
 int32 DiagnosticBytes=0;
 while (FPlatformTime::Seconds()<Deadline)
 {
  // Mac's public byte read is <=32768B. Stop before reading if the trace cannot preserve that chunk.
  if(!TraceReserve(2*32768+8192)){Response.ErrorCode=TEXT("trace_limit_or_unsafe");StopProcess(true);return Response;}
  TArray<uint8> Chunk; FPlatformProcess::ReadPipeToArray(StdoutReadPipe,Chunk);
  if(!Chunk.IsEmpty()&&!TraceRaw(TEXT("stdout-chunk"),Chunk,Request)){Response.ErrorCode=TEXT("trace_write_failed");StopProcess(true);return Response;}PendingRaw.Append(Chunk);
  if (StderrReadPipe)
  {
   TArray<uint8> Diagnostic;FPlatformProcess::ReadPipeToArray(StderrReadPipe,Diagnostic);
   if(!Diagnostic.IsEmpty()&&!TraceRaw(TEXT("stderr-chunk"),Diagnostic,Request)){Response.ErrorCode=TEXT("trace_write_failed");StopProcess(true);return Response;}DiagnosticBytes+=Diagnostic.Num();
   // Do not print untrusted/private diagnostics into the UI log.
   if(DiagnosticBytes>65536){Response.ErrorCode=TEXT("worker_stderr_limit");StopProcess(true);return Response;}
  }
  int32 LF=PendingRaw.IndexOfByKey(uint8('\n'));
  if((LF==INDEX_NONE && PendingRaw.Num()>1048576) || LF>1048576)
  {Response.ErrorCode=TEXT("LIMIT");StopProcess(true);return Response;}
  if(LF!=INDEX_NONE)
  {
   // One in-flight request: extra unsolicited stdout is a channel violation.
   if(PendingRaw.Num()!=LF+1){Response.ErrorCode=TEXT("unsolicited_worker_response");StopProcess(true);return Response;}
   if(!TraceRaw(TEXT("response-complete"),{},Request)){Response.ErrorCode=TEXT("trace_write_failed");StopProcess(true);return Response;}
   Response.RawJsonl=MoveTemp(PendingRaw);PendingRaw.Reset();Response.bSuccess=true; if(Request.Operation==TEXT("status"))bNeedsUniverseStatus=false; return Response;
  }
  if(!FPlatformProcess::IsProcRunning(ProcessHandle))
  {Response.ErrorCode=TEXT("worker_exited");StopProcess(false);return Response;}
  FPlatformProcess::Sleep(.01f);
 }
 Response.ErrorCode=TEXT("worker_timeout");StopProcess(true);return Response;
}

FEdgeWorldResponse FEdgeWorldProcessTransport::Exchange(const FEdgeWorldRequest& Request)
{
 if (Config.LaunchMode == EEdgeWorldWorkerLaunchMode::Universe) return ExchangeUniverse(Request);
	FEdgeWorldResponse Response;
	Response.RequestId = Request.RequestId;
	{
		FScopeLock Lock(&RequestMutex);
		FString StartError;
		if (!EnsureStarted(StartError))
		{
			Response.ErrorCode = bShutdown ? TEXT("worker_stopped") : TEXT("worker_start_failed");
			Response.ErrorMessage = MoveTemp(StartError);
			return Response;
		}

		FTCHARToUTF8 Utf8Request(*Request.JsonLine);
		int32 BytesWritten = 0;
		if (!FPlatformProcess::WritePipe(StdinWritePipe,
			reinterpret_cast<const uint8*>(Utf8Request.Get()), Utf8Request.Length(), &BytesWritten)
			|| BytesWritten != Utf8Request.Length())
		{
			Response.ErrorCode = TEXT("worker_write_failed");
			Response.ErrorMessage = TEXT("Could not write the complete JSONL request to worker stdin.");
			StopProcess(true);
			return Response;
		}

		const double Deadline = FPlatformTime::Seconds() + Config.RequestTimeoutSeconds;
		FString CompleteLine;
		while (FPlatformTime::Seconds() < Deadline)
		{
			if (StderrReadPipe)
			{
				const FString Diagnostic = FPlatformProcess::ReadPipe(StderrReadPipe);
				if (!Diagnostic.IsEmpty())
				{
					UE_LOG(LogTemp, Warning, TEXT("edgeWorld worker: %s"), *Diagnostic.TrimStartAndEnd());
				}
			}
			PendingStdout += FPlatformProcess::ReadPipe(StdoutReadPipe);
			int32 NewlineIndex = INDEX_NONE;
			if (PendingStdout.FindChar(TEXT('\n'), NewlineIndex))
			{
				CompleteLine = PendingStdout.Left(NewlineIndex).TrimStartAndEnd();
				PendingStdout = PendingStdout.Mid(NewlineIndex + 1);
				break;
			}
			if (!FPlatformProcess::IsProcRunning(ProcessHandle))
			{
				PendingStdout += FPlatformProcess::ReadPipe(StdoutReadPipe);
				if (PendingStdout.FindChar(TEXT('\n'), NewlineIndex))
				{
					CompleteLine = PendingStdout.Left(NewlineIndex).TrimStartAndEnd();
					PendingStdout = PendingStdout.Mid(NewlineIndex + 1);
					break;
				}
				int32 ExitCode = INDEX_NONE;
				FPlatformProcess::GetProcReturnCode(ProcessHandle, &ExitCode);
				Response.ErrorCode = TEXT("worker_exited");
				Response.ErrorMessage = FString::Printf(TEXT("Worker exited before replying (code %d)."), ExitCode);
				StopProcess(false);
				return Response;
			}
			FPlatformProcess::Sleep(0.01f);
		}
		if (CompleteLine.IsEmpty())
		{
			Response.ErrorCode = TEXT("worker_timeout");
			Response.ErrorMessage = FString::Printf(TEXT("Worker did not reply within %.1f seconds."), Config.RequestTimeoutSeconds);
			StopProcess(true);
			return Response;
		}

		TSharedPtr<FJsonObject> JsonResponse;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(CompleteLine);
		if (!FJsonSerializer::Deserialize(Reader, JsonResponse) || !JsonResponse.IsValid())
		{
			Response.ErrorCode = TEXT("invalid_worker_response");
			Response.ErrorMessage = TEXT("Worker reply was not a valid JSON object.");
			Response.JsonLine = MoveTemp(CompleteLine);
			StopProcess(true);
			return Response;
		}

		Response.JsonLine = MoveTemp(CompleteLine);
		JsonResponse->TryGetStringField(TEXT("request_id"), Response.RequestId);
		if (Response.RequestId.IsEmpty() || Response.RequestId != Request.RequestId)
		{
			Response.ErrorCode = TEXT("worker_request_id_mismatch");
			Response.ErrorMessage = TEXT("Worker response request_id did not match the in-flight request.");
			StopProcess(true);
			return Response;
		}
		int32 ProtocolVersion = 0;
		if (!JsonResponse->TryGetNumberField(TEXT("protocol_version"), ProtocolVersion) || ProtocolVersion != 1)
		{
			Response.ErrorCode = TEXT("unsupported_worker_protocol");
			Response.ErrorMessage = TEXT("Worker response did not use protocol_version 1.");
			StopProcess(true);
			return Response;
		}
		JsonResponse->TryGetBoolField(TEXT("ok"), Response.bSuccess);
		if (!Response.bSuccess)
		{
			const TSharedPtr<FJsonObject>* ErrorObject = nullptr;
			if (JsonResponse->TryGetObjectField(TEXT("error"), ErrorObject) && ErrorObject && ErrorObject->IsValid())
			{
				(*ErrorObject)->TryGetStringField(TEXT("code"), Response.ErrorCode);
				(*ErrorObject)->TryGetStringField(TEXT("message"), Response.ErrorMessage);
			}
			if (Response.ErrorCode.IsEmpty())
			{
				Response.ErrorCode = TEXT("worker_request_failed");
			}
		}
	}
	return Response;
}

void FEdgeWorldProcessTransport::StopUniverseProcess(bool bFailure)
{
 // EOF is the normal owned-child shutdown protocol. Never infer exit0 from PID absence.
 bool bTraceComplete=true;
 if(StdinWritePipe)
 {
  void* Pipe=StdinWritePipe;StdinWritePipe=nullptr;void* Null=nullptr;FPlatformProcess::ClosePipe(Null,Pipe);
  bTraceComplete=TraceRaw(TEXT("stdin-eof"),{},LastTraceRequest);
 }
 if(ProcessHandle.IsValid())
 {
  FProcHandle Closing=ProcessHandle;ProcessHandle=FProcHandle();
  bool bForced=false,bHardKilled=false;int64 TailBytes=0;constexpr int64 TailCap=1048576;
  auto Drain=[&](bool& ReadAny)
  {
   ReadAny=false;
   if(TailBytes+65536>TailCap||!TraceReserve(2*32768+8192))return false;
   for(int32 I=0;I<2;++I)
   {
    void* Pipe=I==0?StdoutReadPipe:StderrReadPipe;if(!Pipe)continue;TArray<uint8> Chunk;FPlatformProcess::ReadPipeToArray(Pipe,Chunk);
    if(!Chunk.IsEmpty()){ReadAny=true;TailBytes+=Chunk.Num();if(!TraceRaw(I==0?TEXT("shutdown-stdout-chunk"):TEXT("shutdown-stderr-chunk"),Chunk,LastTraceRequest))return false;}
   }
   return true;
  };
  const double GraceDeadline=FPlatformTime::Seconds()+8.;
  while(FPlatformTime::Seconds()<GraceDeadline)
  {
   bool Any=false;if(!Drain(Any)){bTraceComplete=false;break;}
   if(!FPlatformProcess::IsProcRunning(Closing))
   {
    while(Any){if(!Drain(Any)){bTraceComplete=false;break;}}
    break;
   }
   FPlatformProcess::Sleep(.01f);
  }
  if(FPlatformProcess::IsProcRunning(Closing))
  {
   bForced=true;bFailure=true;FPlatformProcess::TerminateProc(Closing,true);
   const double TermDeadline=FPlatformTime::Seconds()+.5;
   while(FPlatformProcess::IsProcRunning(Closing)&&FPlatformTime::Seconds()<TermDeadline)
   {bool Any=false;if(!Drain(Any))bTraceComplete=false;FPlatformProcess::Sleep(.01f);}
#if PLATFORM_MAC
   if(FPlatformProcess::IsProcRunning(Closing)&&int64(Closing.Get())==int64(WorkerPid))
   {bHardKilled=true;kill(pid_t(WorkerPid),SIGKILL);}
#endif
   const double KillDeadline=FPlatformTime::Seconds()+.5;
   while(FPlatformProcess::IsProcRunning(Closing)&&FPlatformTime::Seconds()<KillDeadline)FPlatformProcess::Sleep(.01f);
  }
  bool bReaped=!FPlatformProcess::IsProcRunning(Closing);int32 Exit=INDEX_NONE;bool bHaveCode=false;
  if(bReaped){FPlatformProcess::WaitForProc(Closing);bHaveCode=FPlatformProcess::GetProcReturnCode(Closing,&Exit);}
  bool Any=false;if(!Drain(Any))bTraceComplete=false;while(Any){if(!Drain(Any)){bTraceComplete=false;break;}}
  auto E=MakeShared<FJsonObject>();E->SetBoolField(TEXT("return_code_available"),bHaveCode);if(bHaveCode)E->SetNumberField(TEXT("exit_code"),Exit);else E->SetField(TEXT("exit_code"),MakeShared<FJsonValueNull>());
  E->SetNumberField(TEXT("worker_pid"),WorkerPid);E->SetStringField(TEXT("generation"),LexToString(Generation));E->SetStringField(TEXT("stop_kind"),bForced?TEXT("forced"):TEXT("normal"));E->SetBoolField(TEXT("hard_kill_sent"),bHardKilled);E->SetBoolField(TEXT("reaped"),bReaped);E->SetBoolField(TEXT("trace_complete"),bTraceComplete);E->SetBoolField(TEXT("operational_failure"),bFailure||!bReaped||!bHaveCode||Exit!=0||!bTraceComplete);E->SetNumberField(TEXT("tail_bytes"),double(TailBytes));
  FString Text;FJsonSerializer::Serialize(E,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));FTCHARToUTF8 U(*Text);
  if(!TraceRaw(TEXT("worker-exit"),MakeArrayView(reinterpret_cast<const uint8*>(U.Get()),U.Length()),LastTraceRequest)||bFailure||!bReaped||!bHaveCode||Exit!=0||!bTraceComplete)
   UE_LOG(LogTemp,Warning,TEXT("Universe child lifecycle failed: pid=%u reaped=%d return_code_available=%d forced=%d trace_complete=%d"),WorkerPid,bReaped,bHaveCode,bForced,bTraceComplete);
  FPlatformProcess::CloseProc(Closing);
 }
 for(void** Field:{&StdoutReadPipe,&StderrReadPipe})if(*Field){void* Pipe=*Field;*Field=nullptr;void* Null=nullptr;FPlatformProcess::ClosePipe(Pipe,Null);}
 PendingRaw.Reset();PendingStdout.Reset();bNeedsUniverseStatus=true;
}

void FEdgeWorldProcessTransport::StopProcess(bool bTerminate)
{
 if(Config.LaunchMode==EEdgeWorldWorkerLaunchMode::Universe){StopUniverseProcess(bTerminate);return;}
	if (StdinWritePipe)
	{
		void* PipeToClose = StdinWritePipe;
		StdinWritePipe = nullptr;
		void* NullHandle = nullptr;
		FPlatformProcess::ClosePipe(NullHandle, PipeToClose);
	}
	if (ProcessHandle.IsValid())
	{
		FProcHandle ProcessToClose = ProcessHandle;
		ProcessHandle = FProcHandle();
		if (bTerminate && FPlatformProcess::IsProcRunning(ProcessToClose))
		{
			FPlatformProcess::TerminateProc(ProcessToClose, true);
		}
		else if (FPlatformProcess::IsProcRunning(ProcessToClose))
		{
			FPlatformProcess::WaitForProc(ProcessToClose);
		}
		FPlatformProcess::CloseProc(ProcessToClose);
	}
	if (StdoutReadPipe)
	{
		void* PipeToClose = StdoutReadPipe;
		StdoutReadPipe = nullptr;
		void* NullHandle = nullptr;
		FPlatformProcess::ClosePipe(PipeToClose, NullHandle);
	}
	if (StderrReadPipe)
	{
		void* PipeToClose = StderrReadPipe;
		StderrReadPipe = nullptr;
		void* NullHandle = nullptr;
		FPlatformProcess::ClosePipe(PipeToClose, NullHandle);
	}
	PendingStdout.Reset();
}

void FEdgeWorldProcessTransport::Shutdown()
{
	FScopeLock Lock(&RequestMutex);
	if (!bShutdown)
	{
		bShutdown = true;
		StopProcess(false);
	}
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
	constexpr int64 MaxSafeJsonInteger = (1LL << 53) - 1;
	if (ExpectedRevision < 0 || TargetTick < 0 || ExpectedRevision > MaxSafeJsonInteger || TargetTick > MaxSafeJsonInteger)
	{
		Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.ErrorCode = TEXT("integer_out_of_range");
			Response.ErrorMessage = TEXT("Tick and revision must be safe non-negative JSON integers.");
			Handler(MoveTemp(Response));
		});
		return;
	}
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("world_id"), WorldId);
	Payload->SetNumberField(TEXT("expected_revision"), static_cast<double>(ExpectedRevision));
	Payload->SetNumberField(TEXT("target_tick"), static_cast<double>(TargetTick));
	Payload->SetStringField(TEXT("command_id"), CommandId);
	SendOperation(TEXT("advance"), Payload, MoveTemp(Handler));
}

void FEdgeWorldJsonlClient::Advance(const FString& WorldId, int64 ExpectedRevision, int64 TargetTick,
	const FString& CommandId, const FString& EnvironmentJson, FEdgeWorldResponseHandler Handler) const
{
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(EnvironmentJson);
	TSharedPtr<FJsonObject> Environment;
	if (!FJsonSerializer::Deserialize(Reader, Environment) || !Environment.IsValid())
	{
		Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.ErrorCode = TEXT("invalid_environment");
			Response.ErrorMessage = TEXT("Environment must be a JSON object.");
			Handler(MoveTemp(Response));
		});
		return;
	}
	FString Phase;
	double Moisture = -1.0;
	double Light = -1.0;
	if (!Environment->TryGetStringField(TEXT("phase"), Phase)
		|| (Phase != TEXT("shaoyang") && Phase != TEXT("taiyang")
			&& Phase != TEXT("shaoyin") && Phase != TEXT("taiyin"))
		|| !Environment->TryGetNumberField(TEXT("moisture"), Moisture)
		|| !Environment->TryGetNumberField(TEXT("light"), Light)
		|| !FMath::IsFinite(Moisture) || !FMath::IsFinite(Light)
		|| Moisture < 0.0 || Moisture > 1.0 || Light < 0.0 || Light > 1.0)
	{
		Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.ErrorCode = TEXT("invalid_environment");
			Response.ErrorMessage = TEXT("Environment requires a supported phase and finite moisture/light values in [0, 1].");
			Handler(MoveTemp(Response));
		});
		return;
	}
	const int64 MaxSafeJsonInteger = (1LL << 53) - 1;
	if (ExpectedRevision < 0 || TargetTick < 0 || ExpectedRevision > MaxSafeJsonInteger
		|| TargetTick > MaxSafeJsonInteger || CommandId.IsEmpty())
	{
		Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.ErrorCode = TEXT("invalid_advance");
			Response.ErrorMessage = TEXT("Advance requires safe non-negative tick/revision values and a command ID.");
			Handler(MoveTemp(Response));
		});
		return;
	}
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("world_id"), WorldId);
	Payload->SetNumberField(TEXT("expected_revision"), static_cast<double>(ExpectedRevision));
	Payload->SetNumberField(TEXT("target_tick"), static_cast<double>(TargetTick));
	Payload->SetStringField(TEXT("command_id"), CommandId);
	Payload->SetObjectField(TEXT("environment"), Environment.ToSharedRef());
	SendOperation(TEXT("advance"), Payload, MoveTemp(Handler));
}

void FEdgeWorldJsonlClient::AdvanceOrigin(const FString& WorldId, int64 ExpectedRevision, int64 TargetTick,
	const FString& CommandId, FEdgeWorldResponseHandler Handler) const
{
	constexpr int64 MaxSafeJsonInteger = (1LL << 53) - 1;
	if (WorldId.IsEmpty() || CommandId.IsEmpty() || ExpectedRevision < 0 || TargetTick < 0
		|| ExpectedRevision > MaxSafeJsonInteger || TargetTick > MaxSafeJsonInteger)
	{
		Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.ErrorCode = TEXT("invalid_advance");
			Response.ErrorMessage = TEXT("Origin advance requires world/command IDs and safe non-negative revision/tick.");
			Handler(MoveTemp(Response));
		});
		return;
	}
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("world_id"), WorldId);
	Payload->SetNumberField(TEXT("expected_revision"), static_cast<double>(ExpectedRevision));
	Payload->SetNumberField(TEXT("target_tick"), static_cast<double>(TargetTick));
	Payload->SetStringField(TEXT("command_id"), CommandId);
	Payload->SetStringField(TEXT("origin_action"), TEXT("reveal_world_spirit"));
	SendOperation(TEXT("advance"), Payload, MoveTemp(Handler));
}

void FEdgeWorldJsonlClient::Observe(const FString& WorldId, int64 LogicalTick, const FString& ViewSpecJson,
	FEdgeWorldResponseHandler Handler) const
{
	constexpr int64 MaxSafeJsonInteger = (1LL << 53) - 1;
	if (LogicalTick < 0 || LogicalTick > MaxSafeJsonInteger)
	{
		Async(EAsyncExecution::ThreadPool, [Handler = MoveTemp(Handler)]() mutable
		{
			FEdgeWorldResponse Response;
			Response.ErrorCode = TEXT("integer_out_of_range");
			Response.ErrorMessage = TEXT("Logical tick must be a safe non-negative JSON integer.");
			Handler(MoveTemp(Response));
		});
		return;
	}
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
	const TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
		TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonLine);
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

namespace
{
	bool ReadExactJsonInteger(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, int64& OutValue)
	{
		double Number = 0.0;
		if (!Object.IsValid() || !Object->TryGetNumberField(Field, Number) || !FMath::IsFinite(Number)
			|| Number < 0.0 || Number > static_cast<double>((1LL << 53) - 1) || FMath::FloorToDouble(Number) != Number)
		{
			return false;
		}
		OutValue = static_cast<int64>(Number);
		return true;
	}

	bool ReadUnitNumber(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, double& OutValue)
	{
		return Object.IsValid() && Object->TryGetNumberField(Field, OutValue)
			&& FMath::IsFinite(OutValue) && OutValue >= 0.0 && OutValue <= 1.0;
	}
}

bool EdgeWorldParseTreeObservation(const FEdgeWorldResponse& Response, const FString& ExpectedWorldId,
	int64 ExpectedTick, int64 ExpectedWatermark, const FString& ExpectedRulesetVersion,
	const FString& ExpectedProjectionVersion, FEdgeWorldTreeObservation& OutObservation, FString& OutError)
{
	if (!Response.bSuccess)
	{
		OutError = FString::Printf(TEXT("Observe failed: %s - %s"), *Response.ErrorCode, *Response.ErrorMessage);
		return false;
	}
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response.JsonLine);
	TSharedPtr<FJsonObject> Envelope;
	if (!FJsonSerializer::Deserialize(Reader, Envelope) || !Envelope.IsValid())
	{
		OutError = TEXT("Observe response is not valid JSON.");
		return false;
	}
	const TSharedPtr<FJsonObject>* ResultPtr = nullptr;
	if (!Envelope->TryGetObjectField(TEXT("result"), ResultPtr) || !ResultPtr || !ResultPtr->IsValid())
	{
		OutError = TEXT("Observe response is missing result.");
		return false;
	}
	const TSharedPtr<FJsonObject> Result = *ResultPtr;
	FString WorldId;
	int64 LogicalTick = INDEX_NONE;
	int64 SourceRevision = INDEX_NONE;
	int64 Watermark = INDEX_NONE;
	if (!Result->TryGetStringField(TEXT("world_id"), WorldId) || WorldId != ExpectedWorldId
		|| !ReadExactJsonInteger(Result, TEXT("logical_tick"), LogicalTick) || LogicalTick != ExpectedTick
		|| !ReadExactJsonInteger(Result, TEXT("source_revision"), SourceRevision) || SourceRevision != ExpectedWatermark
		|| !ReadExactJsonInteger(Result, TEXT("watermark"), Watermark) || Watermark != ExpectedWatermark)
	{
		OutError = TEXT("Observe world, logical_tick, source_revision, or watermark did not match the exact requested sample.");
		return false;
	}
	const TSharedPtr<FJsonObject>* SamplePtr = nullptr;
	if (!Result->TryGetObjectField(TEXT("sample"), SamplePtr) || !SamplePtr || !SamplePtr->IsValid())
	{
		OutError = TEXT("Observe response is missing sample.");
		return false;
	}
	const TSharedPtr<FJsonObject> Sample = *SamplePtr;
	FEdgeWorldTreeObservation Parsed;
	Parsed.LogicalTick = LogicalTick;
	Parsed.SourceRevision = SourceRevision;
	Parsed.Watermark = Watermark;
	if (!Sample->TryGetStringField(TEXT("seed_id"), Parsed.SeedId) || Parsed.SeedId.IsEmpty()
		|| !Sample->TryGetStringField(TEXT("stage"), Parsed.Stage)
		|| (Parsed.Stage != TEXT("seed") && Parsed.Stage != TEXT("seedling") && Parsed.Stage != TEXT("mature")
			&& Parsed.Stage != TEXT("declining") && Parsed.Stage != TEXT("dead"))
		|| !ReadUnitNumber(Sample, TEXT("health"), Parsed.Health)
		|| !ReadUnitNumber(Sample, TEXT("biomass"), Parsed.Biomass)
		|| !ReadUnitNumber(Sample, TEXT("water_reserve"), Parsed.WaterReserve)
		|| !Sample->TryGetStringField(TEXT("ruleset_version"), Parsed.RulesetVersion)
		|| Parsed.RulesetVersion != ExpectedRulesetVersion)
	{
		OutError = TEXT("Observe sample has invalid identity, stage, scalar state, or ruleset_version.");
		return false;
	}
	const TSharedPtr<FJsonValue>* TreeIdValue = Sample->Values.Find(TEXT("tree_id"));
	if (!TreeIdValue)
	{
		OutError = TEXT("Observe sample is missing tree_id.");
		return false;
	}
	if ((*TreeIdValue)->Type == EJson::Null)
	{
		if (LogicalTick != 0 || Parsed.Stage != TEXT("seed"))
		{
			OutError = TEXT("Only the initial seed observation may have a null tree_id.");
			return false;
		}
	}
	else if (!(*TreeIdValue)->TryGetString(Parsed.TreeId) || Parsed.TreeId.IsEmpty() || Parsed.Stage == TEXT("seed"))
	{
		OutError = TEXT("Germinated observations require a stable tree_id; the initial seed requires null.");
		return false;
	}
	if (LogicalTick == 0 && (Parsed.Stage != TEXT("seed") || !Parsed.TreeId.IsEmpty()))
	{
		OutError = TEXT("Tick zero must describe an un-germinated seed with a null tree_id.");
		return false;
	}
	const TSharedPtr<FJsonValue>* PhaseValue = Sample->Values.Find(TEXT("phase"));
	if (!PhaseValue)
	{
		OutError = TEXT("Observe sample is missing phase.");
		return false;
	}
	if ((*PhaseValue)->Type == EJson::Null)
	{
		if (LogicalTick != 0)
		{
			OutError = TEXT("Only tick zero may have a null phase.");
			return false;
		}
	}
	else if (!(*PhaseValue)->TryGetString(Parsed.Phase)
		|| (Parsed.Phase != TEXT("shaoyang") && Parsed.Phase != TEXT("taiyang")
			&& Parsed.Phase != TEXT("shaoyin") && Parsed.Phase != TEXT("taiyin")))
	{
		OutError = TEXT("Observe sample has an unsupported phase.");
		return false;
	}
	if ((LogicalTick == 0 && !Parsed.Phase.IsEmpty()) || (LogicalTick > 0 && Parsed.Phase.IsEmpty()))
	{
		OutError = TEXT("Tick zero requires a null phase; later ticks require a supported phase.");
		return false;
	}
	if (!Result->TryGetStringField(TEXT("projection_version"), Parsed.ProjectionVersion)
		|| Parsed.ProjectionVersion != ExpectedProjectionVersion
		|| !Result->TryGetStringField(TEXT("state_hash"), Parsed.StateHash) || Parsed.StateHash.IsEmpty()
		|| !Result->TryGetStringField(TEXT("event_hash"), Parsed.EventHash) || Parsed.EventHash.IsEmpty())
	{
		OutError = TEXT("Observe response has invalid projection_version or missing state/event hash.");
		return false;
	}
	const TSharedPtr<FJsonObject>* ViewSpecPtr = nullptr;
	if (!Result->TryGetObjectField(TEXT("view_spec"), ViewSpecPtr) || !ViewSpecPtr || !ViewSpecPtr->IsValid())
	{
		OutError = TEXT("Observe response is missing echoed view_spec.");
		return false;
	}
	int64 EchoedWatermark = INDEX_NONE;
	if (!ReadExactJsonInteger(*ViewSpecPtr, TEXT("watermark"), EchoedWatermark) || EchoedWatermark != ExpectedWatermark)
	{
		OutError = TEXT("Observe response view_spec watermark did not match the requested sample.");
		return false;
	}
	FString Region;
	FString Observer;
	FString Resolution;
	const TSharedPtr<FJsonObject> ViewSpec = *ViewSpecPtr;
	const TSharedPtr<FJsonObject>* ErrorBudgetPtr = nullptr;
	const TSharedPtr<FJsonObject>* RulesPtr = nullptr;
	if (!ViewSpec->TryGetStringField(TEXT("region"), Region) || Region != TEXT("single-tree-world")
		|| !ViewSpec->TryGetStringField(TEXT("observer"), Observer) || Observer != TEXT("ue-default-camera-v1")
		|| !ViewSpec->TryGetStringField(TEXT("resolution"), Resolution) || Resolution != TEXT("single-tree-proxy-v1")
		|| !ViewSpec->TryGetObjectField(TEXT("error_budget"), ErrorBudgetPtr) || !ErrorBudgetPtr || !ErrorBudgetPtr->IsValid()
		|| !ViewSpec->TryGetObjectField(TEXT("rules"), RulesPtr) || !RulesPtr || !RulesPtr->IsValid())
	{
		OutError = TEXT("Observe response view_spec does not match the fixed single-tree projection query.");
		return false;
	}
	FString SemanticState;
	FString VisualGeometry;
	FString EvolutionVersion;
	FString ProjectionVersionInQuery;
	if (!(*ErrorBudgetPtr)->TryGetStringField(TEXT("semantic_state"), SemanticState) || SemanticState != TEXT("exact")
		|| !(*ErrorBudgetPtr)->TryGetStringField(TEXT("visual_geometry"), VisualGeometry) || VisualGeometry != TEXT("unmeasured-proxy")
		|| !(*RulesPtr)->TryGetStringField(TEXT("evolution"), EvolutionVersion) || EvolutionVersion != ExpectedRulesetVersion
		|| !(*RulesPtr)->TryGetStringField(TEXT("projection"), ProjectionVersionInQuery)
		|| ProjectionVersionInQuery != ExpectedProjectionVersion)
	{
		OutError = TEXT("Observe response view_spec error budget or ruleset/projection query version did not match.");
		return false;
	}

	OutObservation = MoveTemp(Parsed);
	OutError.Reset();
	return true;
}
