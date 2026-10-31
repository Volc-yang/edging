#include "ChaosRealismGameMode.h"

#include "ChaosRealismEcology.h"
#include "ChaosRealismLook.h"
#include "ChaosRealismTerrain.h"
#include "ChaosWorldActor.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Math/RotationMatrix.h"

AChaosRealismGameMode::AChaosRealismGameMode()
{
	PlayerControllerClass = AChaosRealismPlayerController::StaticClass();
}

void AChaosRealismPlayerController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	ACameraActor* Camera = Cast<ACameraActor>(GetViewTarget());
	if (!IsLocalController() || !Camera || DeltaTime <= 0.0f) return;

	const auto Axis = [this](FKey Positive, FKey Negative)
	{
		return (IsInputKeyDown(Positive) ? 1.0f : 0.0f) - (IsInputKeyDown(Negative) ? 1.0f : 0.0f);
	};
	const float Forward = Axis(EKeys::W, EKeys::S);
	const float Right = Axis(EKeys::D, EKeys::A);
	const float Up = Axis(EKeys::E, EKeys::Q);
	const float Yaw = Axis(EKeys::Right, EKeys::Left);
	const float Pitch = Axis(EKeys::Up, EKeys::Down);
	if (FMath::IsNearlyZero(Forward) && FMath::IsNearlyZero(Right) && FMath::IsNearlyZero(Up)
		&& FMath::IsNearlyZero(Yaw) && FMath::IsNearlyZero(Pitch)) return;

	FRotator Rotation = Camera->GetActorRotation();
	Rotation.Yaw += Yaw * 65.0f * DeltaTime;
	Rotation.Pitch = FMath::ClampAngle(Rotation.Pitch + Pitch * 65.0f * DeltaTime, -85.0f, 85.0f);
	Camera->SetActorRotation(Rotation);

	const FVector HorizontalForward = FRotationMatrix(FRotator(0.0f, Rotation.Yaw, 0.0f)).GetUnitAxis(EAxis::X);
	const FVector HorizontalRight = FRotationMatrix(FRotator(0.0f, Rotation.Yaw, 0.0f)).GetUnitAxis(EAxis::Y);
	const FVector Direction = (HorizontalForward * Forward + HorizontalRight * Right + FVector::UpVector * Up).GetClampedToMaxSize(1.0f);
	const float SpeedCmPerSecond = IsInputKeyDown(EKeys::LeftShift) || IsInputKeyDown(EKeys::RightShift) ? 12000.0f : 3500.0f;
	Camera->AddActorWorldOffset(Direction * SpeedCmPerSecond * DeltaTime);
}

void AChaosRealismGameMode::StartPlay()
{
	Super::StartPlay();
	UWorld* World = GetWorld();
	if (!World || !ChaosWorld) return;

	// Keep the O1 boundary under the existing read-only observation actor; replace only its proxy geometry.
	int32 HiddenProxies = 0;
	TArray<UStaticMeshComponent*> Components;
	ChaosWorld->GetComponents<UStaticMeshComponent>(Components);
	for (UStaticMeshComponent* Component : Components)
	{
		if (Component && !Component->ComponentHasTag(TEXT("world-spirit-boundary")))
		{
			Component->SetVisibility(false);
			++HiddenProxies;
		}
	}

	AChaosRealismTerrainActor* Terrain = World->SpawnActor<AChaosRealismTerrainActor>();
	FString Error;
	if (!Terrain || !Terrain->Build(Error))
	{
		UE_LOG(LogTemp, Error, TEXT("Chaos realism assembly terrain failed: %s"), *Error);
		return;
	}
	if (!AChaosRealismEcology::EnsureInWorld(World, Error))
	{
		UE_LOG(LogTemp, Error, TEXT("Chaos realism assembly ecology failed: %s"), *Error);
		return;
	}

	// The OpenWorld template can carry lights; disable them before installing one local daylight rig.
	for (TActorIterator<ADirectionalLight> It(World); It; ++It)
	{
		if (UDirectionalLightComponent* Light = It->GetComponent()) Light->SetVisibility(false);
	}
	for (TActorIterator<ASkyLight> It(World); It; ++It)
	{
		if (USkyLightComponent* Light = It->GetLightComponent()) Light->SetVisibility(false);
	}
	if (!AChaosRealismLook::EnsureInWorld(World))
	{
		UE_LOG(LogTemp, Error, TEXT("Chaos realism assembly daylight failed"));
		return;
	}
	if (OverviewCamera)
	{
		const FVector Position(25000.0, 17000.0, 12000.0);
		const FVector Focus(58000.0, 40000.0, 0.0);
		OverviewCamera->SetActorLocationAndRotation(Position,
			FRotationMatrix::MakeFromX(Focus - Position).Rotator());
		OverviewCamera->GetCameraComponent()->SetFieldOfView(62.0f);
		if (APlayerController* Controller = World->GetFirstPlayerController())
		{
			Controller->SetViewTarget(OverviewCamera);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("Chaos realism assembly ready: hidden_proxy_components=%d, terrain=ready, ecology=ready, daylight=ready; Worker remains observation-only"), HiddenProxies);
}
