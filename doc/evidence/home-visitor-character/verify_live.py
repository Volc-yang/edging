import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone


root = pathlib.Path(sys.argv[1]).resolve()
primary = root / "live-primary-attempt1"
recovery = root / "live-recovery-attempt1"


def load(path):
    return json.loads(path.read_text())


def statuses(text):
    pattern = r"\[([\d.:-]+)\].*Visitor status frame=(\d+).*position=X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+) rotation=P=([-\d.]+) Y=([-\d.]+) R=([-\d.]+) velocity=X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+)"
    return [(datetime.strptime(match[0], "%Y.%m.%d-%H.%M.%S:%f").replace(tzinfo=timezone.utc), int(match[1]), tuple(map(float, match[2:5])), tuple(map(float, match[5:8])), tuple(map(float, match[8:11]))) for match in re.findall(pattern, text)]


readonly = []
advances = []
for before_path in sorted(root.glob("live-*-attempt1/*/before.json")):
    after_path = before_path.with_name("after.json")
    if not after_path.exists():
        continue
    before, after = load(before_path), load(after_path)
    action = before_path.parent.name
    if action in ("advance1-attempt1", "advance2-attempt1"):
        assert before["files"] != after["files"]
        assert after["manifest"]["logical_tick"] == before["manifest"]["logical_tick"] + 1
        assert after["manifest"]["state_revision"] == before["manifest"]["state_revision"] + 1
        advances.append(str(before_path.parent.relative_to(root)))
    else:
        assert before["files"] == after["files"], str(before_path)
        readonly.append(str(before_path.parent.relative_to(root)))
    input_path = before_path.with_name("input.json")
    if input_path.exists():
        operation = load(input_path)
        expected = operation.get("expectedTick")
        if expected is not None:
            delta = before_path.with_name("new-log.txt").read_text()
            assert f"Causal world stg-demo observed tick {expected}, revision {expected}" in delta

holds = {}
for action in ("rail-w-attempt1", "wall-d-attempt1"):
    directory = primary / action
    interval = load(directory / "result.json")
    start = datetime.fromisoformat(interval["started"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(interval["returned"].replace("Z", "+00:00"))
    samples = [sample for sample in statuses((directory / "new-log.txt").read_text()) if start <= sample[0] <= end and any(abs(velocity) > 1 for velocity in sample[4])]
    assert len({sample[1] for sample in samples}) >= 3
    assert len({sample[2] for sample in samples}) >= 3
    holds[action] = [{"frame": sample[1], "position": sample[2], "velocity": sample[4]} for sample in samples]

rail = (primary / "rail-w-attempt1/new-log.txt").read_text()
wall = (primary / "wall-d-attempt1/new-log.txt").read_text()
assert "component=WalkwayRail-1" in rail and "component=LeftWall" in wall
assert "start_penetrating=0 penetration_depth=0.000" in rail
assert "start_penetrating=0 penetration_depth=0.000" in wall
edge = (primary / "edge-s-attempt1/new-log.txt").read_text()
assert "Visitor recovery trigger" in edge and "Y=-480.857" in edge
assert "Visitor local entry restored: X=0.000 Y=-300.000 Z=-50.000" in edge
for run in (primary, recovery):
    enter = statuses((run / "tab-overview-attempt1/new-log.txt").read_text())
    leave = statuses((run / "tab-return-attempt1/new-log.txt").read_text())
    assert enter[0][2:4] == leave[-1][2:4]
    assert "view=CameraActor_0" in (run / "tab-overview-attempt1/new-log.txt").read_text()
    assert "view=EdgeWorldVisitorCharacter_0" in (run / "tab-return-attempt1/new-log.txt").read_text()
    lighting = (run / "lighting-attempt1/new-log.txt").read_text()
    assert "NumLightingUnbuiltObjects=0" in lighting
    assert "Lights with unbuilt interactions: 0" in lighting
    assert "Primitives with unbuilt interactions: 0" in lighting

assert load(primary / "preclose-attempt1/authority.json")["files"] == load(recovery / "restored-tick2-attempt1/authority.json")["files"]
diagnostic = (recovery / "mouse-path-diagnostic-attempt1/new-log.txt").read_text()
assert "HighPrecisionMouseMode Enabled" in diagnostic
assert not re.search(r"Key: Mouse[XY]", diagnostic)
assert "LogPlayerInput                            Log" in diagnostic
summary = {"readonly_pairs": readonly, "explicit_space_pairs": advances, "continuous_hold_samples": holds, "restoration_all_files_equal": True, "tool_mouse_axes": 0, "manual_mouse": "pending", "recovery_close": "pending"}
if "--final" in sys.argv[3:]:
    mouse = load(recovery / "manual-mouse-result-attempt1.json")
    assert mouse["samePosition"] and mouse["allAuthorityFilesUnchanged"]
    assert abs(mouse["pitchDelta"]) > 1 or abs(mouse["yawDelta"]) > 1
    assert (recovery / "manual-mouse-before-attempt2/image.png").read_bytes() != (recovery / "manual-mouse-after-image-attempt1/image.png").read_bytes()
    for run in (primary, recovery):
        status = (run / "launcher-archive/status.log").read_text()
        assert "build_exit_code=0" in status and "ue_exit_code=0" in status
        log = (run / "launcher-archive/ue.log").read_text()
        assert "LogExit: Exiting" in log
        assert "preflush=1 threaded_rendering=1" in log and "owner_unchanged=1" in log
        assert not any(token in log for token in ("Error:", "Ensure condition failed", "Assertion failed"))
    closed = load(recovery / "close-attempt1/after.json")
    assert closed["files"] == load(recovery / "restored-tick2-attempt1/authority.json")["files"]
    for relative, expected_hash in closed["files"].items():
        actual = root / "live-user-attempt1/Saved/EdgeWorldCausal/stg-demo" / relative
        assert hashlib.sha256(actual.read_bytes()).hexdigest() == expected_hash
    summary["manual_mouse"] = mouse
    summary["recovery_close"] = load(recovery / "close-attempt1/result.json")
output = root / sys.argv[2]
with output.open("x") as stream:
    json.dump(summary, stream, indent=2)
    stream.write("\n")
print(json.dumps({"summary": str(output), "readonly_pairs": len(readonly), "explicit_space_pairs": len(advances), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
