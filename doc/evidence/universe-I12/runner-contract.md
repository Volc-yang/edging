# I12A-RUNNER — executable preparation, no actual R12 dispatch

One supervisor invocation owns **one** launcher Popen until actual parent wait returns.
Use initialize then existing sessions from the same card. The outer tool must keep the Python
supervisor process/session alive; do not detach it and later infer exit from `ps` disappearance.
The model uses future approved CUA tools for all UI/console/camera/quit/capture actions while
the supervisor runs. No UI input, screenshot API, AppleScript/JXA/CGEvent, window manipulation,
worker requests, trust provisioning or solver calls exist in this driver.

Default `plan` never launches. Real invocation syntax, for a **later actual root dispatch**, is:

```sh
python3 scripts/run_universe_slice_acceptance.py run --r12-card /private/persistent/r12.json --card-sha256 ROOT_PIN --accepted-source EXACT_PRODUCT_SHA40 --session initialize --execute
python3 scripts/run_universe_slice_acceptance.py run --r12-card /private/persistent/r12.json --card-sha256 ROOT_PIN --accepted-source EXACT_PRODUCT_SHA40 --session existing --execute
```

These commands were not run in preparation. Missing execute/card/hash/source is rejected before
launch. There is no CLI fake mode, free-form shell, arbitrary command array or automatic retry.
The card is an honest local-root authorization boundary, not a remote signature scheme. Keep
mode0600 in an owner0700 directory, UID-owned, nlink1 and canonical/nofollow. Root separately
provides its SHA; a self-invented file is not an actual R12 dispatch.

## Root card `universe-i12-r12.v1`

Required fields:

* `approved:true`, `issuer:"root"`, `scope:"two-real-ue-owned-sessions"`, `allow_forced_cleanup:true`.
  Explicit cleanup permission covers only failure/budget exact-owned TERM then KILL; a forced
  exit always fails supervision. `issued_at,expires_at` are timezone-aware ISO UTC validity bounds.
* `run_id,world_id`, exact `product_source` SHA40, canonical `product_root`, and `launcher_sha256`.
  `accepted_gates` has exactly G-P1/I10B/G-B1 references accepted by root. Tool source is **not**
  product source: the tool branch predates the accepted I11 entry. Product must be the later
  accurate normal integration containing PR97/100 and frozen owner/trace/Host APIs. Never use
  the old tool worktree's launcher. Driver invokes the accepted product's fixed script with
  `--launch --viewport-preflush --universe --owner-config ABS --user-dir ABS`; initialize alone
  adds `--universe-initialize`. The actual accepted launcher performs build with -NoUBA internally.
* `allowed_untracked` is an exact relative-path map. For each preplaced output symlink: include
  `kind:"symlink",readlink:<literal>,target:<canonical DevSSD dir>,provenance:<root record>`.
  For generated DefaultInput.ini: `kind:"file",sha256:<root pin>,provenance:<root record>`.
  Driver verifies every declared item, rejects every tracked modification and every unknown
  untracked path. No blanket untracked ignore or directory-prefix exemption.
* `storage_root` is existing private0700 under `/Volumes/DevSSD/`; `deployment_root` is existing
  private0700 inside it. Four `inputs` exactly build/options/assets/asset_audit, each `{path,sha256}`,
  must already be copied into the persistent deployment and match by SHA. Driver never copies
  from an old worktree or silently replaces inputs. No actual inputs were generated in this card.
* `authority_root` is inside storage, never its ancestor. `key_directory` is owner0700 **outside
  storage/authority/raw**; metadata only, key files are never opened. Existing session requires
  HEAD; initialize rejects an already visible HEAD. Driver never creates/registers authority.
* `launcher_output_root` is canonical existing directory inside storage. The accepted product's
  `engine_platforms/unreal/EdgeWorldHost/Saved/MacLauncher` must already resolve to it. Root's
  deployment must preplace mappings; driver never edits launcher or creates source symlinks.
  Source links are inspected only via the exact allowlist. Evidence traversal uses canonical
  DevSSD **targets**, rejects internal evidence symlinks, and never recursively follows a source
  mapping. This avoids both untracked-source false failures and silent evidence aliasing.
* `python_executable,ue_root`, plus nonempty `runtime_files` of `{path,sha256}` for root's accepted
  executable/Build.version/host/plugin identity pins. File contents are hashed, no binaries run
  during validation. Actual runtime/build correspondence remains independently reviewable.
* `budget` has integer `seconds` ≤1200, `bytes` ≤2GiB, `cleanup_seconds` 1…30, and explicit
  `spent_seconds,spent_bytes` for previous attempts external to this storage. Root accounts every
  prior failure; no hidden fresh quota. Current storage's all files count as well, including
  persistent inputs and both session outputs. Time/bytes leave cleanup and 1MiB evidence reserve.
* `sessions` has exactly initialize/existing. Each has `{owner_config:{path,sha256},max_seconds,
  stage_seconds:{build,startup,interaction,shutdown}}`. Both owner files must already exist in
  deployment, UID-owned0600/nlink1 under0700, hash-pinned. Trusted typed metadata is read once
  for cross-check, never printed/copied into evidence. Card also pins exact `context` (the ten
  DeploymentContext fields), `principal` and `allowed_actions` (retain_snapshot/physics_step).
  Owner mode, typed initialization grant, key directory, world/root/trust/profile context and
  all four path/SHA input specs must exactly match card; expected B/O record digests are independently
  recomputed from deployed public records. A separately valid inputs list cannot hide an owner's
  stale indirect worktree path. Scratch must be persistent and disjoint from authority/deployment/key.
  No key file is opened. Driver passes only private owner path to child. Sum session limits plus
  earlier spent time cannot exceed total.

## Supervision and failure evidence

Each session uses exclusive `storage_root/sessions/<session>`. Existing outputs refuse overwrite
before Popen; new failures need a new explicit root decision/card/output, not automatic retry.
Initialization and re-entry cannot overlap; existing requires the same-card/source initialize
`completion.json` marked normal plus HEAD. Preliminary `supervisor-exit.json` is always normal=false
and can never authorize existing. Normal completion is only supervision, never G-B2.

Supervisor writes source/card/argv/environment-path receipt, PID/PPID/start/argv observations,
stage/budget event JSONL, raw launcher stdout, authority before/after maps when present, actual
launcher wait code, launcher's actual parent-wait UE status and decoded real worker-exit trace.
Startup/interaction transitions depend on accepted launcher's actual markers, not sleep. Stages
are build→startup→interaction→shutdown (shutdown detected from engine exit marker); total caps
apply even if a marker is absent. There is no automatic UI operation or semantic success from a
helper assertion. Actual StartPlay path, independent camera transforms and new Metal/image
identity must still be supplied in real I12; I11B helper checks cannot substitute for them.

On failure, first TERM our actual Popen child so its normal trap/UE EndPlay may close pipes.
After grace, only previously observed descendants with unchanged PID/start/argv are signaled;
unrelated/reused PIDs are never signaled. Parent uses actual wait and bounded KILL fallback.
Unknown/detached/unobserved processes are reported, not guessed by authority path. Any remaining
owned processes, incomplete trace, failed observation/exit or exceeded budget fails supervision.
An interrupted/error path preserves diagnostics and actual wait results where available. Runtime
event-write failure cannot bypass cleanup: failure logging is best effort and cleanup is in finally;
secondary log/close errors do not replace the original runtime error. Live byte measurement uses
lstat, refuses symlinks/nonregular entries, and tolerates only FileNotFound from Store atomic rename.

Session seal hashes current raw files (large raw remains DevSSD) and records that later CUA
screenshots need final collection/sealing. Receipt/whole seal are written before final accounting.
Completion charges ceil(observed time after sealing)+2 seconds for its own final write/audit, and
computes the exact JSON byte fixed point including the completion file. After writing pending
completion, actual elapsed/bytes are audited against that conservative charge before publishing
`completion.json`. Exceeded time/bytes yields false or no completion, never an existing-session
grant. Pending/failure evidence stays intact. Second session charges the first final cumulative
time. The final bundle still independently counts every artifact. All original attempts persist.
Tool tests only mock Popen/git/ps/cleanup/logs; they do not prove the future runtime path, physical
startup, UI, Metal rendering, default exit reliability or G-B2. Root must review exact runner
source/card/product/deployment and separately issue actual R12 after unlock and accepted gates.
