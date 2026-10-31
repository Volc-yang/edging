#include "ChaosRealismLook.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

AChaosRealismLook::AChaosRealismLook()
{
	PrimaryActorTick.bCanEverTick = false;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("RealismLookRoot"));
	RootComponent = SceneRoot;

	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("DaySun"));
	Sun->SetupAttachment(SceneRoot);
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->SetIntensity(8.0f);
	Sun->SetAtmosphereSunLight(true);
	Sun->SetRelativeRotation(FRotator(-38.0f, -28.0f, 0.0f));

	AmbientSky = CreateDefaultSubobject<USkyLightComponent>(TEXT("AmbientSky"));
	AmbientSky->SetupAttachment(SceneRoot);
	AmbientSky->SetMobility(EComponentMobility::Movable);
	AmbientSky->SetIntensity(0.65f);
	AmbientSky->SetRealTimeCapture(true);

	Atmosphere = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("DayAtmosphere"));
	Atmosphere->SetupAttachment(SceneRoot);

	CoastalHaze = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("CoastalHaze"));
	CoastalHaze->SetupAttachment(SceneRoot);
	CoastalHaze->SetFogDensity(0.006f);
	CoastalHaze->SetFogHeightFalloff(0.13f);
	CoastalHaze->SetVolumetricFog(true);

	Exposure = CreateDefaultSubobject<UPostProcessComponent>(TEXT("DayExposure"));
	Exposure->SetupAttachment(SceneRoot);
	Exposure->bUnbound = true;
	Exposure->Priority = 10.0f;
	Exposure->Settings.bOverride_AutoExposureBias = true;
	Exposure->Settings.AutoExposureBias = -0.3f;
}

AChaosRealismLook* AChaosRealismLook::EnsureInWorld(UWorld* World)
{
	if (!World) return nullptr;
	TActorIterator<AChaosRealismLook> Existing(World);
	if (Existing) return *Existing;
	FActorSpawnParameters Spawn;
	Spawn.Name = TEXT("ChaosRealismDaylight");
	AChaosRealismLook* Look = World->SpawnActor<AChaosRealismLook>(
		FVector(50000.0, 40000.0, 0.0), FRotator::ZeroRotator, Spawn);
	if (Look)
	{
		UE_LOG(LogTemp, Display, TEXT("ChaosRealismLook daylight rig installed at sample center; no world state requests"));
	}
	return Look;
}
