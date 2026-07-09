from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from live_cast import LiveCastEngine, LiveCastLayout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stream live hexagram frames as JSON lines.")
    parser.add_argument("--seed", type=int, default=20260620)
    parser.add_argument("--subject", type=str, default="swift-preview")
    parser.add_argument("--fps", type=int, default=100)
    parser.add_argument("--layout", choices=[layout.value for layout in LiveCastLayout], default="3d")
    return parser


def frame_to_payload(frame) -> dict:
    return {
        "seed": frame.seed,
        "subject": frame.subject,
        "dimension": frame.layout.value,
        "count": frame.count,
        "frame_index": frame.frame_index,
        "fps": frame.fps,
        "layout": frame.layout.value,
        "items": [
            {
                "index": item.index,
                "coord": list(item.coord),
                "primary_value": item.primary_value,
                "primary_name": item.primary_name,
                "changed_value": item.changed_value,
                "changed_name": item.changed_name,
                "changing_positions": list(item.changing_positions),
                "line_values_bottom_to_top": list(item.line_values_bottom_to_top),
            }
            for item in frame.items
        ],
    }


def main() -> int:
    args = build_parser().parse_args()
    engine = LiveCastEngine(seed=args.seed, subject=args.subject, fps=args.fps)
    layout = LiveCastLayout(args.layout)
    frame_delay = 1.0 / args.fps

    frame_index = 0
    while True:
        frame = engine.frame(frame_index, layout)
        sys.stdout.write(json.dumps(frame_to_payload(frame), ensure_ascii=False) + "\n")
        sys.stdout.flush()
        frame_index += 1
        time.sleep(frame_delay)


if __name__ == "__main__":
    raise SystemExit(main())
