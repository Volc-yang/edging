import hashlib
import json
import pathlib
import re
import sys


root = pathlib.Path(sys.argv[1]).resolve()
repo = pathlib.Path(__file__).resolve().parents[3]
final_log = root / "nullrhi-bchkcP9v/ue.log"
text = final_log.read_text()
assert text.count("Test Completed. Result={Success}") == 2
assert not any(token in text for token in ("Error:", "Ensure condition failed", "Assertion failed"))
report = json.loads((root / "nullrhi-bchkcP9v/report/index.json").read_text(encoding="utf-8-sig"))
assert report["failed"] == 0 and report["notRun"] == 0
assert report["succeeded"] + report["succeededWithWarnings"] == 2
before = json.loads((root / "primary/locked-before-attempt1.json").read_text())
after = json.loads((root / "primary/locked-after-attempt1.json").read_text())
assert before["files"] == after["files"]
frames = re.findall(r"Visitor status frame=(\d+).*?position=X=([\d.]+) Y=-300.000.*?velocity=X=([\d.]+)", text)
assert len({frame for frame, position, velocity in frames if float(velocity) > 0}) >= 3
paths = []
for path in root.rglob("*"):
    if not path.is_file():
        continue
    relative = path.relative_to(root)
    if "primary-user" in relative.parts or "user" in relative.parts:
        if "EdgeWorldCausal" not in relative.parts:
            continue
    if path.name.startswith("partial-sha256-index-"):
        continue
    paths.append(path)
source = repo / "engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost"
paths.extend(source.glob("EdgeWorldVisitorCharacter*"))
paths.extend(source.glob("EdgeWorldCausalGameMode.*"))
paths.append(source / "EdgeWorldCausalHud.cpp")
paths.append(repo / "engine_platforms/unreal/EdgeWorldHost/Binaries/Mac/libUnrealEditor-EdgeWorldHost.dylib")
index = {
    "status": "partial; UI/Metal gates pending Mac unlock",
    "automation": {"success": report["succeeded"], "success_with_warnings": report["succeededWithWarnings"], "failed": report["failed"]},
    "idle_authority_unchanged": True,
    "files": [{"path": str(path), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(set(paths))],
}
output = root / (sys.argv[2] if len(sys.argv) > 2 else "partial-sha256-index-attempt1.json")
with output.open("x") as stream:
    json.dump(index, stream, indent=2)
    stream.write("\n")
print(json.dumps({"index": str(output), "files": len(index["files"]), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
