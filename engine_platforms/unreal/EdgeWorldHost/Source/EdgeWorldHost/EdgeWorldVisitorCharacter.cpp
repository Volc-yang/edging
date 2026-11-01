#include "EdgeWorldVisitorCharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"

AEdgeWorldVisitorCharacter::AEdgeWorldVisitorCharacter()
{
	GetCapsuleComponent()->InitCapsuleSize(34.0f, 88.0f);
	GetCapsuleComponent()->SetGenerateOverlapEvents(false);
	GetCharacterMovement()->MaxWalkSpeed = 180.0f;
	GetCharacterMovement()->MaxStepHeight = 35.0f;
	GetCharacterMovement()->bOrientRotationToMovement = false;
	bUseControllerRotationYaw = true;
	VisitorCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("VisitorCamera"));
	VisitorCamera->SetupAttachment(GetCapsuleComponent());
	VisitorCamera->SetRelativeLocation(FVector(0, 0, 64));
	VisitorCamera->bUsePawnControlRotation = true;
	VisitorCamera->SetFieldOfView(80.0f);
}

FVector AEdgeWorldVisitorCharacter::EntryLocation() { return FVector(0, -300, -50); }

bool AEdgeWorldVisitorCharacter::ReturnToEntry()
{
	FHitResult Support;
	FCollisionQueryParams Query;
	Query.AddIgnoredActor(this);
	const FVector Entry = EntryLocation();
	if (!GetWorld() || !GetWorld()->LineTraceSingleByChannel(Support,
		Entry + FVector(0, 0, 100), Entry - FVector(0, 0, 200), ECC_Pawn, Query)
		|| Support.ImpactNormal.Z < GetCharacterMovement()->GetWalkableFloorZ()) return false;
	const FVector Destination(Entry.X, Entry.Y, Support.ImpactPoint.Z + GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.0f);
	if (GetWorld()->OverlapBlockingTestByChannel(Destination, FQuat::Identity, ECC_Pawn,
		FCollisionShape::MakeCapsule(GetCapsuleComponent()->GetScaledCapsuleRadius(),
			GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Query)) return false;
	GetCharacterMovement()->StopMovementImmediately();
	SetActorLocationAndRotation(Destination, FRotator(0, 90, 0), false, nullptr, ETeleportType::TeleportPhysics);
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	if (Controller) Controller->SetControlRotation(FRotator(0, 90, 0));
	UE_LOG(LogTemp, Display, TEXT("Visitor local entry restored: %s"), *GetActorLocation().ToString());
	return true;
}

void AEdgeWorldVisitorCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const FVector Position = GetActorLocation();
	if (Position.Y < -480 || Position.Y > 550 || Position.X < -430 || Position.X > 830 || Position.Z < -300)
		ReturnToEntry();
}
