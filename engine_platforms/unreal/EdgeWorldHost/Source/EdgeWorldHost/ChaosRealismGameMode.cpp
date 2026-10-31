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
#include "Math/RotationMatrix.h"

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
