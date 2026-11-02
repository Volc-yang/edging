# I12D bounded session namespace

Status: focused stdlib checks complete; root/u9 final review and CI pending. Base01b16d1.
Owned runner + this evidence directory; no product/launcher/layout changes.

Optional root-card session_namespace defaults to literal sessions. It may only be
sessions or sessions-[a-z0-9-]+, ASCII and total length<=64. One helper returns a
strict safe_path direct child of storage; both initialize completion lookup and
new session output use that same root. Existing revisit still requires matching
card SHA, accepted source and normal initialize completion. Missing completion
in a new namespace cannot borrow one from sessions/another namespace.

No free paths/external roots/role changes or overwrites. Supervisor consumes the
already prepared output unchanged. Full tree_bytes(storage) accounting stays
unchanged, so old caches/failed sessions/originals remain counted; no copy, deletion
or budget reset. A new namespace requires a new approved card/hash, not hidden retry.
Runtime source layout/rpath fixes are I12-owner work, not part of this leaf.

Five synthetic prepare-only cases exercise default compatibility, explicit retry
without overwriting or omitting old bytes, invalid names/symlink refusal, cross-
namespace completion rejection, and unchanged card/source/normal requirements.
The existing metadata fixture is reused; subprocess.Popen is forbidden in all
cases. No actual authority, venv, UE, GS or CUA is touched. Commit source before
CPU<=120s/raw16MiB first + at most one justified targeted retry; no full suite.

## Actual checks

First ordinary source3ac0542 used the wrong reused fixture class name
EvidenceTools; all5 cases stopped in setUp before production namespace validation.
Real exit1/0.169s, original failure retained. Independent u9 review identified the
same test issue. Ordinary sourcefb31364724148d7914107d0cd56023bd4d5e0546 changes
only the test class to existing RunnerPreparation; production bytes unchanged.
Unique justified targeted check reran exactly5 cases and passed exit0/0.227s.
Combined0.396s (<120s), no extra suite/runtime execution. Source, shared verifier
and reused original metadata fixture SHA stable before/after each attempt.

Immutable raw under /Volumes/DevSSD/Unreal/Projects/EdgeWorld/:

| Directory | originals | bytes | raw-index SHA256 |
| --- | ---: | ---: | --- |
| I12D-20261102-session-namespace-attempt1 | 7 | 10569 | 75aca1f855a28e7c56673f9d63d2d3787ee62bae79d3d175a5383f7e3856905a |
| I12D-20261102-session-namespace-targeted | 7 | 4710 | 8ba6055e3f3a34ea1b2415d4ee7dcab50d8b1e4dfdbd443a7e90f4d73707a7c0 |

No UE/GS/CUA, authority, venv or launcher was executed/changed. The tests exercised
prepare validation only, with Popen forbidden and synthetic metadata explicitly
labelled. Actual layout/rpath/session runtime acceptance stays with I12's new card;
this tool leaf does not claim that gate passed. Final commit is report-only;
root final-source CI/review/integration required. No self-merge/cleanup.
