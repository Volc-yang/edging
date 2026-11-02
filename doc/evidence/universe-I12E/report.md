# I12E strict client protocol ID generation

Status: implementation prepared; static check pending. Basea7bb2859.
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
