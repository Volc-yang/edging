#pragma once

#include "GameFramework/Actor.h"
#include "ChaosRealismLook.generated.h"

class UDirectionalLightComponent;
class UExponentialHeightFogComponent;
class UPostProcessComponent;
class USceneComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;

/** Local, non-authoritative daylight rig for the forest–marsh–coast sample. */
UCLASS()
class EDGEWORLDHOST_API AChaosRealismLook : public AActor
{
	GENERATED_BODY()

public:
	AChaosRealismLook();
	/** Idempotent setup; the sole world assembler calls this after creating the sample. */
	static AChaosRealismLook* EnsureInWorld(UWorld* World);

private:
	UPROPERTY() TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY() TObjectPtr<UDirectionalLightComponent> Sun;
	UPROPERTY() TObjectPtr<USkyLightComponent> AmbientSky;
	UPROPERTY() TObjectPtr<USkyAtmosphereComponent> Atmosphere;
	UPROPERTY() TObjectPtr<UExponentialHeightFogComponent> CoastalHaze;
	UPROPERTY() TObjectPtr<UPostProcessComponent> Exposure;
};
