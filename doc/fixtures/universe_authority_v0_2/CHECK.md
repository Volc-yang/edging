# I0E bounded Check record

First invocation: `python3 scripts/validate_universe_authority_v0_2_fixtures.py`.
Budget120s; actual<1s; exit1. Before invocation Python3.10 grammar parse passed.
Original invocation/input hashes/stdout/stderr/exit are retained unchanged at
`/Volumes/DevSSD/edgeworld-evidence/i0e-check1-22gkua0r/`.

The 67 golden/complete archive/inventory/source-manifest and four positive proofs
passed before the fixed-negative loop reached `proof-full-history`. That vector
adds a second proposal; the verifier correctly rejects the per-kind cardinality
first, producing PROOF_LIMIT rather than the authored expected PROOF. Only that
expected error code was corrected after Check. No positive/golden or algorithm
was regenerated. Remaining negatives had not run in this attempt. Awaiting final
independent API/scope review before the single allowed targeted rerun.

This is static self-check evidence only; no runtime, storage, GPU or gate claim.

The single targeted rerun executed at source commit
`168e5f6f4add1e6996ec935256d1de9f8a944929`, with120s timeout. It completed<1s,
exit0: PASS_STATIC_CONTRACT_ONLY,67 golden/records,4 roots,57 negative vectors,
5 selective proof vectors, worst-case compact proof457,728B. Python3.10 grammar
passed; input hashes remained unchanged. Raw invocation/hashes/stdout/stderr/exit:
`/Volumes/DevSSD/edgeworld-evidence/i0e-check2-rd8h1ty4/`.

Between attempts, the single expected negative code was corrected and final
independent static API review changes were applied: public labeled HeadBinding,
pre-expansion typed edges/memo, strict auxiliary dedup, synthetic-only verifier,
horizon256, geography bounds, initial budget, compatible PinnedRoot default,
precise trust/bootstrap/provider/wire preparation APIs. Positive67-record golden
bytes/hashes were not changed. Five Observe envelopes include the four selected
roots plus explicitly unconfirmed-readonly; seven additional targeted negatives
cover the final fixes. Check budget is exhausted; no further oracle invocation
was run or authorized by this record.

Fixture bytes are static; source manifest is a read-only audit. UE/Genesis/GPU,
real key provisioning, storage/crash recovery, runtime-default export and actual
UE dependency closure were not executed. Await independent golden recomputation
and root G-C0.2 disposition; passing self-check is not self-acceptance.
