#include "EdgeWorldCausalGameMode.h"

#include "EdgeWorldCausalActor.h"
#include "EdgeWorldCausalHud.h"
#include "EdgeWorldVisitorCharacter.h"
#include "EdgeWorldCausalObservation.h"
#include "EdgeWorldJsonlClient.h"

#include "Async/Async.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "HAL/PlatformMisc.h"
#include "HAL/IConsoleManager.h"
#include "InputCoreTypes.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	FAutoConsoleCommandWithWorld DumpCausalLightingEvidence(
		TEXT("edgeworld.DumpLightingEvidence"),
		TEXT("Log actual world lighting counts and runtime light mobility, then dump unbuilt interactions."),
		FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
		{
			if (!World || !IsInGameThread()) return;
			UE_LOG(LogTemp, Display, TEXT("Lighting evidence: world=%s NumLightingUnbuiltObjects=%u"),
				*World->GetPathName(), World->NumLightingUnbuiltObjects);
			for (TActorIterator<ADirectionalLight> It(World); It; ++It)
				UE_LOG(LogTemp, Display, TEXT("Lighting evidence: directional=%s mobility=%d"),
					*It->GetPathName(), static_cast<int32>(It->GetLightComponent()->GetMobility()));
			for (TActorIterator<ASkyLight> It(World); It; ++It)
				UE_LOG(LogTemp, Display, TEXT("Lighting evidence: sky=%s mobility=%d"),
					*It->GetPathName(), static_cast<int32>(It->GetLightComponent()->GetMobility()));
			if (GEngine) GEngine->Exec(World, TEXT("DumpUnbuiltLightInteractions"));
		}));

	bool ExactInt(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, int64& Value)
	{
		double N = 0;
		if (!Object.IsValid() || !Object->TryGetNumberField(Key, N) || !FMath::IsFinite(N)
			|| N < 0 || N > static_cast<double>((1LL << 53) - 1) || FMath::FloorToDouble(N) != N) return false;
		Value = static_cast<int64>(N); return true;
	}
	bool InfluenceInt(const TSharedPtr<FJsonObject>& Object, int64& Value)
	{
		double N = 0;
		if (!Object.IsValid() || !Object->TryGetNumberField(TEXT("influence_mm"), N)
			|| !FMath::IsFinite(N) || N < -1000 || N > 1000 || FMath::FloorToDouble(N) != N) return false;
		Value = static_cast<int64>(N); return true;
	}
	bool HexHash(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, FString& Value)
	{
		if (!Object.IsValid() || !Object->TryGetStringField(Key, Value) || Value.Len() != 64) return false;
		for (TCHAR C : Value) if (!FChar::IsHexDigit(C)) return false;
		return true;
	}
	bool Head(const FEdgeWorldResponse& Response, const FString& WorldId, bool bAdvance,
		int64 ExpectedTick, int64 ExpectedRevision, int64& Tick, int64& Revision,
		FString& OutConfigHash, FString& OutCheckpointHash, FString& OutStateHash, FString& OutEventHash)
	{
		if (!Response.bSuccess) return false;
		TSharedPtr<FJsonObject> Envelope;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response.JsonLine), Envelope) || !Envelope.IsValid()) return false;
		const TSharedPtr<FJsonObject>* Result = nullptr;
		FString Name, Schema, Probe, Seed;
		if (!Envelope->TryGetObjectField(TEXT("result"), Result) || !Result || !Result->IsValid()
			|| !(*Result)->TryGetStringField(TEXT("world_id"), Name) || Name != WorldId
			|| !(*Result)->TryGetStringField(TEXT("schema_version"), Schema) || Schema != TEXT("abstract-seed-genesis.v1")
			|| !(*Result)->TryGetStringField(TEXT("seed_id"), Seed) || Seed != WorldId + TEXT(":seed:0")
			|| !(*Result)->TryGetStringField(TEXT("physical_probe_id"), Probe) || Probe != WorldId + TEXT(":physical:0")
			|| !HexHash(*Result, TEXT("head_state_hash"), OutStateHash)
			|| !HexHash(*Result, TEXT("event_head_hash"), OutEventHash)
			|| !HexHash(*Result, TEXT("checkpoint_sha256"), OutCheckpointHash)
			|| !HexHash(*Result, TEXT("genesis_config_hash"), OutConfigHash)
			|| !ExactInt(*Result, TEXT("logical_tick"), Tick) || !ExactInt(*Result, TEXT("state_revision"), Revision)) return false;
		if (bAdvance)
		{
			FString Command;
			const TSharedPtr<FJsonObject>* Record = nullptr;
			int64 RecordTick = 0, RecordRevision = 0, Influence = 0;
			FString NodeId, EdgeId, CandidateHash, RecordCheckpoint, RecordState, RecordEvent;
			if (Tick != ExpectedTick || Revision != ExpectedRevision || Tick != Revision
				|| !(*Result)->TryGetStringField(TEXT("command_id"), Command)
				|| Command != FString::Printf(TEXT("causal-%lld"), static_cast<long long>(ExpectedTick))
				|| !(*Result)->TryGetObjectField(TEXT("record"), Record) || !Record || !Record->IsValid()
				|| !ExactInt(*Record, TEXT("logical_tick"), RecordTick) || RecordTick != Tick
				|| !ExactInt(*Record, TEXT("state_revision"), RecordRevision) || RecordRevision != Revision
				|| !InfluenceInt(*Record, Influence)
				|| !(*Record)->TryGetStringField(TEXT("node_id"), NodeId) || NodeId != WorldId + FString::Printf(TEXT(":node:%lld"), static_cast<long long>(Tick))
				|| !(*Record)->TryGetStringField(TEXT("edge_id"), EdgeId) || EdgeId != WorldId + FString::Printf(TEXT(":edge:%lld"), static_cast<long long>(Tick))
				|| !HexHash(*Record, TEXT("physics_candidate_hash"), CandidateHash)
				|| !HexHash(*Record, TEXT("checkpoint_sha256"), RecordCheckpoint) || RecordCheckpoint != OutCheckpointHash
				|| !HexHash(*Record, TEXT("state_hash"), RecordState) || RecordState != OutStateHash
				|| !HexHash(*Record, TEXT("event_hash"), RecordEvent) || RecordEvent != OutEventHash) return false;
		}
		return Tick == Revision;
	}
	FString JsonLine(const TSharedRef<FJsonObject>& Payload)
	{
		FString Line;
		FJsonSerializer::Serialize(Payload, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Line));
		Line.AppendChar(TEXT('\n'));
		return Line;
	}
}

AEdgeWorldCausalGameMode::AEdgeWorldCausalGameMode()
{
	PlayerControllerClass = AEdgeWorldCausalPlayerController::StaticClass();
	DefaultPawnClass = nullptr;
	HUDClass = AEdgeWorldCausalHud::StaticClass();
}
AEdgeWorldCausalGameMode::~AEdgeWorldCausalGameMode() = default;

void AEdgeWorldCausalGameMode::StartPlay()
{
	Super::StartPlay();
	UWorld* World = GetWorld();
	if (!World) return;
	CausalActor = World->SpawnActor<AEdgeWorldCausalActor>();
	if (ADirectionalLight* Light = World->SpawnActor<ADirectionalLight>(FVector(0, 0, 500), FRotator(-50, -35, 0)))
	{
		Light->GetLightComponent()->SetMobility(EComponentMobility::Movable);
		Light->GetLightComponent()->SetIntensity(40.0f);
	}
	if (ASkyLight* Light = World->SpawnActor<ASkyLight>())
	{
		Light->GetLightComponent()->SetMobility(EComponentMobility::Movable);
		Light->GetLightComponent()->SetIntensity(1.0f);
	}
	Camera = World->SpawnActor<ACameraActor>(FVector(750, -900, 700), FRotator(-27, 132, 0));
	if (Camera)
	{
		Camera->GetCameraComponent()->SetFieldOfView(55.0f);
	}
	if (APlayerController* Controller = World->GetFirstPlayerController())
	{
		FActorSpawnParameters Spawn;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
		AEdgeWorldVisitorCharacter* Visitor = World->SpawnActor<AEdgeWorldVisitorCharacter>(
			AEdgeWorldVisitorCharacter::EntryLocation(), FRotator(0, 90, 0), Spawn);
		if (Visitor && Visitor->ReturnToEntry())
		{
			Controller->Possess(Visitor);
			Controller->SetControlRotation(FRotator(0, 90, 0));
			Controller->SetViewTarget(Visitor);
		}
		else
		{
			if (Visitor) Visitor->Destroy();
			UE_LOG(LogTemp, Error, TEXT("Visitor safe entry unavailable"));
		}
	}
	StartWorker();
	UE_LOG(LogTemp, Display, TEXT("Causal world: Space advances; 0/1/2 history; H latest; R reconciles head; WASD walk; mouse/arrows look; Tab overview."));
}

void AEdgeWorldCausalGameMode::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Transport) Transport->Shutdown();
	Client.Reset(); Transport.Reset();
	Super::EndPlay(Reason);
}

void AEdgeWorldCausalGameMode::StartWorker()
{
	const FString Python = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_CAUSAL_PYTHON"));
	const FString Worker = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_CAUSAL_WORKER"));
	if (Python.IsEmpty() || Worker.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("Set EDGEWORLD_CAUSAL_PYTHON and EDGEWORLD_CAUSAL_WORKER for live causal world."));
		return;
	}
	FEdgeWorldWorkerLaunchConfig Config;
	Config.PythonExecutable = Python;
	Config.WorkerScript = Worker;
	Config.StateDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EdgeWorldCausal"), WorldId);
	Config.WorldId = WorldId;
	Config.RequestTimeoutSeconds = 60.0;
	Transport = MakeShared<FEdgeWorldProcessTransport, ESPMode::ThreadSafe>(MoveTemp(Config));
	Client = MakeShared<FEdgeWorldJsonlClient>(Transport.ToSharedRef());
	RefreshHead();
}

void AEdgeWorldCausalGameMode::RefreshHead()
{
	if (!Client || bRequestInFlight) return;
	bRequestInFlight = true;
	TWeakObjectPtr<AEdgeWorldCausalGameMode> Weak(this);
	Client->Status(WorldId, [Weak](FEdgeWorldResponse&& Response)
	{
		AsyncTask(ENamedThreads::GameThread, [Weak, Response = MoveTemp(Response)]() mutable
		{
			if (Weak.IsValid()) Weak->OnHead(MoveTemp(Response), false, 0, 0);
		});
	});
}

void AEdgeWorldCausalGameMode::OnHead(FEdgeWorldResponse&& Response, bool bAdvance, int64 ExpectedTick, int64 ExpectedRevision)
{
	bRequestInFlight = false;
	int64 Tick = 0, NewRevision = 0;
	FString ConfigHash, CheckpointHash, StateHash, EventHash;
	if (!Head(Response, WorldId, bAdvance, ExpectedTick, ExpectedRevision,
		Tick, NewRevision, ConfigHash, CheckpointHash, StateHash, EventHash)
		|| (!bAdvance && Tick < HeadGate.LatestTick)
		|| (!HeadGate.LatestConfigHash.IsEmpty() && ConfigHash != HeadGate.LatestConfigHash))
	{
		UE_LOG(LogTemp, Error, TEXT("Causal head rejected: %s %s"), *Response.ErrorCode, *Response.ErrorMessage);
		return;
	}
	HeadGate.Stage(Tick, NewRevision, ConfigHash, CheckpointHash, StateHash, EventHash);
	ObserveAt(Tick);
}

void AEdgeWorldCausalGameMode::AdvanceOneTick()
{
	if (!Transport || bRequestInFlight || !HeadGate.CanAdvance() || HeadGate.LatestTick >= (1LL << 53) - 1) return;
	const int64 Target = HeadGate.LatestTick + 1;
	const FString Phase = Target % 2 == 1 ? TEXT("shaoyang") : TEXT("taiyang");
	const FString RequestId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
	const FString CommandId = FString::Printf(TEXT("causal-%lld"), static_cast<long long>(Target));
	TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetNumberField(TEXT("protocol_version"), 1);
	Payload->SetStringField(TEXT("request_id"), RequestId);
	Payload->SetStringField(TEXT("operation"), TEXT("advance"));
	Payload->SetStringField(TEXT("world_id"), WorldId);
	Payload->SetStringField(TEXT("command_id"), CommandId);
	Payload->SetNumberField(TEXT("expected_revision"), static_cast<double>(HeadGate.LatestRevision));
	Payload->SetNumberField(TEXT("target_tick"), static_cast<double>(Target));
	TSharedRef<FJsonObject> External = MakeShared<FJsonObject>();
	External->SetStringField(TEXT("schema_version"), TEXT("abstract-causal-input.v1"));
	External->SetStringField(TEXT("phase"), Phase);
	Payload->SetObjectField(TEXT("external_inputs"), External);
	bRequestInFlight = true;
	TWeakObjectPtr<AEdgeWorldCausalGameMode> Weak(this);
	Transport->SendJsonLine({RequestId, TEXT("advance"), JsonLine(Payload)}, [Weak, Target, Expected = HeadGate.LatestRevision + 1](FEdgeWorldResponse&& Response)
	{
		AsyncTask(ENamedThreads::GameThread, [Weak, Target, Expected, Response = MoveTemp(Response)]() mutable
		{
			if (Weak.IsValid()) Weak->OnHead(MoveTemp(Response), true, Target, Expected);
		});
	});
}

void AEdgeWorldCausalGameMode::ObserveAt(int64 Tick)
{
	const int64 AvailableTick = HeadGate.bPending ? HeadGate.PendingTick : HeadGate.LatestTick;
	if (!Client || bRequestInFlight || Tick < 0 || Tick > AvailableTick) return;
	const FString View = FString::Printf(TEXT("{\"watermark\":%lld,\"region\":\"causal-fragment-v1\",\"observer\":\"ue-causal-camera-v1\",\"resolution\":\"causal-graph-proxy-v1\",\"error_budget\":{\"semantic_state\":\"exact\",\"visual_geometry\":\"unmeasured-proxy\"},\"rules\":{\"evolution\":\"abstract-causal-probe.v1\",\"projection\":\"causal-graph-ue.v1\"}}"), static_cast<long long>(Tick));
	bRequestInFlight = true;
	TWeakObjectPtr<AEdgeWorldCausalGameMode> Weak(this);
	Client->Observe(WorldId, Tick, View, [Weak, Tick](FEdgeWorldResponse&& Response)
	{
		FEdgeWorldCausalObservation Sample;
		FString Error;
		const bool bValid = EdgeWorldParseCausalObservation(Response, TEXT("stg-demo"), Tick, Tick, Sample, Error);
		AsyncTask(ENamedThreads::GameThread, [Weak, bValid, Sample = MoveTemp(Sample), Error = MoveTemp(Error)]() mutable
		{
			if (!Weak.IsValid()) return;
			Weak->bRequestInFlight = false;
			if (!bValid) { UE_LOG(LogTemp, Error, TEXT("Causal observe rejected: %s"), *Error); return; }
			const bool bAccepted = Weak->HeadGate.bPending && Sample.Tick == Weak->HeadGate.PendingTick
				? Weak->HeadGate.Accept(Sample) : Weak->HeadGate.CheckHistory(Sample);
			if (!bAccepted)
			{
				UE_LOG(LogTemp, Error, TEXT("Causal observe rejected: head/config/checkpoint mismatch"));
				return;
			}
			if (Weak->CausalActor) Weak->CausalActor->ApplyObservation(Sample);
			if (UWorld* World = Weak->GetWorld())
			{
				if (APlayerController* Controller = World->GetFirstPlayerController())
				{
					if (AEdgeWorldCausalHud* Hud = Cast<AEdgeWorldCausalHud>(Controller->GetHUD()))
						Hud->PresentValidated(Sample, Weak->HeadGate.LatestTick, Weak->HeadGate.LatestRevision);
				}
			}
			UE_LOG(LogTemp, Display, TEXT("Causal world %s observed tick %lld, revision %lld"), *Sample.WorldId,
				static_cast<long long>(Sample.Tick), static_cast<long long>(Sample.Revision));
		});
	});
}

void AEdgeWorldCausalGameMode::ObserveHistory(int64 Tick) { ObserveAt(Tick); }
void AEdgeWorldCausalGameMode::ObserveLatest() { ObserveAt(HeadGate.bPending ? HeadGate.PendingTick : HeadGate.LatestTick); }
void AEdgeWorldCausalGameMode::MoveCamera(const FVector& LocalOffset, const FRotator& RotationDelta)
{
	if (!Camera) return;
	const FRotator NewRotation = Camera->GetActorRotation() + RotationDelta;
	const FVector WorldOffset = Camera->GetActorRotation().RotateVector(LocalOffset);
	Camera->SetActorLocationAndRotation(Camera->GetActorLocation() + WorldOffset, NewRotation);
}

void AEdgeWorldCausalGameMode::ToggleVisitorView()
{
	APlayerController* Controller = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	AEdgeWorldVisitorCharacter* Visitor = Controller ? Cast<AEdgeWorldVisitorCharacter>(Controller->GetPawn()) : nullptr;
	if (!Visitor || !Camera) return;
	bOverview = !bOverview;
	Visitor->GetCharacterMovement()->StopMovementImmediately();
	Visitor->ConsumeMovementInputVector();
	Visitor->GetCharacterMovement()->SetMovementMode(bOverview ? MOVE_None : MOVE_Walking);
	Controller->SetViewTarget(bOverview ? static_cast<AActor*>(Camera.Get()) : static_cast<AActor*>(Visitor));
	UE_LOG(LogTemp, Display, TEXT("Visitor view=%s position=%s"), bOverview ? TEXT("overview") : TEXT("walking"), *Visitor->GetActorLocation().ToString());
}

AEdgeWorldCausalPlayerController::AEdgeWorldCausalPlayerController()
{
	bAutoManageActiveCameraTarget = false;
}

void AEdgeWorldCausalPlayerController::PlayerTick(float DeltaSeconds)
{
	Super::PlayerTick(DeltaSeconds);
	AEdgeWorldCausalGameMode* GameMode = Mode();
	AEdgeWorldVisitorCharacter* Visitor = Cast<AEdgeWorldVisitorCharacter>(GetPawn());
	if (!GameMode || !Visitor || !IsLocalController()) return;
	const float ForwardInput = static_cast<float>(IsInputKeyDown(EKeys::W)) - static_cast<float>(IsInputKeyDown(EKeys::S));
	const float RightInput = static_cast<float>(IsInputKeyDown(EKeys::D)) - static_cast<float>(IsInputKeyDown(EKeys::A));
	const float YawInput = static_cast<float>(IsInputKeyDown(EKeys::Right)) - static_cast<float>(IsInputKeyDown(EKeys::Left));
	const float PitchInput = static_cast<float>(IsInputKeyDown(EKeys::Down)) - static_cast<float>(IsInputKeyDown(EKeys::Up));
	float MouseX = 0, MouseY = 0;
	GetInputMouseDelta(MouseX, MouseY);
	if (GameMode->IsOverview())
	{
		const float VerticalInput = static_cast<float>(IsInputKeyDown(EKeys::E)) - static_cast<float>(IsInputKeyDown(EKeys::Q));
		GameMode->MoveCamera(FVector(ForwardInput, RightInput, VerticalInput).GetClampedToMaxSize(1.0f) * 240.0f * DeltaSeconds,
			FRotator(PitchInput * 60.0f * DeltaSeconds, YawInput * 60.0f * DeltaSeconds, 0));
		return;
	}
	FRotator Look = GetControlRotation();
	Look.Yaw += YawInput * 75.0f * DeltaSeconds + MouseX * 0.15f;
	Look.Pitch = FMath::Clamp(FRotator::NormalizeAxis(Look.Pitch) - PitchInput * 60.0f * DeltaSeconds + MouseY * 0.15f, -75.0f, 75.0f);
	Look.Roll = 0;
	SetControlRotation(Look);
	const FRotationMatrix Heading(FRotator(0, Look.Yaw, 0));
	const FVector Input = FVector(ForwardInput, RightInput, 0).GetClampedToMaxSize(1.0f);
	Visitor->AddMovementInput(Heading.GetUnitAxis(EAxis::X), Input.X);
	Visitor->AddMovementInput(Heading.GetUnitAxis(EAxis::Y), Input.Y);
}

AEdgeWorldCausalGameMode* AEdgeWorldCausalPlayerController::Mode() const
{
	return GetWorld() ? Cast<AEdgeWorldCausalGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
}
void AEdgeWorldCausalPlayerController::VisitorStatus()
{
	const AEdgeWorldVisitorCharacter* Visitor = Cast<AEdgeWorldVisitorCharacter>(GetPawn());
	if (!Visitor || !Mode()) return;
	Visitor->LogVisitorStatus();
}
void AEdgeWorldCausalPlayerController::VisitorTrace(float Seconds)
{
	if (AEdgeWorldVisitorCharacter* Visitor = Cast<AEdgeWorldVisitorCharacter>(GetPawn())) Visitor->TraceMovement(Seconds);
}
void AEdgeWorldCausalPlayerController::Advance() { if (auto* M = Mode()) M->AdvanceOneTick(); }
void AEdgeWorldCausalPlayerController::History0() { if (auto* M = Mode()) M->ObserveHistory(0); }
void AEdgeWorldCausalPlayerController::History1() { if (auto* M = Mode()) M->ObserveHistory(1); }
void AEdgeWorldCausalPlayerController::History2() { if (auto* M = Mode()) M->ObserveHistory(2); }
void AEdgeWorldCausalPlayerController::Latest() { if (auto* M = Mode()) M->ObserveLatest(); }
void AEdgeWorldCausalPlayerController::Refresh() { if (auto* M = Mode()) M->RefreshHead(); }
void AEdgeWorldCausalPlayerController::ToggleView() { if (auto* GameMode = Mode()) GameMode->ToggleVisitorView(); }
void AEdgeWorldCausalPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	InputComponent->BindKey(EKeys::SpaceBar, IE_Pressed, this, &AEdgeWorldCausalPlayerController::Advance);
	InputComponent->BindKey(EKeys::Zero, IE_Pressed, this, &AEdgeWorldCausalPlayerController::History0);
	InputComponent->BindKey(EKeys::One, IE_Pressed, this, &AEdgeWorldCausalPlayerController::History1);
	InputComponent->BindKey(EKeys::Two, IE_Pressed, this, &AEdgeWorldCausalPlayerController::History2);
	InputComponent->BindKey(EKeys::H, IE_Pressed, this, &AEdgeWorldCausalPlayerController::Latest);
	InputComponent->BindKey(EKeys::R, IE_Pressed, this, &AEdgeWorldCausalPlayerController::Refresh);
	InputComponent->BindKey(EKeys::Tab, IE_Pressed, this, &AEdgeWorldCausalPlayerController::ToggleView);
}
