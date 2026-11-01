# I12A-OFFLINE — accepted I10B data, read-only

2026-11-02. Root found a real verifier error: archive profile had incorrectly been
used for persisted HEAD storage identity. Earlier synthetic wrapper construction
repeated the same mistake and did not catch this integration difference.

Input: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I10B-20261102-runtime-attempt2-topological-authority`.
Schema is this tree's `doc/fixtures/universe_authority_v0_2/schema.json`, pinned in
`offline-targeted.json`. No Store, Lease, production imports, Genesis, keys, worker,
UE or CUA. No provisioning, ownership registration or changes to the dataset.

The root-issued card allows ≤30s/raw2MiB, first check and one targeted retry only.

| Attempt | Ordinary committed source | Result |
| --- | --- | --- |
| Unmodified real input | `4e892ffe20fc6efd672b9428411def21c4a8ab54` | Expected failure `HEAD identity`, exit1, 0.067s; `offline-initial.log/json`. |
| Corrected affected offline check | `ef1770721e9f2e3437890c65e2938888ac75090a` | Exit0, 0.068s; `offline-targeted.log/json`. |

Correction is confined to the independent verifier and synthetic evidence wrapper:
persisted `HEAD.json.profile` must be `local-posix-blob-sync-v0.2`; the archive/
HeadBinding profile remains `composite-rigid-support.v0.2`. Production and source
data are unchanged. Manifest revision0 requires only state, while later revisions
require state/event/index/prior_manifest, following the contract's optional-ref
union rather than interpreting every `?` as freely omissible. Output distinguishes
storage/archive profiles, raw payload count and state budget/cursor/physical steps.
No additional real-input discrepancy appeared in the one targeted retry.

Root's immutable expectations were compared as supplied, with all true:

* 81 record files, 5 retained roots, 3 unique real raw payloads.
* Exact retained pairs: (0,0), (0,1), (1,2), (2,3), (2,4).
* D: null, null, −7, −48, −48; weak/strong values recomputed from exact binary64
  snapshot positions using independent Fraction arithmetic and ties-to-even.
* Final tick2/revision4, budget6, random_cursor2, physical_step_count16.
* Complete hashes, typed refs, acyclic retained closure and every raw descriptor
  payload hash/size were checked. Descriptor bytes total 787486.

`offline-before-map.json`, `offline-initial-after-map.json`, and
`offline-final-after-map.json` are byte-for-byte identical maps of all authority
files (paths, sizes, SHA256), also compared against the second attempt's immediate
before map. `offline-targeted.json` records the comparison. Large source raw stays
on DevSSD; only small hashes, logs and reports are committed. Prior attempt/guard/
PREP2 evidence is retained unchanged. No unrelated old tests or full suite rerun.

This establishes an **offline partial authority check on upstream accepted I10B
data**, not either new I12 UE-owned session, real transport/Metal/navigation gate,
or G-B2. `verify_bundle` was not run; missing UE/images/two-session proof remains
open. Draft PR99 stays draft, run mode disabled; await final merged source/owner
inputs/actual R12. Locked Mac is not bypassed or counted as a passed gate.
