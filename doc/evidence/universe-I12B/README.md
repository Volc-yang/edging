# I12B-PREP — new-world deployment, no R12 execution

Base `f85428128da93270b7df368e318c4b9de79887a5`. Owner paths limited to this evidence
directory; product/accepted runner/verifier/launcher are unchanged. Root authorized only CPU
≤120s/raw64MiB, new-world explicit trusted provisioning/metadata and output deployment. No
Genesis/UE/real launcher/CUA/advance/build is authorized. Root owns future UI via CUA.

Root accepted metadata rebind of existing actual B/O **body** after source/native identity
checks. This does not constitute new options measurement. `prepare_deployment.py` first compares
accepted B/O/origin SHA, current adapter and authority modules, all264 Genesis .py/19critical,
37native/METADATA bytes/SHA and accepted invocation's canonical Python executable SHA. No
Genesis import or execution of that runtime Python/native/UE binary is needed for identity.
Tool Python runs only stdlib/explicit trusted provision and actual product's pure public-pins
export. Source/kernel/body identity mismatch stops before provision or output links and requires
root's fresh bootstrap decision. New provider.initialize must still measure strict B/O itself.

Explicit PREP operation (already authorized only for preparing metadata):

```sh
env -u PYTHONHOME -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 -B doc/evidence/universe-I12B/prepare_deployment.py --storage /Volumes/DevSSD/Unreal/Projects/EdgeWorld/I12B-20261102-world --prepare
```

Exclusive storage0700, four persistent public inputs and origin copies, two0600 owner configs,
new external key directory/anchor, output symlinks and generated-ini provenance are retained.
The helper never reads/copies/hashes key bytes; accepted provision writes a new secret internally.
Owner metadata is validated by actual pure worker loaders. New B/O world/O.build refs, assets
world and audit world/candidate world/digest are the only changes; body canonical bytes remain.
Candidate card is approved=false and expired, never runtime permission. Future root must set
actual card times/final accepted product SHA and the separately reviewed I12C interpreter pins.
Native/installation runtime_files are immutable; Host/plugin hashes are captured after each
actual official build rather than pre-pinned across two sessions. No extra build is done here.

## Passive action capture for root

Root may later import `capture_action.capture` directly, or call the standalone helper. It uses
the accepted authority_map/process/log conventions and writes exclusive before/after directories.
No screenshot, input, console command or state advance is performed. Supply actual current
UE PID/project/log/trace paths from the owning launcher, never infer them from old runs:

```sh
python3 -B doc/evidence/universe-I12B/capture_action.py --run i12b-20261102 --action camera --phase before --ue-pid ACTUAL_PID --project ABS_PRODUCT_UPROJECT --log ABS_UE_LOG --authority ABS_NEW_AUTHORITY --scratch ABS_NEW_SCRATCH --trace ABS_RAW_TRACE --output ABS_NEW_ACTION_BEFORE
```

Then root performs CUA action, gets explicit readback/marker, and captures after into a new
directory. `authority-map.json` has accepted `{root,files,bytes}` shape for verifier readonly
pairs; scratch map is independent. Actual process argv, capture times and rawtrace directory are
recorded. Snapshot's log pins give `start_offset,prefix_sha256,device,inode` for accepted marker
waiter's explicit-offset mode, allowing action-completed-before-wait without sleep assumptions.
Maps are read twice within capture and must stay quiescent. No missing authority is created.

Useful actual-world readbacks, issued only by root's later CUA console:

* `GetAllLocation CameraActor` and `GetAllRotation CameraActor`: preserve matching world/actor
  names and ViewTarget/image binding before/after scripted UniverseCamera. Helper assertion is
  not a full transform or human relative-mouse proof.
* `getall StaticMeshActor bHidden`: all actual projection proxy actors hidden/restored; match
  object identity with the current proof/projection generation and image.
* `getall WorldSettings PauserPlayerState`: actual pause state and resume readback.
* `t.MaxFPS`: actual console readback after bounded change and restoration.

Capture full raw console result, before/after maps, stable Metal originals and action/log offsets;
do not turn a typed command or old helper success into evidence of actual effect. LOD is N/A for
this technical proxy, with explicit rationale. All UI interaction and actual StartPlay/image
identity remain future R12 checks, not PREP claims.
