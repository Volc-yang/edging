# I0A — installed UE source-asset closure export

Status: exporter implemented; one measured resolved candidate, awaiting coordinator review.
This is an **editor installation source-content graph**, not a cooked/package closure,
shipping-license approval, rendered image, physics result, or G-Q/typed-world scale gate.

## Source and scope

- Base: `e47065a3319cddf20d6a757b85cbdcbabab10ae4`.
- Tested implementation: `937c8665e58b37e9e2a0dbc633ea7429a0120cb6`.
- Worktree: `/Users/yangacan/edgeWorld/edge-world/.worktrees/i0a-universe-assets`.
- Branch: `codex/i0a-universe-assets`; PR targets `codex/plan-consolidation`.
- Owned implementation: `EdgeWorldUniverseAssetAudit.h/.cpp`, its automation test,
  and `EdgeWorldRuntime.Build.cs` adding only an Editor-conditional private
  `AssetRegistry` dependency. No `UnrealEd` dependency was added to this module.
- UE5.8.3 / CL58210709, installed release. No parser, contract, worker, engine,
  `.uproject`, static fixture/golden, or existing authority state was modified.

## Actual result

Two collections in the same explicitly started NullRHI process produced byte-identical
full audits and canonical candidates. The four authored roots are Cube, Cylinder,
Sphere and BasicShapeMaterial: **three meshes and one material**.

| Source asset | Bytes | Content Package dependencies |
| --- | ---: | --- |
| `/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial` | 9,557 | none |
| `/Engine/BasicShapes/Cube.Cube` | 16,384 | WorldGridMaterial |
| `/Engine/BasicShapes/Cylinder.Cylinder` | 36,719 | DefaultMaterial |
| `/Engine/BasicShapes/Sphere.Sphere` | 61,552 | DefaultMaterial |
| `/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial` | 34,943 | T_Default_Material_Grid_M, T_Default_Material_Grid_N, CameraDepthFade |
| `/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial` | 30,169 | T_Default_Material_Grid_M, T_Default_Material_Grid_N, CameraDepthFade |
| `/Engine/EngineMaterials/T_Default_Material_Grid_M.T_Default_Material_Grid_M` | 134,708 | none |
| `/Engine/EngineMaterials/T_Default_Material_Grid_N.T_Default_Material_Grid_N` | 9,201 | none |
| `/Engine/Functions/Engine_MaterialFunctions01/Opacity/CameraDepthFade.CameraDepthFade` | 19,108 | none |

- Measured `A_declared=4`, `A_actual=9`, `asset_bytes_actual=352341`.
- All nine captured content files were standalone `.uasset` files. No same-stem
  sidecar, cooked flag, unsupported resource table, virtualized/referenced trailer
  payload, unresolved content edge, ambiguity, cycle, or limit gap was observed.
- Eighteen Registry edges were retained with category/property flags. Package
  queries impose no hard/soft/game/build filter. Manage/SearchableName edges are
  audited as such and are not turned into content dependencies.
- Four separately verified loaded compiled-in native terminals:
  `/Script/CoreUObject` (flags16), `/Script/Engine` (16),
  `/Script/NavigationSystem` (16), `/Script/UnrealEd` (80). These are **not A assets**.
  The UnrealEd terminal underlines that this export is an editor-source graph;
  cooking and packaged runtime dependencies require their own later measurement.
- Candidate record digest:
  `48c79f429917bebbebfc69a78dfc6970353a7b3e6286eeb6d7c7d57c2b12665e`.

The candidate uses audit-only `world_id=asset-audit-world`. I10 must explicitly
compose the approved owner/world initial records and recompute their identities;
this file neither initializes nor migrates an authority. The real defaults also
show why merely relabeling the four static declarations would be wrong: the
meshes reference WorldGridMaterial/DefaultMaterial and their further dependencies.

## Validation actually executed

First invocation only; the permitted targeted rerun was unused.

| Check | Real result |
| --- | --- |
| `EdgeWorldHostEditor Mac Development -NoUBA`, PID18306 | exit0; 43.750s |
| Actual `UnrealEditor.app/Contents/MacOS/UnrealEditor`, PID18704 | initialized; `edgeWorld.UniverseAssetAudit.ExportRegistry` started/completed Success; exit0; 21.357s |
| Separate stdlib/public E1 cross-check, PID18819 | exit0; 0.514s |

UE report: succeeded1, succeededWithWarnings0, failed0, notRun0. Total bounded
window: **65.688s of300s**. Raw evidence: **4,557,891 bytes of128MiB**.
The stdout success line alone was not the disposition: the cross-check used public
`validate_record`, strict `decode`, `canonical` and `digest`, independently recomputed
all nine recorded file SHA256/byte counts, and checked root coverage, package edges,
content/native separation, ID uniqueness, complete DAG reachability and manifest
references. This separate implementation was run by the same task owner; it is
not a substitute for the coordinator's nonauthor review.

The exporter forces synchronous on-disk rescans of each discovered package, then
queries disk-only assets. It checks file size/modification time before and after
streamed hashing and again after traversal. Package summary/trailer inspection
uses public CoreUObject APIs without loading payloads or contacting virtualization.
All original source/config/fixture inputs and launched binaries matched their
post-run hashes. The actual PID exited normally; no cleanup signal or crash
report submission was used. No asset bytes were copied or downloaded.

## Preserved evidence

Run directory:
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I0A-20261102-assets-attempt1/`

Raw index:
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I0A-20261102-assets-attempt1/raw-index.json`

Index SHA256:
`0159d32458dfba1c2dc21ec28a5f252f082fe0ab7ed2ce855f319c612f26fab4`

The 111 indexed files include source/config/fixture snapshots, exact argv and
process IDs/exits, full build/editor stdout/stderr, UE initialization/test report,
prelaunch and post-run module hashes, both complete collections, the separate
canonical candidate, cross-check code/command/result, and post-source verification.

Relevant payloads under that directory:

- `asset-export/collection-first.json`, `collection-second.json`: nodes, all-category
  Registry edges, native flags, per-file bytes/hash/stat observations and disposition.
- `asset-export/candidate-record.json`: exact canonical frozen-schema asset record.
- `independent-check-result.json`: separate public E1/stdlib check result.
- `prelaunch-binary-manifest.json`, `post-binary-verification.json`: actual binaries.
- `output-links.json`, `generated-DefaultInput.ini`: known generated output evidence.

## Limits and next action

Any future missing/unknown/native-unloaded dependency, sidecar, ambiguous object
mapping, external mount, cycle, limit breach, cooked package, external/unsupported
payload or schema mismatch yields explicit gaps and **no candidate**; actual A/bytes
stay null. Existing sidecars are hashed for evidence, never silently excluded from
an otherwise resolved record. These rejection branches were reviewed in code;
this run encountered no such real source asset and did not inject synthetic bad
engine files. In particular, no asset hash framing extension was invented.

The frozen eight entry keys and two body keys remain unchanged; source/use/license
literals remain the installed UE technical-proxy declarations with shipping review
open. The old synthetic fixtures and their `A_actual=null` are unchanged. Nine asset
entries are not U8's typed structure count and do not establish realism or scale.

Next: coordinator independently reviews this exact implementation and raw evidence,
then I10 may consume the measured graph as an input to its explicit initial-world
assembly. Recompare file identities against the candidate before presentation;
future cooks, asset changes and dynamic runtime references require fresh evidence.
No PR self-merge or worktree cleanup was performed. Five DevSSD output symlinks and
UE-generated `Config/DefaultInput.ini` remain untracked, excluded from commits,
for coordinator cleanup after integration; the DevSSD output targets are retained.
