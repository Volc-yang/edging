#include "EdgeWorldObservationActor.h"

AEdgeWorldObservationActor::AEdgeWorldObservationActor()
{
	PrimaryActorTick.bCanEverTick = false;
}

void AEdgeWorldObservationActor::ApplyCommittedObservation(const FString& InStableEntityId,
	const FVector& Position, const FRotator& Rotation, const FVector& Scale)
{
	StableEntityId = InStableEntityId;
	SetActorTransform(FTransform(Rotation, Position, Scale), false, nullptr, ETeleportType::TeleportPhysics);
}
