#include "ChaosRealismEcology.h"
#include "ChaosRealismTerrain.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChaosRealismEcologyLayoutTest,
	"edgeWorld.ChaosRealism.EcologyLayout", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChaosRealismEcologyLayoutTest::RunTest(const FString& Parameters)
{
	TArray<FChaosRealismPlant> A, B;
	FChaosRealismEcologyLayout::Generate(A);
	FChaosRealismEcologyLayout::Generate(B);
	TestTrue(TEXT("Nonempty layout"), A.Num() > 100);
	TestEqual(TEXT("Deterministic count"), A.Num(), B.Num());
	int32 Trees = 0, Reeds = 0, Scrubs = 0;
	for (int32 Index = 0; Index < A.Num(); ++Index)
	{
		TestTrue(TEXT("Stable location"), A[Index].Location.Equals(B[Index].Location, 0.001));
		TestTrue(TEXT("Within terrain sample"), FChaosRealismTerrain::Contains(FVector2D(A[Index].Location.X, A[Index].Location.Y)));
		if (A[Index].Kind == EChaosRealismPlantKind::Conifer || A[Index].Kind == EChaosRealismPlantKind::Broadleaf) ++Trees;
		else if (A[Index].Kind == EChaosRealismPlantKind::MarshReed) ++Reeds;
		else ++Scrubs;
	}
	TestTrue(TEXT("Forest trees present"), Trees > 50);
	TestTrue(TEXT("Marsh reeds present"), Reeds > 10);
	TestTrue(TEXT("Coastal scrub present"), Scrubs > 2);
	return true;
}
#endif
