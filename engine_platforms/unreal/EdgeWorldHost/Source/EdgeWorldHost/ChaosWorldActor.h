#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ChaosWorldActor.generated.h"

class UMaterialInterface;
class ULevel;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;

/** Read-only visual projection of a committed chaos InitialWorld. Never advances logical time. */
UCLASS()
class EDGEWORLDHOST_API AChaosWorldActor : public AActor
{
	GENERATED_BODY()

public:
	AChaosWorldActor();
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** Build once from the P0 InitialWorld JSON. Geometry is a disposable presentation cache. */
	bool BuildFromInitialWorldJson(const FString& Json, const FString& ExpectedInitialHash, FString& OutError);
	/** P0's fixed six-place fixture, used when no external manifest was supplied. */
	bool BuildContractFixture(FString& OutError);
	/** D4 may call this only after validating a committed ONE observation. */
	void SetWorldSpiritVisible(bool bVisible);
	const FString& GetWorldId() const { return WorldId; }
	const FString& GetInitialManifestHash() const { return InitialManifestHash; }

private:
	void HideTemplateLandscape();
	void OnLevelAdded(ULevel* Level, UWorld* World);
	bool HideLandscapeActor(AActor* Actor, const TCHAR* Source);
	UStaticMeshComponent* AddShape(UStaticMesh* Mesh, const FVector& CenterCm,
		const FVector& SizeCm, const FLinearColor& Color, const FString& Label);
	void AddSegment(UStaticMesh* Mesh, const FVector& Start, const FVector& End,
		float WidthCm, float HeightCm, const FLinearColor& Color, const FString& Label);

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> SpiritBoundary;
	FString WorldId;
	FString InitialManifestHash;
	bool bBuilt = false;
	FDelegateHandle LevelAddedHandle;
};
