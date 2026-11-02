# I12F installed-editor standalone asset audit

Base: 227a7501516a819a92e27d5f0551dd52839c6fe5. Static checks passed; native validation pending.

The installed editor launched with -game has GIsEditor=false. Its verified
observation reached asset auditing, where the editor-only entry rejected it.
Collect now has a default Editor context preserving the prior guard semantics,
plus explicit InstalledEditorStandalone restricted to non-editor game,
non-commandlet, uncooked platform, initialized engine, game thread and valid ID.
Both remain WITH_EDITOR-only; no GEditor dependency or shipping support.
GameMode.VerifyInstalledAssets requests this explicit context after the existing
strict observation verification. Collector body, audit schema, DAG/native/file
checks and resolved/zeroGap/exact manifest comparisons are unchanged.

Native selector: `edgeWorld.UniverseHost.StandaloneAssetAudit` (ClientContext only; it intentionally requires !GIsEditor).
It requires actual standalone game mode, checks default rejection and invalid
world rejection, then runs the actual collector requiring resolved/zero gaps
and a canonical candidate/digest. It reads installed content only; no GS,
transport, actor or authority operations. Native compile/run and actual-session
full collect remain pending root's separately budgeted R12. ProtocolIds also
remains pending native execution despite actual ID/worker progress.

Agent may execute stdlib static checks only <=120s/raw16MiB, first plus at most
one justified targeted rerun, after ordinary source commit. No UE, build, GS,
CUA, environment mutation or authority access is authorized here.

## Executed check and handoff

Tested source: `673ee04afa2995f89e41b33719a06cd5c73953ff`.
Command: `python3 -m unittest discover -s doc/evidence/universe-I12F -p check_source.py -v`
from this worktree with `PYTHONDONTWRITEBYTECODE=1`. First attempt only;
4 guards passed (unittest 0.022s), real process PID 39605, exit 0, wall
0.076991084 seconds. Original attempt input hashes unchanged, including
strict observation parser. Guards compare the entire collector namespace
and GameMode changes against fixed base; these are static checks only.

Raw: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I12F-20261102-standalone-audit-attempt1`
includes runner, argv/cwd/environment override, real PID/exit/timing, source
and file SHA256 before/after, stdout/stderr and index excluding itself.
Index SHA256: `c85ca380ab8117eca4bdb70df9b8931dd190192466be56fc9216625dbc99dc00`.
Time cap 120s and raw cap16MiB enforced. No native compile/run, UE, GS or
authority operation performed. Root must compile and execute the exact
standalone selector and complete actual-session full collect/manifest
comparison; native and runtime acceptance remain **pending**.

Root review narrowed StandaloneAssetAudit registration to ClientContext only,
avoiding intentional standalone precondition failure in normal editor suites.
ProtocolIds remains Editor|Client. One authorized targeted static rerun checked
only the affected native-selector source guard after this source commit.

Targeted rerun source: `3e7fbfff55a8d9868b0fe4c27379ee1423352c3a`.
Command: `python3 -m unittest check_source.Guards.test_real_native_selector_has_no_authority_or_transport -v`,
cwd this task's `doc/evidence/universe-I12F`, PYTHONDONTWRITEBYTECODE=1.
1 affected guard passed, PID42246 exit0 wall0.040905833 seconds; no further
checks. Source/input hashes unchanged. Both attempts total0.118s.
Raw: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I12F-20261102-standalone-audit-attempt2-targeted`.
Index SHA256: `ce69a3f2d837438475ac3c5f2dc3f3a19c481015f6feb26f11083f2628af9293`.
First attempt remains preserved. Actual native/run gates remain pending.
