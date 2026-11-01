import hashlib
import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1]).resolve()
summary = json.loads((root / "live-checks-final-attempt1.json").read_text())
assert summary["manual_mouse"]["allAuthorityFilesUnchanged"]
assert summary["recovery_close"]["ueExitCode"] == 0
binary = root / "final-provenance-attempt1/binary/libUnrealEditor-EdgeWorldHost.dylib"
assert hashlib.sha256(binary.read_bytes()).hexdigest() == "caaeae2ae465cf3e5866221210bed99296d19fd3946aa65b6b506fa145074aa8"
records = []
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(root)
    if any(part in ("primary-user", "live-user-attempt1", "user") for part in relative.parts) and "EdgeWorldCausal" not in relative.parts:
        continue
    if path.name.startswith("final-sha256-index-"):
        continue
    records.append({"path": str(relative), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
index = {"root": str(root), "scope": "H6B owner evidence; independent H6C acceptance remains downstream", "readonly_pairs": len(summary["readonly_pairs"]), "explicit_space_pairs": len(summary["explicit_space_pairs"]), "manual_mouse": "physical confirmation plus changed image/control rotation and identical position/authority; no per-axis physical-event trace", "files": records}
output = root / "final-sha256-index-attempt1.json"
with output.open("x") as stream:
    json.dump(index, stream, indent=2)
    stream.write("\n")
for record in records:
    path = root / record["path"]
    assert path.stat().st_size == record["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
print(json.dumps({"index": str(output), "files": len(records), "bytes": sum(record["bytes"] for record in records), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
