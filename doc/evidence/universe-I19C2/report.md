# I19C2 — explicit fourteen-step slice admission

Implementation complete; independent review, CI and runtime admission remain separate. Base `8c3523d`, branch `codex/i19-slice-admission`, worktree `.worktrees/i19-slice-admission`, target `codex/plan-consolidation`.

## Frozen interface and scope

- Card `universe-i19-capability.v2`, scope `one-existing-metal-readonly-history-input-slice-then-native-replay`.
- Prepared `universe-i19-prepared.v2`; the same exact 36 fields, pinned source/tool/native/build and all inherited runtime checks still apply.
- Card/prepared `probe_manifest_ref` must match. The manifest must equal `probe_actions.probe_manifest_v2()` as a typed JSON value; canonical encoding also prevents bool/int or float/int equality from accepting changed types.
- Only this card/prepared/manifest combination admits at most 20s per exact fixed logical step. Changed commands, costs, action order, missing/extra items and optional actions are rejected. The 900s/global, 420s/Metal, 180s/Native, 2GiB and normal quit reserves are unchanged. CLI shapes remain unchanged.

## Timing

For v2, `started_monotonic` is the permit's `issued_monotonic`, before the before-map snapshot, rather than the later consume timestamp. `completed_monotonic` is measured after raw-ref validation, the after-map snapshot and trace checking. A slow after-map therefore produces a timeout receipt retaining both maps and the actual raw-tool ref, then requests quit. A before-map that exhausts the permit cannot be consumed. Actual CUA/round-trip delays between begin/end remain inside this clock bracket.

Old v1 card/prepared/manifest behavior, its 10s absolute permit cap and narrower command-specific caps, consume timestamp and end timestamp placement are retained. This versioning does not retroactively change an old result or grant the full matrix/G-B2. The receipt file's own final serialization occurs after its timestamp; root also accounts the full outer tool wall interval and evidence-writing cost.

## Checks actually run

- `python3 -B -m unittest discover -s tests -p 'test_universe_slice_admission.py' -v`: 11 passed, 0.041s; exact opt-in/ref/typed manifest, timing and slow-map negative cases.
- `python3 -B -m unittest discover -s tests -p 'test_universe_iteration_probe*.py' -v`: 23 passed, 0.435s; old full probe and new finite slice.
- `python3 -B -m unittest discover -s tests -p 'test_universe_iteration_i15_cli.py' -v`: 6 passed, 0.001s.
- `python3 -B -m unittest discover -s tests -p 'test_universe_*completion.py' -v`: 24 passed, 9.838s, under explicit process-observation permission; only synthetic Python child writers were launched.
- `git diff --check`: pass.

No UE/build/worker/Genesis/UI/private owner/key actions. No product/parser/C++ changes. Root owns the real run, original evidence, outer time/resource ledger and final acceptance. All live Metal/input/PNG and new exact-response Native checks remain pending.
