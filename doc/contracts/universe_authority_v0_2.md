# Universe Authority v0.2 — I0E composite contract

2026-11-01. I0E local reopening, implementation base
`d2b7d29d8602db7da8f19bf21637fce98123dc36`. This document and fixed vectors are
submitted for **independent G-C0.2 review**, not self-acceptance. No production
module is changed here. v0.1's neutral kernel, archives, public API and evidence
remain supported and untouched. Unknown/mixed versions fail closed; no migration,
implicit upgrade, garbage collection or legacy HEAD fallback is authorized.

This profile joins the already accepted technical six-place initial geography
and I7's `genesis-rigid-support.v0.1` candidate interface. Seed→Tree denotes
initial state→causal development, not botanical growth. Geography and BasicShapes
are technical proxies, not physical terrain, ecological laws, realism or new
spirit rules. UE5 release plugins/adapters remain the preferred presentation
path. G-P0 is static physics design; G-P1, G-B0 and UE gates require real evidence.

## 1. Encoding, identities and schema

Domain is `edgeworld.universe.authority`; version is the **string `0.2`**;
transport protocol_version is the **integer 1**. Retain v0.1 section 1's exact
canonical C(x), strict UTF-8/JSON parsing, scalar-ordinal key sorting, ASCII
escaping, integer range ±(2^53−1), lowercase finite `$f64` big-endian bits,
Unicode scalar validity and bool-vs-int distinction. No raw JSON floats,
NaN/Infinity, duplicate decoded keys, BOM, lone surrogates or trailing tokens.
Depth≤32, objects≤64 keys, strings≤4096 UTF-8 bytes, internal arrays≤256.
Archive/proof packaging arrays have the explicit limits below; they do not
relax any record. Wire bytes are checked before parsing; one final LF is
optional, CRLF and embedded raw LF/CR are rejected. Fixture pretty printing
is packaging only, not JSONL wire syntax.

For every complete record R:

```
H(R) = SHA256(b"edgeworld.universe.authority\0v0.2\0" + C(R))
```

Every record has exactly `domain,version,world_id,kind,id,body,refs`. IDs match
`[a-z][a-z0-9._-]{0,63}`. `(world_id,kind,id)` and event_id are unique and
immutable; cross-world refs, cycles, forward refs and unknown keys/enums/kinds
are rejected. Refs are whole-record lowercase SHA-256, not URIs or mutable IDs.
Content is immutable, collisions with differing bytes are corruption.

The normative exact body keys, scalar specifications, per-kind byte caps,
required refs and physical parameter literals are in
[`schema.json`](../fixtures/universe_authority_v0_2/schema.json). This is an
allowlist, not an open object schema. `pN` on route means exactly p0…p(n−1),
matching the ordered place_ids. For revision0, manifest has only state; later
manifest refs state/event/index/prior_manifest are all required. Event omits
prior_event only for the first event. No other optional refs are introduced.

| Group | Kinds / relationship |
| --- | --- |
| Persistent existence | existence: allocated world/place/physical ID, spirit_record=`not_separately_assigned` |
| Geography | place→existence; route→ordered places; watercourse→forest/marsh/ocean |
| UE projection | asset_manifest; unit_transform; projection→assets/transform |
| Provider identity | provider_build; resolved_options→build; physics_config→build/options |
| Physical data | physics_binding→config/dynamic_exists/support_exists; physics_sample→config/binding; checkpoint_descriptor→config/binding/build; physics_snapshot→config/binding/sample/checkpoint |
| World | world_manifest→world/dynamic/support existence, six places, two routes, watercourse, projection |
| Authority | state→world/snapshot; proposal/intent/approval→command→candidate→admission→event→result→index→manifest, with exact refs in schema |

The archive wrapper is exactly
`{domain,version,test_profile,artifact_class,records,head}`. test_profile is
`composite-rigid-support.v0.2`. Records are in topological order. All supplied
records, including orphans, receive structural, typed-ref, context, receipt and
available linked semantic checks; only manifest-linked results on the pinned
retained chain are committed idempotency successes. Orphan candidate/result or
index is never a success. Recovery validates complete retained closures and raw
payloads; it never promotes an orphan to HEAD.

## 2. Initial world, assets and units

Initial state has tick=revision=random_cursor=0, development_mm=null, budget=8.
Initial snapshot has case_id=`initial`, physical_step_count=0. Null D means no
physical influence has yet been measured; do not replace it with zero. Initial
world_manifest allocates exactly nine persistent existence IDs: one world,
six places, dynamic body and support body. Existence is explicit; no existence
or spirit assignment is inferred from UE actors, place names or asset IDs.
No independent spirit-domain record is assigned by this technical profile.

The six distinct places are city, wildland, plain, forest, river_marsh, ocean,
with closed bounded footprints. Main route is
city→plain→forest→river_marsh→ocean; branch is forest→wildland. Watercourse refs
forest, river_marsh and ocean in upstream/marsh/outlet roles. Routes are authored
connectivity, not measured traversal. Watercourse is authored topology, not a
fluid solver. Footprints and polylines are integer cm within the declared
technical world extent; elevations are cm. Geometry points are counted explicitly.

Physics remains SI, right-handed Z-up. Versioned transform `si-to-ue.v0.2`
is p_UE_cm=origin_cm+100·(x,−y,z). Unit quaternion/velocity transforms must use
the versioned handedness conversion in the future UE adapter. Physical layout
is versioned-transform; development layout is explicitly abstract-magnified,
with declared development_cm_per_mm. D is not a physical body displacement in
UE cm and must not be presented as biological height.

BasicShapes proxy declares Cube, Cylinder, Sphere and BasicShapeMaterial from
the installed UE5.8.3 content. Each entry pins URI, bytes, SHA, dependencies,
source/use/license_status; each decoration pins instance/place/asset IDs and
position/scale. `declared-static` explicitly means these four declarations are
**not the complete UE dependency closure**. A_declared=4, A_actual=null and
asset_bytes_actual=null in static fixtures. The files' actual bytes were
read/hashed for declarations; this does not prove transitive materials/textures
or shipping license clearance. Runtime `runtime-resolved` requires a complete
UE AssetRegistry-exported dependency graph, all recursively reachable entries,
content hashes and byte counts, compared to the manifest before presentation.
Only that complete graph can report actual A/bytes. No UE registry export was
performed here. A false resolved label is invalid in synthetic context.

## 3. Provider build and options identity

The I7 numerical configuration is copied under authority_version=`0.2`, not
silently edited in I7: Genesis1.4.3, Metal, solver_precision32, seed7, two rigid
entities, eight Scene.step calls per physical advance, horizon32; all exact
options are `schema.physics_parameters`. Physical candidate rules, contact,
fixed-support, settle and recovery probe obligations remain I7's accepted
[`universe_physics_v0_1.md`](universe_physics_v0_1.md). This oracle is not evidence
that those dynamic obligations have run.

provider_build pins distribution/version, METADATA byte SHA, Python ABI,
critical source byte hashes, installed Python source-tree hash/count, dependency
METADATA/version and adapter source hash. Tree hash is SHA256(C(files)), where
files is the path-sorted list `{path,sha256}` of installed package `.py` files,
relative slash paths, excluding generated bytecode. The supplied audit lists
264 files. It is an installation identity, not a wheel signature or guarantee
of all native dependency bytes. Runtime adds a non-null hash of the actual
candidate adapter source. Synthetic adapter_source_sha256=null; never insert
an arbitrary SHA to make synthetic evidence appear runtime eligible.

resolved_options binds build and SHA256(C(physics_config.body.config)). Its
normalizer is `public-model-dump.v0.2`. `static-declared` has AST-derived
declarations and exports={}; strings describe source declarations, **not
executed defaults**. `runtime-exported` requires complete normalized public
dumps of sim_options, rigid_options, dynamic_morph, support_morph and
rigid_material, including inherited defaults. Preserve finite floats with
$f64; enums become their explicit declared value, tuples become arrays, public
model fields are key-sorted. Unsupported values fail BUILD; no repr/address,
private-field dump, nonfinite coercion or dropped unknown values. Full output
must fit its declared record cap or fail; do not truncate to fit.

Owner-injected deployment context pins expected_build and expected_options
record digests. The adapter measures and compares both before initialize,
load_checkpoint or propose; mismatch BUILD and no solve/admission/write. An
archive cannot nominate its own trusted build/options. Runtime identities must
be measured in the actual runtime, not copied from static audit fixture SHA.

## 4. Commands, revisions and causal development

Retain v0.1's single writer, authenticated retry-before-new-action ordering,
command fingerprint, admission separation, event/result/index atomicity and
W1…W8 / write→V→D commit semantics. Every new accepted command increments
revision by one; watermark=revision. Only these two actions are admitted:

| action | tick_delta / case / budget | candidate / state effect |
| --- | --- | --- |
| retain_snapshot | 0 / null / 0 | adapter checkpoint_reuse; exact prior snapshot; tick, physical_step_count, D (including null), budget and random_cursor unchanged |
| physics_step | 1 / weak or strong / explicitly authorized nonnegative cost | adapter genesis; eight steps; tick+1; step count+8; budget−cost≥0; cursor+1; new snapshot and computed D |

retain_snapshot is an **explicit approved command**, with distinct proposal,
intent, approval, command, candidate, admission, event, result, index and root.
Observe/status never create a revision or a reuse command. Reuse performs no
solver call, random draw or blob copy. Physical solve starts from exact prior
checkpoint/config/binding; provider has no authority writer. Random cursor
counts physical commands only in this profile, not internal solver RNG draws.

For physical action, sample dynamic z is solver float32 promoted exactly to f64.
D_mm is the nearest integer, ties to even, of
`1000 * (exact_binary64(z_after) − exact_binary64(z_before))`, computed using
Decimal.from_float, precision2000, ROUND_HALF_EVEN. Finite |D|≤1000. Do not first
round/subtract through binary64 or use an approximate UE float. D is a bounded
physical influence input to abstract development, not a general evolution law.
Candidate/state D, tick and revision agree. State keeps exact world_manifest.
Result.checkpoint refers to physics_snapshot, not candidate or a fabricated blob.

Command fingerprint is H(command), including signed approval refs; approval
exists before fingerprint. Candidate binds command/prior_state/snapshot.
Admission is signed after candidate and binds exact command/candidate; admission
never goes into fingerprint. This ordering has no hash/signature cycle. Repeated
same (world,principal,command_id) and fingerprint returns original retained
result with no solve, new A, new root, cost or cursor. Conflicting fingerprint
fails COMMAND_CONFLICT. Authentication still applies to historical retries.

## 5. Durable local trust — owner injected, not archive supplied

v0.1's fixed trusted_receipts map cannot authenticate future unknown real
candidate hashes. v0.2 introduces `local-hmac-sha256.v0.2`, implemented later in
a separate trust.py card. This is a cooperative local POSIX/honest-owner model,
not remote identity, hostile same-UID isolation or an external account service.
The initial root has no receipt, and HEAD has no external monotonic seal. Internal
MAC/closure validation alone does not prove genesis authenticity or detect rollback
to an earlier valid HEAD. Bootstrap and HeadBinding rely on the honest registered
local owner/root; this profile makes no anti-rollback or malicious-owner-filesystem
tamper-resistance claim.

An explicitly configured key directory is outside authority_root, mode0700.
Provisioning is an explicit owner operation before root initialization. Key is
exactly32 cryptographically random bytes, independent of world seed, in a
regular no-follow single-link mode0600 file; reject symlink/replacement/unsafe
permissions. File and key-directory entries are fsynced before root initialize.
Opening for read/status/observe/recovery never creates a key/directory. Missing,
wrong or unreadable key means unavailable/AUTHORIZATION; no regeneration,
fixture fallback, default allow-all or zero key. Never log/export/repr the key.

Owner registration pins a unique canonical authority_root plus world/domain,
version/profile, algorithm/anchor, expected_build/options and artifact_class.
CLI state-dir must equal that root; a copied/migrated authority directory, even
with the same world/key, fails ROOT_MISMATCH. Path identity is also checked under
the lease; no alias, symlink escape or automatic re-registration. Root identity
adds trust_algorithm and trust_anchor. Registration is external trusted input,
not a field accepted from archive/CLI request JSON.

Exact framing (NUL is one byte; ASCII digests are lowercase):

```
anchor = SHA256(b"edgeworld.universe.trust-anchor\0v0.2\0"
                + world_id.ascii + b"\0" + canonical_authority_root.utf8
                + b"\0" + key32)
unsigned = full_receipt with only body.auth_tag removed
message = (b"edgeworld.universe.receipt\0v0.2\0" + anchor.ascii + b"\0"
           + kind.ascii + b"\0" + C(unsigned))
auth_tag = HMAC_SHA256(key32, message).lowercase_hexdigest
```

The auth_tag itself is part of the final receipt's canonical bytes/digest.
Verification compares MAC in constant time and checks complete receipt/world/
principal/refs/revision/expiry semantics. Recover validates **all historical
approval/admission MACs** from the retained closure before D_recovery. A valid
MAC is not a substitute for causal/revision/rule validation.

Only the coordinator receives a signer. Candidate provider receives no key,
signer or authority-root write capability. Store/records receive a read-only
verifier; I2 receives public expected_root/anchor, not a signer import. A verifier
must be injected by owner and cannot be constructed from archive contents.

`fixture_key.json` publishes bytes00…1f for test reproducibility. Runtime rejects
**those exact key bytes for every world/root**, not just this fixture's anchor.
Synthetic fixture root `/edgeworld-static-fixture/composite-demo` is an inert
identity string and is never provisioned. Oracle's FixtureVerifier is a
public-key test helper, not the runtime key owner or secret API.

## 6. Full recovery and selective read proofs

Full closure/raw validation is retained for writer recovery, durability and
historical corruption. A wire Observe is a separate **selected-slice proof**,
not a complete archive and never input to validate_closure/validate_archive.
No raw Genesis bytes are sent to UE. Before expansion, check all supplied typed
ref targets, then memoize traversal by (digest,normal/previous mode) with active
cycle rejection. A shared DAG must not cause exponential work before rejection.

Trusted caller inputs are outstanding request ID, world/context, exact
(tick,revision,watermark), authenticated public HeadBinding (head, world_id, canonical authority_root,
trust_algorithm, trust_anchor, domain, version, profile, artifact_class,
expected_build and expected_options) and expected
profile/build/options. A response cannot establish its own trusted HEAD. HeadBinding comes from this
owned authority after full successful recovery, or explicit unconfirmed-readonly
recovery with its label; never from the same untrusted response. The verifier
compares every context field to this separately supplied binding before parsing
the slice. No key or secret verifier is needed by the UE proof consumer.
Envelope exact keys are protocol_version,request_id,ok,result; success result
exactly domain,version,world_id,operation=`observe`,payload. Payload exact keys:

```
manifest,state,event,watermark,storage_state,artifact_class,
head,membership,records,opaque_refs
```

manifest/state/event are full selected records; event=null only revision0.
Membership is manifest records ordered pinned HEAD→selected, including both,
max64 with no loops; each prev digest/revision/tick step is verified. records is
the exact selected manifest dependency slice, including index/result/command/
approval/proposal/intent/candidate/admission and world/physics/config/binding/
build/options/assets/geography dependencies. Include immediate prior manifest,
prior state and required old sample/snapshot to verify F or exact reuse. Do not
recursively include unrelated prior event/index/command history. Canonical
records are deduplicated: records excludes explicit manifest/state/event and
membership copies. References omitted solely for unrelated membership history
and historical event predecessors are sorted unique opaque_refs. Missing
selected dependency, extra historical record, duplicate/conflicting ID or
incorrect opaque list fails PROOF. No raw/checkpoint/whole-archive extra fields.

Verifier checks original wire bytes/strict parser, request/context/version,
record SHA/typed refs, membership from trusted HEAD, exact watermark, selected
transition, build/options and dependency scope. Receipt MACs are authenticated
by selected records' committed inclusion under the already trusted HEAD; a
client is never given the secret. This proves selected slice membership and
local transition, **not all omitted historical semantics, raw integrity or
successful durability**. storage_state=`unconfirmed_readonly` stays explicit
and never authorizes writes. A storage corruption elsewhere must be caught by
full recovery; do not advertise selective Observe as recovery.

## 7. Bounds, inventory and storage accounting

Engineering caps are enforced independently and never silently reused as a
product scale target. S is transitive current state-reference JSON objects;
H is retained manifest count; D is projection instances; A_declared and A_actual
are distinguished as above. Max S288, H64, D1000, A64; geometry points4096;
asset graph bytes≤2GiB. Internal array256 remains a tighter cap where applicable.
Archive≤2048 records and≤16MiB; individual record≤64KiB plus tighter kind caps.
Each raw descriptor≤8MiB; unique retained raw bytes≤512MiB. Duplicate retained
raw hashes count once only when size/media/class metadata match. Actual disk
copies, duplicate files and orphan raw bytes are separately counted; these caps
do not authorize hidden duplicates or automatic deletion. Raw SHA is ordinary
SHA256(payload), distinct from prefixed record hashes; descriptor pins actual
byte count/format/media and config/binding/build. Reject missing/corrupt raw;
never relabel static text as `.gstraj`.

Observe≤1MiB wire; membership≤64, records≤96, opaque_refs≤256. Every per-kind
cardinality/cap is in schema.proof_kind_max/kind_bytes. Sum of those products
plus65,536 wrapper reserve is **457,728 bytes**, below1MiB. Count repeated
explicit fields in this bound. Enforce actual wire bytes too; fail PROOF_LIMIT
or LIMIT rather than truncating dependencies/history. This is a proven bounded
profile, not the size of an entire 64-root archive.

Fixed positive inventory (independently enumerated in inventory.json): S30,
H4, D6, A_declared4/A_actual=null,40 geometry points,67 JSON objects totaling
38,090 canonical bytes. Declared asset bytes124,212; actual closure bytes unknown.
Two unique static raw files total82B. All per-kind JSON and raw/orphan counters
are explicit in inventory.json. U8's provisional S32 estimate is not silently
adopted. Raw/checkpoint volume does not disappear from counts because it is
outside JSON; archive wrappers, pretty-printing, source-audit packaging and
negative vectors are evidence bytes separately from retained object bytes.

## 8. Versioned implementation API reopening (future cards)

No production API below is implemented by this document. Retain all v0.1
signatures/dispatch and behavior. New APIs are explicit; never feed v0.2 into a
neutral-transfer fallback. Python≥3.10, stdlib core, no import-time I/O/process/
Genesis initialization. Defensive copies and frozen public values remain.

- codec: version-aware digest dispatch by validated record.version; strict
  decode/canonical keep v0.1 scalar rules. Explicit archive decoder has the
  bounded16MiB/2048 packaging allowance; canonical record validation is not
  globally relaxed for that wrapper.
- records: extend `validate_closure(records,head,*,world_id,version="0.1",
  profile=None,trusted_receipts=None,trust_verifier=None,context=None,blobs=None)`.
  v0.1 requires its injected fixed map; v0.2 requires exact trusted context,
  verifier and full raw resolver/mapping; never both trust modes or absent raw
  checks. Returned closure preserves current fields plus version/profile/
  artifact_class/context identity and validated raw descriptors. Expose bounded
  `validate_archive(archive,*,context,trust_verifier,blobs)->ValidatedClosure`
  as convenience for exact v0.2 wrapper; no I/O, normalization or trust inference.
- records: `verify_observation(raw:bytes,*,context,expected_request_id:str,
  tick:int,revision:int,watermark:int,trusted_head:HeadBinding)->VerifiedObservation`.
  Pure separate selective proof verifier; returns selected manifest/state/event,
  storage_state/artifact_class and explicit scope label, never ValidatedClosure.
- trust.py: imports codec only. `provision(key_dir:Path,*,context)->None` is
  explicit side effect; `open_trust(key_dir:Path,*,context,signing:bool=False)`
  reads existing key and returns either read-only ReceiptVerifier or coordinator
  LocalTrust signer. ReceiptVerifier protocol `assert_context(context)->None`,
  `__call__(receipt:Record)->None`; no exposed key attribute. LocalTrust additionally
  `sign_approval(unsigned:Record)->Record`, `sign_admission(unsigned:Record)->Record`;
  all semantic policy checks precede signing. Its existing admission/command
  integration must preserve authorize_read/verify_approval/admit ordering.
- ownership: v0.2 acquire takes explicit owner context with expected canonical
  root/public algorithm/anchor/build/options/class. Identity pins those values;
  lease exposes immutable context identity. No trust implementation import.
- Store: v0.2 construction injects verifier/context/raw provider; retains
  write→V→D, post-V fail-stop and D_recovery rules. Add pure defensive `.world_id`
  getter in both versions and `.trust_verifier` read-only accessor for v0.2.
  `.trusted_receipts` defensive accessor remains v0.1 only. No signer access.
  Raw writes/fsync precede snapshot descriptor/root visibility and raw reread/
  digest checks precede HEAD. I3's v0.1 work is unaffected until its extension card.
- commands/rules: explicit version-specific candidate provider; no untrusted
  dynamic import. Reuse is pure; physics provider returns candidates only.
- recovery: full raw/receipt/context validation then D_recovery; observe builds
  exact selective proof from pinned validated snapshot, never solver/I/O writes.

Imports: trust→codec; records→codec (verifier protocol only); ownership→codec;
store→codec/records/ownership; recovery→store/records; commands/admission→those.
Store never imports commands/recovery/trust implementation. No cycle, import
fallback, eager __init__ re-export or signer passed through generic Store.

## 9. Evidence and next gate

The read-only stdlib fixture checker imports no production module or Genesis.
67 literal goldens were authored before Check; no generator/update mode is
shipped. Static vectors contain retain(0,1)→physical(1,2)→retain(1,3), including
null and non-null D reuse. Four exact selected proofs and fixed negatives cover
strict encoding, wrong world/version/build/options/root, invalid MAC, forbidden
fixture runtime key, retain/physics changes, route/assets, missing/corrupt raw,
request/head/membership/watermark/selection scope and wire bounds.

Self-check success only means fixed static contract consistency. G-C0.2 requires
nonauthor golden recomputation and independent schema/API/security review before
dependent implementation cards reopen. Runtime public-option export, safe key
provisioning/reopen/ROOT_MISMATCH/MAC recovery, real Genesis checkpoint restore,
weak/strong difference, full physical validity, crash durability, UE proof
consumer, AssetRegistry closure and rendered read-only isolation remain unrun.
No static success passes G-P1/G-B0 or advances authoritative runtime state.
