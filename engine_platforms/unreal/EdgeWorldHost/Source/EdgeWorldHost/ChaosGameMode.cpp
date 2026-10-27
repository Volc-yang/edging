#include "ChaosGameMode.h"

#include "ChaosWorldActor.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Math/RotationMatrix.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"

void AChaosGameMode::StartPlay()
{
	Super::StartPlay();
	UWorld* World = GetWorld();
	if (!World) return;

	ChaosWorld = World->SpawnActor<AChaosWorldActor>();
	if (!ChaosWorld)
	{
		UE_LOG(LogTemp, Error, TEXT("ChaosWorld actor could not be spawned"));
		return;
	}
	FString Error;
	FString ManifestPath;
	FString ExpectedHash;
	FParse::Value(FCommandLine::Get(), TEXT("ChaosWorldData="), ManifestPath);
	FParse::Value(FCommandLine::Get(), TEXT("ChaosInitialHash="), ExpectedHash);
	bool bBuilt = false;
	if (ManifestPath.IsEmpty())
	{
		bBuilt = ChaosWorld->BuildContractFixture(Error);
	}
	else
	{
		FString Json;
		if (!FFileHelper::LoadFileToString(Json, *ManifestPath))
		{
			Error = FString::Printf(TEXT("Cannot load InitialWorld from %s"), *ManifestPath);
		}
		else
		{
			// ExpectedHash is an external assertion. D4 must compare it with a worker observation.
			bBuilt = ChaosWorld->BuildFromInitialWorldJson(Json, ExpectedHash, Error);
		}
	}
	if (!bBuilt)
	{
		UE_LOG(LogTemp, Error, TEXT("ChaosWorld projection failed: %s"), *Error);
		ChaosWorld->Destroy();
		ChaosWorld = nullptr;
		return;
	}

	TActorIterator<ADirectionalLight> SunIt(World);
	const bool bHasSun = static_cast<bool>(SunIt);
	if (!bHasSun)
	{
		if (ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(
			FVector(50000.0f, 50000.0f, 25000.0f), FRotator(-50.0f, -20.0f, 0.0f)))
		{
			Sun->GetLightComponent()->SetIntensity(8.0f);
		}
	}
	TActorIterator<ASkyLight> SkyIt(World);
	const bool bHasSky = static_cast<bool>(SkyIt);
	if (!bHasSky)
	{
		if (ASkyLight* Sky = World->SpawnActor<ASkyLight>())
		{
			Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
			Sky->GetLightComponent()->SetIntensity(0.8f);
			Sky->GetLightComponent()->bRealTimeCapture = true;
			Sky->GetLightComponent()->RecaptureSky();
		}
	}

	const FVector CameraLocation(10000.0f, -28000.0f, 41000.0f);
	const FVector FocusPoint(57000.0f, 42000.0f, 0.0f);
	const FRotator CameraRotation = FRotationMatrix::MakeFromX(FocusPoint - CameraLocation).Rotator();
	OverviewCamera = World->SpawnActor<ACameraActor>(CameraLocation, CameraRotation);
	if (OverviewCamera)
	{
		OverviewCamera->GetCameraComponent()->SetFieldOfView(64.0f);
		if (APlayerController* Controller = World->GetFirstPlayerController())
		{
			Controller->SetViewTarget(OverviewCamera);
		}
	}
	UE_LOG(LogTemp, Display, TEXT("ChaosWorld static projection ready for %s. No worker or logical tick is started by D3."),
		*ChaosWorld->GetWorldId());
}
