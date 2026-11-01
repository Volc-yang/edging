#!/bin/bash
# Build the owning worktree before launching the published Mac editor in game mode.
set -euo pipefail

usage() {
    cat <<'HELP'
Usage: scripts/launch_edgeworld_ue_mac.sh [--build-only | --launch] [--user-dir ABS_PATH] [--no-render-thread]
Defaults to --build-only (no UE/Metal process). --launch waits for UE to exit.
--no-render-thread passes UE's -norenderthread as an experimental viewport-crash
workaround. It is not a root-cause fix; CPU/GPU performance is unmeasured and may
degrade. Omit it to retain UE's default rendering mode. Earlier GQ timings do not apply.
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
while (($#)); do
    case "$1" in
        --build-only) mode=build-only; shift ;;
        --launch) mode=launch; shift ;;
        --no-render-thread) no_render_thread=1; shift ;;
        --user-dir) (($# >= 2)) || fail '--user-dir needs an absolute path'; user_dir=$2; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done
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
if [[ $mode == launch ]]; then
    [[ ${EDGEWORLD_CAUSAL_PYTHON:-} == /* && -x ${EDGEWORLD_CAUSAL_PYTHON:-} ]] || fail 'set EDGEWORLD_CAUSAL_PYTHON to an absolute executable'
    [[ -f $worker ]] || fail 'owning worktree causal worker missing'
    # Override stale inherited worker paths from other worktrees.
    export EDGEWORLD_CAUSAL_WORKER="$worker"
fi
mkdir -p "$project_dir/Saved/MacLauncher"
run_dir=$(mktemp -d "$project_dir/Saved/MacLauncher/run-XXXXXXXX")
status_log="$run_dir/status.log"
status() { echo "[launcher] $*" | tee -a "$status_log"; }
status "project=$project"
status "evidence=$run_dir"
status 'build_started target=EdgeWorldHostEditor platform=Mac configuration=Development'
# Capture Build.sh, not tee, as the authoritative exit status.
set +e
/bin/bash "$build" EdgeWorldHostEditor Mac Development "-Project=$project" -WaitMutex 2>&1 | tee "$run_dir/build.log"
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
status "worker=$EDGEWORLD_CAUSAL_WORKER"
ue_log="$run_dir/ue.log"
args=("$project" '/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode'
    -game -log -windowed -ResX=960 -ResY=600 "-UserDir=$user_dir" "-abslog=$ue_log")
if ((no_render_thread)); then
    args+=(-norenderthread)
    status 'render_mode=no_render_thread; experimental_workaround_not_root_fix; performance_unmeasured_may_degrade; previous_GQ_timings_not_applicable'
else
    status 'render_mode=engine_default; intermittent_viewport_reliability_not_established'
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
    if ((mode_seen == 0)) && [[ -f $ue_log ]] && grep -Fq 'Causal world: Space advances;' "$ue_log"; then
        mode_seen=1
        status 'gamemode_startplay_seen; visual_acceptance_not_tested'
    fi
    if ((observation_seen == 0)) && [[ -f $ue_log ]] && grep -Eq 'Causal world stg-demo observed tick [0-9]+, revision [0-9]+' "$ue_log"; then
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
if [[ -f $ue_log ]] && grep -Fq 'Causal world: Space advances;' "$ue_log"; then mode_seen=1; fi
if [[ -f $ue_log ]] && grep -Eq 'Causal world stg-demo observed tick [0-9]+, revision [0-9]+' "$ue_log"; then observation_seen=1; fi
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
