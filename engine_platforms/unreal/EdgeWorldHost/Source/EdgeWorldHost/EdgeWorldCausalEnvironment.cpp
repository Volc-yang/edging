#include "EdgeWorldCausalEnvironment.h"

#include "Components/SceneComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "EdgeWorldCausalActor.h"
#include "EngineUtils.h"
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#endif

AEdgeWorldCausalEnvironment::AEdgeWorldCausalEnvironment()
{
	PrimaryActorTick.bCanEverTick = false;
	USceneComponent* SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("ObservatoryRoot"));
	SceneRoot->SetMobility(EComponentMobility::Static);
	RootComponent = SceneRoot;
	Exposure = CreateDefaultSubobject<UPostProcessComponent>(TEXT("ObservatoryExposure"));
	Exposure->SetupAttachment(RootComponent);
	Exposure->bUnbound = true;
	Exposure->Settings.bOverride_AutoExposureBias = true;
	Exposure->Settings.AutoExposureBias = -3.0f;
}

void AEdgeWorldCausalEnvironment::AddShape(UStaticMesh* Mesh, UMaterialInterface* BaseMaterial,
	const TCHAR* Name, const FVector& Location, const FVector& Scale,
	const FLinearColor& Color, bool bSolid, const FRotator& Rotation)
{
	if (!Mesh || !BaseMaterial) return;
	UStaticMeshComponent* Shape = NewObject<UStaticMeshComponent>(this, Name);
	Shape->SetMobility(EComponentMobility::Static);
	Shape->SetupAttachment(RootComponent);
	Shape->SetStaticMesh(Mesh);
	Shape->SetRelativeLocationAndRotation(Location, Rotation);
	Shape->SetRelativeScale3D(Scale);
	Shape->SetCollisionObjectType(ECC_WorldStatic);
	Shape->SetCollisionResponseToAllChannels(ECR_Ignore);
	if (bSolid)
	{
		Shape->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
		Shape->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
	}
	Shape->SetCollisionEnabled(bSolid ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
	Shape->SetGenerateOverlapEvents(false);
	Shape->SetMaterial(0, BaseMaterial);
	AddInstanceComponent(Shape);
	Shape->RegisterComponent();
	if (UMaterialInstanceDynamic* Material = Shape->CreateAndSetMaterialInstanceDynamic(0))
		Material->SetVectorParameterValue(TEXT("Color"), Color);
	Shapes.Add(Shape);
}

void AEdgeWorldCausalEnvironment::BeginPlay()
{
	Super::BeginPlay();
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	if (!Cube || !Cylinder || !Material)
	{
		UE_LOG(LogTemp, Warning, TEXT("Causal observatory: UE BasicShapes unavailable"));
		return;
	}

	// This floor and its landmarks are visual coordinates; they do not model world state.
	AddShape(Cube, Material, TEXT("Floor"), FVector(200, 0, -145), FVector(12, 10, 0.10),
		FLinearColor(0.035f, 0.055f, 0.075f), true);
	AddShape(Cube, Material, TEXT("CentralWalkway"), FVector(200, -150, -138), FVector(9, 1.2, 0.025),
		FLinearColor(0.12f, 0.16f, 0.19f), true);
	AddShape(Cube, Material, TEXT("FarWall"), FVector(200, 510, 45), FVector(12, 0.10, 4.0),
		FLinearColor(0.055f, 0.095f, 0.13f), true);
	AddShape(Cube, Material, TEXT("LeftWall"), FVector(-395, 0, 45), FVector(0.10, 10, 4.0),
		FLinearColor(0.055f, 0.095f, 0.13f), true);
	AddShape(Cube, Material, TEXT("RightWall"), FVector(795, 0, 45), FVector(0.10, 10, 4.0),
		FLinearColor(0.055f, 0.095f, 0.13f), true);
	for (int32 Tick = 0; Tick != 3; ++Tick)
	{
		const double X = 200.0 * Tick;
		const FString PedestalName = FString::Printf(TEXT("Tick%dPedestal"), Tick);
		AddShape(Cylinder, Material, *PedestalName, FVector(X, 0, -80), FVector(0.85, 0.85, 1.25),
			FLinearColor(0.11f, 0.16f, 0.20f), true);
		const FString RingName = FString::Printf(TEXT("Tick%dRing"), Tick);
		AddShape(Cylinder, Material, *RingName, FVector(X, 0, -14), FVector(0.92, 0.92, 0.07),
			Tick == 0 ? FLinearColor(0.02f, 0.36f, 0.48f) : FLinearColor(0.38f, 0.23f, 0.08f));
		const FString MarkerName = FString::Printf(TEXT("Tick%dMarker"), Tick);
		AddShape(Cube, Material, *MarkerName, FVector(X, -155, -127), FVector(0.08, 0.8, 0.06),
			FLinearColor(0.20f, 0.55f, 0.60f));
	}
	for (int32 Side = -1; Side <= 1; Side += 2)
	{
		const FString RailName = FString::Printf(TEXT("WalkwayRail%d"), Side);
		AddShape(Cube, Material, *RailName, FVector(200, -150 + Side * 68, -88), FVector(9, 0.04, 0.90),
			FLinearColor(0.16f, 0.28f, 0.31f), true);
	}
}

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FEdgeWorldObservatoryCollisionTest,
	"edgeWorld.CausalObservatory.WalkableCollision",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FEdgeWorldObservatoryCollisionTest::RunTest(const FString& Parameters)
{
	FTestWorldWrapper TestWorld;
	if (!TestWorld.CreateTestWorld(EWorldType::Game))
	{
		TestWorld.ForwardErrorMessages(this);
		return false;
	}
	UWorld* World = TestWorld.GetTestWorld();
	AEdgeWorldCausalEnvironment* Environment = World->SpawnActor<AEdgeWorldCausalEnvironment>();
	TestNotNull(TEXT("environment spawned"), Environment);
	if (!Environment || !TestWorld.BeginPlayInTestWorld())
	{
		TestWorld.ForwardErrorMessages(this);
		return false;
	}
	FCollisionQueryParams OnlyObservatory;
	for (TActorIterator<AActor> It(World); It; ++It)
		if (*It != Environment) OnlyObservatory.AddIgnoredActor(*It);

	FHitResult FloorHit;
	const bool bFloor = World->LineTraceSingleByChannel(FloorHit,
		FVector(0, -300, 100), FVector(0, -300, -300), ECC_Visibility, OnlyObservatory);
	AddInfo(FString::Printf(TEXT("Floor hit=%d actor=%s z=%f"), bFloor,
		FloorHit.GetActor() ? *FloorHit.GetActor()->GetName() : TEXT("none"), FloorHit.ImpactPoint.Z));
	TestTrue(TEXT("entry floor blocks visibility query"), bFloor && FloorHit.GetActor() == Environment);
	if (bFloor) TestTrue(TEXT("entry floor near expected height"), FMath::Abs(FloorHit.ImpactPoint.Z + 140.0) < 5.0);

	const FCollisionShape VisitorCapsule = FCollisionShape::MakeCapsule(34.0f, 88.0f);
	FHitResult StandingHit;
	const bool bStanding = World->SweepSingleByChannel(StandingHit,
		FVector(0, -300, 0), FVector(0, -300, -100), FQuat::Identity, ECC_Pawn, VisitorCapsule, OnlyObservatory);
	TestTrue(TEXT("visitor capsule supported by floor"), bStanding && StandingHit.GetActor() == Environment);
	FHitResult WallHit;
	const bool bWall = World->SweepSingleByChannel(WallHit,
		FVector(-300, -300, -40), FVector(-500, -300, -40), FQuat::Identity, ECC_Pawn, VisitorCapsule, OnlyObservatory);
	AddInfo(FString::Printf(TEXT("Wall hit=%d actor=%s x=%f"), bWall,
		WallHit.GetActor() ? *WallHit.GetActor()->GetName() : TEXT("none"), WallHit.ImpactPoint.X));
	TestTrue(TEXT("visitor capsule blocked by side wall"), bWall && WallHit.GetActor() == Environment);
	FHitResult RailHit;
	const bool bRail = World->SweepSingleByChannel(RailHit,
		FVector(200, -300, -40), FVector(200, -100, -40), FQuat::Identity, ECC_Pawn, VisitorCapsule, OnlyObservatory);
	AddInfo(FString::Printf(TEXT("Rail hit=%d actor=%s y=%f"), bRail,
		RailHit.GetActor() ? *RailHit.GetActor()->GetName() : TEXT("none"), RailHit.ImpactPoint.Y));
	TestTrue(TEXT("visitor capsule blocked by walkway rail"), bRail && RailHit.GetActor() == Environment);

	AEdgeWorldCausalActor* Graph = World->SpawnActor<AEdgeWorldCausalActor>();
	FEdgeWorldCausalObservation Sample;
	FEdgeWorldCausalNode Initial;
	Initial.Tick = 0;
	Initial.bInitial = true;
	Sample.Nodes.Add(Initial);
	if (Graph) Graph->ApplyObservation(Sample);
	FHitResult GraphHit;
	const bool bGraph = World->LineTraceSingleByChannel(GraphHit,
		FVector(0, 0, 160), FVector(0, 0, 70), ECC_Visibility);
	TestFalse(TEXT("causal node remains noncolliding"), bGraph);
	TestWorld.ForwardErrorMessages(this);
	return true;
}
#endif
