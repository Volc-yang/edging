# CHAOS-REALISM-01 T1: terrain and water prototype

## Scope

This opt-in UE 5.8.3 preview generates a fixed seed-7, 650 × 450 m continuous terrain mesh covering forest, river marsh, and coast. It adds ocean, river, marsh, and route mesh sections without reading or advancing the authoritative Worker. The existing default GameMode and Chaos scene are unchanged.

`FChaosRealismTerrain::Sample` exposes height, normal, slope, water mask, and sample bounds in the P0 world centimetre coordinates for the vegetation task. The preview GameMode is `/Script/EdgeWorldHost.ChaosRealismTerrainPreviewGameMode` on `/Engine/Maps/Entry`.

## Implementation decision

The installed UE Landscape workflow does not provide a stable runtime construction path for this prototype. The installed `ProceduralMeshComponent` plugin builds the continuous height surface in four colour sections. The UE Water plugin is Experimental; ocean, river, and marsh are mesh stand-ins. These are technical proxies, not production water or approved realistic art.

## Verification

- UE 5.8.3 `EdgeWorldHost Mac Development` build succeeded (`Renders/Terrain/build_final.log` on DevSSD).
- `edgeWorld.ChaosRealism.TerrainSamples` passed in NullRHI Editor automation. It checks bounds, coast height relation, marsh/ocean masks, finite normal, and deterministic repeated sampling.
- Independent Metal game preview on `/Engine/Maps/Entry` logged `land_vertices=46800`, `water_sections=3`, `route_segments=4`; see `Renders/Terrain/preview_metal_final.log` on DevSSD. It uses no Worker and does not share the other Chaos preview's state directory.
- An in-engine Metal screenshot was captured to `Renders/Terrain/seed7_terrain_metal.png` on DevSSD (SHA-256 `29b9ad2843a8943aabe17884ac1482e19b7ab7e7c038186e4cb5e7c6e14fcfc4`), but it is black despite successful mesh creation. This does **not** pass visual acceptance. V1 must diagnose the standalone `/Engine/Maps/Entry` camera/render setup and recapture a visible image.

## Limits and handoff

This surface has deterministic geometry and query interfaces, but no licensed photoreal terrain materials, foliage, shore foam, water simulation, collision, streaming, or performance budget. The preview is for T1 integration and visual layout checks only. E1 may call the read-only surface query. Final assembly and realism gate remain with the lead task.
