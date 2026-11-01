#if WITH_DEV_AUTOMATION_TESTS

#include "EdgeWorldVisitorCharacter.h"
#include "EdgeWorldCausalEnvironment.h"
#include "EdgeWorldCausalGameMode.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/LocalPlayer.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/WorldSettings.h"
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
	World->GetWorldSettings()->DefaultGameMode = AGameModeBase::StaticClass();
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
	Controller->SetPlayer(NewObject<ULocalPlayer>(GEngine));
	Controller->Possess(Visitor);
	TestTrue(TEXT("test controller is local"), Controller->IsLocalController());
	TestFalse(TEXT("test movement input enabled"), Visitor->IsMoveInputIgnored());
	TestTrue(TEXT("safe entry supported and clear"), Visitor->ReturnToEntry());
	for (int32 Frame = 0; Frame < 60; ++Frame) TestWorld.TickTestWorld(1.0f / 60);
	TestTrue(TEXT("standing on floor"), Visitor->GetCharacterMovement()->IsMovingOnGround());
	TestTrue(TEXT("standing height stable"), FMath::Abs(Visitor->GetActorLocation().Z + 50.0) < 5);
	const FVector Start = Visitor->GetActorLocation();
	Visitor->TraceMovement(1.0f);
	for (int32 Frame = 0; Frame < 60; ++Frame)
	{
		Visitor->AddMovementInput(FVector(1, 0, 0));
		TestWorld.TickTestWorld(1.0f / 60);
	}
	TestTrue(TEXT("continuous movement traverses floor"), Visitor->GetActorLocation().X > Start.X + 100);
	Visitor->LogVisitorStatus();
	Visitor->ReturnToEntry();
	Visitor->TraceMovement(3.0f);
	for (int32 Frame = 0; Frame < 180; ++Frame)
	{
		Visitor->AddMovementInput(FVector(0, 1, 0));
		TestWorld.TickTestWorld(1.0f / 60);
	}
	TestTrue(TEXT("rail blocks actual character movement"), Visitor->GetActorLocation().Y < -252 && Visitor->GetActorLocation().Y > -270);
	Visitor->LogVisitorStatus();
	Visitor->ReturnToEntry();
	Visitor->TraceMovement(4.0f);
	for (int32 Frame = 0; Frame < 240; ++Frame)
	{
		Visitor->AddMovementInput(FVector(-1, 0, 0));
		TestWorld.TickTestWorld(1.0f / 60);
	}
	TestTrue(TEXT("wall blocks actual character movement"), Visitor->GetActorLocation().X > -357 && Visitor->GetActorLocation().X < -350);
	Visitor->LogVisitorStatus();
	Visitor->ReturnToEntry();
	bool bRecoveredAtEdge = false;
	for (int32 Frame = 0; Frame < 180; ++Frame)
	{
		const FVector Before = Visitor->GetActorLocation();
		Visitor->AddMovementInput(FVector(0, -1, 0));
		TestWorld.TickTestWorld(1.0f / 60);
		if (Before.Y < -460 && Visitor->GetActorLocation().Y > -350)
		{
			bRecoveredAtEdge = true;
			break;
		}
	}
	TestTrue(TEXT("continuous walk triggers open-edge guard"), bRecoveredAtEdge);
	TestTrue(TEXT("open edge returns to safe entry"), Visitor->GetActorLocation().Equals(AEdgeWorldVisitorCharacter::EntryLocation(), 5));
	Visitor->SetActorLocation(FVector(0, -300, -350));
	TestWorld.TickTestWorld(1.0f / 60);
	TestTrue(TEXT("fall returns to safe entry"), Visitor->GetActorLocation().Equals(AEdgeWorldVisitorCharacter::EntryLocation(), 5));
	TestWorld.ForwardErrorMessages(this);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldVisitorOverviewTest,
	"edgeWorld.Visitor.OverviewRetainsPawnAndPosition",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FEdgeWorldVisitorOverviewTest::RunTest(const FString& Parameters)
{
	if (!FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_CAUSAL_PYTHON")).IsEmpty()
		|| !FPlatformMisc::GetEnvironmentVariable(TEXT("EDGEWORLD_CAUSAL_WORKER")).IsEmpty())
	{
		AddError(TEXT("Run visitor fixture without live worker environment; no worker is permitted in this test"));
		return false;
	}
	FTestWorldWrapper TestWorld;
	if (!TestWorld.CreateTestWorld(EWorldType::Game))
	{
		TestWorld.ForwardErrorMessages(this);
		return false;
	}
	UWorld* World = TestWorld.GetTestWorld();
	World->GetWorldSettings()->DefaultGameMode = AEdgeWorldCausalGameMode::StaticClass();
	AEdgeWorldCausalPlayerController* Controller = World->SpawnActor<AEdgeWorldCausalPlayerController>();
	if (!TestNotNull(TEXT("visitor controller"), Controller)) return false;
	Controller->SetPlayer(NewObject<ULocalPlayer>(GEngine));
	if (!TestWorld.BeginPlayInTestWorld())
	{
		TestWorld.ForwardErrorMessages(this);
		return false;
	}
	AEdgeWorldCausalGameMode* GameMode = Cast<AEdgeWorldCausalGameMode>(World->GetAuthGameMode());
	AEdgeWorldVisitorCharacter* Visitor = Cast<AEdgeWorldVisitorCharacter>(Controller->GetPawn());
	if (!TestNotNull(TEXT("causal GameMode"), GameMode) || !TestNotNull(TEXT("possessed visitor"), Visitor)) return false;
	for (int32 Frame = 0; Frame < 30; ++Frame) TestWorld.TickTestWorld(1.0f / 60);
	const FVector Position = Visitor->GetActorLocation();
	const FRotator Rotation = Controller->GetControlRotation();
	TestTrue(TEXT("initial view is walking visitor"), Controller->GetViewTarget() == Visitor && !GameMode->IsOverview());
	GameMode->ToggleVisitorView();
	TestTrue(TEXT("overview targets camera"), Controller->GetViewTarget() != Visitor && GameMode->IsOverview());
	for (int32 Frame = 0; Frame < 30; ++Frame) TestWorld.TickTestWorld(1.0f / 60);
	TestTrue(TEXT("overview retains visitor position"), Visitor->GetActorLocation().Equals(Position, 0.01));
	TestTrue(TEXT("overview retains possession"), Controller->GetPawn() == Visitor);
	GameMode->MoveCamera(FVector(100, 0, 0), FRotator(0, 10, 0));
	GameMode->ToggleVisitorView();
	TestTrue(TEXT("walking view restored"), Controller->GetViewTarget() == Visitor && !GameMode->IsOverview());
	TestTrue(TEXT("return retains visitor position"), Visitor->GetActorLocation().Equals(Position, 0.01));
	TestTrue(TEXT("return retains visitor heading"), Controller->GetControlRotation().Equals(Rotation, 0.01));
	TestTrue(TEXT("walking movement restored"), Visitor->GetCharacterMovement()->MovementMode == MOVE_Walking);
	TestWorld.ForwardErrorMessages(this);
	return true;
}

#endif
