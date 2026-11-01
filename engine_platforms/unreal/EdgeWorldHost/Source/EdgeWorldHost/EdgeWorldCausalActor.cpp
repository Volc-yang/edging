#include "EdgeWorldCausalActor.h"

#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AEdgeWorldCausalActor::AEdgeWorldCausalActor()
{
	PrimaryActorTick.bCanEverTick = false;
}

void AEdgeWorldCausalActor::ApplyObservation(const FEdgeWorldCausalObservation& Observation)
{
	UWorld* World = GetWorld();
	if (!World) return;
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UMaterialInterface* BaseMaterial = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	if (!Sphere || !Cylinder || !BaseMaterial) return;
	for (AActor* Proxy : Proxies) if (IsValid(Proxy)) Proxy->Destroy();
	Proxies.Reset();
	TArray<FVector> Centers;
	for (const FEdgeWorldCausalNode& Node : Observation.Nodes)
	{
		const FVector Center(200.0 * Node.Tick, Node.bInitial ? 0.0 : static_cast<double>(Node.InfluenceMm), 0.0);
		Centers.Add(Center);
		if (AStaticMeshActor* Proxy = World->SpawnActor<AStaticMeshActor>(Center, FRotator::ZeroRotator))
		{
			UStaticMeshComponent* Mesh = Proxy->GetStaticMeshComponent();
			Mesh->SetMobility(EComponentMobility::Movable);
			Mesh->SetStaticMesh(Sphere);
			Mesh->SetMaterial(0, BaseMaterial);
			Proxy->SetActorScale3D(FVector(0.24));
			if (UMaterialInstanceDynamic* Material = Mesh->CreateAndSetMaterialInstanceDynamic(0))
				Material->SetVectorParameterValue(TEXT("Color"), Node.bInitial
					? FLinearColor(0.0f, 0.6f, 1.0f) : FLinearColor(1.0f, 0.6f, 0.0f));
			Proxies.Add(Proxy);
		}
	}
	for (int32 Index = 0; Index < Observation.Edges.Num(); ++Index)
	{
		const FVector Start = Centers[Index], End = Centers[Index + 1];
		const FVector Delta = End - Start;
		const FQuat Rotation = FQuat::FindBetweenNormals(FVector::UpVector, Delta.GetSafeNormal());
		if (AStaticMeshActor* Proxy = World->SpawnActor<AStaticMeshActor>((Start + End) * 0.5, Rotation.Rotator()))
		{
			UStaticMeshComponent* Mesh = Proxy->GetStaticMeshComponent();
			Mesh->SetMobility(EComponentMobility::Movable);
			Mesh->SetStaticMesh(Cylinder);
			Mesh->SetMaterial(0, BaseMaterial);
			Proxy->SetActorScale3D(FVector(0.04, 0.04, Delta.Size() / 100.0));
			if (UMaterialInstanceDynamic* Material = Mesh->CreateAndSetMaterialInstanceDynamic(0))
				Material->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.8f, 0.8f, 0.8f));
			Proxies.Add(Proxy);
		}
	}
}
