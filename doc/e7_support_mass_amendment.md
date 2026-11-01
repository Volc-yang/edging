# E7 fixed-support mass amendment

Status: implementation and bounded checks complete; integration review pending. Base: `13899a26108da9072cd2f58a038cafa812519b08`.
Parent: universe v0.2 runtime readiness; task owner u7; integration owns acceptance.

## Plan / fixed decisions

Genesis1.4.3 fixed primitives can expose zero solver inertial mass through public
`get_links_mass()`. The earlier universal `mass>0` predicate rejected that real
getter value in production, the independent oracle and UE observation parsing.
Only frozen `body-support` permits finite mass >=0; dynamic remains >0. Both zero
signs are accepted for support and persisted without bit normalization. Identity
comes from frozen config and exact binding, never a new provider-owned fixed flag.
Negative/subnormal-negative mass, nonfinite f64, malformed types, unknown or
ambiguous body identities and changed bindings/config remain rejected.

This narrowly corrects a runtime compatibility gap. Existing positive3200
synthetic vectors, golden bytes/digests, config bytes and v0.1 are unchanged.
Synthetic values are not runtime mass expectations. No provider/Genesis code,
Store, trust, ownership, commands, schema or integration documents are edited.

## Do / owned paths

- This report and the two physical/authority contract documents.
- `engine/universe_authority/records.py`: only the bodies mass/identity predicate.
- `scripts/validate_universe_authority_v0_2_fixtures.py`: independent predicate.
- UE `EdgeWorldUniverseObservation.cpp`: equivalent parser predicate.
- New `tests/test_universe_support_mass.py` and existing UE observation test.

Python tests independently rebuild genesis references using oracle hashing,
cross-check each hash with production, and check full archives and selective
proofs. No receipts are forged or fixture files rewritten. C++ tests construct
boundary records and independently rehash complete genesis proofs, including
forged-binding rejection. Every derived input is synthetic-only.

## Check / budget and evidence

CPU first batch <=120s and raw<=16MiB, at most one justified targeted retry:
new mass tests, existing composite-record tests and independent frozen validator;
source/fixture hashes before and after, literal commands, outputs and real exits.

Root separately authorized UE5.8.3 `-NoUBA` build and compact actual-app NullRHI
`edgeWorld.UniverseObservation.StrictV02` execution, total<=5min/raw<=128MiB,
at most one justified targeted retry within the same total budget. Check actual
processes for shared-resource conflicts first. Keep unique absolute logs/report
and DevSSD output paths; record source/binary/raw hashes and true exits. No
Genesis imports, scene creation or GPU provider execution are part of this task.

## Act / evaluation

Pass requires all boundaries agree across production/oracle/UE, rehashed valid
zero-support closures/proofs pass, identity forgeries fail, and all old frozen
vectors/hash bytes remain unchanged. Build/test success is parser evidence only,
not real Genesis physics, provider recovery, rendering or overall runtime gate.
Integration review/CI/merge and subsequent I8 real probes remain root-owned.
Failures retain original evidence and reopen only the affected check.

## Check results / exact source provenance

- CPU source `17536807e62ba7a3d34eed2727739b2579977b66`: 9 new E7 tests
  plus 8 existing composite-record tests passed; independent oracle passed
  67 golden records, 57 negative vectors and 5 proofs. All real exits 0;
  0.767s total, no CPU retry. Every source/fixture SHA unchanged during checks.
- First UE build at that source: PID21901, exit0, 43.826s. The actual app
  initialized and started StrictV02, then the newly added third-body test
  `Bodies.Add(Bodies[1])` hit UE's TArray alias-protection assertion. This was
  a test-construction defect, not a production parser failure. Original logs
  and stack retained. Exact owned fatal editor PID22352 was killed, exit -9;
  no claim of a normal exit or completed automation on that attempt.
- Corrected test source `8601ad266ed24a53d9ef9e875902a60c6d6dc754`: copy
  the shared pointer before appending. No Python or production-source changes.
  Unique authorized targeted retry: build PID22667 exit0/6.377s; actual
  `UnrealEditor.app/Contents/MacOS/UnrealEditor` PID22743 initialized,
  StrictV02 explicitly Completed Success (report succeeded=1, failed=0),
  real exit0/16.736s. Source/fixture and pre/post actual binary SHA unchanged.
  Existing 67 goldens/5 proofs/27 applicable negatives plus E7 mass boundary
  cases, independently rehashed support±0 genesis proofs and forged-binding
  rejection passed. Full UE window, including first failure/wait, 149.450s
  (<300s). There were no shared UE/UBT/reporter processes before either run.
- CPU check sources remain identical at corrected C++ source. Final report-only
  commit does not alter any checked executable/test/contract source.

Raw evidence (unique directories; no overwrites):

- `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/E7-20261102-support-mass-attempt1/`
  raw-index SHA256 `41300004f4c45bac96012f3f9da5d21708568c3e5e9a1d3c070e0818534366f9`.
- `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/E7-20261102-support-mass-ue-attempt1/`
  raw-index SHA256 `cedabd40161661391eceaa761e76e8f8ee548ab38ffa7353014ef84f68d6d533`.
- `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/E7-20261102-support-mass-ue-attempt2/`
  raw-index SHA256 `661e6e3b2b6cfff2520341ece95a3442de0550a8874e5b9d7aede9282281de7d`.

Raw CPU <=16MiB; aggregate UE raw <2MiB (<=128MiB), including runners,
commands/environment, exact PIDs/exits, stdout/stderr/absolute engine logs,
automation report, before/after sources and actual binary manifests. Generated
binary/intermediate outputs are registered separately in `output-links.json`;
they are not source commits or raw-budget data. Five task output symlinks and
UE-generated `Config/DefaultInput.ini` remain untracked for root's disposition.
The generated ini is also archived in retry raw. Fatal engine log/stack is
retained; no separate native crash file was observed in task Saved outputs.

## Handoff

Independent PR targets `codex/plan-consolidation`. Root owns review, final-head
CI acceptance, merge and eventual cleanup; I8 real getter/provider probes remain
pending. No self-merge or worktree cleanup was performed. No Genesis import,
provider/GPU scene, renderer evidence or overall runtime gate is claimed.
