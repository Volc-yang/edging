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
from snapshot_store import SnapshotError, SnapshotLockTimeout, next_tick_from_snapshot, snapshot_lock

#: Waiting for another frontend must outlast its own model call before giving up.
LOCK_TIMEOUT_SLACK_SECONDS = 60.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Edge World Chapter One through its rule-gated AI loop.")
    parser.add_argument("--seed", type=int, default=20260920)
    tick_mode = parser.add_mutually_exclusive_group()
    tick_mode.add_argument("--tick", type=int, default=1, help="Run a specific replayable world tick.")
    tick_mode.add_argument("--advance", action="store_true", help="Advance one tick from the existing output snapshot.")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "llama3.2:latest"))
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--lock-timeout",
        type=float,
        default=None,
        help="Seconds to wait for another frontend's round to finish "
        "(default: --timeout plus 60s).",
    )
    parser.add_argument("--player-action", choices=("ascend", "receive", "flow", "illuminate", "awaken", "adapt", "stabilize", "exchange"), default="awaken")
    parser.add_argument("--player-intensity", type=float, default=0.7)
    parser.add_argument("--player-expression", default="玩家进入世界并尝试唤醒眼前之物。")
    parser.add_argument("--offline", action="store_true", help="Use the deterministic rule fallback without contacting Ollama.")
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "chapter_one_snapshot.json")
    args = parser.parse_args()

    lock_timeout = args.lock_timeout
    if lock_timeout is None:
        lock_timeout = max(args.timeout, 0.0) + LOCK_TIMEOUT_SLACK_SECONDS

    client = None if args.offline else OllamaDecisionClient(args.model, args.ollama_url, args.timeout)
    runtime = ChapterOneRuntime(seed=args.seed, client=client)

    # The lock covers the whole read-modify-write cycle, so two frontends that
    # submit at the same moment advance the world one round each instead of
    # both writing the same tick.
    try:
        with snapshot_lock(args.output, timeout=lock_timeout):
            tick = next_tick_from_snapshot(args.output) if args.advance else args.tick
            snapshot = runtime.write_snapshot(
                args.output,
                tick=tick,
                player_action=args.player_action,
                player_intensity=args.player_intensity,
                player_expression=args.player_expression,
            )
    except SnapshotLockTimeout as exc:
        print(json.dumps({"error": "snapshot_lock_timeout", "detail": str(exc)}, ensure_ascii=False))
        return 75  # EX_TEMPFAIL: safe to retry
    except SnapshotError as exc:
        parser.error(str(exc))

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
