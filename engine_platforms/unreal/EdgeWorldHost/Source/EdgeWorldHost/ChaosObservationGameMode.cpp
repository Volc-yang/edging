#include "ChaosObservationGameMode.h"

#include "ChaosWorldActor.h"
#include "ChaosValidationControl.h"
#include "EdgeWorldJsonlClient.h"
#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformMisc.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/Engine.h"
#include "Kismet/GameplayStatics.h"
#include "Math/RotationMatrix.h"
#include "Containers/StringConv.h"
#if PLATFORM_MAC
#include <CommonCrypto/CommonDigest.h>
#endif
#include "Serialization/JsonSerializer.h"

namespace
{
	constexpr TCHAR Ruleset[] = TEXT("chaos-o1-exp-v1");
	constexpr TCHAR Projection[] = TEXT("chaos-ue-projection-exp-v1");
	constexpr TCHAR ExpectedWorld[] = TEXT("chaos-demo");
	constexpr TCHAR ExpectedInitialHash[] = TEXT("75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3");

	bool CanonicalString(const FString& Value, FString& Out)
	{
		// P0 InitialWorld uses ASCII IDs, enum names and keys with no JSON escapes.
		// Reject a wider input instead of silently hashing unlike Python canonical().
		for (TCHAR Character : Value)
		{
			if (Character < 0x20 || Character > 0x7e || Character == TEXT('"') || Character == TEXT('\\'))
			{
				return false;
			}
		}
		Out += TEXT("\"") + Value + TEXT("\"");
		return true;
	}

	bool CanonicalValue(const TSharedPtr<FJsonValue>& Value, FString& Out)
	{
		if (!Value.IsValid()) return false;
		switch (Value->Type)
		{
		case EJson::Null: Out += TEXT("null"); return true;
		case EJson::String:
		{
			FString Text;
			return Value->TryGetString(Text) && CanonicalString(Text, Out);
		}
		case EJson::Number:
		{
			double Number = 0;
			if (!Value->TryGetNumber(Number) || !FMath::IsFinite(Number)
				|| FMath::Abs(Number) > static_cast<double>((1LL << 53) - 1)
				|| FMath::FloorToDouble(Number) != Number) return false;
			Out += FString::Printf(TEXT("%lld"), static_cast<long long>(Number));
			return true;
		}
		case EJson::Array:
		{
			const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
			if (!Value->TryGetArray(Array) || !Array) return false;
			Out += TEXT("[");
			for (int32 Index = 0; Index < Array->Num(); ++Index)
			{
				if (Index) Out += TEXT(",");
				if (!CanonicalValue((*Array)[Index], Out)) return false;
			}
			Out += TEXT("]");
			return true;
		}
		case EJson::Object:
		{
			const TSharedPtr<FJsonObject>* Object = nullptr;
			if (!Value->TryGetObject(Object) || !Object || !Object->IsValid()) return false;
			TArray<FString> Keys;
			for (const auto& Pair : (*Object)->Values) Keys.Add(FString(Pair.Key));
			Keys.Sort();
			Out += TEXT("{");
			for (int32 Index = 0; Index < Keys.Num(); ++Index)
			{
				if (Index) Out += TEXT(",");
				if (!CanonicalString(Keys[Index], Out)) return false;
				Out += TEXT(":");
				if (!CanonicalValue((*Object)->TryGetField(Keys[Index]), Out)) return false;
			}
			Out += TEXT("}");
			return true;
		}
		default: return false;
		}
	}

	bool ExactInteger(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, int64 Expected)
	{
		double Value = -1;
		return Object.IsValid() && Object->TryGetNumberField(Key, Value)
			&& FMath::IsFinite(Value) && Value == static_cast<double>(Expected);
	}

	TSharedPtr<FJsonObject> ResultOf(const FEdgeWorldResponse& Response)
	{
		if (!Response.bSuccess) return nullptr;
		TSharedPtr<FJsonObject> Envelope;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response.JsonLine), Envelope)
			|| !Envelope.IsValid()) return nullptr;
		const TSharedPtr<FJsonObject>* Result = nullptr;
		return Envelope->TryGetObjectField(TEXT("result"), Result) && Result ? *Result : nullptr;
	}

	bool FieldEquals(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, const FString& Expected)
	{
		FString Actual;
		return Object.IsValid() && Object->TryGetStringField(Key, Actual) && Actual == Expected;
	}

	bool ValidHead(const TSharedPtr<FJsonObject>& Result, const FString& WorldId, const FString& Hash,
		int64 Tick, int64 Revision)
	{
		return (Tick == 0 || Tick == 1) && Tick == Revision
			&& FieldEquals(Result, TEXT("world_id"), WorldId)
			&& FieldEquals(Result, TEXT("initial_manifest_hash"), Hash)
			&& FieldEquals(Result, TEXT("phase"), Tick == 0 ? TEXT("CHAOS") : TEXT("ONE"))
			&& ExactInteger(Result, TEXT("logical_tick"), Tick)
			&& ExactInteger(Result, TEXT("state_revision"), Revision)
			&& ExactInteger(Result, TEXT("event_watermark"), Tick)
			&& FieldEquals(Result, TEXT("ruleset_version"), Ruleset)
			&& FieldEquals(Result, TEXT("projection_version"), Projection);
	}

	bool ValidObservation(const TSharedPtr<FJsonObject>& Result, const FString& WorldId,
		const FString& Hash, int64 Tick, FString& OutError)
	{
		const TSharedPtr<FJsonObject>* Sample = nullptr;
		const TSharedPtr<FJsonObject>* View = nullptr;
		const TSharedPtr<FJsonObject>* Rules = nullptr;
		const TArray<TSharedPtr<FJsonValue>>* Boundary = nullptr;
		if (!FieldEquals(Result, TEXT("world_id"), WorldId)
			|| !FieldEquals(Result, TEXT("initial_manifest_hash"), Hash)
			|| !FieldEquals(Result, TEXT("phase"), Tick == 0 ? TEXT("CHAOS") : TEXT("ONE"))
			|| !FieldEquals(Result, TEXT("projection_version"), Projection)
			|| !ExactInteger(Result, TEXT("logical_tick"), Tick)
			|| !ExactInteger(Result, TEXT("source_revision"), Tick)
			|| !ExactInteger(Result, TEXT("watermark"), Tick)
			|| !Result->TryGetObjectField(TEXT("view_spec"), View) || !View || !View->IsValid()
			|| !ExactInteger(*View, TEXT("watermark"), Tick)
			|| !FieldEquals(*View, TEXT("region"), TEXT("origin-sample"))
			|| !FieldEquals(*View, TEXT("observer"), TEXT("ue-camera-v1"))
			|| !FieldEquals(*View, TEXT("resolution"), TEXT("chaos-proxy-v1"))
			|| !(*View)->TryGetObjectField(TEXT("rules"), Rules) || !Rules || !Rules->IsValid()
			|| !FieldEquals(*Rules, TEXT("evolution"), Ruleset)
			|| !FieldEquals(*Rules, TEXT("projection"), Projection)
			|| !Result->TryGetObjectField(TEXT("sample"), Sample) || !Sample || !Sample->IsValid()
			|| !(*Sample)->TryGetArrayField(TEXT("spirit_boundary_place_ids"), Boundary) || !Boundary)
		{
			OutError = TEXT("Origin observation identity, version, time, or sample mismatch");
			return false;
		}
		FString Spirit;
		if (Tick == 0)
		{
			const TSharedPtr<FJsonValue> SpiritValue = (*Sample)->TryGetField(TEXT("world_spirit_id"));
			if (!SpiritValue.IsValid() || SpiritValue->Type != EJson::Null || Boundary->Num() != 0)
			{
				OutError = TEXT("CHAOS must have no world spirit or boundary");
				return false;
			}
		}
		else if (!(*Sample)->TryGetStringField(TEXT("world_spirit_id"), Spirit)
			|| Spirit != TEXT("spirit-597eac36f6d6c494") || Boundary->Num() != 6)
		{
			OutError = TEXT("ONE requires a world spirit and boundary");
			return false;
		}
		return true;
	}
}

bool ChaosCanonicalInitialWorldHash(const FString& Json, FString& OutHash, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
	{
		OutError = TEXT("InitialWorld is not a JSON object");
		return false;
	}
	FString Canonical;
	if (!CanonicalValue(MakeShared<FJsonValueObject>(Root), Canonical))
	{
		OutError = TEXT("InitialWorld contains unsupported non-integer or non-ASCII canonical data");
		return false;
	}
	FTCHARToUTF8 Bytes(*Canonical);
#if PLATFORM_MAC
	uint8 Digest[CC_SHA256_DIGEST_LENGTH];
	if (!CC_SHA256(Bytes.Get(), static_cast<CC_LONG>(Bytes.Length()), Digest))
	{
		OutError = TEXT("SHA-256 computation failed");
		return false;
	}
	OutHash = BytesToHex(Digest, UE_ARRAY_COUNT(Digest)).ToLower();
	return true;
#else
	OutError = TEXT("Canonical InitialWorld SHA-256 is currently implemented for macOS only");
	return false;
#endif
}

AChaosObservationGameMode::AChaosObservationGameMode()
{
	PlayerControllerClass = AChaosObservationPlayerController::StaticClass();
}
AChaosObservationGameMode::~AChaosObservationGameMode() = default;

void AChaosObservationGameMode::StartPlay()
{
	// D3 loads this same immutable file for the visual projection.
	Super::StartPlay();
	if (!ChaosWorld) return;
	FString InitialWorldPath;
	FParse::Value(FCommandLine::Get(), TEXT("ChaosWorldData="), InitialWorldPath);
	const FString Python = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_CHAOS_PYTHON"));
	const FString Worker = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_CHAOS_WORKER"));
	if (InitialWorldPath.IsEmpty() || Python.IsEmpty() || Worker.IsEmpty())
	{
		UE_LOG(LogTemp, Error, TEXT("Chaos observation requires ChaosWorldData, EDGEWORLD_CHAOS_PYTHON and EDGEWORLD_CHAOS_WORKER"));
		return;
	}
	FString InitialJson;
	FString ComputedHash;
	FString HashError;
	if (!FFileHelper::LoadFileToString(InitialJson, *InitialWorldPath)
		|| !ChaosCanonicalInitialWorldHash(InitialJson, ComputedHash, HashError)
		|| ComputedHash != ExpectedInitialHash)
	{
		UE_LOG(LogTemp, Error, TEXT("Chaos InitialWorld canonical hash rejected: %s"), *HashError);
		return;
	}
	WorldId = ChaosWorld->GetWorldId();
	InitialHash = ChaosWorld->GetInitialManifestHash();
	if (WorldId != ExpectedWorld || InitialHash != ComputedHash)
	{
		UE_LOG(LogTemp, Error, TEXT("Chaos projection identity/hash is missing or unexpected"));
		return;
	}
	FEdgeWorldWorkerLaunchConfig Config;
	Config.PythonExecutable = Python;
	Config.WorkerScript = Worker;
	Config.InitialWorldPath = InitialWorldPath;
	Config.StateDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EdgeWorldChaos"), WorldId);
	Config.WorldId = WorldId;
	Config.Seed = 7;
	Config.RequestTimeoutSeconds = 60.0;
	Transport = MakeShared<FEdgeWorldProcessTransport, ESPMode::ThreadSafe>(MoveTemp(Config));
	Client = MakeShared<FEdgeWorldJsonlClient>(Transport.ToSharedRef());
	FString ValidationPath;
	FString ValidationAckPath;
	FParse::Value(FCommandLine::Get(), TEXT("ChaosValidationControl="), ValidationPath);
	FParse::Value(FCommandLine::Get(), TEXT("ChaosValidationAck="), ValidationAckPath);
	if (!ValidationPath.IsEmpty() && !ValidationAckPath.IsEmpty())
	{
		ValidationControl = MakeUnique<FChaosValidationControl>(this, ValidationPath, ValidationAckPath);
		UE_LOG(LogTemp, Display, TEXT("ChaosValidation control enabled: %s"), *ValidationPath);
	}
	bRequestInFlight = true;
	TWeakObjectPtr<AChaosObservationGameMode> WeakThis(this);
	Client->Status(WorldId, [WeakThis](FEdgeWorldResponse&& Response)
	{
		const TSharedPtr<FJsonObject> Result = ResultOf(Response);
		int64 Tick = -1, Revision = -1;
		const bool bParsed = Result.IsValid() && Result->TryGetNumberField(TEXT("logical_tick"), Tick)
			&& Result->TryGetNumberField(TEXT("state_revision"), Revision);
		AsyncTask(ENamedThreads::GameThread, [WeakThis, Result, Tick, Revision, bParsed]()
		{
			if (!WeakThis.IsValid()) return;
			WeakThis->bRequestInFlight = false;
			if (!bParsed || !ValidHead(Result, WeakThis->WorldId, WeakThis->InitialHash, Tick, Revision))
			{
				UE_LOG(LogTemp, Error, TEXT("Chaos worker status rejected"));
				return;
			}
			WeakThis->HeadTick = Tick;
			WeakThis->HeadRevision = Revision;
			WeakThis->ObserveAt(0);
		});
	});
}

void AChaosObservationGameMode::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ValidationControl.Reset();
	if (Transport.IsValid()) Transport->Shutdown();
	Client.Reset();
	Transport.Reset();
	Super::EndPlay(EndPlayReason);
}

void AChaosObservationGameMode::ObserveAt(int64 Tick)
{
	if (!Client.IsValid() || bRequestInFlight || Tick < 0 || Tick > HeadTick || Tick > 1) return;
	const FString Spec = FString::Printf(TEXT("{\"watermark\":%lld,\"region\":\"origin-sample\",\"observer\":\"ue-camera-v1\",\"resolution\":\"chaos-proxy-v1\",\"error_budget\":{\"semantic_state\":\"exact\",\"visual_geometry\":\"proxy\"},\"rules\":{\"evolution\":\"chaos-o1-exp-v1\",\"projection\":\"chaos-ue-projection-exp-v1\"}}"), static_cast<long long>(Tick));
	bRequestInFlight = true;
	TWeakObjectPtr<AChaosObservationGameMode> WeakThis(this);
	Client->Observe(WorldId, Tick, Spec, [WeakThis, Tick](FEdgeWorldResponse&& Response)
	{
		const TSharedPtr<FJsonObject> Result = ResultOf(Response);
		AsyncTask(ENamedThreads::GameThread, [WeakThis, Result, Tick]()
		{
			if (!WeakThis.IsValid()) return;
			WeakThis->bRequestInFlight = false;
			FString Error;
			if (!ValidObservation(Result, WeakThis->WorldId, WeakThis->InitialHash, Tick, Error))
			{
				UE_LOG(LogTemp, Error, TEXT("Chaos observation rejected: %s"), *Error);
				return;
			}
			if (WeakThis->ChaosWorld) WeakThis->ChaosWorld->SetWorldSpiritVisible(Tick == 1);
			UE_LOG(LogTemp, Display, TEXT("Chaos origin observed committed tick %lld"), static_cast<long long>(Tick));
		});
	});
}

void AChaosObservationGameMode::ObserveHistoricalTick(int64 Tick) { ObserveAt(Tick); }

bool AChaosObservationGameMode::ExecuteValidationCommand(
	const TSharedPtr<FJsonObject>& Command, FString& OutDetail)
{
	if (!Command.IsValid()) { OutDetail = TEXT("invalid JSON object"); return false; }
	FString Action;
	if (!Command->TryGetStringField(TEXT("action"), Action))
	{
		OutDetail = TEXT("missing action"); return false;
	}
	if (Action == TEXT("camera"))
	{
		const TArray<TSharedPtr<FJsonValue>>* Position = nullptr;
		const TArray<TSharedPtr<FJsonValue>>* Focus = nullptr;
		double Fov = 0;
		if (!OverviewCamera || !Command->TryGetArrayField(TEXT("position"), Position)
			|| !Command->TryGetArrayField(TEXT("focus"), Focus)
			|| !Position || !Focus || Position->Num() != 3 || Focus->Num() != 3
			|| !Command->TryGetNumberField(TEXT("fov"), Fov)
			|| !FMath::IsFinite(Fov) || Fov < 20 || Fov > 120)
		{
			OutDetail = TEXT("invalid camera arguments"); return false;
		}
		double P[3], F[3];
		for (int32 Index = 0; Index < 3; ++Index)
		{
			if (!(*Position)[Index]->TryGetNumber(P[Index]) || !(*Focus)[Index]->TryGetNumber(F[Index])
				|| !FMath::IsFinite(P[Index]) || !FMath::IsFinite(F[Index]))
			{
				OutDetail = TEXT("nonfinite camera coordinate"); return false;
			}
		}
		const FVector Location(P[0], P[1], P[2]);
		const FVector Target(F[0], F[1], F[2]);
		if (Location.Equals(Target)) { OutDetail = TEXT("camera equals focus"); return false; }
		OverviewCamera->SetActorLocationAndRotation(Location,
			FRotationMatrix::MakeFromX(Target - Location).Rotator());
		OverviewCamera->GetCameraComponent()->SetFieldOfView(static_cast<float>(Fov));
		if (APlayerController* Controller = GetWorld()->GetFirstPlayerController())
		{
			Controller->SetViewTarget(OverviewCamera);
		}
		OutDetail = FString::Printf(TEXT("camera position=%s focus=%s fov=%.1f"),
			*OverviewCamera->GetActorLocation().ToString(), *Target.ToString(),
			OverviewCamera->GetCameraComponent()->FieldOfView);
		return true;
	}
	if (Action == TEXT("max_fps"))
	{
		double Limit = 0;
		if (!GEngine || !Command->TryGetNumberField(TEXT("fps"), Limit)
			|| !FMath::IsFinite(Limit) || Limit < 5 || Limit > 240)
		{
			OutDetail = TEXT("invalid fps"); return false;
		}
		GEngine->SetMaxFPS(static_cast<float>(Limit));
		OutDetail = FString::Printf(TEXT("max_fps=%.1f"), GEngine->GetMaxFPS());
		return true;
	}
	if (Action == TEXT("pause") || Action == TEXT("resume"))
	{
		const bool bPaused = Action == TEXT("pause");
		const bool bChanged = UGameplayStatics::SetGamePaused(GetWorld(), bPaused);
		const bool bActual = UGameplayStatics::IsGamePaused(GetWorld());
		OutDetail = FString::Printf(TEXT("world_paused=%s"), bActual ? TEXT("true") : TEXT("false"));
		return bChanged && bActual == bPaused;
	}
	if (Action == TEXT("visibility"))
	{
		bool bVisible = false;
		if (!ChaosWorld || !Command->TryGetBoolField(TEXT("visible"), bVisible))
		{
			OutDetail = TEXT("invalid visibility"); return false;
		}
		ChaosWorld->SetWorldSpiritVisible(bVisible);
		OutDetail = bVisible ? TEXT("spirit_boundary_visible=true") : TEXT("spirit_boundary_visible=false");
		return true;
	}
	if (Action == TEXT("observe"))
	{
		int64 Tick = -1;
		if (!Command->TryGetNumberField(TEXT("tick"), Tick) || !Client.IsValid()
			|| bRequestInFlight || Tick < 0 || Tick > HeadTick || Tick > 1)
		{
			OutDetail = TEXT("observe unavailable"); return false;
		}
		ObserveAt(Tick);
		OutDetail = FString::Printf(TEXT("observe dispatched tick=%lld; await committed observation log"),
			static_cast<long long>(Tick));
		return true;
	}
	if (Action == TEXT("reveal"))
	{
		if (!Client.IsValid() || bRequestInFlight || HeadTick != 0 || HeadRevision != 0)
		{
			OutDetail = TEXT("O1 unavailable"); return false;
		}
		RevealWorldSpirit();
		OutDetail = TEXT("explicit O1 dispatched; await committed observation log");
		return true;
	}
	OutDetail = TEXT("unknown action");
	return false;
}

void AChaosObservationGameMode::RevealWorldSpirit()
{
	if (!Client.IsValid() || bRequestInFlight || HeadTick != 0 || HeadRevision != 0) return;
	bRequestInFlight = true;
	TWeakObjectPtr<AChaosObservationGameMode> WeakThis(this);
	Client->AdvanceOrigin(WorldId, 0, 1, TEXT("origin-o1"), [WeakThis](FEdgeWorldResponse&& Response)
	{
		const TSharedPtr<FJsonObject> Result = ResultOf(Response);
		AsyncTask(ENamedThreads::GameThread, [WeakThis, Result]()
		{
			if (!WeakThis.IsValid()) return;
			WeakThis->bRequestInFlight = false;
			if (!FieldEquals(Result, TEXT("world_id"), WeakThis->WorldId)
				|| !FieldEquals(Result, TEXT("phase"), TEXT("ONE"))
				|| !ExactInteger(Result, TEXT("logical_tick"), 1)
				|| !ExactInteger(Result, TEXT("state_revision"), 1)
				|| !ExactInteger(Result, TEXT("event_watermark"), 1))
			{
				UE_LOG(LogTemp, Error, TEXT("Chaos O1 advance rejected"));
				return;
			}
			WeakThis->HeadTick = 1;
			WeakThis->HeadRevision = 1;
			WeakThis->ObserveAt(1);
		});
	});
}

void AChaosObservationPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	if (InputComponent)
	{
		InputComponent->BindKey(EKeys::SpaceBar, IE_Pressed, this, &AChaosObservationPlayerController::RevealWorldSpirit);
		InputComponent->BindKey(EKeys::Zero, IE_Pressed, this, &AChaosObservationPlayerController::ObserveChaos);
		InputComponent->BindKey(EKeys::One, IE_Pressed, this, &AChaosObservationPlayerController::ObserveOne);
	}
}
void AChaosObservationPlayerController::RevealWorldSpirit()
{
	if (auto* Mode = GetWorld() ? Cast<AChaosObservationGameMode>(GetWorld()->GetAuthGameMode()) : nullptr) Mode->RevealWorldSpirit();
}
void AChaosObservationPlayerController::ObserveChaos()
{
	if (auto* Mode = GetWorld() ? Cast<AChaosObservationGameMode>(GetWorld()->GetAuthGameMode()) : nullptr) Mode->ObserveHistoricalTick(0);
}
void AChaosObservationPlayerController::ObserveOne()
{
	if (auto* Mode = GetWorld() ? Cast<AChaosObservationGameMode>(GetWorld()->GetAuthGameMode()) : nullptr) Mode->ObserveHistoricalTick(1);
}
