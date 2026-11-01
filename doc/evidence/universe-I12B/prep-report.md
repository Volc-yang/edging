# I12B-PREP1 report — deployment only

2026-11-02. **Prepared, no actual R12 or build/UE/Genesis/advance.**
Task branch `codex/i12b-universe-live`, base `f85428128da93270b7df368e318c4b9de79887a5`;
ordinary helper source committed first as `61b9a853f1ee29b7c63bbbd3e0bd7faee7c705b5`.
Only `doc/evidence/universe-I12B/` is committed. Six explicit source-side output artifacts
(five links, generated ini) remain outside Git and are exactly allowlisted/provenanced; no
tracked product/runner/verifier/launcher changes. Do not clean/remove this active task tree.

## Identity and reuse decision

Current actual adapter SHA `15f5b96bb0381781d0357eb93510622afe6ec3d5caf60adb5ed8190ff6abb192`,
all264 Genesis Python sources/19critical, authority modules, and37native/METADATA sizes/SHA
match accepted I10B run2 inputs. Canonical Python binary SHA
`30b2a6bf9706029b609327ca5db722cd458239df96efc87e1f8e37beed49db2e`
matches accepted `invocation.executable_sha256` exactly. No execution of that runtime Python
or any UE/native binary was needed for the hash audit. All readlink components/pyvenv.cfg
path+SHA are retained in `source-installation-identity.json`. u9 separately confirmed the
package/native/adapter identity to root. Body reuse is conditional on this unchanged identity.

Root explicitly accepted new-world metadata rebind, not complete-record byte reuse. Approved
origin four files are retained exactly under the persistent storage's `approved-origin/`.
New B/O world/O.build refs, asset world, and audit world/candidate world/digest are the only
changed fields. Canonical B/O/assets body bytes remain identical; audit package/file graph
remains identical after normalizing those metadata fields. `metadata-rebind-proof.json` and
separately computed `independent-preflight.json` include original/deployed SHA and body SHA
equality. This is **rebound-from-accepted-actual-measurement**, not a new runtime B/O/asset export.
Actual provider.initialize still must remeasure B/O and strictly match these pins; defaults
were neither hand-filled nor measurement checks bypassed.

## Persistent deployment

Storage: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I12B-20261102-world` (0700).
New world: `edgeworld-i12b-20261102`; new authority/scratch paths are inside storage but still
**absent**. Old authority was not opened or changed. New keys are outside storage/raw/authority,
in the sibling `I12B-20261102-world-keys` (0700). Only accepted explicit provision generated and
wrote the secret; helper never reads/copies/hashes key bytes. Metadata records UID/mode/nlink/
size only. No open_trust, Lease, Store, provider or runtime was invoked.

`deployment/` (0700) holds four public persistent inputs and two0600/nlink1 owner files. All
four indirect refs/hash/context/mode/principal/grants were checked by actual pure worker
loaders, and independently by the accepted runner's owner cross-check without executing run.
Tool Python3.14 performed stdlib preparation and pure `--print-public-pins`; no GS runtime
interpreter execution occurred. PYTHONHOME/PYTHONPATH were removed for helper/export children.

| Public receipt | SHA256 |
| --- | --- |
| owner-initialize.json (metadata/hash only) | `4bcbace0128bd1a77d4d3420929651697943a9a5fecedcd48908fba4c1ee4e11` |
| owner-existing.json (metadata/hash only) | `f690bdfe677ea18ba52ff52343a91b5d0cf14de2318de76b48aac75201f96e27` |
| public-pins.json | `ae9a22be4e905e1c5387cfc4a725e9b3f3b9d5be90d213a0dfc0412efe7e2555` |
| r12-candidate.json | `5255cb1ea6c0c38f904ad2dc144ced8bb014de3ba38aa68761bafe60f610d968` |

Do not print/copy private owner contents into Git. Public pins/candidate/provenance copies in
this evidence directory are safe metadata; no credential bytes. Actual owning product's two
pure public exports matched and caused no authority/scratch creation. These are metadata-only
CPU subprocesses, not owned UE-worker/Genesis runtime or lifecycle evidence.

Five exact symlinks map Host Binaries/Intermediate/Saved and plugin Binaries/Intermediate into
new DevSSD output targets. `Saved/MacLauncher` resolves inside storage. Generated ini is the
exact accepted I11B archived bytes, SHA
`e1b7a60e4da1acca28b8540ed7b2746551df9ae1ddc0056eb45a0932ed82ea78`;
its source/archive are recorded, not a new engine-generated claim. All readlink/lstat/provenance
is in persistent `prep/output-mapping-provenance.json` and candidate's exact untracked allowlist.

## Candidate and remaining blockers

`deployment/r12-candidate.json` has **approved:false**, expired validity, candidate-only marker,
1200s/2GiB combined two-session candidate budget (800/400s, build included). It is not a resource
grant. Its product SHA records the PREP helper commit; root must later pin exact accepted I12C
merge/product source and issue a separate actual card without overwriting this candidate.
Immutable runtime_files pin installation/native/METADATA and canonical Python bytes only.
Host/plugin output binaries are deliberately not pre-pinned across two builds; both real builds
need independent source/binary receipts and root review, no additional PREP build or card switch.

The real GS interpreter is a venv/Homebrew symlink chain. I12C must narrowly accept the exact
root-pinned chain/pyvenv.cfg while retaining lexical venv argv. No global verifier safe_path
relaxation, wrapper, alternate Python, shared venv modification or runtime execution workaround
was used. Actual R12 remains blocked on that accepted fix and root's separate dispatch.

`capture_action.py` is ready as a small passive import/CLI for root: explicit run/action/phase,
actual UE PID/project, authority/scratch all-file maps, log prefix SHA/offset/dev/inode, rawtrace
path and capture interval. Maps are checked twice for quiescence and preserve accepted verifier
root/files shape. It never inputs/advances/captures UI. Only AST-checked in PREP because no UE is
running here. Root must collect actual console transforms/visibility/pause/FPS readbacks, stable
Metal originals and two UE-owned StartPlay sessions; helper or I11B test entry cannot replace them.

## Checks and resource ledger

PREP1 actual CPU operation: exit0,1.025s wall; stdout151B/stderr0; internal prep0.979s. Raw command,
cleared environment fields, source/hash and output are `prep-attempt1.*`. Independent JSON rebind
normalization/body SHA and accepted owner cross-check passed; both helpers AST-parse. No actual
runner/launcher, compiler, GS import, CUA or state action. All new secret handling stayed inside
accepted provision; no private owner/key contents are copied into this report/index.

Persistent raw/public origins remain DevSSD; public index pins explicitly enumerated public
files and private owner/key **metadata only**. Root should independently review this checkpoint/
PR and exact I12C integration before authorizing real run. No G-B2, visual, performance, default
exit, human mouse, cook, license or production gate follows from PREP.
