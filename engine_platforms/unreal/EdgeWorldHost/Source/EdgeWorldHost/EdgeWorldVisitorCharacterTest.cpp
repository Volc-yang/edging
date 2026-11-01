#if WITH_DEV_AUTOMATION_TESTS

#include "EdgeWorldVisitorCharacter.h"
#include "EdgeWorldCausalEnvironment.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldVisitorMovementTest,
	"edgeWorld.Visitor.SupportMovementCollisionRecovery",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FEdgeWorldVisitorMovementTest::RunTest(const FString& Parameters)
{
	FTestWorldWrapper TestWorld;
	if (!TestWorld.CreateTestWorld(EWorldType::Game))
	{
		TestWorld.ForwardErrorMessages(this);
		return false;
	}
	UWorld* World = TestWorld.GetTestWorld();
	for (TActorIterator<AStaticMeshActor> Actor(World); Actor; ++Actor) Actor->SetActorEnableCollision(false);
	World->SpawnActor<AEdgeWorldCausalEnvironment>();
	if (!TestWorld.BeginPlayInTestWorld())
	{
		TestWorld.ForwardErrorMessages(this);
		return false;
	}
	AEdgeWorldVisitorCharacter* Visitor = World->SpawnActor<AEdgeWorldVisitorCharacter>(
		AEdgeWorldVisitorCharacter::EntryLocation(), FRotator(0, 90, 0));
	APlayerController* Controller = World->SpawnActor<APlayerController>();
	if (!TestNotNull(TEXT("visitor"), Visitor) || !TestNotNull(TEXT("controller"), Controller)) return false;
	Controller->Possess(Visitor);
	TestTrue(TEXT("safe entry supported and clear"), Visitor->ReturnToEntry());
	for (int32 Frame = 0; Frame < 60; ++Frame) TestWorld.TickTestWorld(1.0f / 60);
	TestTrue(TEXT("standing on floor"), Visitor->GetCharacterMovement()->IsMovingOnGround());
	TestTrue(TEXT("standing height stable"), FMath::Abs(Visitor->GetActorLocation().Z + 50.0) < 5);
	const FVector Start = Visitor->GetActorLocation();
	for (int32 Frame = 0; Frame < 60; ++Frame)
	{
		Visitor->AddMovementInput(FVector(1, 0, 0));
		TestWorld.TickTestWorld(1.0f / 60);
	}
	TestTrue(TEXT("continuous movement traverses floor"), Visitor->GetActorLocation().X > Start.X + 100);
	Visitor->ReturnToEntry();
	for (int32 Frame = 0; Frame < 180; ++Frame)
	{
		Visitor->AddMovementInput(FVector(0, 1, 0));
		TestWorld.TickTestWorld(1.0f / 60);
	}
	TestTrue(TEXT("rail blocks actual character movement"), Visitor->GetActorLocation().Y < -252 && Visitor->GetActorLocation().Y > -270);
	Visitor->ReturnToEntry();
	for (int32 Frame = 0; Frame < 240; ++Frame)
	{
		Visitor->AddMovementInput(FVector(-1, 0, 0));
		TestWorld.TickTestWorld(1.0f / 60);
	}
	TestTrue(TEXT("wall blocks actual character movement"), Visitor->GetActorLocation().X > -357 && Visitor->GetActorLocation().X < -350);
	Visitor->SetActorLocation(FVector(0, -490, -50));
	TestWorld.TickTestWorld(1.0f / 60);
	TestTrue(TEXT("open edge returns to safe entry"), Visitor->GetActorLocation().Equals(AEdgeWorldVisitorCharacter::EntryLocation(), 5));
	Visitor->SetActorLocation(FVector(0, -300, -350));
	TestWorld.TickTestWorld(1.0f / 60);
	TestTrue(TEXT("fall returns to safe entry"), Visitor->GetActorLocation().Equals(AEdgeWorldVisitorCharacter::EntryLocation(), 5));
	TestWorld.ForwardErrorMessages(this);
	return true;
}

#endif
