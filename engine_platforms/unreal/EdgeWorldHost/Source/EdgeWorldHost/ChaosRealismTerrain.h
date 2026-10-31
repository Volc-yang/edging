#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/GameModeBase.h"
#include "ChaosRealismTerrain.generated.h"

class UProceduralMeshComponent;

/** Presentation-only surface query in the P0 world coordinate system (centimetres). */
struct EDGEWORLDHOST_API FChaosRealismSurfaceSample
{
	double HeightCm = 0.0;
	FVector Normal = FVector::UpVector;
	double WaterMask = 0.0;
	double Slope = 0.0;
	bool bInsideSample = false;
};

/** Fixed seed-7 prototype. Samples never read or mutate the authoritative Worker. */
struct EDGEWORLDHOST_API FChaosRealismTerrain
{
	static FChaosRealismSurfaceSample Sample(const FVector2D& XY);
	static double HeightAt(const FVector2D& XY);
	static FVector NormalAt(const FVector2D& XY);
	static double WaterMaskAt(const FVector2D& XY);
	static double SlopeAt(const FVector2D& XY);
	static bool Contains(const FVector2D& XY);
};

/** Continuous runtime mesh for the forest–marsh–coast visual slice. */
UCLASS()
class EDGEWORLDHOST_API AChaosRealismTerrainActor : public AActor
{
	GENERATED_BODY()
public:
	AChaosRealismTerrainActor();
	bool Build(FString& OutError);
	bool IsBuilt() const { return bBuilt; }
private:
	UPROPERTY()
	TObjectPtr<UProceduralMeshComponent> TerrainMesh;
	UPROPERTY()
	TObjectPtr<UProceduralMeshComponent> WaterMesh;
	UPROPERTY()
	TObjectPtr<UProceduralMeshComponent> RouteMesh;
	bool bBuilt = false;
};

/** Opt-in visual preview without a Worker; final assembly is owned by the lead task. */
UCLASS()
class EDGEWORLDHOST_API AChaosRealismTerrainPreviewGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	virtual void StartPlay() override;
};
