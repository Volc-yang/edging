import argparse
import hashlib
import json
import pathlib
import subprocess
from datetime import datetime, timezone


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--run", required=True)
parser.add_argument("--pid", required=True, type=int)
parser.add_argument("--log", required=True, type=pathlib.Path)
parser.add_argument("--state-dir", required=True, type=pathlib.Path)
parser.add_argument("--output", required=True, type=pathlib.Path)
args = parser.parse_args()
command = subprocess.check_output(["ps", "-p", str(args.pid), "-o", "command="], text=True).strip()
assert command.startswith("/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor ")
assert f"-UserDir={args.state_dir}" in command
assert f"-abslog={args.log}" in command
log = args.log.read_text()
assert "Engine is initialized. Leaving FEngineLoop::Init()" in log
assert "Causal world stg-demo observed tick" in log
authority = args.state_dir / "Saved/EdgeWorldCausal/stg-demo"
files = {str(path.relative_to(authority)): digest(path) for path in sorted(authority.rglob("*")) if path.is_file()}
assert "abstract_world.json" in files
record = {
    "utc": datetime.now(timezone.utc).isoformat(),
    "run": args.run,
    "pid": args.pid,
    "command": command,
    "log": str(args.log),
    "log_offset": args.log.stat().st_size,
    "state_dir": str(args.state_dir),
    "files": files,
    "manifest": json.loads((authority / "abstract_world.json").read_text()),
}
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x") as output:
    json.dump(record, output, indent=2)
    output.write("\n")
print(json.dumps({"run": args.run, "pid": args.pid, "files": len(files), "output": str(args.output)}))
