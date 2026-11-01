"""Seal H6C evidence using new outputs only, after independently checking it."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_evidence import verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exclusive(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.raw
    checked = verify(root)
    frozen = json.loads((root / "frozen-source-binary-sha256.json").read_text())
    for path, expected in frozen.items():
        source = Path(path)
        if "/Source/EdgeWorldHost/" in path:
            archived = root / "final-source-attempt1" / source.name
        elif "/Config/" in path:
            archived = root / "final-config-attempt1" / source.name
        elif "/Binaries/Mac/" in path:
            archived = root / "final-binary-attempt1" / source.name
        else:
            assert path == "scripts/launch_edgeworld_ue_mac.sh"
            archived = root / "final-launcher-attempt1.sh"
        assert sha(archived) == expected, path
    records = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or relative.parts[0] == "world-user-attempt1" or "__pycache__" in relative.parts:
            continue
        if path.name.startswith("sha256-index-"):
            continue
        records.append({"path": str(relative), "bytes": path.stat().st_size, "sha256": sha(path)})
    index_path = root / "sha256-index-attempt1.json"
    exclusive(index_path, {"root": str(root), "excluded": ["UserDir non-authority caches; final authority copied separately", "pycache", "index itself"],
                           "files": records})
    for record in records:
        assert sha(root / record["path"]) == record["sha256"]
    compact = {
        "base": "f674483db3eec1f8bb71ed00f9e626928ea5de25", "raw_root": str(root),
        "raw_index": str(index_path), "raw_index_sha256": sha(index_path),
        "raw_files": len(records), "raw_bytes": sum(x["bytes"] for x in records),
        "readonly_pairs": checked["readonly_pair_count"], "advances": checked["advances"],
        "sessions": checked["sessions"], "moving_samples_in_hold": len(checked["free_moving_samples_in_hold"]),
        "frozen_sources_binary": frozen, "recovery_files": checked["recovery_files"],
        "checks_sha256": sha(root / "checks-attempt2.json"),
        "manual_mouse_reuse_sha256": sha(root / "manual-mouse-reuse-attempt1.json"),
        "primary_full_head2_image": {"path": "primary-attempt1/full-head2-overview-attempt1/image.jpg",
                                     "sha256": sha(root / "primary-attempt1/full-head2-overview-attempt1/image.jpg")},
    }
    exclusive(args.output, compact)
    print(json.dumps({"files": len(records), "index_sha256": compact["raw_index_sha256"],
                      "readonly_pairs": compact["readonly_pairs"]}))
