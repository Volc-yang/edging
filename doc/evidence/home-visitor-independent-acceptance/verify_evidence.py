"""Verify the bounded H6C raw observations; never drive UE or rewrite evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def load(path):
    return json.loads(path.read_text())


def status_lines(text):
    output = []
    pattern = re.compile(
        r"\[([^]]+)\].*Visitor status frame=(\d+) time=([\d.]+) pawn=(\S+) view=(\S+) "
        r"position=X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+) "
        r"rotation=P=([-\d.]+) Y=([-\d.]+) R=([-\d.]+) "
        r"velocity=X=([-\d.]+) Y=([-\d.]+) Z=([-\d.]+) mode=(\d+) "
        r"grounded=(\d) falling=(\d).*floor_blocking=(\d) floor_walkable=(\d).*blocking_overlap=(\d)"
    )
    for match in pattern.finditer(text):
        values = match.groups()
        output.append({
            "utc": datetime.strptime(values[0], "%Y.%m.%d-%H.%M.%S:%f").replace(tzinfo=timezone.utc).isoformat(),
            "frame": int(values[1]), "time": float(values[2]), "pawn": values[3], "view": values[4],
            "position": list(map(float, values[5:8])), "rotation": list(map(float, values[8:11])),
            "velocity": list(map(float, values[11:14])), "mode": int(values[14]),
            "grounded": int(values[15]), "falling": int(values[16]),
            "floor_blocking": int(values[17]), "floor_walkable": int(values[18]),
            "blocking_overlap": int(values[19]),
        })
    return output


def verify(root):
    primary = root / "primary-attempt1"
    recovery = root / "recovery-attempt1"
    readonly, advances = [], []
    for run in (primary, recovery):
        for path in sorted(run.glob("*/result.json")):
            action = path.parent
            before, after = load(action / "before.json"), load(action / "after.json")
            result = load(path)
            context = load(action / "context.json")
            assert context["run"] == run.name
            assert context["pid"] == load(run / "context.json")["pid"]
            text = (action / "new-log.txt").read_text()
            changed = before["files"] != after["files"]
            assert result["all_files_unchanged"] == (not changed)
            if result.get("key") == "space":
                assert run == primary
                target = result["tick"]
                assert after["manifest"]["logical_tick"] == before["manifest"]["logical_tick"] + 1 == target
                assert len(after["manifest"]["commands"]) == len(before["manifest"]["commands"]) + 1
                assert len(after["manifest"]["events"]) == len(before["manifest"]["events"]) + 1
                assert changed
                advances.append({"action": action.name, "tick": target,
                                 "view_before": status_lines(text)[0]["view"]})
            else:
                assert not changed, action
                readonly.append(str(action.relative_to(root)))
            if result.get("tick") is not None:
                tick = result["tick"]
                assert f"Causal world stg-demo observed tick {tick}, revision {tick}" in text
            for image in action.glob("image.*"):
                if image.suffix not in (".jpg", ".png"):
                    continue
                data = image.read_bytes()
                assert data.startswith(b"\xff\xd8") if image.suffix == ".jpg" else data.startswith(b"\x89PNG\r\n\x1a\n")
    assert sorted(x["tick"] for x in advances) == [1, 2]
    assert next(x for x in advances if x["tick"] == 1)["view_before"].startswith("EdgeWorldVisitorCharacter")
    assert next(x for x in advances if x["tick"] == 2)["view_before"].startswith("CameraActor")

    standing = status_lines((primary / "safe-standing-attempt1/new-log.txt").read_text())
    assert all(x["grounded"] == x["floor_blocking"] == x["floor_walkable"] == 1 and
               x["blocking_overlap"] == 0 and abs(x["position"][2] + 50) < 1 for x in standing)
    free = primary / "free-channel-a-attempt1"
    interval = load(free / "input.json"), load(free / "result.json")
    start, end = (datetime.fromisoformat(x.replace("Z", "+00:00"))
                  for x in (interval[0]["started"], interval[1]["returned"]))
    moving = [x for x in status_lines((free / "new-log.txt").read_text())
              if start <= datetime.fromisoformat(x["utc"]) <= end and any(abs(v) > 1 for v in x["velocity"])]
    assert len({x["frame"] for x in moving}) >= 3
    assert len({tuple(x["position"]) for x in moving}) >= 3

    contacts = {}
    for action, name, reverse, axis, direction in (
        ("rail-w-attempt1", "WalkwayRail-1", "rail-reverse-s-attempt1", 1, -1),
        ("wall-d-attempt1", "LeftWall", "wall-reverse-a-attempt1", 0, 1),
    ):
        text = (primary / action / "new-log.txt").read_text()
        input_record = load(primary / action / "input.json")
        result_record = load(primary / action / "result.json")
        interval_start = datetime.fromisoformat(input_record["started"].replace("Z", "+00:00"))
        interval_end = datetime.fromisoformat(result_record["returned"].replace("Z", "+00:00"))
        hits = []
        for line in text.splitlines():
            if "Visitor blocking hit" not in line or f"component={name} " not in line:
                continue
            timestamp = datetime.strptime(line[1:line.index("]")], "%Y.%m.%d-%H.%M.%S:%f").replace(tzinfo=timezone.utc)
            if interval_start <= timestamp <= interval_end:
                hits.append(line)
        assert hits and all("start_penetrating=0" in x for x in hits)
        pose = status_lines(text)[-1]
        away = status_lines((primary / reverse / "new-log.txt").read_text())[-1]
        assert direction * (away["position"][axis] - pose["position"][axis]) > 50
        assert pose["grounded"] == 1 and pose["blocking_overlap"] == 0
        contacts[name] = {"first_hit": hits[0], "stopped": pose, "reverse": away}
    edge = (primary / "edge-s-attempt1/new-log.txt").read_text()
    assert "Visitor recovery trigger" in edge and "Visitor local entry restored: X=0.000 Y=-300.000 Z=-50.000" in edge
    edge_after = status_lines(edge)[-1]
    assert edge_after["grounded"] == 1 and edge_after["blocking_overlap"] == 0

    tabs = []
    for run in (primary, recovery):
        before = status_lines((run / "tab-overview-attempt1/new-log.txt").read_text())[0]
        overview = status_lines((run / "tab-overview-attempt1/new-log.txt").read_text())[-1]
        after = status_lines((run / "tab-return-attempt1/new-log.txt").read_text())[-1]
        assert before["pawn"] == overview["pawn"] == after["pawn"]
        assert before["position"] == overview["position"] == after["position"]
        assert before["rotation"] == overview["rotation"] == after["rotation"]
        assert overview["view"].startswith("CameraActor") and overview["mode"] == 0
        assert after["view"] == after["pawn"] and after["mode"] == 1
        tabs.append({"run": run.name, "before": before, "overview": overview, "after": after})

    final = root / "final-authority-attempt1"
    files = {str(p.relative_to(final)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(final.rglob("*")) if p.is_file()}
    comparisons = [primary / "final-preclose-attempt1/authority.json", primary / "postclose-authority.json",
                   recovery / "first-restored-tick2-attempt1/authority.json",
                   recovery / "final-preclose-attempt1/authority.json", recovery / "postclose-authority.json"]
    assert all(load(p)["files"] == files for p in comparisons)
    final_manifest = json.loads((final / "abstract_world.json").read_text())
    assert final_manifest["logical_tick"] == final_manifest["state_revision"] == 2
    assert set(final_manifest["commands"]) == {"causal-1", "causal-2"}

    sessions = []
    for run in (primary, recovery):
        assert int((run / "launcher.exit").read_text()) == 0
        log, launcher = (run / "ue.log").read_text(), (run / "status.log").read_text()
        assert "[launcher] build_exit_code=0" in launcher and "[launcher] ue_exit_code=0" in launcher
        assert "threaded_rendering=1" in log and "preflush=1" in log and "owner_unchanged=1" in log
        assert log.index("H1e preflush end") < log.rindex("being destroyed")
        assert "LogExit: Exiting" in log and not re.search(r"Assertion failed:|Ensure condition failed:|Fatal error:", log)
        assert "NumLightingUnbuiltObjects=0" in log and "Primitives with unbuilt interactions: 0" in log
        sessions.append({"run": run.name, "pid": load(run / "context.json")["pid"], "exit": 0})
    reused = load(root / "manual-mouse-reuse-attempt1.json")
    assert reused["config_and_canonical_input_path_diff"] == "none"
    for record in reused["selected_original_records"]:
        assert hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest() == record["sha256"]
    return {"readonly_pairs": readonly, "readonly_pair_count": len(readonly), "advances": advances,
            "free_moving_samples_in_hold": moving, "contacts": contacts, "edge_after": edge_after,
            "tab_roundtrips": tabs, "recovery_files": files, "sessions": sessions,
            "manual_mouse": "independently reviewed H6B physical case reused; no new H6C mouse action"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.raw)
    if args.output:
        with args.output.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print(json.dumps({"readonly_pairs": result["readonly_pair_count"], "advance_pairs": len(result["advances"]),
                      "moving_samples": len(result["free_moving_samples_in_hold"]), "sessions": result["sessions"]}))
