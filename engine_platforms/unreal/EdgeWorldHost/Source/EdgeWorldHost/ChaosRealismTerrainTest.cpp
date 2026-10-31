#include "ChaosRealismTerrain.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChaosRealismTerrainSamples,
	"edgeWorld.ChaosRealism.TerrainSamples", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChaosRealismTerrainSamples::RunTest(const FString& Parameters)
{
	const FVector2D Forest(45000.0, 45000.0);
	const FVector2D Marsh(61000.0, 40000.0);
	const FVector2D Ocean(82000.0, 40000.0);
	TestTrue(TEXT("forest inside fixed sample"), FChaosRealismTerrain::Contains(Forest));
	TestFalse(TEXT("city outside fixed sample"), FChaosRealismTerrain::Contains(FVector2D(15000.0, 15000.0)));
	TestTrue(TEXT("ocean water mask"), FChaosRealismTerrain::WaterMaskAt(Ocean) > 0.9);
	TestTrue(TEXT("marsh water mask"), FChaosRealismTerrain::WaterMaskAt(Marsh) > 0.5);
	TestTrue(TEXT("coast lower than forest"), FChaosRealismTerrain::HeightAt(Ocean) < FChaosRealismTerrain::HeightAt(Forest));
	TestTrue(TEXT("normal finite"), FChaosRealismTerrain::NormalAt(Forest).IsNormalized());
	const double First = FChaosRealismTerrain::HeightAt(Marsh);
	TestEqual(TEXT("repeat sample deterministic"), FChaosRealismTerrain::HeightAt(Marsh), First);
	return true;
}
#endif
