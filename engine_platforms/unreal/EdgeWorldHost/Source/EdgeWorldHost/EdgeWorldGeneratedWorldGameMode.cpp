#include "EdgeWorldGeneratedWorldGameMode.h"

#include "EdgeWorldJsonlClient.h"
#include "EdgeWorldObservationActor.h"

#include "Async/Async.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Materials/MaterialInterface.h"
#include "Engine/SkyLight.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "HAL/PlatformMisc.h"
#include "InputCoreTypes.h"
#include "Math/RotationMatrix.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	constexpr TCHAR WorldName[] = TEXT("seed-tree-demo");
	constexpr TCHAR ProjectionVersion[] = TEXT("stylized-tree-ue-v1");
	constexpr TCHAR DefaultRulesetVersion[] = TEXT("experimental.seed-tree.v1");

	bool ReadExactInteger(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, int64& OutValue)
	{
		double Number = 0.0;
		if (!Object.IsValid() || !Object->TryGetNumberField(Field, Number) || !FMath::IsFinite(Number)
			|| Number < 0.0 || Number > static_cast<double>((1LL << 53) - 1)
			|| FMath::FloorToDouble(Number) != Number)
		{
			return false;
		}
		OutValue = static_cast<int64>(Number);
		return true;
	}

	TSharedPtr<FJsonObject> ReadResultObject(const FEdgeWorldResponse& Response)
	{
		if (!Response.bSuccess)
		{
			return nullptr;
		}
		TSharedPtr<FJsonObject> Envelope;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response.JsonLine);
		if (!FJsonSerializer::Deserialize(Reader, Envelope) || !Envelope.IsValid())
		{
			return nullptr;
		}
		const TSharedPtr<FJsonObject>* Result = nullptr;
		return Envelope->TryGetObjectField(TEXT("result"), Result) && Result && Result->IsValid() ? *Result : nullptr;
	}
}

AEdgeWorldGeneratedWorldGameMode::AEdgeWorldGeneratedWorldGameMode()
{
	PlayerControllerClass = AEdgeWorldGeneratedWorldPlayerController::StaticClass();
	WorldId = WorldName;
	RulesetVersion = DefaultRulesetVersion;
}

AEdgeWorldGeneratedWorldGameMode::~AEdgeWorldGeneratedWorldGameMode() = default;

void AEdgeWorldGeneratedWorldGameMode::StartPlay()
{
	Super::StartPlay();
	SpawnGeneratedWorld();
	StartWorkerObservation();
	UE_LOG(LogTemp, Display, TEXT("edgeWorld tree demo ready. Press Space to explicitly advance one logical tick."));
}

void AEdgeWorldGeneratedWorldGameMode::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (WorkerTransport.IsValid())
	{
		WorkerTransport->Shutdown();
		WorkerTransport.Reset();
	}
	WorkerClient.Reset();
	Super::EndPlay(EndPlayReason);
}

void AEdgeWorldGeneratedWorldGameMode::SpawnGeneratedWorld()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UMaterialInterface* ShapeMaterial = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	if (AStaticMeshActor* Ground = World->SpawnActor<AStaticMeshActor>(FVector(0.0, 0.0, -25.0), FRotator::ZeroRotator))
	{
		UStaticMeshComponent* GroundMesh = Ground->GetStaticMeshComponent();
		GroundMesh->SetMobility(EComponentMobility::Movable);
		GroundMesh->SetStaticMesh(Cube);
		GroundMesh->SetMaterial(0, ShapeMaterial);
		Ground->SetActorScale3D(FVector(35.0, 35.0, 0.5));
		if (UMaterialInstanceDynamic* GroundMaterial = GroundMesh->CreateAndSetMaterialInstanceDynamic(0))
		{
			GroundMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.18f, 0.28f, 0.14f, 1.0f));
		}
	}

	if (World->SpawnActor<ASkyAtmosphere>())
	{
	}
	if (ASkyLight* Sky = World->SpawnActor<ASkyLight>())
	{
		Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
		Sky->GetLightComponent()->SetIntensity(0.8f);
		Sky->GetLightComponent()->bRealTimeCapture = true;
		Sky->GetLightComponent()->RecaptureSky();
	}
	if (ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(FVector(0.0, 0.0, 900.0), FRotator(-48.0, -32.0, 0.0)))
	{
		Sun->GetLightComponent()->SetIntensity(50.0f);
		Sun->GetLightComponent()->SetLightColor(FLinearColor(1.0f, 0.96f, 0.86f));
	}

	if (AEdgeWorldObservationActor* Tree = World->SpawnActor<AEdgeWorldObservationActor>(FVector::ZeroVector, FRotator::ZeroRotator))
	{
		ObservationActor = Tree;
	}

	const FVector CameraLocation(900.0, -1350.0, 760.0);
	const FVector FocusPoint(0.0, 0.0, 240.0);
	const FRotator CameraRotation = FRotationMatrix::MakeFromX(FocusPoint - CameraLocation).Rotator();
	if (ACameraActor* Camera = World->SpawnActor<ACameraActor>(CameraLocation, CameraRotation))
	{
		UCameraComponent* CameraComponent = Camera->GetCameraComponent();
		CameraComponent->SetFieldOfView(48.0f);
		CameraComponent->PostProcessSettings.bOverride_AutoExposureBias = true;
		CameraComponent->PostProcessSettings.AutoExposureBias = -0.5f;
		ObservationCamera = Camera;
		if (APlayerController* PlayerController = World->GetFirstPlayerController())
		{
			PlayerController->SetViewTarget(Camera);
		}
	}

	if (APlayerController* PlayerController = World->GetFirstPlayerController())
	{
		PlayerController->SetShowMouseCursor(false);
	}
}

void AEdgeWorldGeneratedWorldGameMode::StartWorkerObservation()
{
	const FString Python = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_TREE_PYTHON"));
	const FString Worker = FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_TREE_WORKER"));
	if (Python.IsEmpty() || Worker.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("Tree worker is not configured. Set EDGEWORLD_TREE_PYTHON and EDGEWORLD_TREE_WORKER; no synthetic tree state will be shown."));
		return;
	}

	FEdgeWorldWorkerLaunchConfig Config;
	Config.PythonExecutable = Python;
	Config.WorkerScript = Worker;
	Config.StateDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EdgeWorldTree"), WorldName);
	Config.WorldId = WorldId;
	Config.RequestTimeoutSeconds = 60.0;
	WorkerTransport = MakeShared<FEdgeWorldProcessTransport, ESPMode::ThreadSafe>(MoveTemp(Config));
	WorkerClient = MakeShared<FEdgeWorldJsonlClient>(WorkerTransport.ToSharedRef());

	TWeakObjectPtr<AEdgeWorldGeneratedWorldGameMode> WeakThis(this);
	WorkerClient->Status(WorldId, [WeakThis](FEdgeWorldResponse&& Response)
	{
		const TSharedPtr<FJsonObject> Result = ReadResultObject(Response);
		int64 Tick = INDEX_NONE;
		int64 Revision = INDEX_NONE;
		const bool bValidHead = Result.IsValid()
			&& ReadExactInteger(Result, TEXT("logical_tick"), Tick)
			&& ReadExactInteger(Result, TEXT("state_revision"), Revision);
		AsyncTask(ENamedThreads::GameThread, [WeakThis, bValidHead, Tick, Revision, ErrorCode = Response.ErrorCode, ErrorMessage = Response.ErrorMessage]()
		{
			if (!WeakThis.IsValid()) return;
			WeakThis->bRequestInFlight = false;
			if (!bValidHead)
			{
				UE_LOG(LogTemp, Error, TEXT("Tree worker status failed: %s - %s"), *ErrorCode, *ErrorMessage);
				return;
			}
			WeakThis->LogicalTick = Tick;
			WeakThis->StateRevision = Revision;
			WeakThis->ObserveAt(Tick, Revision);
		});
	});
	bRequestInFlight = true;
}

void AEdgeWorldGeneratedWorldGameMode::ObserveAt(int64 Tick, int64 Watermark)
{
	if (!WorkerClient || bRequestInFlight)
	{
		return;
	}
	const FString ViewSpec = FString::Printf(
		TEXT("{\"watermark\":%lld,\"region\":\"single-tree-world\",\"observer\":\"ue-default-camera-v1\",\"resolution\":\"single-tree-proxy-v1\",\"error_budget\":{\"semantic_state\":\"exact\",\"visual_geometry\":\"unmeasured-proxy\"},\"rules\":{\"evolution\":\"%s\",\"projection\":\"%s\"}}"),
		static_cast<long long>(Watermark), *RulesetVersion, ProjectionVersion);
	TWeakObjectPtr<AEdgeWorldGeneratedWorldGameMode> WeakThis(this);
	WorkerClient->Observe(WorldId, Tick, ViewSpec, [WeakThis, Tick, Watermark](FEdgeWorldResponse&& Response)
	{
		FEdgeWorldTreeObservation Sample;
		FString ParseError;
		const bool bValid = EdgeWorldParseTreeObservation(Response, WorldName, Tick, Watermark,
			DefaultRulesetVersion, ProjectionVersion, Sample, ParseError);
		AsyncTask(ENamedThreads::GameThread, [WeakThis, bValid, Sample = MoveTemp(Sample), ParseError = MoveTemp(ParseError)]() mutable
		{
			if (!WeakThis.IsValid()) return;
			WeakThis->bRequestInFlight = false;
			if (!bValid)
			{
				UE_LOG(LogTemp, Error, TEXT("Tree observation rejected: %s"), *ParseError);
				return;
			}
			if (WeakThis->ObservationActor)
			{
				FString ApplyError;
				if (!WeakThis->ObservationActor->ApplyTreeObservation(Sample, Sample.LogicalTick, Sample.Watermark, ApplyError))
				{
					UE_LOG(LogTemp, Error, TEXT("Tree presentation rejected: %s"), *ApplyError);
					return;
				}
				WeakThis->LogicalTick = Sample.LogicalTick;
				WeakThis->StateRevision = Sample.SourceRevision;
				UE_LOG(LogTemp, Display, TEXT("Observed %s at tick %lld/revision %lld (%s, biomass %.3f, %s)"),
					*Sample.SeedId, static_cast<long long>(Sample.LogicalTick), static_cast<long long>(Sample.SourceRevision),
					*Sample.Stage, Sample.Biomass, *Sample.StateHash);
			}
		});
	});
	bRequestInFlight = true;
}

void AEdgeWorldGeneratedWorldGameMode::AdvanceOneTick()
{
	if (!WorkerClient || bRequestInFlight)
	{
		return;
	}
	const int64 TargetTick = LogicalTick + 1;
	static const TCHAR* Phases[] = { TEXT("shaoyang"), TEXT("taiyang"), TEXT("shaoyin"), TEXT("taiyin") };
	const FString Environment = FString::Printf(TEXT("{\"phase\":\"%s\",\"moisture\":0.8,\"light\":0.7}"),
		Phases[(TargetTick - 1) % UE_ARRAY_COUNT(Phases)]);
	const FString CommandId = FString::Printf(TEXT("ue-demo-seed-advance-%lld"), static_cast<long long>(TargetTick));
	TWeakObjectPtr<AEdgeWorldGeneratedWorldGameMode> WeakThis(this);
	WorkerClient->Advance(WorldId, StateRevision, TargetTick, CommandId, Environment,
		[WeakThis, TargetTick](FEdgeWorldResponse&& Response)
	{
		const TSharedPtr<FJsonObject> Result = ReadResultObject(Response);
		int64 CommittedTick = INDEX_NONE;
		int64 CommittedRevision = INDEX_NONE;
		const bool bCommitted = Result.IsValid()
			&& ReadExactInteger(Result, TEXT("logical_tick"), CommittedTick) && CommittedTick == TargetTick
			&& ReadExactInteger(Result, TEXT("state_revision"), CommittedRevision);
		AsyncTask(ENamedThreads::GameThread, [WeakThis, bCommitted, CommittedTick, CommittedRevision,
			ErrorCode = Response.ErrorCode, ErrorMessage = Response.ErrorMessage]()
		{
			if (!WeakThis.IsValid()) return;
			WeakThis->bRequestInFlight = false;
			if (!bCommitted)
			{
				UE_LOG(LogTemp, Error, TEXT("Explicit tree advance failed: %s - %s"), *ErrorCode, *ErrorMessage);
				return;
			}
			WeakThis->LogicalTick = CommittedTick;
			WeakThis->StateRevision = CommittedRevision;
			WeakThis->ObserveAt(CommittedTick, CommittedRevision);
		});
	});
	bRequestInFlight = true;
}

void AEdgeWorldGeneratedWorldPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	if (InputComponent)
	{
		InputComponent->BindKey(EKeys::SpaceBar, IE_Pressed, this,
			&AEdgeWorldGeneratedWorldPlayerController::AdvanceOneTick);
	}
}

void AEdgeWorldGeneratedWorldPlayerController::AdvanceOneTick()
{
	if (AEdgeWorldGeneratedWorldGameMode* GameMode = GetWorld()
		? Cast<AEdgeWorldGeneratedWorldGameMode>(GetWorld()->GetAuthGameMode()) : nullptr)
	{
		GameMode->AdvanceOneTick();
	}
}
