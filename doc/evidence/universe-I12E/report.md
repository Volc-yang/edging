# I12E strict client protocol ID generation

Status: implementation committed; 3 static guards passed. Native validation pending.
Base: a7bb2859. Tested source: 87a23dbb55697ffc3ee7b570a7477cf915a702f3.
Owned GameMode.h/.cpp + ProtocolTest.cpp + this evidence only.

Actual StartPlay first status was rejected locally as REQUEST before worker or
authority: FGuid Digits defaults uppercase A-F while the accepted strict wire ID
accepts lowercase only. Prepare's c-ID had the same later failure. Parser remains
unchanged; fixing its grammar would hide the generation defect.

One fixed two-kind factory supplies u-/c- IDs with DigitsLower, including default
NewGuid and deterministically injected FGuid through the same method. Actual
SendControl, Observe and Prepare generation sites all use it. No free prefix,
signing, shared-contract change or world state changes.

New tiny native test `edgeWorld.UniverseHost.ProtocolIds` is EditorContext and
ClientContext. It injects a known A-F GUID into the actual factory, then exercises
strict status/observe Request and actual BuildPrepare→strict prepare builder;
expected lowercase strings/lengths and derived record ID bounds are checked.
Old lowercase prefix + uppercase Digits remains explicitly rejected. All metadata
is synthetic in memory; no transport, owner file, actor or GS operations.

Agent authorization is stdlib static only<=120s/raw16MiB first+one justified
failure retry, source committed before checks. check_source.py guards actual call
sites/single implementation and native regression wiring; it does not mirror
GUID behavior or claim compiled/native execution. Root's separately budgeted
R12 combination must compile and run the tiny test in the actual session.
No agent UE/nativebuild/GS/CUA/venv activity or runtime acceptance claim.

## Executed static check

Command: `python3 -m unittest discover -s doc/evidence/universe-I12E -p check_source.py -v`
with `PYTHONDONTWRITEBYTECODE=1`, from this worktree. First attempt only:
3 tests passed, process PID 14470, exit 0, elapsed 0.0771865 seconds.
No rerun. Source commit and five input SHA256 values remained unchanged,
including the unmodified strict parser EdgeWorldUniverseObservation.cpp.

Raw directory: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I12E-20261102-protocol-ids-attempt1`
contains runner, exact argv/cwd/environment override, PID/exit/timing, source
identity before/after, stdout and stderr. The index excludes itself.
Index SHA256: `7fc47c2a68e2579e58928bc74a6a091c7cc5a27739c59c69b2bd4aefb93bc2f1`.
Budget enforced: 120 seconds and raw below 16 MiB.

Native compile and `edgeWorld.UniverseHost.ProtocolIds` execution remain
**pending**, owned by root under its R12 runtime budget. These static checks
verify source wiring only. No UE, Genesis, native build or runtime acceptance
was performed by this task. Prior R12 failures remain preserved.
