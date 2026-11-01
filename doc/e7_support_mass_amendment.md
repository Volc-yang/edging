# E7 fixed-support mass amendment

Status: implementation prepared; checks pending. Base: `13899a26108da9072cd2f58a038cafa812519b08`.
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

Implementation/check results will be appended after execution. No self-merge
or worktree cleanup is authorized.
