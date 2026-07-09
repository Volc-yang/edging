from __future__ import annotations

import argparse
import time
from pathlib import Path
import sys

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from live_cast import LiveCastEngine, LiveCastLayout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a live hexagram casting demo at a fixed frame rate.")
    parser.add_argument("--seed", type=int, default=20260620, help="Deterministic seed.")
    parser.add_argument("--subject", type=str, default="live-demo", help="Deterministic subject string.")
    parser.add_argument("--fps", type=int, default=100, help="Logical refresh rate.")
    parser.add_argument("--layout", choices=[item.value for item in LiveCastLayout], default="3d", help="Layout to stream.")
    parser.add_argument("--frames", type=int, default=10, help="How many frames to emit.")
    parser.add_argument("--sleep", action="store_true", help="Sleep between frames to approximate real-time playback.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    engine = LiveCastEngine(seed=args.seed, subject=args.subject, fps=args.fps)
    layout = LiveCastLayout(args.layout)

    frame_duration = 1.0 / args.fps
    for frame in engine.stream(layout, frames=args.frames):
        first = frame.items[0]
        print(
            f"frame={frame.frame_index:04d} layout={frame.layout.value} "
            f"count={frame.count} first={first.primary_name}->{first.changed_name} "
            f"changes={list(first.changing_positions)}"
        )
        if args.sleep:
            time.sleep(frame_duration)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
