#include "EdgeWorldVisitorCharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"

AEdgeWorldVisitorCharacter::AEdgeWorldVisitorCharacter()
{
	GetCapsuleComponent()->InitCapsuleSize(34.0f, 88.0f);
	GetCapsuleComponent()->SetGenerateOverlapEvents(false);
	GetCapsuleComponent()->OnComponentHit.AddDynamic(this, &AEdgeWorldVisitorCharacter::OnVisitorHit);
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
	{
		UE_LOG(LogTemp, Display, TEXT("Visitor recovery trigger frame=%llu time=%.3f before=%s bounds=x[-430,830],y[-480,550],z>=-300"),
			static_cast<unsigned long long>(GFrameCounter), GetWorld()->GetTimeSeconds(), *Position.ToString());
		ReturnToEntry();
	}
	if (GetWorld()->GetTimeSeconds() < TraceUntil && GetWorld()->GetTimeSeconds() >= NextTrace)
	{
		LogVisitorStatus();
		NextTrace = GetWorld()->GetTimeSeconds() + 0.2;
	}
}

void AEdgeWorldVisitorCharacter::LogVisitorStatus() const
{
	const UCharacterMovementComponent* Movement = GetCharacterMovement();
	const FFindFloorResult& Floor = Movement->CurrentFloor;
	const APlayerController* Player = Cast<APlayerController>(Controller);
	FCollisionQueryParams Query;
	Query.AddIgnoredActor(this);
	const bool bOverlap = GetWorld()->OverlapBlockingTestByChannel(GetActorLocation(), GetActorQuat(), ECC_Pawn,
		FCollisionShape::MakeCapsule(GetCapsuleComponent()->GetScaledCapsuleRadius(), GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Query);
	UE_LOG(LogTemp, Display, TEXT("Visitor status frame=%llu time=%.3f pawn=%s view=%s position=%s rotation=%s velocity=%s mode=%d grounded=%d falling=%d capsule=%.1f,%.1f floor_blocking=%d floor_walkable=%d floor_dist=%.3f floor_actor=%s floor_component=%s blocking_overlap=%d"),
		static_cast<unsigned long long>(GFrameCounter), GetWorld()->GetTimeSeconds(), *GetName(),
		*GetNameSafe(Player ? Player->GetViewTarget() : nullptr), *GetActorLocation().ToString(),
		*GetControlRotation().ToString(), *GetVelocity().ToString(), static_cast<int32>(Movement->MovementMode),
		Movement->IsMovingOnGround(), Movement->IsFalling(), GetCapsuleComponent()->GetScaledCapsuleRadius(),
		GetCapsuleComponent()->GetScaledCapsuleHalfHeight(), Floor.bBlockingHit, Floor.IsWalkableFloor(), Floor.FloorDist,
		*GetNameSafe(Floor.HitResult.GetActor()), *GetNameSafe(Floor.HitResult.GetComponent()), bOverlap);
}

void AEdgeWorldVisitorCharacter::TraceMovement(float Seconds)
{
	const float Duration = FMath::IsFinite(Seconds) ? FMath::Clamp(Seconds, 0.0f, 10.0f) : 0.0f;
	TraceUntil = GetWorld()->GetTimeSeconds() + Duration;
	NextTrace = GetWorld()->GetTimeSeconds();
	UE_LOG(LogTemp, Display, TEXT("Visitor trace duration=%.3f interval=0.2 max_duration=10"), Duration);
}

void AEdgeWorldVisitorCharacter::OnVisitorHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit)
{
	if (GetWorld()->GetTimeSeconds() >= TraceUntil) return;
	UE_LOG(LogTemp, Display, TEXT("Visitor blocking hit frame=%llu time=%.3f actor=%s component=%s point=%s normal=%s start_penetrating=%d penetration_depth=%.3f"),
		static_cast<unsigned long long>(GFrameCounter), GetWorld()->GetTimeSeconds(), *GetNameSafe(OtherActor),
		*GetNameSafe(OtherComponent), *Hit.ImpactPoint.ToString(), *Hit.ImpactNormal.ToString(), Hit.bStartPenetrating, Hit.PenetrationDepth);
}
