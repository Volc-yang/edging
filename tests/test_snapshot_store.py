"""Tests for cross-process safe snapshot access (risk R4)."""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from snapshot_store import (
    SNAPSHOT_SCHEMA_VERSION,
    SnapshotError,
    SnapshotLockTimeout,
    lock_path,
    next_tick_from_snapshot,
    read_snapshot,
    snapshot_lock,
    write_snapshot_atomic,
)


def _snapshot(tick: int, **extra):
    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "tick": tick,
        "chapter": "first",
    }
    payload.update(extra)
    return payload


# One full round in a separate process: lock -> read -> compute -> write.
# The deliberate sleep widens the window that an unlocked implementation
# would race in.
ROUND_SCRIPT = textwrap.dedent(
    """
    import sys, time
    from pathlib import Path
    sys.path.insert(0, sys.argv[1])
    from snapshot_store import next_tick_from_snapshot, read_snapshot, snapshot_lock, write_snapshot_atomic

    target = Path(sys.argv[2])
    delay = float(sys.argv[3])
    with snapshot_lock(target):
        tick = next_tick_from_snapshot(target)
        time.sleep(delay)
        payload = read_snapshot(target) or {"schema_version": "edgeworld.chapter-one-snapshot.v2"}
        payload["tick"] = tick
        payload["written_by"] = sys.argv[4]
        write_snapshot_atomic(target, payload)
    print(tick)
    """
)


class SnapshotStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "chapter_one_snapshot.json"

    # ------------------------------------------------------------- basics
    def test_missing_snapshot_reads_as_none_and_starts_at_tick_one(self):
        self.assertIsNone(read_snapshot(self.path))
        self.assertEqual(1, next_tick_from_snapshot(self.path))

    def test_next_tick_follows_the_stored_tick(self):
        write_snapshot_atomic(self.path, _snapshot(7))
        self.assertEqual(8, next_tick_from_snapshot(self.path))

    def test_malformed_snapshot_raises_instead_of_resetting_time(self):
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(SnapshotError):
            next_tick_from_snapshot(self.path)

    def test_unsupported_schema_raises(self):
        write_snapshot_atomic(self.path, {"schema_version": "edgeworld.chapter-one-snapshot.v1", "tick": 3})
        with self.assertRaises(SnapshotError):
            next_tick_from_snapshot(self.path)

    def test_non_positive_or_non_integer_tick_raises(self):
        for bad_tick in (0, -1, "3", 3.0, None):
            with self.subTest(tick=bad_tick):
                write_snapshot_atomic(self.path, _snapshot(1) | {"tick": bad_tick})
                with self.assertRaises(SnapshotError):
                    next_tick_from_snapshot(self.path)

    def test_atomic_write_leaves_no_temporary_files_and_valid_content(self):
        write_snapshot_atomic(self.path, _snapshot(1))
        write_snapshot_atomic(self.path, _snapshot(2))

        leftovers = [p.name for p in self.path.parent.iterdir() if p.name.startswith("tmp")]
        self.assertEqual([], leftovers)
        self.assertEqual(2, json.loads(self.path.read_text(encoding="utf-8"))["tick"])

    # -------------------------------------------------------------- locking
    def test_lock_timeout_when_another_holder_never_releases(self):
        holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    f"""
                    import sys, time
                    sys.path.insert(0, {str(ENGINE_DIR)!r})
                    from snapshot_store import snapshot_lock
                    with snapshot_lock({str(self.path)!r}, timeout=5):
                        print("held", flush=True)
                        time.sleep(1.5)
                    """
                ),
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual("held", holder.stdout.readline().strip())
            with self.assertRaises(SnapshotLockTimeout):
                with snapshot_lock(self.path, timeout=0.2, poll=0.02):
                    self.fail("lock must not be granted while another process holds it")
        finally:
            holder.wait(timeout=10)
            holder.stdout.close()

    def test_lock_file_is_a_sidecar_and_is_reusable(self):
        with snapshot_lock(self.path, timeout=1):
            self.assertTrue(lock_path(self.path).exists())
        self.assertFalse(self.path.exists())
        # A second acquisition on the same sidecar must succeed.
        with snapshot_lock(self.path, timeout=1):
            pass

    def test_concurrent_rounds_advance_one_tick_each(self):
        """Four simultaneous frontends must produce four distinct rounds."""
        write_snapshot_atomic(self.path, _snapshot(1))

        workers = [
            subprocess.Popen(
                [sys.executable, "-c", ROUND_SCRIPT, str(ENGINE_DIR), str(self.path), "0.25", f"engine-{i}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for i in range(4)
        ]
        ticks = []
        for worker in workers:
            stdout, stderr = worker.communicate(timeout=60)
            self.assertEqual(0, worker.returncode, f"worker failed: {stderr}")
            ticks.append(int(stdout.strip()))

        # Every worker must have observed a different tick...
        self.assertEqual(sorted(ticks), [2, 3, 4, 5])
        # ...and the final snapshot must reflect all four rounds, not one.
        self.assertEqual(5, json.loads(self.path.read_text(encoding="utf-8"))["tick"])

    def test_unlocked_rounds_would_collide(self):
        """Guard for the regression itself: the race is real without the lock.

        This documents why the lock exists. It deliberately bypasses
        ``snapshot_lock`` and shows that four rounds collapse into one tick,
        which is exactly the defect the lock prevents.
        """
        write_snapshot_atomic(self.path, _snapshot(1))
        unlocked = textwrap.dedent(
            """
            import sys, time
            from pathlib import Path
            sys.path.insert(0, sys.argv[1])
            from snapshot_store import next_tick_from_snapshot, read_snapshot, write_snapshot_atomic

            target = Path(sys.argv[2])
            tick = next_tick_from_snapshot(target)
            time.sleep(float(sys.argv[3]))
            payload = read_snapshot(target) or {"schema_version": "edgeworld.chapter-one-snapshot.v2"}
            payload["tick"] = tick
            write_snapshot_atomic(target, payload)
            """
        )
        workers = [
            subprocess.Popen([sys.executable, "-c", unlocked, str(ENGINE_DIR), str(self.path), "0.25"])
            for _ in range(4)
        ]
        for worker in workers:
            worker.communicate(timeout=60)
        self.assertEqual(2, json.loads(self.path.read_text(encoding="utf-8"))["tick"])


if __name__ == "__main__":
    unittest.main()
