# Universe Authority v0.1 — I0 frozen experimental contract

2026-11-01. Owner I0; implementation base `b3e1fd4fac69ce7d78bf5c14a4d8ed554622048c`.
This is a **new archive/domain**, not a migration or relaxation of S4, chaos-demo or
stg-demo. G-C and G-S0 require independent acceptance; this document alone does
not pass G-S1, G-P1 or any UE/Metal gate. UE released plugins/adapters remain the
first integration choice. Seed→Tree means initial state→causal development.
No biology, spirit lifecycle, geography law or autonomous clock is established.

### Extension boundary (not implemented here)

v0.1 is only the **neutral kernel fixture profile**. Its fake candidate is not a
real Genesis checkpoint or an extensible production world state. I7 must specify
real checkpoint/blob/config/binding types; I10's six-region initial manifest also
needs explicit typed geography/existence/route/water references. These require
versioned schemas/profile identifiers and reopening affected G-C/APIs before
I8/I10/I9 integration; never add unknown keys or rename fake evidence in place.
I1 strictly dispatches known version schemas and rejects unknown/mixed versions;
I2 pins version/profile in root identity; I3/I5 validate a version-specific closure
then store/restore opaque immutable canonical objects without solving physics;
I4 uses an explicit version-specific candidate/trust provider, with no import-time
Genesis initialization or dynamic untrusted plugin loading. This preserves the
ownership/commit boundary without pretending current neutral fields support
production checkpoints. No automatic legacy/new-profile migration is allowed.

## 1. Exact bytes and bounded values

Domain is `edgeworld.universe.authority`, schema version is the **string** `0.1`.
Transport `protocol_version` remains the **integer** `1`.
One JSONL line is strict UTF-8, at most **1,048,576 bytes excluding one final LF**;
CRLF, BOM, invalid UTF-8, trailing tokens, duplicate decoded object keys, lone
surrogates, raw JSON floating numbers and NaN/Infinity tokens are rejected.
The fixture decoder also accepts whitespace because fixture archives are pretty
printed; the wire line parser must reject embedded raw LF/CR and accept one LF
terminator only. JSON escaped `\n` is a string character, not a line separator.
Check byte length before decoding; depth must be bounded before recursive work
or fail closed on parser recursion errors. Do not trust UE's already decoded
FJsonObject to detect duplicate keys: inspect the **original raw JsonLine**.
Transport-prefilled RequestId/bSuccess is not domain validation.

All object keys and strings are Unicode scalar sequences without normalization.
Strings ≤4096 UTF-8 bytes; objects ≤64 members; arrays ≤256 entries; maximum
container/value depth 32, with top-level value depth 0. Identifiers match
`[a-z][a-z0-9._-]{0,63}` (ASCII, case sensitive). JSON integers have absolute value
≤9007199254740991; protocol integer fields are nonnegative exact integers,
**never booleans**. A number spelled `1.0`/`1e0` is rejected, even if integral.
Limits are experimental engineering caps, not approved product scale targets.
Archives ≤256 records and ≤1 MiB decoded input bytes; large future archives need
an explicitly versioned streaming profile, not silent relaxation.

Binary64 is represented only by `{"$f64":"hhhhhhhhhhhhhhhh"}`: exactly 16 lowercase
hex digits of IEEE-754 binary64 **big-endian bits**. Exponent 0x7ff is forbidden
(infinities and every NaN payload); subnormals and signed zero are preserved.
No bare JSON float is permitted anywhere. Arithmetic is round-to-nearest,
ties-to-even binary64; finite output required. No implicit unit conversion.
Typed values here are neutral scalar fixtures, not physical measurements.

Canonical bytes C(x): recursively sort Unicode scalar keys by scalar ordinal;
JSON without whitespace, `,`/`:` separators, ASCII-only escaped strings, short
escapes for `\b\t\n\f\r`, quote and backslash; other controls/non-ASCII use lowercase
`\uXXXX`, supplementary scalars use surrogate-pair escapes. Slash is unescaped.
Integers use minimal decimal (minus only for negative); booleans/null lowercase.
This is Python stdlib `json.dumps(ensure_ascii=True,sort_keys=True,
separators=(',',':'),allow_nan=False)` over validated values. No NFC transform.

For every record R, digest is lowercase 64-hex:
`SHA256(b"edgeworld.universe.authority\x00v0.1\x00" + C(R))`.
There is no digest field inside R and no kind-specific hash alternative. The
prefix bytes (including NULs) and whole record, including kind/world/id, are
hashed. A reference is that digest, never a filename, URI, mutable alias or ID.

## 2. Records and acyclic chain

Every record has **exactly** `domain,version,world_id,kind,id,body,refs`.
`world_id` is root scoped; `(world_id,kind,id)` is unique and immutable. CommandId
is scoped by (world, principal), not by session; principal and receipt IDs are scoped by the
registered authority/trust profile. EventId is allocated before hashing and
must never be reused. Repeated digest bytes may be stored once; differing bytes
at an existing digest path are corruption. Cross-world references are forbidden.
Unknown fields/enums/kinds are rejected; `body` keys below are exact. `refs`
keys below are required except the stated genesis omissions. Every target must
be an already validated earlier record of the indicated kind. This topological
order rejects cycles and forward/forged references before trust evaluation.

| kind | exact body fields | refs name → kind |
| --- | --- | --- |
| proposal | principal:ID, output:string≤1024 scalars | none |
| intent (semantic B) | command_id:ID, principal:ID, expected_revision:uint, tick_delta:0/1, transfer:f64, budget:uint, random_cursor:uint | none |
| approval | principal:ID, receipt_id:ID, expires_revision:uint | proposal→proposal, intent→intent |
| command | empty object | proposal→proposal, intent→intent, approval→approval |
| candidate | adapter_kind:`fake`, test_profile:`neutral-transfer-v0.1`, value:f64, tick:uint, revision:uint | command→command, prior_state→state |
| admission (A) | receipt_id:ID, principal:ID, evaluated_revision:uint | command→command, candidate→candidate |
| state | tick:uint, revision:uint, value:f64, budget:uint, random_cursor:uint | none |
| event | event_id:ID | state→state, admission→admission, prior_event→event (omitted only first event) |
| result | command_id:ID, tick:uint, revision:uint, watermark:uint | command→command, state→state, event→event, checkpoint→candidate |
| index | command_id:ID, fingerprint:digest | result→result |
| manifest | tick:uint, revision:uint, watermark:uint | state→state, event→event, index→index, prior_manifest→manifest |

Genesis is the sole exception: state revision=0/tick=0/random_cursor=0; manifest
revision=0/tick=0/watermark=0 has **only** state ref. Initialize explicitly creates
this manifest; it has no command/result/event. Each later manifest increments
revision exactly once. Its prior_manifest must exist, event.prior_event must
match prior manifest event (absent for revision1), candidate.prior_state must
match prior manifest state. All state/event/result/manifest views agree exactly.
No current event/index/manifest hash goes into state; result does not refer to
its future manifest. Index fingerprint equals command digest, and command ID
matches its intent/result. Candidate and A cannot be folded back into command.

An archive fixture has exactly `domain,version,test_profile,records,head`. `records` is the topological array; `head` pins one manifest.
Retained history is its prior_manifest chain, not every arbitrary state blob.
Orphans may exist but are fully validated and never made visible by observation.
Production storage stores records separately; it must validate all retained
root closures and reject any referenced corruption, not just current state.

## 3. Neutral transfer and authorization

This profile is **test only**. Initial budget=8/value=+0 in golden fixtures.
For a new action, intent.expected_revision=prior.revision; candidate.revision=
prior.revision+1; candidate.tick=prior.tick+tick_delta. `tick_delta=0` proves
revision is independent of logical time. candidate.value is the finite binary64
sum of prior.value + intent.transfer; state copies candidate value/tick/revision.
State budget=prior.budget−intent.budget, nonnegative; cursor=prior.cursor+1 and
intent.random_cursor=prior.cursor. Cursor is only a deterministic fixture
counter: no global RNG, hidden seeds or physical solve. Actual physics profile
will be frozen by I7; it must not call fake evidence Genesis.

Approval binds proposal digest + H(B) (intent digest), the same principal and
expiry. Final fingerprint is the command digest, binding immutable approval,
proposal and intent. A binds final command + candidate after all checks; it does
not enter the fingerprint. Candidate precedes A. External services cannot write
world state and their billing/reservations remain a separate recovery domain.

In fixtures the separate `trusted_receipts.json` is an explicit injected trust anchor map; it is
**not a signature scheme** and archive-supplied receipt assertions are never
trusted in production. Approval map value is exactly
`{kind:"approval",principal,intent,proposal,expires_revision}`; admission value is
exactly `{kind:"admission",principal,command,candidate,evaluated_revision}`.
Validator requires exact equality and matching principals; approval refs equal
command refs; A candidate references the same command; evaluated_revision is
intent.expected_revision and ≤approval.expires_revision. Production I4 receives
a trusted callable from its owning process, never from JSON input. No cryptographic
external authority implementation is claimed.

Read authentication/authorization applies even to retries. Then look up committed
CommandId **before** new-action expiry, current-head and budget checks: identical
fingerprint returns its original immutable authorized result, no new solve, A,
revision, charge or random cursor. Different fingerprint returns COMMAND_CONFLICT.
Uncommitted intents are not durable idempotency successes. For a new action,
check current principal/revocation/expiry/head/rule/budget/input, solve once,
then obtain final A. A is an immutable local decision binding exact candidate
and revision; subsequent revocation/expiry does not retroactively void this
admitted transaction. This is not instantaneous distributed revocation. If
external reservation validity is unknown **before A**, do not admit; if uncertain
after V, preserve unknown-commit and recover, never manufacture a second intent.

## 4. Transport and pure observation

The new worker's future CLI keeps `--state-dir --world-id --dt --physical-steps
--seed`; I11 owns any explicit expansion. Existing transport envelope v1 remains.
Request exact keys: `protocol_version,request_id,operation,payload`. request_id
is an ID; operations: `initialize,status,observe,advance`. Payload exact keys:
initialize=`{domain,version,world_id,test_profile}`; status=`{domain,version,
world_id}`; observe adds `{tick,revision,watermark}`; advance adds `{principal,command_records,command_digest}`. command_records is exactly
the four full proposal/intent/approval/command records in topological order;
command_digest must equal the last record digest. No arbitrary filesystem paths
or request-supplied trust map is accepted. The authenticated local authority
checks principal; a JSON principal string alone grants no permission. World/domain/version must match registered root.
No operation named status/observe may create root, lockfile, Genesis, manifest,
checkpoint, receipts, action budget, RNG state or advance tick/revision.

Success exact envelope keys `protocol_version,request_id,ok,result` (`ok=true`);
failure `protocol_version,request_id,ok,error` (`ok=false`), error exact keys
`code,message,commit_status` with commit_status `not_attempted|unknown|confirmed`.
`message` bounded string, not stack trace; result has exact keys `domain,version,world_id,operation,payload`. Initialize/advance payload is
`{manifest,result,commit_status}` (result null only genesis); status payload is
`{head,tick,revision,watermark,storage_state}`; observe payload is
`{manifest,state,event,watermark,storage_state}` (genesis event null). All refs are
digests; observing returns full matching state/event records alongside manifest
record under those keys, so parser can rehash and check the binding. Status.head
is a digest; initialize/advance.manifest is a digest; advance.result is a record.
Never accept transport-prefilled RequestId, bSuccess or decoded keys as proof:
validate raw duplicate keys, exact envelope, expected outstanding request ID,
operation/world/profile, full result shape and reference hashes independently.

Watermark is **revision**, not tick or an ambiguous latest timestamp. Observe
requires exact (tick,revision,watermark) with watermark==revision and a retained
manifest matching all three. Return NOT_FOUND, never nearest/current fallback.
No write from rendering/camera/LOD/history or historical re-solve. Advance uses
expected revision, not observed tick. Timeout/killed child means unknown commit
if V might have occurred; transport failure alone cannot prove noncommit.

Storage states: `uninitialized,locked,recovering,ready,unconfirmed_readonly,
corrupt,closed`. Only ready accepts new writes. Pure reads of explicitly
unconfirmed validated snapshots must carry that label; corrupt refuses reads.
Errors include JSON,DUPLICATE_KEY,UNICODE,LIMIT,NUMBER,INTEGER,F64,SCHEMA,DOMAIN,
ID,WORLD,REFERENCE,PROFILE,AUTHORIZATION,COMMAND_CONFLICT,HEAD,TRANSITION,WATERMARK,
NOT_FOUND and runtime LOCKED,ROOT_MISMATCH,UNINITIALIZED,CLOSED,NOT_READY,
CORRUPT,IO_BEFORE_VISIBILITY,COMMIT_UNKNOWN,SYNC_UNSUPPORTED. These names are stable;
public exceptions carry code and optional bounded detail, not mutable snapshots.

## 5. Local storage profile `local-posix-sync-v0.1`

New empty canonical registered directory only; no automatic legacy discovery,
restore, migration, rollback, garbage collection, historical solve or deletion.
Root registration pins canonical absolute path, world/domain/version/profile
and directory device/inode. Symlink aliases are canonicalized and must match
registration; caller cannot choose a second spelling as a new authority.
Directory replacement/mismatched registration is ROOT_MISMATCH. Registration
and stable `.authority.lock` are explicitly created only by initialize while
holding the lock; initialization race must use atomic create and then lock the
same stable inode. Never unlink/replace the lockfile or steal by PID/timeout.
Use OS exclusive advisory fd lock, retained from initialize/recovery through
solve/A/commit/shutdown; subprocess authority requires its own lock attempt.
No fork-inherited lease may authorize a second writer. Check lease PID and root
identity at each mutation. Observers use worker's existing pinned snapshot, or
acquire existing ownership to recover read-only without creating any file.

`identity.json` is C(object) without newline, exact keys `domain,version,
world_id,profile,root_canonical,root_device,root_inode`. Domain/version/world/profile
are the pinned values above. root_canonical is absolute resolved path string
(no trailing slash except filesystem root, no symlink components); root_device
and root_inode are **decimal strings** matching `0|[1-9][0-9]{0,19}`, equal to
`str(os.stat(root).st_dev)`/`str(os.stat(root).st_ino)`. Strings avoid unsafe JSON
integer coercion of 64-bit inode values. These are durable registration fields,
checked against current stat on every acquire/mutation. Lock fd dev/inode/PID
are additional runtime lease pins, not mutable registration fields. Identity is
created exclusively after acquiring the stable lock, fsynced, then root directory
synced before HEAD initialization; partial/mismatched identity never overwrites.
An absent identity with existing HEAD is corrupt, not permission to initialize.

Layout: `identity.json`, `.authority.lock`, `objects/<digest>.json` (C(record)),
`HEAD.json` (canonical `{domain,version,world_id,manifest:<digest>,
profile:"local-posix-sync-v0.1"}`). Prepare HEAD temp files in the same root/filesystem;
objects immutable, no automatic orphan removal. Registration/profile/fsync
capability is checked explicitly; unsupported directory synchronization stops
writes rather than silently downgrading. No hardlinks/symlinks in internal paths; open regular internal files with
no-follow semantics and require link count 1; refuse escaping paths. This profile assumes a local POSIX filesystem and honest
OS synchronization calls, not malicious concurrent root mutation.

A is final immutable admission, not a durable visibility point. Commit order:

1. Hold valid lease, ready, exact expected head; fully validate bundle/closure.
2. Persist every missing object directly at its final digest name using
   `O_CREAT|O_EXCL|O_NOFOLLOW` (no link/rename publication), complete write, flush
   userspace and `fsync(fd)`, then `fsync(objects directory)`. Existing names
   are opened read-only and their full exact bytes verified; never overwrite.
   Exclusive creation is atomic for the name, not the file contents: incomplete
   objects after interruption remain unreferenced by HEAD. They are never
   interpreted as committed or silently repaired/deleted; a later same-digest
   collision with partial bytes is CORRUPT and stops that write. Only HEAD makes
   complete synchronized objects visible as authority. Failure before HEAD attempt reports IO_BEFORE_VISIBILITY;
   orphan objects do not commit state. Event/result/index/manifest are objects.
3. Write complete new HEAD temp, flush and `fsync(temp fd)`; named public hooks
   before/after each phase below. Verify prior pinned HEAD under same lease.
4. **V:** mark outcome unknown **before** attempting atomic same-filesystem
   `os.replace(temp, HEAD.json)`. Once attempted, any exception loses permission
   to keep writing or assert the old head from memory, including exception from
   replace itself. Re-read only by recovery protocol, not an optimistic retry.
5. `fsync(root directory)` establishes **D** under this profile; only then publish
   confirmed result to caller and ready snapshot. A durable result/index in the
   same manifest restores retry identity after a lost response.

D means successful specified syscall confirmation, **not** a hardware power-loss
or APFS persistence warranty. No claim that kill/fault injection equals blackout.
Raw prior/new HEAD bytes, syscall/fault phase and response evidence remain useful.

Recovery acquires same lease, pins HEAD once, validates identity and its exact
bytes, **all retained manifest closures**, object names/bytes/digests/kinds/world,
command/result uniqueness, history/watermarks and all referenced checkpoints.
No older backup fallback on corruption. Integrity alone cannot confirm D.
Then explicitly `fsync` all reachable immutable object files, objects directory,
HEAD file, root directory in that order: **D_recovery**. Only success transitions
to ready and confirms lookup. Sync failure remains unconfirmed_readonly (if fully
validated) and forbids writes; unknown HEAD/references/corruption rejects reads.
No recovering/ready state is persisted as a substitute for these operations.

Public fault hooks, synchronous callable `(phase:str, context:Mapping)->None`:
`W0_LOCKED,W1_VALIDATED,W2_OBJECT_FILE_SYNCED,W3_OBJECTS_DIR_SYNCED,
W4_HEAD_FILE_SYNCED,W5_BEFORE_REPLACE,W6_AFTER_REPLACE,W7_ROOT_SYNCED,
W8_BEFORE_RESPONSE,W9_RECOVERY_SYNCED` plus `RECOVERY_VALIDATED` before sync.
Context exact world_id/command_id (null genesis/recovery), prior/new manifest,
object digest if applicable, visibility_attempted bool. W2 repeats per object.
Hooks run under lease; exceptions obey the same pre-/post-V uncertainty rule.
A W5 exception is conservatively unknown because the boundary has been entered.
W7/W8 failures also fail-stop until recovery; do not translate them to noncommit.
Hooks are injected by owner, never via untrusted protocol; I6 can raise/exit in a
separate process using these public hooks. W9 failure leaves unconfirmed.

## 6. Frozen Python module APIs (I1–I5)

Python ≥3.10, stdlib only for I1–I6. No module import may open files, acquire locks,
start processes/threads, initialize a solver/model, or change cwd/environment.
`engine/universe_authority/__init__.py` contains only docstring/optional literal
`__all__`; callers import owning modules directly. No eager re-exports.
Imports: records → codec; ownership → codec; store → codec/records/ownership;
admission/rules → codec/records; commands → those + store; recovery → store/records.
Codec imports no sibling. Store never imports
commands/recovery; ownership never imports store. No circular-import workaround.

Shared JSON type means validated primitive trees (dict/list/str/int/bool/null);
Record = dict[str,JSON]. Inputs/outputs are defensive copies at ownership
boundaries; callers cannot mutate store snapshots through a returned mapping.
Dataclasses below are frozen; nested record mappings must also be defensive
copies, not mutable aliases. No public return of open file descriptors except
Lease's opaque internal ownership. Exceptions are not silently retried.

**I1 `codec.py`:**

- `ContractError(ValueError)` with `.code:str`, `.detail:str` (≤4096 UTF-8 bytes).
- `decode(raw:bytes) -> JSON`: strict domain limits/types above; no filesystem.
- `canonical(value:JSON) -> bytes`: validate tree then exact C; no newline.
- `digest(record:Record) -> str`: domain prefix + C; validate record's profile.
- `f64(bits:str) -> float`, `encode_f64(value:float) -> dict[str,str]`: finite
  binary64 only, input value must be exactly Python float, no bool/int coercion;
  bits function preserves signed zero. ContractError(F64) on invalid input.

**I1 `records.py`:**

- `validate_record(record:Record) -> None`: exact structural/kind/type checks.
- `validate_closure(records:Sequence[Record], head:str,
  *, world_id:str, trusted_receipts:Mapping[str,JSON]) -> ValidatedClosure`:
  complete semantic/DAG/trust/history checks, no I/O. Trusted map is injected,
  never extracted from a request/archive. `ValidatedClosure` has `head:str`,
  `world_id:str`, `records:Mapping[digest,Record]`, `retained:tuple[str,...]`
  (head first), `commands:Mapping[tuple[principal,command_id],result_digest]`.
  Class construction is internal to validation; Store must not accept an
  arbitrary hand-constructed object as proof without rechecking contents.
- `select(closure:ValidatedClosure, *, tick:int, revision:int,
  watermark:int) -> Record`: exact retained manifest lookup, NOT_FOUND or
  WATERMARK; never selects nearest, creates objects or replays computation.

**I2 `ownership.py`:**

- `acquire(root:Path, world_id:str, *, initialize:bool=False) -> Lease`:
  explicit side effect. With initialize=False all directory/identity/lock entries
  must exist; missing means UNINITIALIZED with **zero creates**. With True only
  explicitly new/partially initialized matching root registration is eligible;
  arbitrary nonempty legacy directories reject ROOT_MISMATCH. Nonblocking OS
  lock attempt; busy returns LOCKED. Partial creation never overwrites identity.
- `Lease`: frozen public `.root:Path` (canonical), `.world_id:str`, `.owner_pid:int`,
  `.profile:str`, `.initializing:bool`; private fd and pinned root/lock identity.
  `check() -> None` verifies PID, fd lock ownership, stable registered inodes;
  `close() -> None` idempotently closes only own fd and never deletes anything.
  Context manager returns self, closes on exit without swallowing exceptions.
  Reusing closed lease=CLOSED; root replacement=ROOT_MISMATCH; fork misuse=LOCKED.
  All errors use ContractError; `__del__` is not a correctness mechanism.
  Explicit read-only acquire may take existing exclusive lock but creates no
  files; initialization is never implied by a status/observe request.

**I3 `store.py`:**

- `StoreError(ContractError)` adds `.commit_status:str` (`not_attempted|unknown|
  confirmed`) and `.phase:str`. Ordinary I/O exceptions are wrapped with cause.
- `FaultHook = Callable[[str,Mapping[str,JSON]],None]` per section 5; default no-op.
- `Store(lease:Lease, *, trusted_receipts:Mapping[str,JSON],
  fault:FaultHook|None=None)`: construction only stores defensive inputs; no I/O.
  Owns no extra lease lifetime: caller keeps lease through Store.close, then
  closes lease. `.state:str` initially `uninitialized` for initializing lease,
  otherwise `recovering`; `.close()->None` makes closed, does not close lease.
- `initialize(genesis:Sequence[Record], head:str) -> CommitReceipt`:
  only explicit initializing lease and absent HEAD; exact revision0 closure,
  same A-free write/V/D order; identity.json must be fully written and
  fsynced before preparing HEAD, with new directory entries synchronized. If HEAD exists, do not overwrite/reinitialize;
  require recovery. No double initialize. Its committed result is None.
- `pin() -> PinnedRoot`: requires lease.check; reads/validates exact HEAD identity
  and pins bytes/digest once; no writes or implicit recovery. `PinnedRoot` fields
  `head:str,head_bytes:bytes,objects:Mapping[str,bytes]`; includes entire retained
  closure discovered with bounded reads/digests. Reads of bad objects fail
  CORRUPT; no fallback. Never ready merely by pinning.
- `confirm_recovery(pinned:PinnedRoot, closure:ValidatedClosure) -> Snapshot`:
  verifies closure matches pinned head/bytes/world, rechecks raw objects and
  reference closure against its trusted receipts, then executes recovery sync
  order. Only success marks Store ready. Error yields unconfirmed_readonly only
  for an already fully validated pinned root; otherwise corrupt/fail closed.
  This method centralizes low-level sync for I5, not a shortcut around validation.
- `snapshot() -> Snapshot`: requires ready or explicit unconfirmed_readonly;
  no new I/O, returns defensive pinned snapshot with `.storage_state:str`,
  `.closure:ValidatedClosure`. Unconfirmed snapshot cannot authorize writes.
- `lookup_result(principal:str, command_id:str, fingerprint:str) -> Record|None`:
  searches snapshot's persistent command index; mismatch COMMAND_CONFLICT;
  unknown None. This does not authorize access; I4 must authenticate first.
- `commit(bundle:CommitBundle) -> CommitReceipt`: ready only, valid lease,
  `bundle.expected_head:str`, `records:tuple[Record,...]`, `head:str`,
  `principal:str`, `command_id:str`, `fingerprint:str`; closure is assembled with
  already retained snapshot and validated **again** before any writes. Exactly
  one revision successor, matching A and command/result index. Full budget/cursor
  and result/root atomicity. Never accepts an authority object from fake adapter.
  Before V failure leaves ready old snapshot if intact; after V attempted failure
  Store invalidates its cached snapshot and enters recovering (or corrupt): no
  reads claiming the old head and no subsequent commit until fresh recovery.
  Only freshly pinned, fully validated recovery may expose unconfirmed_readonly.
- `CommitReceipt` fields `manifest:str,result:Record|None,
  commit_status:str='confirmed'`; created only after D or D_recovery.
  Exceptions from W8 still propagate as unknown and fail-stop conservatively.

**I4 `admission.py`:**

- `TrustVerifier` protocol methods `authorize_read(principal:str,world_id:str)->None`,
  `verify_approval(approval:Record,proposal:Record,intent:Record)->None`,
  `admit(command:Record,candidate:Record,*,current_revision:int,
  admission_id:str)->Record`.
  Fail AUTHORIZATION or external uncertainty NOT_READY; no world mutation.
  admit returns one admission record, never changes command fingerprint.
- `FixtureTrust(receipts:Mapping[str,JSON])` implements that protocol for only
  profile `neutral-transfer-v0.1`; authenticate against explicit injected
  principals from the fixed anchor map. No default allow-all, network or billing.

**I4 `rules.py`:**

- `neutral_candidate(prior:Record, command:Record, intent:Record,
  *, candidate_id:str) -> Record`: pure deterministic fake transfer above;
  checks principal/profile/revision/cursor/budget/finite sum, no Genesis import.
- `validate_rule_dag(nodes:Mapping[str,Sequence[str]]) -> tuple[str,...]`:
  IDs validated, missing/self/cycle rejected REFERENCE; deterministic lexical
  topological order. Empty graph allowed for neutral profile. Future rules may
  not silently mutate this fixture contract or import world laws.

**I4 `commands.py`:**

- `execute(store:Store, command_records:Sequence[Record],
  *, command_digest:str, principal:str, verifier:TrustVerifier,
  candidate_id:str, admission_id:str, state_id:str, event_id:str,
  result_id:str, index_id:str, manifest_id:str) -> CommitReceipt`.
  Closure includes proposal/intent/approval/command in topological order; exact
  fingerprint is computed locally, not trusted from caller. Authorize read,
  match world/principal and immutable command inputs, then committed retry lookup
  before new-action checks. Retry returns original confirmed receipt only when
  snapshot ready; unconfirmed is explicit NOT_READY, not fake success.
  New action validates approval/current-head/expiry/budget/rule/input, calls pure
  fake candidate, obtains final A via verifier, builds rest, calls Store.commit.
  A's allocated id must equal admission_id; stable IDs are supplied by owner
  before solve and must not collide. Event prior link comes from pinned head.
  No auto retry, timer, hidden randomness, thread or own lease acquisition.
  ContractError leaves noncommit only if Store has not attempted V; StoreError
  propagates unchanged with commit_status. I4 never re-labels timeout as safe.

**I5 `recovery.py`:**

- `recover(store:Store) -> RecoveryReport`: same existing lease, invokes pin,
  validates every retained root and full reference closure with store's injected
  trust context, calls confirm_recovery; returns `.storage_state:str`,
  `.snapshot:Snapshot|None`, `.confirmed:bool`, `.error_code:str|None`.
  Corruption raises StoreError(CORRUPT), never exposes snapshot; integrity valid
  but sync unsuccessful returns unconfirmed_readonly/confirmed=False with
  immutable validated snapshot. Unknown pin validity raises, not partial success.
  No reads/writes for earlier backup, solve, GC, migration, automatic retry.
- `status(snapshot:Snapshot) -> dict`: exact section-4 status payload, no I/O.
- `observe(snapshot:Snapshot, *, tick:int,revision:int,watermark:int) -> dict`:
  exact retained historical payload plus storage_state; no current fallback or
  writes. unconfirmed snapshots must visibly retain their storage_state label.

The oracle is **not** an I1–I5 implementation: its public functions are a compact
contract checker, not the production module API or a storage/GPU test. An API
change affecting bytes, ordering, ownership or downstream calls reopens G-C;
implementation-only choices within these signatures belong to their card owner.

## 7. Checks and evidence boundaries

Fixed files are [positive archive](../fixtures/universe_authority_v0_1/positive.json),
[golden bytes/hashes](../fixtures/universe_authority_v0_1/golden.json),
[negative inputs](../fixtures/universe_authority_v0_1/negative.json) and separate
[trusted fixture anchors](../fixtures/universe_authority_v0_1/trusted_receipts.json).
They are authored literals; the validation command only reads them and compares
against fixed expected bytes/digests, never rewrites or blesses new expectations.

`python3 scripts/validate_universe_authority_fixtures.py` checks fixed records,
closure, same-tick history and rejection codes. Initial actual local check:
24 records, 3 retained roots, 26 negative vectors, PASS. Directed review added
a rehashed duplicate EventId vector. Final directed check: **24 fixed records,
3 roots, 27 negative vectors, PASS**; Python 3.10 grammar parse passed and all
fixture SHA256 values before/after execution matched (read-only check). Checks
completed locally in <1 second each within the assigned 120-second cap; no
additional rerun performed. Exact final source is in the PR/coordinator record. Negative inputs include
rehashed history truncation (not just a stale digest), duplicate decoded keys,
unsafe/inexact integer, illegal finite encoding, wrong domain/version/watermark,
command conflict, forged receipt/reference and approval cycle. The independently
implemented recomputation entry point is documented in fixture README; external
review evidence is separate. A second implementation agreeing with golden is
necessary independent evidence, not proof of all semantic/storage properties.

No UE/Genesis/GPU/network solver, storage fault injection, actual lock/recovery,
power-loss, product law, renderer or performance claim follows from I0 checks.
