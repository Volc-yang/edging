# H6A walkable observatory collision

Date: 2026-11-01. Parent: V-HOME/H6A. Input `0c77e3d` on `codex/home-walkable-environment`; UE 5.8.3 installed release engine, Mac Development Editor build. This task adds local presentation collision only. It does not change the worker, Genesis, world state, GameMode, player controller, or 4D causal rules.

## Implementation

- The observatory floor, central walkway, side/far walls, pedestals, and walkway rails use static UE BasicShapes with query-only `WorldStatic` collision that blocks `Pawn` and `Visibility`. Decorative rings and markers remain noncolliding. Rails were raised from 35 cm to 90 cm so a standard capsule cannot simply step over them. The root scene component is static too, avoiding invalid static-child attachment warnings.
- Dynamically reconstructed causal node and edge proxies explicitly disable collision and overlap events. Therefore a visitor cannot use them as authority-affecting physical obstacles.
- No simulation or gameplay physics was added. The floor has an open near edge; H6B must choose a safe spawn and H6C must check the route. The collision layout does not establish an approved world topology or a vehicle landing surface.

## Checks and evidence

Final `Build.sh EdgeWorldHostEditor Mac Development` succeeded, exit 0; full raw build log `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H6A/build-final2.log`, SHA256 `87993471b52775fb90bb881c69f0c9bc458038a6faffca2df21c5e69a3f48707`.

The `edgeWorld.CausalObservatory.WalkableCollision` automation test ran in an isolated `-UserDir` with `-NullRHI` and exited 0. It creates a temporary UE game world and uses real scene queries: an entry-floor ray hits this environment at z=-140 cm; a 34 cm radius/88 cm half-height capsule is supported by the floor, stopped by the side wall and stopped by a walkway rail; a ray through a generated causal node finds no collision. The final UE log says `Result={Success}` and records wall x=-390 cm, rail y=-220 cm. Raw log: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H6A/run-final2/Saved/Logs/EdgeWorldHost.log`, SHA256 `f52512f48f7da62026a32a0069c3e1103a115c1a67377bb5f5c881cd52bb546e`. `git diff --check` passed.

The first test run failed because the temporary world contained a default `StaticMeshActor` that the queries hit before the observatory. One attempted test-world reinitialization produced `WorldSettings` name collision and was removed. The final test ignores unrelated world actors in its queries and passes against the observatory actor; those earlier logs remain under `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H6A/`. The final run has no static-child attachment warning. This is a structural collision check, not a real visitor walk or Metal visual check; H6B/H6C still need those checks.
