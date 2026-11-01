# I12A passive evidence tools

2026-11-02. Parent I12-P1 accepted by root. Implementation base `0a7a0fb4b4f11a70dc2e9157a28673d6f9045dd9`.
This directory records **tool preparation**, not a real UE/Genesis run or G-B2.
The assigned owner did not implement I8/I10/I11. Main workspace changes remain untouched.

Scope: `scripts/verify_universe_slice_evidence.py`, `scripts/run_universe_slice_acceptance.py`, this directory.
No product, worker, launcher, UE, engine or DNS changes. Standard library only, no production imports.
Code Complete 2 skill applied: Ch.3 requirements, Ch.8 boundary validation, Ch.12 exact numerical data,
Ch.22 directed tests, Ch.29 transport integration evidence. No agent delegation required.

## Execution boundary

Real I12 still requires root dispatch fixing the final **normally merged** source/build, accepted
G-P1/I10B/I11B/G-B1, trusted owner inputs and actual R12. The candidate budget is two sessions
combined ≤1200s/2GiB including failed attempts, not actual authorization. `run` explicitly refuses
to launch. A later dispatch must add/review real orchestration; no shell command is accepted from
an evidence JSON file. Existing I10B CLI evidence is upstream input, not either I12 session.

Both real sessions must use one new authority on DevSSD. Session1 explicitly initializes and
retains (0,1), then weak physical (1,2), followed by exact committed-closure retry. Both (0,0)
and (0,1) must be observed, including historical write/held-input rejection. Session2 is existing
mode, same canonical root/world/anchor, new owned worker PID/pipes, recovered fresh binding;
observe (1,2)/(0,1), no automatic advance. Both exit normally through explicit viewport-preflush.
Registered empty-root startup status may be NOT_READY; missing-root existing startup is
UNINITIALIZED. Before explicit initialization, require no HEAD, scratch or solver work;
do not change production to fit an error-message expectation.

Raw Metal PNGs are new stable-runtime CUA captures in an independent Space/fullscreen when
needed, not startup HighResShot. UI operations occur only after later dispatch; no CUA binding
is performed in I12A. Scripted camera motion proves local-view read-only behavior, not a human
relative-mouse gate. LOD is N/A for this technical proxy; record why. Standard pause and
t.MaxFPS require actual readback/action evidence. Each action gets an individual before/after map.
Legacy default/preflush limitations remain. Do not send crash reports, kill processes or reuse
old mouse evidence as a new domain gate. Unexpected unknown preserves original CommandId;
no automatic new intent or fault injection.

## Commands

From this worktree (all paths supplied to evidence should be absolute and canonical):

```sh
python3 scripts/run_universe_slice_acceptance.py
python3 scripts/run_universe_slice_acceptance.py --output /existing/evidence/before.json snapshot --authority /existing/authority
python3 scripts/run_universe_slice_acceptance.py --output /existing/evidence/processes.json processes --pid 123
python3 scripts/run_universe_slice_acceptance.py --output /existing/evidence/metadata.json metadata /private/owner-config /private/key-dir
python3 scripts/run_universe_slice_acceptance.py wait-marker --log /existing/ue.log --initial-sha256 HASH --marker 'Universe world' --seconds 10
python3 scripts/run_universe_slice_acceptance.py --output /existing/evidence/bundle.json collect --spec /existing/evidence/spec.json
python3 scripts/verify_universe_slice_evidence.py --bundle /existing/evidence/bundle.json
```

Default is stdout-only plan. Output files are exclusive mode0600; no directories are created.
Metadata uses lstat only, never reads private bytes. Map hashes existing public authority files,
refuses symlinks/potential key paths, creates no root and does not acquire a writer lease.
`processes` executes only `/bin/ps` for explicitly supplied PIDs. A missing PID is not an exit code.
`wait-marker` polls only newly appended log bytes, bounded ≤60s/16MiB, with caller-pinned initial
log hash. It does not trigger an action; start the waiter before the externally authorized action.
`collect` hashes only enumerated public artifacts; private_key/owner_config content roles are refused.
Do not put keys/config contents into evidence under another role. Keep private keys outside raw.
Every failed marker wait is evidence, not an instruction to retry or kill.

## Bundle v1

`collect` takes JSON `format="universe-i12-evidence.v1"` plus the following fields; artifact input
entries need only `role,path`, while collected entries also pin `bytes,sha256`:

* `resource_card`: actual root-issued card reference; `budget`: `seconds,bytes,elapsed_seconds,covers_all_attempts`.
* `artifacts`: exhaustive unique absolute paths, including **every** copied authority/trace file,
  maps, images, action logs, build/source/environment identity and failed attempts. Required roles:
  source, build, public_pins, owner_metadata, asset_export, ue_log, launcher_log, processes.
* `sessions`: exactly two objects with `authority_copy,canonical_authority,trace_directory`;
  `ue_exit` and `launcher_exit` each contain `observed,pid,exit_code,process_evidence` (indexed
  parent-wait/raw process evidence path). The two exit roles are distinct, worker exit is decoded
  separately from actual I11 trace. No inference from launcher PID or process disappearance.
* Each session's `screenshots`: `path,renderer="Metal",after_observation,captured_at,before_exit`.
  Times are ordered numeric seconds on one declared capture clock. Keep original PNG, capture
  metadata, visible world/tick/revision and observed UE source/RHI log binding for review.
* `readonly_pairs`: `action,before,after,action_evidence`, all three paths indexed. Required action
  IDs are camera, visibility, framerate, pause, history, history_write_rejected, held_input, retry,
  revisit. Repeated pairs per action are encouraged; actual low-level input/console interval and
  view readback must be present. A pair compares all files, not a list of selected hashes.
* `independent_reviews`: gate→indexed review document path, for causal_chain, initial_six_places,
  exact_history, same_closure_retry, input_gates, metal_ui, source_build_identity, trusted_bootstrap,
  resource_authorization. These remain human/root responsibilities; booleans are insufficient.

Immutable authority copies are captured only at quiescent markers. Bind copied bytes to live
before/after maps and capture timing. Include all history/raw, orphan files, registered-root/lock
metadata and failures; never prune old attempts to fit budget. Capture schema/tool/source hashes.
Trace JSON follows I11R2 source `3e8b0b8`: per-prefix contiguous serial, PID/generation, raw_file,
byte_count, request/write-result/stdout/stderr/response-complete, stdin-eof and worker-exit payload.
Verifier checks actual request write size and reassembles split stdout without normalizing bytes.

## What checks establish

The verifier independently implements canonical record hashing, complete typed refs/acyclic
closure, raw descriptor size/hash, initial geography/time, retain invariants and physical state
D using exact Fraction subtraction and ties-to-even. It consumes the accepted schema as data,
not production code. It checks maps, artifact inventory/byte/time budgets, trace continuity,
owned identities and decoded normal worker lifecycle; screenshots must be indexed original PNGs
with observation/capture/exit ordering. `--authority`/`--trace` are explicitly partial checks.

It does **not** authenticate runtime MACs (no key access), reconstruct every schema scalar's
domain predicate, establish true UI operation or GPU work from a label, certify build binaries,
prove real-world action timing from self-reported JSON, or authorize resource use. Independent
review must compare original logs/frames, source/build pins, MAC-recovery behavior and maps.
The review must verify two admitted commands and exact same-closure retry, no extra solve/root/
charge/cursor, all precise selected proofs, parser rejection and write gates. Missing evidence
is inconclusive; contradictions fail. Exit0 means structural checks complete **requiring root
verdict**, never G-B2. Exit1 is malformed/contradictory evidence; exit2 is required missing evidence.
No new realism, performance, default-exit-root-fix, mouse, G-Q or production claims follow.

## I12A verification

`selfcheck.py` uses literal accepted contract goldens and explicitly synthetic trace/archive
files in temporary directories. No trust provisioning, registered authority, solver or renderer.
Tests cover exact numbers, JSONL errors, split frames, truncated writes, raw corruption, missing
bundle requirements, exclusive outputs, symlinks and private metadata boundaries. Raw check
output and exact script hashes accompany the implementation report. Actual runtime fields remain
empty until later root dispatch.
