# CHAOS / ONE six-place visual proxy (V1)

This is a disposable UE 5.8.3 BasicShapes presentation of the committed seed-7 `InitialWorld`; it does not alter the InitialWorld JSON, worker state, O1 event or observation rules. `ChaosWorldActor` has no Tick. Place and route IDs come from the input JSON and are logged with their coordinates when projected.

| Place ID / kind | Center (cm) | Visual cue | Suggested camera location (cm) | Focus (cm) |
| --- | --- | --- | --- | --- |
| `city-1` / city | (15000, 15000) | warm blocks and a tall roofed tower | (5000, -5000, 18000) | (15000, 15000, 0) |
| `wildland-1` / wildland | (17500, 80000) | ochre rocky cones and a central peak | (7000, 60000, 20000) | (17500, 80000, 0) |
| `plain-1` / plain | (35000, 20000) | yellow-green field strips | (25000, 4000, 16000) | (35000, 20000, 0) |
| `forest-1` / forest | (45000, 45000) | green conifer grid | (30000, 20000, 23000) | (45000, 45000, 0) |
| `river-marsh-1` / river_marsh | (60000, 40000) | teal water, reeds and raised islands | (50000, 20000, 17000) | (60000, 40000, 0) |
| `ocean-1` / ocean | (85000, 50000) | blue water with pale wave bands | (73000, 30000, 22000) | (85000, 50000, 0) |

Use FOV 55° for local views. Route overview suggestion: camera (50000, 50000, 85000), focus (50000, 50000, 0), FOV 65°. The committed `origin-route-1` goes city → plain → forest → river-marsh → ocean via five stored points; a dark edge and bright raised center mark it. `river-1` follows its three stored points from forest through marsh to ocean using a wider blue channel. The visual line widths and elevation are presentation choices, not geography rules.

For independent C3 review, record each camera transform actually applied, world/tick/watermark, log lines for all six place IDs and both line IDs, screenshot hashes, and pre/post worker manifest/state/event digests. The construction log and NullRHI startup confirm only that geometry was created; they cannot prove Metal visibility or region continuity. The proxy still lacks authored city, terrain and ecosystem assets and should not be described as a near-perfect world.

## V1 construction check (2026-10-27)

`Build.sh EdgeWorldHostEditor Mac Development -Project=<this EdgeWorldHost.uproject> -WaitMutex` succeeded with UE 5.8.3. `UnrealEditor-Cmd <uproject> '?game=/Script/EdgeWorldHost.ChaosGameMode' -game -nullrhi -unattended -nosplash -NoSound -ExecCmds=quit -log -stdout` exited 0 both with the built-in fixture and with `-ChaosWorldData=<fixed seed7 JSON> -ChaosInitialHash=<P0 canonical hash>`. The external-input run's `EdgeWorldHost.log` recorded six `Chaos place projection` lines, `river-1`, `origin-route-1`, and `ChaosWorld projection built ... places=6` with the P0 digest. This confirms only construction and stable provenance; C3 must inspect actual Metal frames and the state isolation matrix.
