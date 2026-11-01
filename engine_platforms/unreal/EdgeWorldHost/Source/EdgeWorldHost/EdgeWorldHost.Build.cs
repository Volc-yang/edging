using UnrealBuildTool;

public class EdgeWorldHost : ModuleRules
{
	public EdgeWorldHost(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "Json", "EdgeWorldRuntime", "InputCore", "ProceduralMeshComponent" });
		PrivateDependencyModuleNames.AddRange(new[] { "Slate", "SlateCore", "RenderCore" });
	}
}
