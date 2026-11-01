# H2 UE causal observatory implementation

Date: 2026-11-01. Parent: V-HOME/H2. Base `b55128a`, branch `codex/home-causal-scene`, code commit `3a36ef5`.

The UE5 release-build host now creates a fixed spatial frame when its causal actor begins play. The environment uses only engine BasicShapes: a floor, walkway, far and side walls, three tick plinths and position markers. It remains in place across observations. Validated abstract nodes and edges still use the existing deterministic x=200 cm/tick and y=`influence_mm` mapping; all graph points receive a constant presentation height of 115 cm and larger meshes for legibility. No worker, transport, rule, state, command or engine source changed. The geometry is a technical observatory, not an approved 4D world topology or a realistic environment.

Editor build: `EdgeWorldHostEditor Mac Development` against installed UE 5.8.3 completed 29 actions, exit 0. Full log: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H2/editor-build.log`, SHA256 `41ef99ba7887b09487fc8275ace8c0149a030c49004c11b4eeaa5874172c1349`. `git diff --check` passed. Existing camera pose (750,-900,700), rotation (-27,132,0), FOV 55° projects tick 0/1/2 nodes at approximately -2.0°/-9.1°/-16.9° horizontal, within the frame; this is a geometry calculation, not a rendered visual check.

The first Metal frame was washed out by automatic exposure. H2 added an unbound post-process exposure bias of -3 EV and rebuilt (`editor-build-v2.log`, 4 actions, exit 0, SHA256 `a48c7126829a71f2804837fe09adb8f64380ce47d3143c0ee21f2c66ddf940b8`). In the second Metal run, the dark floor, walls, walkway, plinths, colored causal nodes and edges were legible at tick 0/1/2. Raw 960×600 UE `HighResShot` images are local only at `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H2/`:

| Frame | SHA256 |
| --- | --- |
| `tick0.png` | `2b14c957d714a66920586bab78d16017d83fac577e882e6e9e198bb1f2f06282` |
| `tick1.png` | `fc8649f1667891fa697765bdbee9ead25b9ccb55ef82ad13e05932fd63b6dd87` |
| `tick2.png` | `a4943f8ca4f789e2766cb8c6336c331697d94863609b48097e5e34a072a1facb` |
| `history0-camera-w.png` | `2cc6a6ca5c1ff631b1bb71fd737fc54ff54339ceb129b87cee064091001d8828` |

The manifest moved from tick/revision 0/0 (SHA256 `6a54afc2…803bfcf`) to 1/1 (`494bae4e…b5e31`) and 2/2 (`238d210d…d52b9c17`) after two explicit Space presses. W camera motion and 0 history observation then left the tick-2 manifest byte-for-byte unchanged (`238d210d…d52b9c17`). H returned to head. `ue-metal.log` SHA256 `e824d7976f645ea7f404b45118b0d8b3016c3671056b09a78b862eb8d2e3b2af` includes `LogExit: Exiting`; Cmd+Q process exit code was 0, and no matching UE/worker remained. This is a bounded H2 technical visual/read-only check, not an independent G4 test.

An unrelated neutral white sphere is visible in the frames. H2 creates no neutral sphere: its environment uses only cubes/cylinders, while the validated causal actor creates the colored graph sphere(s). H3 owns GameMode and is investigating the likely default pawn mesh; the combined run must verify removal before visitor acceptance. The scene remains a finite BasicShapes proxy rather than a realistic world. Formal G0 visual/performance thresholds remain open.
