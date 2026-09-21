#!/usr/bin/env python3
"""Generate the shared Chapter One snapshot for both engine frontends."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

from chapter_one_runtime import ChapterOneRuntime, OllamaDecisionClient


def next_tick_from_snapshot(path: Path) -> int:
    """Return the next world tick without weakening snapshot validation."""
    if not path.exists():
        return 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot advance from invalid snapshot: {exc}") from exc
    if payload.get("schema_version") != "edgeworld.chapter-one-snapshot.v2":
        raise ValueError("cannot advance from an unsupported snapshot schema")
    current_tick = payload.get("tick")
    if type(current_tick) is not int or current_tick < 1:
        raise ValueError("cannot advance from a snapshot without a positive tick")
    return current_tick + 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Edge World Chapter One through its rule-gated AI loop.")
    parser.add_argument("--seed", type=int, default=20260920)
    tick_mode = parser.add_mutually_exclusive_group()
    tick_mode.add_argument("--tick", type=int, default=1, help="Run a specific replayable world tick.")
    tick_mode.add_argument("--advance", action="store_true", help="Advance one tick from the existing output snapshot.")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "llama3.2:latest"))
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--player-action", choices=("ascend", "receive", "flow", "illuminate", "awaken", "adapt", "stabilize", "exchange"), default="awaken")
    parser.add_argument("--player-intensity", type=float, default=0.7)
    parser.add_argument("--player-expression", default="玩家进入世界并尝试唤醒眼前之物。")
    parser.add_argument("--offline", action="store_true", help="Use the deterministic rule fallback without contacting Ollama.")
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "chapter_one_snapshot.json")
    args = parser.parse_args()

    try:
        tick = next_tick_from_snapshot(args.output) if args.advance else args.tick
    except ValueError as exc:
        parser.error(str(exc))
    client = None if args.offline else OllamaDecisionClient(args.model, args.ollama_url, args.timeout)
    snapshot = ChapterOneRuntime(seed=args.seed, client=client).write_snapshot(
        args.output,
        tick=tick,
        player_action=args.player_action,
        player_intensity=args.player_intensity,
        player_expression=args.player_expression,
    )
    summary = {
        "output": str(args.output.resolve()),
        "tick": snapshot["tick"],
        "decision_source": snapshot["decision"]["source"],
        "model": snapshot["decision"]["model"],
        "chapter_score": snapshot["validation"]["score"],
        "cycle_completed": snapshot["cycle"]["completed"],
        "final_integrity": snapshot["cycle"]["final_integrity"],
        "encounter": snapshot["encounter"]["primary_hexagram"]["name"],
        "changed_hexagram": snapshot["encounter"]["changed_hexagram"]["name"],
        "presentation_source": snapshot["presentation"]["source"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
