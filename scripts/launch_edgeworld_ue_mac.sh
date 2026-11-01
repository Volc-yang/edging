#!/bin/bash
# Build the owning worktree before launching the published Mac editor in game mode.
set -euo pipefail

usage() {
    cat <<'HELP'
Usage: scripts/launch_edgeworld_ue_mac.sh [--build-only | --launch] [--user-dir ABS_PATH] [--no-render-thread | --viewport-preflush]
Defaults to --build-only (no UE/Metal process). --launch waits for UE to exit.
--no-render-thread passes UE's -norenderthread as an experimental viewport-crash
workaround. It is not a root-cause fix; CPU/GPU performance is unmeasured and may
degrade. Omit it to retain UE's default rendering mode. Earlier GQ timings do not apply.
--viewport-preflush passes -EWDiagPreflushViewport once, retaining default rendering
threads with a limited project viewport-close workaround. Default off; performance
cost is unmeasured. Mutually exclusive with --no-render-thread; no automatic fallback.
--universe explicitly selects the v0.2 Universe host (legacy remains default).
--owner-config ABS passes the private owner configuration path only to the trusted
worker; --universe-initialize additionally requests explicit wire initialization.
Universe uses EDGEWORLD_UNIVERSE_PYTHON and derives public pins through the owning
worker's --print-public-pins CLI. Public pins do not authorize initialization.
Environment: UE5_ROOT (default /Users/Shared/Epic Games/UE_5.8),
EDGEWORLD_CAUSAL_PYTHON (absolute Genesis-enabled Python, required by --launch).
The project and causal worker always come from this script's worktree.
--user-dir reuses an explicit isolated state directory for recovery; otherwise each
launch gets a fresh directory. Do not share it between running instances.
HELP
}
fail() { echo "[launcher] error: $*" >&2; exit 64; }
mode=build-only
user_dir=
no_render_thread=0
viewport_preflush=0
universe=0
universe_initialize=0
owner_config=
while (($#)); do
    case "$1" in
        --build-only) mode=build-only; shift ;;
        --launch) mode=launch; shift ;;
        --no-render-thread) no_render_thread=1; shift ;;
        --viewport-preflush) viewport_preflush=1; shift ;;
        --user-dir) (($# >= 2)) || fail '--user-dir needs an absolute path'; user_dir=$2; shift 2 ;;
        --universe) universe=1; shift ;;
        --owner-config) (($# >= 2)) || fail '--owner-config needs an absolute path'; owner_config=$2; shift 2 ;;
        --universe-initialize) universe_initialize=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done
if ((universe == 0)) && { [[ -n $owner_config ]] || ((universe_initialize)); }; then
    fail '--owner-config and --universe-initialize require --universe'
fi
if ((no_render_thread && viewport_preflush)); then
    fail '--viewport-preflush and --no-render-thread are mutually exclusive'
fi
[[ $(uname -s) == Darwin ]] || fail 'macOS is required'
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
project_dir="$repo/engine_platforms/unreal/EdgeWorldHost"
project="$project_dir/EdgeWorldHost.uproject"
worker="$repo/engine/edgeworld_worker/abstract_causal_worker.py"
ue_root=${UE5_ROOT:-/Users/Shared/Epic Games/UE_5.8}
[[ $ue_root == /* && -d $ue_root ]] || fail 'UE5_ROOT must be an existing absolute directory'
ue_root=$(cd -- "$ue_root" && pwd -P)
build="$ue_root/Engine/Build/BatchFiles/Mac/Build.sh"
# The sibling Binaries/Mac/UnrealEditor is a launcher that can exit while the
# app keeps running. Execute the app binary so $! and wait own the real UE PID.
editor="$ue_root/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
[[ -f $project && -f $build && -x $editor ]] || fail 'project, official Build.sh or UnrealEditor missing'
command -v python3 >/dev/null || fail 'python3 is required to validate Build.version'
python3 - "$ue_root/Engine/Build/Build.version" <<'PY' || fail 'requires installed UE 5.8.3'
import json, sys
with open(sys.argv[1]) as f:
    v = json.load(f)
if tuple(v[k] for k in ('MajorVersion', 'MinorVersion', 'PatchVersion')) != (5, 8, 3):
    sys.exit(1)
print('[launcher] UE 5.8.3 CL', v['Changelist'])
PY
[[ -f "$ue_root/Engine/Build/InstalledBuild.txt" ]] || fail 'requires an installed engine build'
if [[ -n $user_dir ]]; then
    [[ $user_dir == /* ]] || fail '--user-dir must be absolute'
fi
game_mode='/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode'
start_marker='Causal world: Space advances;'
observe_pattern='Causal world stg-demo observed tick [0-9]+, revision [0-9]+'
if [[ $mode == launch ]]; then
    if ((universe)); then
        [[ ${EDGEWORLD_UNIVERSE_PYTHON:-} == /* && -x ${EDGEWORLD_UNIVERSE_PYTHON:-} ]] || fail 'set EDGEWORLD_UNIVERSE_PYTHON to an absolute executable'
        [[ $owner_config == /* ]] || fail '--universe --launch requires --owner-config ABS'
        [[ $owner_config != *$'\n'* && $owner_config != *$'\r'* && $owner_config != *'"'* ]] || fail 'unsafe owner config path'
        worker="$repo/engine/universe_authority/worker.py"
        [[ -f $worker ]] || fail 'owning worktree Universe worker missing (I10 prerequisite)'
        export EDGEWORLD_UNIVERSE_WORKER="$worker"
        export EDGEWORLD_UNIVERSE_OWNER_CONFIG="$owner_config"
        export EDGEWORLD_UNIVERSE_INITIALIZE="$universe_initialize"
        game_mode='/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldUniverseGameMode'
        start_marker='Universe world: 1 weak;'
        observe_pattern='Universe world [a-z][a-z0-9._-]* observed tick [0-9]+, revision [0-9]+'
    else
        [[ ${EDGEWORLD_CAUSAL_PYTHON:-} == /* && -x ${EDGEWORLD_CAUSAL_PYTHON:-} ]] || fail 'set EDGEWORLD_CAUSAL_PYTHON to an absolute executable'
        [[ -f $worker ]] || fail 'owning worktree causal worker missing'
        export EDGEWORLD_CAUSAL_WORKER="$worker"
    fi
fi
mkdir -p "$project_dir/Saved/MacLauncher"
run_dir=$(mktemp -d "$project_dir/Saved/MacLauncher/run-XXXXXXXX")
status_log="$run_dir/status.log"
status() { echo "[launcher] $*" | tee -a "$status_log"; }
status "project=$project"
status "evidence=$run_dir"
if ((universe)) && [[ $mode == launch ]]; then
    viewer_dir="$run_dir/viewer"
    # Only the trusted worker reads private config. Its pure export has no lease/key/Genesis effects.
    pins_sha=$(python3 - "$EDGEWORLD_UNIVERSE_PYTHON" "$repo" "$owner_config" "$viewer_dir" <<'PINS'
import hashlib,json,os,pathlib,re,subprocess,sys
python,repo,owner,directory=sys.argv[1:]
argv=[python,'-m','engine.universe_authority.worker','--owner-config',owner,'--print-public-pins']
r=subprocess.run(argv,cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
if r.returncode: raise SystemExit('trusted public pins export failed; private diagnostics withheld')
raw=r.stdout
if len(raw)>16385 or not raw.endswith(b'\n') or b'\r' in raw or b'\n' in raw[:-1]: raise SystemExit('invalid pins framing')
def pairs(items):
 d={}
 for k,v in items:
  if k in d:raise ValueError('duplicate pins key')
  d[k]=v
 return d
x=json.loads(raw[:-1].decode('ascii'),object_pairs_hook=pairs)
keys={'domain','version','profile','world_id','authority_root','trust_algorithm','trust_anchor','artifact_class','expected_build','expected_options','principal','allowed_actions'}
assert type(x) is dict and set(x)==keys
assert x['domain']=='edgeworld.universe.authority' and x['version']=='0.2' and x['profile']=='composite-rigid-support.v0.2'
assert x['trust_algorithm']=='local-hmac-sha256.v0.2' and x['artifact_class']=='genesis-runtime'
for key in ('world_id','principal'):assert type(x[key]) is str and re.fullmatch(r'[a-z][a-z0-9._-]{0,63}',x[key])
for key in ('trust_anchor','expected_build','expected_options'):assert type(x[key]) is str and re.fullmatch(r'[0-9a-f]{64}',x[key])
root=x['authority_root'];assert type(root) is str and root.startswith('/') and not root.startswith('//') and '\x00' not in root and str(pathlib.PurePosixPath(root))==root and '..' not in pathlib.PurePosixPath(root).parts
assert type(x['allowed_actions']) is list and len(x['allowed_actions'])<=2 and all(type(a) is str and a in ('physics_step','retain_snapshot') for a in x['allowed_actions']) and len(set(x['allowed_actions']))==len(x['allowed_actions'])
canonical=json.dumps(x,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode('ascii');assert canonical==raw[:-1]
os.mkdir(directory,0o700);path=pathlib.Path(directory)/'public-pins.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as f:f.write(canonical);f.flush();os.fsync(f.fileno())
assert path.stat().st_uid==os.getuid() and path.stat().st_nlink==1 and path.stat().st_mode&0o777==0o600
print(hashlib.sha256(canonical).hexdigest())
PINS
    ) || fail 'Universe public pins validation failed; UE/build not started'
    trace_dir="$run_dir/trace"
    mkdir -m 700 "$trace_dir"
    trace_dir=$(cd -- "$trace_dir" && pwd -P)
    export EDGEWORLD_UNIVERSE_TRACE="$trace_dir"
    export EDGEWORLD_UNIVERSE_PINS="$viewer_dir/public-pins.json"
    export EDGEWORLD_UNIVERSE_PINS_SHA256="$pins_sha"
    status "universe_public_pins_sha256=$pins_sha; explicit_initialize=$universe_initialize; worker_permissions_decide"
fi
status 'build_started target=EdgeWorldHostEditor platform=Mac configuration=Development'
# Capture Build.sh, not tee, as the authoritative exit status.
set +e
build_args=(EdgeWorldHostEditor Mac Development "-Project=$project" -WaitMutex)
if ((universe)); then build_args+=(-NoUBA); fi
/bin/bash "$build" "${build_args[@]}" 2>&1 | tee "$run_dir/build.log"
build_rc=${PIPESTATUS[0]}
set -e
status "build_exit_code=$build_rc"
if ((build_rc != 0)); then
    status 'build_failed; UE was not launched (inspect build.log, including Mac SDK/compiler errors)'
    exit "$build_rc"
fi
status 'build_succeeded; non-Mac SDK warnings do not override Build.sh exit code 0'
if [[ $mode == build-only ]]; then
    status 'build_only_complete; runtime_not_tested'
    exit 0
fi
if [[ -z $user_dir ]]; then user_dir="$run_dir/user"; fi
mkdir -p "$user_dir"
user_dir=$(cd -- "$user_dir" && pwd -P)
status "user_dir=$user_dir"
status "worker=$worker"
ue_log="$run_dir/ue.log"
args=("$project" "$game_mode"
    -game -log -windowed -ResX=960 -ResY=600 "-UserDir=$user_dir" "-abslog=$ue_log")
if ((no_render_thread)); then
    args+=(-norenderthread)
    status 'render_mode=no_render_thread; viewport_preflush=disabled; experimental_workaround_not_root_fix; performance_unmeasured_may_degrade; previous_GQ_timings_not_applicable'
elif ((viewport_preflush)); then
    args+=(-EWDiagPreflushViewport)
    status 'render_mode=engine_default; viewport_preflush=enabled; default_rendering_threads_retained; limited_project_workaround_not_root_fix; performance_cost_unmeasured'
else
    status 'render_mode=engine_default; viewport_preflush=disabled; intermittent_viewport_reliability_not_established'
fi
printf '%q ' "$editor" "${args[@]}" > "$run_dir/command.txt"
printf '\n' >> "$run_dir/command.txt"
"$editor" "${args[@]}" > "$run_dir/console.log" 2>&1 &
ue_pid=$!
status "process_spawned pid=$ue_pid; initialization_pending"
# Forward interruption, then still wait for and report the child's actual exit.
trap 'kill -TERM "$ue_pid" 2>/dev/null || true' INT TERM
engine_initialized_seen=0
mode_seen=0
observation_seen=0
while kill -0 "$ue_pid" 2>/dev/null; do
    if ((engine_initialized_seen == 0)) && [[ -f $ue_log ]] && grep -Fq 'Engine is initialized. Leaving FEngineLoop::Init()' "$ue_log"; then
        engine_initialized_seen=1
        status 'engine_initialized_seen; visual_acceptance_not_tested'
    fi
    if ((mode_seen == 0)) && [[ -f $ue_log ]] && grep -Fq "$start_marker" "$ue_log"; then
        mode_seen=1
        status 'gamemode_startplay_seen; visual_acceptance_not_tested'
    fi
    if ((observation_seen == 0)) && [[ -f $ue_log ]] && grep -Eq "$observe_pattern" "$ue_log"; then
        observation_seen=1
        status 'validated_observation_seen; visual_acceptance_not_tested'
    fi
    sleep 1
done
set +e
wait "$ue_pid"
ue_rc=$?
set -e
trap - INT TERM
status "ue_exit_code=$ue_rc"
# A fast process can exit between polling iterations; inspect the final log too.
if [[ -f $ue_log ]] && grep -Fq 'Engine is initialized. Leaving FEngineLoop::Init()' "$ue_log"; then engine_initialized_seen=1; fi
if [[ -f $ue_log ]] && grep -Fq "$start_marker" "$ue_log"; then mode_seen=1; fi
if [[ -f $ue_log ]] && grep -Eq "$observe_pattern" "$ue_log"; then observation_seen=1; fi
status "final_engine_initialized_seen=$engine_initialized_seen final_gamemode_seen=$mode_seen final_validated_observation_seen=$observation_seen"
if ((ue_rc != 0)); then
    status 'runtime_failed; build success does not establish viewport reliability'
    exit "$ue_rc"
fi
if [[ -f $ue_log ]] && grep -Eq 'Assertion failed:|Fatal error:|Critical error:' "$ue_log"; then
    status 'runtime_failure_logged despite exit 0; inspect ue.log'
    exit 70
fi
if ((mode_seen == 0 || observation_seen == 0)); then
    status 'initialization_unconfirmed; inspect ue.log and console.log'
    exit 70
fi
status 'session_exited_cleanly; visual and intermittent viewport reliability gates remain open'
