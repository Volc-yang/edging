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
expected_build, expected_options and storage_state) and expected
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
Physical step count≤256 (32 advances×8); exceeding horizon fails LIMIT.
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

These are implementation targets, not implemented APIs in this PR. Python≥3.10,
stdlib core, no import-time I/O/process/Genesis initialization. Preserve every
v0.1 call and its return/error behavior. Additional optional kwargs below do not
change existing positional parameters. Selecting v0.2 is explicit; never infer
an upgrade from untrusted input or reinterpret a v0.1 root. Structures below
are frozen dataclasses; nested mappings/records are defensive read-only copies.
All fields listed without a default are required; no omitted implicit fields.

### 8.1 Shared types, trust bootstrap and public head binding

```
ProvisionSpec(world_id:str, authority_root:Path,
              domain_version:str="0.2",
              trust_algorithm:str="local-hmac-sha256.v0.2")
TrustAnchor(world_id:str, authority_root:str, domain_version:str,
            trust_algorithm:str, trust_anchor:str)
DeploymentContext(world_id:str, authority_root:str, trust_anchor:str,
                  expected_build:str, expected_options:str,
                  artifact_class:str="genesis-runtime",
                  trust_algorithm:str="local-hmac-sha256.v0.2",
                  domain_version:str="0.2",
                  archive_profile:str="composite-rigid-support.v0.2",
                  storage_profile:str="local-posix-blob-sync-v0.2")
HeadBinding(head:str, world_id:str, authority_root:str, trust_algorithm:str,
            trust_anchor:str, expected_build:str, expected_options:str,
            artifact_class:str, domain:str, version:str, profile:str,
            storage_state:str)
VerifiedObservation(manifest:str, state:Record, event:Record|None,
                    storage_state:str, artifact_class:str, scope:str, bytes:int)
BlobMeta(sha256:str, byte_count:int, media_type:str,
         artifact_class:str="genesis-runtime")
BlobWrite(sha256:str, payload:bytes, media_type:str,
          artifact_class:str="genesis-runtime")
```

HeadBinding.profile is archive_profile, not storage_profile. Its storage_state
is trusted and must equal the Observe label, preventing an unconfirmed→ready
flip. Domain/version/profile are literal allowlist values; root is canonical
registered spelling with no `..`, `//`, symlink aliases or copied-root fallback.
Fixture context.json is the seven nonconstant context fields; version/profile
constants are explicit on archive/HeadBinding. VerifiedObservation.scope is
exactly `selected-slice-membership-only-not-full-history-or-raw-validation`.
bytes is actual validated wire JSON byte count excluding one optional LF.
Its manifest field is selected record digest; state/event are full records.
This is not a ValidatedClosure and cannot authorize Store writes.

Trust module imports codec only; verifier protocol does not import trust.py:

```
provision(key_dir:Path, *, spec:ProvisionSpec) -> TrustAnchor
open_trust(key_dir:Path, *, context:DeploymentContext,
           signing:bool=False) -> ReceiptVerifier|LocalTrust
ReceiptVerifier.assert_context(context:DeploymentContext) -> None
ReceiptVerifier.__call__(receipt:Record) -> None
LocalTrust.sign_approval(unsigned:Record) -> Record
LocalTrust.sign_admission(unsigned:Record) -> Record
LocalTrust.authorize_read(principal:str,world_id:str) -> None
LocalTrust.verify_approval(approval:Record,proposal:Record,intent:Record) -> None
LocalTrust.admit(command:Record,candidate:Record,*,current_revision:int,
                admission_id:str) -> Record
```

ProvisionSpec has **no anchor/key/build/options requirement**. Owner explicitly
provisions a new key and receives the public TrustAnchor only after file/dir
fsync. Owner then freezes DeploymentContext with that returned anchor and its
chosen audited build/options/class, and registers root before initialize. This
breaks the anchor/key bootstrap cycle. Existing key means no overwrite/new key;
partial provisioning is retained and reported NOT_READY, never regenerated.
No status/read/recovery operation provisions or trusts a newly discovered anchor.
open_trust only reads an existing safe key, recomputes and compares frozen anchor
and canonical root, and rejects public test key bytes internally for runtime.
Missing/unreadable/unsafe key gives AUTHORIZATION (wrapped I/O cause; no key in
error); root mismatch ROOT_MISMATCH; unsupported profile PROFILE. Signing methods
accept full receipt except omitted auth_tag, validate exact semantic policy and
return signed copy; no mutation, automatic retries or public secret attributes.
Read-only verifier exposes only the two protocol methods. FixtureVerifier is
synthetic-only, rejects runtime context in assert_context; generic archive code
must never access `.key`. Admit preserves existing I4 authorization/expiry flow.

### 8.2 codec/records compatibility and full vs selective validation

```
decode(raw:bytes) -> JSON
canonical(value:JSON) -> bytes
digest(record:Record) -> str
decode_archive(raw:bytes, *, domain_version:str="0.1") -> JSON
validate_record(record:Record) -> None
validate_closure(records:Sequence[Record],head:str,*,world_id:str,
                 trusted_receipts:Mapping[str,JSON]|None=None,
                 domain_version:str="0.1", profile:str|None=None,
                 trust_verifier:ReceiptVerifier|None=None,
                 context:DeploymentContext|None=None,
                 blobs:Mapping[str,bytes]|None=None) -> ValidatedClosure
validate_archive(archive:JSON,*,world_id:str,
                 trusted_receipts:Mapping[str,JSON]|None=None,
                 domain_version:str="0.1", profile:str|None=None,
                 trust_verifier:ReceiptVerifier|None=None,
                 context:DeploymentContext|None=None,
                 blobs:Mapping[str,bytes]|None=None) -> ValidatedClosure
select(closure:ValidatedClosure,*,tick:int,revision:int,watermark:int) -> Record
verify_observation(raw:bytes,*,context:DeploymentContext,
                   expected_request_id:str,tick:int,revision:int,watermark:int,
                   trusted_head:HeadBinding) -> VerifiedObservation
```

Existing validate_archive(world_id=…,trusted_receipts=…) is unchanged for v0.1.
profile=None selects **only** the static archive profile for explicitly selected
domain_version (0.1 neutral-transfer-v0.1, 0.2 composite-rigid-support.v0.2).
Version must match all records/wrapper. v0.1 requires trusted_receipts mapping;
context/verifier/blobs must be None (empty blobs also allowed). v0.2 requires
world_id=context.world_id, context/verifier/full raw bytes mapping and no fixed
receipt map. Missing or mixed trust modes AUTHORIZATION; mismatch DOMAIN/PROFILE/
WORLD/ROOT_MISMATCH as applicable. Raw missing/hash/length errors CORRUPT, limits
BLOB_LIMIT/LIMIT/COUNTS; never ignore a missing raw resolver or infer trust from
archive. decode_archive has version-specific packaging limits; decode/canonical
record tree limits are never relaxed globally. digest dispatches known validated
record versions. No validator performs I/O, normalization, initialization or
solver work. ReceiptVerifier.assert_context is called before archive validation.

ValidatedClosure retains `head,world_id,records,retained,commands` and adds pure
`domain_version:str,profile:str,artifact_class:str|None,context:DeploymentContext|None,
binary_refs:Mapping[str,BlobMeta]`. v0.1 context/artifact_class=None, binary_refs={};
other fields stay old semantics. Only manifest-linked indexes contribute commands.
Construction remains validator-internal; Store revalidates rather than accepting
an arbitrary dataclass as proof. For selective parser, trusted HeadBinding is
injected separately from response and every field is checked against context;
no secret verifier required. Typed edges/record caps precede scope traversal;
traversal memoizes (digest,mode) and rejects active cycles. Exact duplicate
auxiliary records or overlap with explicit/membership fields fails PROOF.

### 8.3 ownership and Store

```
acquire(root:Path,world_id:str,*,initialize:bool=False,
        domain_version:str="0.1",profile:str="local-posix-sync-v0.1",
        context:DeploymentContext|None=None) -> Lease
Store(lease:Lease,*,trusted_receipts:Mapping[str,JSON]|None=None,
      trust_verifier:ReceiptVerifier|None=None,
      context:DeploymentContext|None=None,fault:FaultHook|None=None)
Store.initialize(genesis:Sequence[Record],head:str,*,
                 blobs:Sequence[BlobWrite]=()) -> CommitReceipt
Store.pin() -> PinnedRoot
Store.confirm_recovery(pinned:PinnedRoot,closure:ValidatedClosure) -> Snapshot
Store.snapshot() -> Snapshot
Store.lookup_result(principal:str,command_id:str,fingerprint:str) -> Record|None
Store.read_blob(sha256:str) -> bytes
Store.commit(bundle:CommitBundle) -> CommitReceipt
Store.close() -> None
CommitBundle(expected_head:str,records:tuple[Record,...],head:str,
             principal:str,command_id:str,fingerprint:str,
             blobs:tuple[BlobWrite,...]=())
PinnedRoot(head:str,head_bytes:bytes,objects:Mapping[str,bytes],
           blobs:Mapping[str,bytes])
```

Static allowed ownership pairs are (0.1,local-posix-sync-v0.1) and
(0.2,local-posix-blob-sync-v0.2). v0.1 context=None; v0.2 explicit context required,
root/world/version/storage profile must match. Unknown pair PROFILE; wrong
registered directory/identity ROOT_MISMATCH; absent old registration with
initialize=False UNINITIALIZED and zero creates; busy LOCKED. Lease keeps all
v0.1 fields/methods and adds frozen `.domain_version:str` and
`.context:DeploymentContext|None`; `.profile` is storage profile. Public context
pins expected_root/algorithm/anchor/build/options/class, never key or signer.
No ownership→trust implementation import. Fork/closed/lease checks remain v0.1.

Store constructor remains side-effect-free. v0.1 requires fixed map and no
verifier/context; v0.2 requires verifier/context matching Lease and no fixed map.
Store `.world_id:str` is pure in both versions; `.trusted_receipts` returns a
defensive map for v0.1 only, raises PROFILE on v0.2; `.trust_verifier` returns the
read-only injected verifier for v0.2 only, raises PROFILE on v0.1. Existing
`.state` and close/lease lifetime remain. Snapshot fields stay
`storage_state:str,closure:ValidatedClosure`; CommitReceipt stays
`manifest:str,result:Record|None,commit_status:str="confirmed"`.

v0.1 initialize/commit requires empty blobs and pin returns empty blobs mapping.
v0.2 initializes exact initial world/physics closure and descriptor payloads;
commit includes every new required raw BlobWrite once, may reuse already pinned
valid raw. Hash/size/media/class must match BlobMeta; unused/conflicting supplied
blob REFERENCE/CORRUPT, no overwrite repair. `.read_blob` only returns a defensive
copy of an already pinned validated reference; unreferenced REFERENCE, bad/missing
raw CORRUPT, not ready NOT_READY. Pin gathers complete retained raw bytes bounded
by descriptors; no Genesis loading. Raw no-follow/nlink1/exclusive-write file
fsync and blobs-directory fsync precede V. Synthetic payloads use `.static`, real
runtime uses `.gstraj`; never infer artifact class from suffix. D_recovery syncs
all retained JSON/raw files, object/blob directories, HEAD and root. Extra
`BLOB_FILE_SYNCED,BLOBS_DIR_SYNCED,RECOVERY_BLOBS_SYNCED` hooks carry raw hash;
v0.1 W1…W8 handling/order unchanged. All StoreError(commit_status,phase), unknown
post-V fail-stop, pinned-read-only limits and no-retry rules remain v0.1. No
provider may write via Store or take a second lease.

### 8.4 explicit provider/command dispatch and recovery

```
PhysicsIds(candidate:str,sample:str,snapshot:str,checkpoint_descriptor:str)
PhysicsInitialIds(sample:str,snapshot:str,checkpoint_descriptor:str)
PhysicsDraft(records:tuple[Record,...],candidate_digest:str,
             snapshot_digest:str,blob:BlobWrite)
PhysicsInitialDraft(records:tuple[Record,...],snapshot_digest:str,blob:BlobWrite)
GenesisProvider(config:Record,binding:Record,*,scratch:Path,
                context:DeploymentContext,build:Record,options:Record)
PhysicsProvider.initialize(*,ids:PhysicsInitialIds) -> PhysicsInitialDraft
PhysicsProvider.restore(snapshot:Record,*,records:Mapping[str,Record],
                         read_blob:Callable[[str],bytes]) -> Mapping[str,JSON]
PhysicsProvider.propose(prior_state:Record,command:Record,intent:Record,*,
                        records:Mapping[str,Record],
                        read_blob:Callable[[str],bytes],ids:PhysicsIds) -> PhysicsDraft
PhysicsProvider.close() -> None
execute(store:Store,command_records:Sequence[Record],*,command_digest:str,
        principal:str,verifier:TrustVerifier,candidate_id:str,admission_id:str,
        state_id:str,event_id:str,result_id:str,index_id:str,manifest_id:str,
        provider:PhysicsProvider|None=None,physics_ids:PhysicsIds|None=None
        ) -> CommitReceipt
recover(store:Store) -> RecoveryReport
status(snapshot:Snapshot) -> dict
observe(snapshot:Snapshot,*,tick:int,revision:int,watermark:int) -> dict
head_binding(snapshot:Snapshot) -> HeadBinding
```

I7 PhysicsIds/InitialIds/Draft fields are preserved; BlobWrite gains only the
artifact_class default. GenesisProvider constructor stores validated copies,
no solver or filesystem work. Each explicit initialize/restore/propose first
measures runtime build/options against injected templates and context digests,
then may initialize/load/solve in controlled scratch. Restore returns exact
physics_sample.body keys, not records/HEAD. Propose always starts from prior
committed checkpoint, not uncommitted scene memory; returns candidate-only draft
with raw bytes, no authority writer/signer. PHYSICS_INVALID for input/sample/F,
PHYSICS_FAILED for solve/load failure, BUILD for identity/default mismatch,
BLOB_LIMIT for excessive payload, before any commit; preserve original cause.
No dynamic imports selected by request strings or untrusted plugin registration.

execute keeps v0.1 arguments/behavior and requires provider/physics_ids None for
v0.1. For v0.2 physics_step both are required and physics_ids.candidate must
match candidate_id; coordinator validates returned draft/config/binding/build/F,
obtains signed A then builds state/event/result/index/manifest and uniquely
Store.commit. For retain_snapshot provider is never called, physics_ids must
be None; candidate_id identifies new reuse candidate referring exact prior
snapshot and CommitBundle.blobs=(). Authorization then committed retry lookup
precedes any provider/action validation; identical retry does no solve/charge/
new A. New action requires ready snapshot, exact context/head/expiry/principal/
budget/cursor; mismatches return established errors, no automatic retries. Before
V ContractError is noncommit; StoreError propagates exact phase/status unchanged.
LocalTrust implements existing TrustVerifier methods; explicit production signer
is coordinator-owned and not exposed through Store or provider.

recover reuses Lease; validates every retained root, context, all MACs and raw
bytes then calls confirm_recovery/D_recovery. RecoveryReport fields remain
`storage_state:str,snapshot:Snapshot|None,confirmed:bool,error_code:str|None`.
Corruption raises StoreError(CORRUPT), no snapshot; valid integrity but failed
sync gives unconfirmed_readonly/confirmed=False, never ready. It never invokes
provider, key provisioning or solver replay. status/observe are pure snapshot
operations. v0.1 payloads are unchanged. v0.2 status exact keys are
`world_id,head,tick,revision,watermark,state,event,storage_state,artifact_class,
head_binding`; head/state/event are digests (event null only revision0), and
head_binding is the serialized public HeadBinding from this recovered snapshot.
v0.2 observe returns exactly §6 payload, not an archive; trusted worker transport
wraps it in domain/version/world/operation result and request-ID envelope.
head_binding rejects v0.1 PROFILE; for v0.2 requires ready or validated
unconfirmed_readonly snapshot and preserves its label. A client establishes
trust in this public binding through the owned worker/deployment boundary,
never through an unauthenticated Observe response containing its own binding.

Imports: trust→codec; records→codec (verifier protocol only); ownership→codec;
store→codec/records/ownership; recovery→store/records; commands/admission→those.
No import of trust implementation by Store/ownership/records, no secret access,
no circular workaround or eager __init__ re-exports. The protocols/shared frozen
types are defined at their owning module (codec for trust/context types, records
for closure/blob metadata, Store for write/bundle/pin, physics.py for
physics protocols/drafts (imports codec/records/store), and genesis_adapter.py
for the explicit runtime provider); annotations never require a reverse import.

### 8.5 Local owner channel, preparation and exact v0.2 wire

The worker is spawned by the trusted local launcher with inherited private
stdin/stdout pipes, the pre-registered DeploymentContext/key_dir and frozen
`OwnerSession(principal:str,can_initialize:bool,allowed_actions:tuple[str,...])`.
Session is injected as an in-process value by that launcher, never accepted
from JSON, a request-supplied key path or a public network socket. The launcher
and worker remain within the honest local-owner trust model. No external user
account service or remote endpoint is introduced. The launcher pins worker PID,
pipe endpoints and context; UI cannot acquire a signer, alter session permissions
or obtain key bytes. allowed_actions is an explicit subset of the two actions;
JSON principal must equal session principal and grants no authorization itself.
Read access still goes through LocalTrust.authorize_read and registered world.

All v0.2 request envelopes have exactly
`protocol_version,request_id,operation,payload` with integer1 and request ID:ID.
Operation is one of initialize/status/observe/prepare/advance. Payload keys:

| operation | exact payload keys |
| --- | --- |
| initialize | domain,version,world_id,test_profile |
| status | domain,version,world_id |
| observe | domain,version,world_id,tick,revision,watermark |
| prepare | domain,version,world_id,principal,proposal,intent,approval_id,command_record_id |
| advance | domain,version,world_id,principal,command_records,command_digest |

Domain/version/world/profile must match owner registration. initialize's
profile is composite-rigid-support.v0.2; caller supplies no path, key, candidate,
blob, world seed override or trusted map. It requires can_initialize and an
explicit initializing lease. Worker composes approved technical world records
and provider.initialize draft, then calls Store.initialize. Existing HEAD
rejects reinitialize; ordinary startup opens/recover existing authority without
initializing anything. If ready/unconfirmed snapshot does not exist, status/
observe returns UNINITIALIZED/NOT_READY/LOCKED/CORRUPT as appropriate, never a
self-authenticated null-head status. No read provisions keys/root/lock files.

prepare is the missing signing step for UE: proposal and intent are complete
unsigned typed records; refs config/binding must match this authority; principal
must equal OwnerSession/proposal/intent. approval_id and command_record_id are
stable IDs supplied by caller, allocated before sending. Intent supplies stable
command_id plus expected_revision/cursor/action/case/cost. Approval expiry is
**exactly intent.expected_revision** in this finite profile, not a caller chosen
infinite permission. The coordinator checks session action grant, ready snapshot,
current expected revision/cursor, approval principals, action/refs/budget, and
allocated IDs before signing approval. It assembles exact four-record closure
(proposal,intent,signed approval,command), computes H(command), and returns it.
No candidate, physics, A, blob, index, root, tick, cost or cursor is produced.
Preparing is not an admission or a durable idempotency success.

New pure/core entry point (read-only snapshot use; signer is owner injected):

```
PreparedCommand(command_records:tuple[Record,...],command_digest:str,
                committed_result:Record|None)
prepare_command(store:Store,*,session:OwnerSession,proposal:Record,intent:Record,
                approval_id:str,command_record_id:str,
                signer:ApprovalSigner) -> PreparedCommand
ApprovalSigner.sign_approval(unsigned:Record) -> Record
```

ApprovalSigner is a codec-owned protocol, not an import of LocalTrust; the
coordinator passes its signer explicitly. A repeated identical prepare at the
same HEAD/IDs deterministically returns byte-identical signed closure: no random
receipt ID/timestamp. No pending-reservation database is added. For a lost
prepare/advance response after commit, authenticate and consult the **committed**
(world,session.principal,command_id) index first. Retrieve its stored command/
proposal/intent/approval, compare exact proposal/intent/approval_id/command_record_id
and fixed expiry to the prepare request. If identical, return that stored closure
and original committed_result without signing an expired replacement. Any mismatch
COMMAND_CONFLICT. Uncommitted stale prepare fails HEAD/AUTHORIZATION; no durable
reservation or automatic semantic rewrite. Changing expected revision after a
conflict requires a new owner decision/command ID, never hidden replay.

UE stores the returned command_records/digest and sends advance, which has the
same four-record shape as v0.1 but v0.2 signed approval. The worker checks exact
stored/received MAC and session, then follows execute retry→new-action ordering.
A lost advance response is retried with identical closure and fingerprint; no
new prepare, signature, solve or charge is required. A rejected new action does
not become success merely because prepare signed it. Private key stays entirely
in worker coordinator; providers and UE receive no signing capability.

Success/failure envelopes are exactly v0.1's shapes: success
`{protocol_version,request_id,ok:true,result}` with result exact
`{domain,version,world_id,operation,payload}`; failure
`{protocol_version,request_id,ok:false,error}` with error exact
`{code,message,commit_status}`. No stdout logging outside JSONL; errors use the
stable codes, bounded message and not_attempted/unknown/confirmed classifications.
Exact v0.2 success payloads:

- initialize/advance: `{manifest,result,commit_status,head_binding}`; manifest is
  committed manifest digest, result full result record (null only initialize),
  commit_status confirmed only after D. An idempotent advance returns original
  manifest/result while head_binding is the **current** recovered snapshot.
- status: §8.4's exact status keys; tick/revision refer to binding.head's current
  manifest. This establishes bootstrap binding only through the already trusted
  launcher/worker channel, with public context checked separately by the client.
- prepare: `{command_records,command_digest,committed_result,head_binding}`;
  committed_result null unless this was a committed exact retry. No commit_status
  success claim for a new prepared intent; binding still labels current storage.
- observe: exactly §6 selected proof payload; trusted_head for verifying it comes
  from a separately pinned status/initialize/advance binding under that same
  owner channel. It is not supplied as a self-assertion by this Observe payload.

Before publishing any new trusted binding, worker rechecks its pinned snapshot
and lease/context. Client rejects a mismatching request ID, response operation,
world/context, root or trust identity; a pipe/PID reconnection requires a fresh
status binding from recovered worker, not a stale cached hash. The returned
storage_state cannot override external HeadBinding. Viewer observation remains
read only; advancing occurs only on explicit owner-approved command. v0.1 wire
operations and payloads remain unchanged and have no prepare operation.

## 9. Evidence and next gate

The read-only stdlib fixture checker imports no production module or Genesis.
67 literal goldens were authored before Check; no generator/update mode is
shipped. Static vectors contain retain(0,1)→physical(1,2)→retain(1,3), including
null and non-null D reuse. Four exact selected roots plus an unconfirmed-readonly proof and fixed negatives cover
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
