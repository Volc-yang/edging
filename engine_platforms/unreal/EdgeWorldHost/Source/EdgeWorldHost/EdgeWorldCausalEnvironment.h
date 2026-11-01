#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EdgeWorldCausalEnvironment.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;

// A replaceable, read-only spatial frame for the abstract causal graph.
UCLASS()
class EDGEWORLDHOST_API AEdgeWorldCausalEnvironment : public AActor
{
	GENERATED_BODY()
public:
	AEdgeWorldCausalEnvironment();
	virtual void BeginPlay() override;
private:
	void AddShape(UStaticMesh* Mesh, UMaterialInterface* BaseMaterial,
		const TCHAR* Name, const FVector& Location, const FVector& Scale,
		const FLinearColor& Color, const FRotator& Rotation = FRotator::ZeroRotator);
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> Shapes;
};
