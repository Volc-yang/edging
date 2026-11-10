# I20B — realistic presentation profile / CPU contract

2026-11-10；status **complete design/CPU deliverable; independent review pending**。Worktree `.worktrees/i20-profile`，branch `codex/i20-profile`，base6c533af；parent/root owns integration. No product or authority code changed.

## Delivered

- [Profile design and executable D3/D4 task cards](../../design/universe-realistic-presentation-profile.md).
- [Fixed JSONSchema2020-12 structures and explicitly synthetic fixtures](../../fixtures/universe_realistic_presentation_profile_v0_1/README.md).
- [Scoped CPU checker](check_contract.py), [actual output](cpu-check.txt), [machine result/source hashes](cpu-result.json).
- [Isolated dependency identity](dependency-identity.json) and [exact version lock](requirements.lock.txt). Installed jsonschema4.23.0 only in `/private/tmp/edgeworld-i20b-contract-env`, using `pip --isolated --index-url https://pypi.org/simple`; project/user `.venv` untouched. All downloaded dependency URLs/hash identities are retained, not an implicit new product dependency.

The versioned renderer mode is `realistic-readonly-sidecar.v0.1`; the verified authority continues declaring `basicshapes-proxy.v0.2`. ViewBinding records both identities, exact world/Manifest/State/Event/triple/Transform, profile SHA, independent renderer build SHA and generation. No source wire, golden record, worker/I0A asset audit, public pins or old authority was rewritten. Actual rendered identity belongs in developer logs; normal product UI shows meaningful time/load/error information, not hashes.

Source facts inspected include the current parser's BasicShapes-only constants, I0A exact graph and Actor loading path; original six decorations are Cube markers, not authored tree species. Current GameMode updates Session before ApplyVerified, so D3 explicitly owns the last-complete-view/HUD atomicity fix and its real producer tests. This task does not claim that failure path was fixed or executed.

## Checks actually run

Final command: `/private/tmp/edgeworld-i20b-contract-env/bin/python -B doc/evidence/universe-I20B/check_contract.py` — **14 tests passed**, unittest0.471s, actual process exit0. The original stdout/stderr bytes are saved in `cpu-check.txt`; `cpu-result.json` binds exact checker/fixture bytes. Earlier directed runs were13 tests/0.293s, then14/0.484s while adding material rules; final results bind the final input set.

These are two different checks:

1. JSONSchema validates exact structure/version/types and unresolved-vs-proposed Native metadata shapes.
2. Independent semantic code hashes **actual temporary file bytes** and exact profile bytes; rejects missing/mutated source/license references, traversal/symlinks, duplicate/missing/cyclic dependencies, wrong mesh/material roles and source PlaceKind, duplicate material slots, missing alpha coverage declarations, invalid normal/color-space recipes, unstable/misplaced instances, wrong context or cross-time/profile/renderer binding. No schema-only result is advertised as file verification.

All synthetic positive profiles use unresolved Native metadata and `.fixture` strings that explicitly are not glTF, textures, UE assets or third-party licensing evidence. Results always retain `runtime_authenticity_verified=false`, `license_authenticity_verified=false`, `hud_atomicity_verified=false` and `visual_gate=not_run`. A purported `native-observed-proposal` can only satisfy structural/reference consistency; it still needs an actual Native producer and independent review. The checker never grants runtime readiness.

I20A's asset-index SHA `d9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7` was actually re-read in the sibling A tree. Only public metadata was read by B; B did not download/open the models or verify their render quality. Stable cross-node links target integration `doc/evidence/universe-I20A/` after A is integrated, not that temporary sibling tree.

## D3/D4 handoff and limitations

The next implementation uses actual A input identities, genuine imported mesh/material classes, Native unit/pivot/bounds/slots and licensing/source review. Fern's separate Alpha PNG must bind OpacityMask0.5/Masked/TwoSided because its BaseColor JPEG has no alpha. Ground's glTF preview sphere must not become terrain; DX normals and ARM channels need explicit UE sampler checks. Real Native evidence, not synthetic examples, must fill import metadata.

No UE compilation, engine/UI session, worker, Genesis solve, key/owner content read, authority write, or existing main-checkout modification occurred. HUD/Actor atomicity, missing-asset runtime failure, actual PBR wiring/coverage, platform/cook support, visual quality and performance are all **planned/unexecuted**. No I18/I19 result or source failure was relaxed. Actual profile/loader/Actor/GameMode implementation remains D3 under a separate reviewed card; this fixture is not a new generic runtime framework.

Recommended next action: independently review the exact diff and rerun14 checks, integrate the bounded design/CPU delivery alongside A, then publish the D3 import/adapter/build cards with fixed actual sources. Worktree is to be retained until review/PR completion; there is no runtime dependency on this temporary tree because all fixture paths are repository-relative and final links target stable integration locations.
