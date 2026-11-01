# I10A CPU worker construction

Status: implementation and I10R review fixes complete; independent final review/CI/integration pending. No real Genesis, UE or GPU was imported or run. I10B / G-P1 / G-B1 / G-B2 remain open.

## Scope and source

Base `761a9673eae92a22dcdb99b2200a40fb16c4b0b2`, branch `codex/i10-universe-worker`, worktree `/Users/yangacan/edgeWorld/edge-world/.worktrees/i10-universe-worker`.

Source `5bcb056` introduced pure 26-record static assembly, 31-record initialization with validated raw closure, explicit owner modes, exact owner/public schemas, literal lazy GenesisProvider import, single lease/Store, E4 command execution, E5 recovery/status/observation, strict bounded JSONL, sanitized correlated failures, and unknown-outcome exit. Source `75f82fe0c0c5fee6d7df4fbd48a2dd09c2cdc7c8` corrects the committed-prepare test's identity expectation and adds typed-locator enumeration and recovery/capacity/stdout checks. Production contains approved authored static geography/config only; measured B/O, assets, physical samples/checkpoints and trust keys remain external inputs. No fixture or synthetic provider import exists in production.

CLI: `python -m engine.universe_authority.worker --owner-config ABS`, optionally `--print-public-pins`. Print mode requires runtime artifact class but does not load inputs/keys, acquire a lease, create authority/scratch or import provider. Normal worker never measures runtime options at startup/status. Only explicit initialize request invokes provider initialization. Existing mode recovers full closure/raw first. The trusted provider path is `engine.universe_authority.genesis_adapter.GenesisProvider`; this source's base intentionally lacks I8's module, so normal production execution requires accepted I8 integration. No stub or CLI fake switch was added.

Assets retain the provided body exactly, rebinding world_id only, and require id `asset-manifest-runtime`. I10R source `0522433` additionally checks the owner-pinned runtime asset audit: resolved/no gaps, exact candidate except world rebinding, candidate digest, 9 content/files, 4 native terminals, 18 registry edges, package/manifest dependency closure, file hashes/bytes and observed totals. The worker does not rerun UE asset collection or independently measure those files. The approved I0A audit/manifest metadata is copied under approved-asset-inputs solely as a pinned CPU validation input. Owner session and all input specifications are frozen once. Runtime key provisioning is never implicit. Existing private canonical owner scratch directories are reusable, preserving all content; read/status never create or clean scratch. Existing HEAD is refused before provider construction by the already existing acquire() locked guard, now covered explicitly; no duplicate private HEAD reader was added. Worker-generated protocol/build/reinitialize errors use frozen SCHEMA/BUILD/NOT_READY; owner path/permissions use ROOT_MISMATCH/AUTHORIZATION.

## Bounded CPU checks

Both invocations archived original source and all fixture inputs before running, plus argv, relevant environment (no secret environment dump), Python/platform, actual unittest child PID, stdout/stderr, exit, and authority file maps/raw before/after each WorkerTests case. Raw files are synthetic and explicitly labelled. Key directory is never archived.

| Attempt | Source | Result | Measured time | Indexed original bytes |
| --- | --- | --- | --- | --- |
| 1 | `5bcb056` | 7 pass / 1 test error, exit 1 | 0.283s | 3,537,183 |
| 2, sole reasoned rerun | `75f82fe` | 11 pass, exit 0 | 12.286s | 4,041,706 |
| I10R root-authorized review card, first check | `0522433` | 15 pass, exit 0 | 11.283s | 4,162,171 |

First error: test supplied different approval/command IDs for a committed prepare retry, correctly receiving `COMMAND_CONFLICT`. E4 requires original IDs. The corrected test reuses original IDs, separately asserts the conflict, and retains the original failed invocation unchanged. Each attempt stayed below 120 seconds and combined original bytes stay below 64 MiB. After the original card closed, root explicitly issued I10R with a new 120s/64MiB card for the four review boundaries. Its first invocation passed all 15 tests; no I10R rerun occurred.

Passing checks: safe owner permissions/aliases/hardlinks and runtime-only production context; exact 12 public pins without key/input/root creation; no implicit initialization on status; 31 records/9 existence/6 places/36 typed slots; read-only status/observation; deterministic prepare; retain→physical→retain; exact historical pairs; committed retry after later HEAD; stale uncommitted rejection; H64 capacity rejection while old retry succeeds; real Store W6 post-replace injected failure returns unknown then stops channel; close/new Runtime recovery returns committed result without another physical call; corrupt HEAD fails without provider construction/fallback; malformed/duplicate/invalid UTF8/CRLF/NUL/overlong frames; uncorrelated malformed frames produce no invented ID; Python/native fd1 noise is redirected to stderr while protocol fd remains clean.

Evidence limitation: recovery above recreates Runtime/Lease/Store inside the same Python process, not a true owned CLI process restart. The public-pins and stdout-isolation checks launch actual child processes and assert exit/stdout/stderr, but do not separately save those internal child PIDs/output as raw files; only the outer unittest child's actual PID/output/exit is archived. Unconfirmed read-only and deeper authenticated corruption cases rely on the already accepted E4/E5 kernel tests; this card does not claim new independent coverage for those paths.

## Original evidence

Full original trees are preserved at `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I10A-20261102-cpu-archive/{cpu-attempt1,cpu-attempt2}`. Every copied source/raw byte was verified equal before replacing only the worktree's original input/authority copies with this archival reference. Git contains each attempt's raw-index, invocation, stdout/stderr and archive index hash. Relative paths in raw-index resolve against its DevSSD attempt directory. No compression, truncation or relabelling was used to fit the cap.

I10R original tree is `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I10R-20261102-cpu-attempt1`; source/inputs/raw were archived there on first invocation, and review-attempt1 holds the hash index and necessary logs. The new cases reject unresolved/gapped/mismatched candidate/hash/count/edge audit inputs, prove initialize-mode existing HEAD leaves all authority hashes unchanged and constructs zero new providers, and prove existing private scratch reuse preserves contents. Typed slots are computed from actual validated current records/segments/binding items/rules/state slots with record/path locators, not a hardcoded count.

Next: independent source/evidence review and CI, then root integration. Only after fresh accepted I8 B/O and G-P1, execute separately authorized I10B against exact runtime artifacts and true subprocess lifecycle. This card passes a CPU construction check only.
