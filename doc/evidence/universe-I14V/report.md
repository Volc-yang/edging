# I14-V independent public-evidence composition

Base `729dcdcfd907fa8214d544543e413eb27e763daf`; status implementation
prepared, CPU checks pending. Owned verification.py, its test and this report.
No product/shared verifier/A/B/C modifications, UI, UE/native build, solver,
provision, key or private-input reads. Public authority COPY directories are
explicitly inventoried before fixed independent archive/trace parsers read them.
The real authority is never traversed by this module.

## Frozen public API and versions

`verify_evidence(bundle_ref, *, expected_policy, authority_parser, trace_parser)`
returns status `fail`, `inconclusive` or at most
`checks_complete_requires_review`, always `g_b2_granted=false` and
`runtime_authorized=false`. Fixed parser code is passed by root, never selected
by JSON. Callback booleans/`passed` objects are rejected. Authenticity of trusted
root code/policy, source/card and public originals remains independent review;
a malicious trusted Python caller is outside this structural verifier's boundary.

One-way imports actions/capture/lifecycle only. Calls the frozen
`lifecycle.validate_ledger_v2(ledger, expected_policy=policy.lifecycle,
actual_finalized_monotonic=policy.actual_finalized_monotonic)` and D's
`manifest_v2/readiness_v2/validate_session_v2`, preserving old v1 behavior. Until
those accepted implementations are integrated the result is inconclusive. The
lifecycle policy, including external launcher_source_ref, is passed unchanged.
No manual wait/role/budget relaxation substitutes for the v2 validator.

Top policy fields are exactly the root-frozen `format,lifecycle,
actual_finalized_monotonic,public_context,schema,manifest_ref,resource_card_ref,
capabilities,session_expectations`. Policy format is
`universe-i14-verification-policy.v1`. Expected policy originates outside the
bundle; it is never populated from a bundle's declarations.

Bundle `format=universe-i14-evidence.v1` has exact fields `format,artifacts,
resource_card_ref,manifest_ref,ledger_ref,sessions`. Artifacts are exact
`{path,sha256,bytes}`; they cover the external public allowlist except the bundle
itself (its hash is the caller's bundle_ref, avoiding self-reference). Actual
bytes/hash, public scope, no symlinks, every public parser-directory file and
nested `{path,sha256}` refs must agree with that inventory. It never follows
private references to manufacture an allowlist.

Session keys exactly `initialize,existing`. Each session has exact fields
`binding,authority_copy,trace_directory,trace_refs,action_receipt_refs,captures`;
captures items are `{capture_id,capture_ref}`. External session expectations have
exact fields `authority_copy,trace_directory,trace_refs,captures`. Each external
capture expectation has:

```text
capture_id, action_id, stage, trace_frame_index, observation_ref,
trusted_head, selected_observation, clock, after_map_ref,
after_map_monotonic, before_exit_monotonic, before_exit_ref
```

D and V agreed that v2 B image_checks items are exactly
`{capture_id,stage,capture_ref}`, with capture_id=`action_id+'/'+stage` and
exactly one item per required stage. V consumes each global ID and receipt once,
matches the B action/stage and external expectation, and matches its authority
map content with that checkpoint. Each C original/prepare/command/log and all
nested refs are inventoried. C verifies the actual capture interval and exit
wrapper; actual-before-exit is also bounded by the matching B exit action. B,
C and ledger must share the exact controller clock. No captured_at single point
is generated and the legacy verify_bundle is never called.

## Proof closure actually implemented

Fixed independent inspect_authority/inspect_trace are root code dependencies.
V checks parser outputs have real records/frames/one normal transport, rehashes
all returned archive records, checks final archive HEAD against action current
head and cross-compares every independent raw frame with B's separately loaded
trace. Existing-session initialize/prepare/advance is rejected, both sessions
bind the same external run/world/root/source/card/context and distinct PIDs.
Normal completion, actual waits, core/build role checks and global accounting
are delegated to accepted L v2 rather than invented from callback flags.

For EVERY observe, V independently checks wire/result identity, strict payload
fields/profile, selection integers, record keys/canonical hash/size/schema keys,
identity collisions and per-kind limits, declared reference names/kinds against
archive records, head→selected membership links/revision/tick continuity,
selected manifest/state/event hashes, unique auxiliary records, selected/prior
closure, no unused records and exact sorted opaque omissions. History proof
current head and selected ancestor remain separate. Each capture's observation
wrapper verification_ref must hash an actual full JSON observe response
matching that exact independently reassembled trace frame; a `passed` label or
arbitrary verification bytes cannot replace the response.

## Existing proof checks NOT claimed complete

Even an otherwise consistent composition remains **inconclusive** while these
existing UE contract checks have no accepted independent public implementation:

1. FValidator::Record typed body value constraints beyond scalar/schema/ref
   keys (numeric ranges, unions and record-specific value constraints).
2. FValidator::Static selected geometry/options/transform constraints, including
   full places/routes/asset/config/binding/unit-transform semantics.
3. FValidator::Transition selected-proof semantic parity beyond the existing
   archive inspector's independently recomputed retain/physics history checks.

These are named gaps in the existing strict Observe contract, not new gates.
Archive record equality and known closure validation are necessary but do not
claim the full UE parser ran. Root must later connect an independently accepted
public proof verifier or keep this outcome inconclusive. Real strict UE parser,
Metal/UI provenance, card/bootstrap authority and source authenticity remain
root's real-run/independent verdict, never inferred from matching metadata.
D/L can be independently accepted without closing these V/runtime gaps.

## Check scope

Focused synthetic tests exercise known proof/hash/membership/history/opaque
closure and fail-closed composition, missing adapters/components, forged parser
booleans, wrong external policy/ref/source/clock, stale/replaced PNG originals,
missing/duplicated/unclaimed captures, wrong actual exit ranges, extra writes,
normalfalse and map/trace/hash/allowlist disagreements. The composition fixture
uses explicitly fake A-v2/B-v2 adapters and fixed synthetic archive/trace results
to test V integration only. Actual C prepare/collect/verify and PNG decode run
against synthetic public tempfiles. Such mocks do NOT accept D/L, real archive
physics, actual parent waits, real UI/Metal or a runtime card. D/L integration
and final shared-verifier adapter are root follow-ups. Source commits precede
CPU checks; raw original attempts/limits are retained separately on DevSSD.

First focused suite executed source `ad55208a072b854868a5cee71e3e5e45448d63e3`:
20 tests passed, one history-proof synthetic fixture errored because its schema
added event/index kinds but omitted their kind_bytes limits. Production code
correctly required the bound; no production code changed for this fixture fix.
The original attempt is preserved. Only that history case will rerun after the
ordinary test/report commit adding the two explicit synthetic size limits.
