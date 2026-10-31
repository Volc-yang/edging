using UnrealBuildTool;

public class EdgeWorldRuntime : ModuleRules
{
	public EdgeWorldRuntime(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "Json", "JsonUtilities" });
	}
}
