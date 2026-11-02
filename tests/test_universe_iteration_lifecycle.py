"""CPU replay of owned lifecycles; never launches UE, solver, UI or a child."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts.universe_iteration import lifecycle as lc


class Replay:
    def __init__(self, root):
        self.root = root
        self.executable = str(root / 'UnrealEditor')
        self.run = dict(run_id='i13-replay', source_sha='a' * 40,
                        world_id='i13-world', authority_root=str(root / 'authority'))
        self.launchers, self.bindings, self.processes = [], {}, []
        self.epoch = datetime(2026, 11, 2, tzinfo=timezone.utc)
        self.ledger = dict(format=lc.FORMAT, run_binding=self.run,
                           clock=dict(id='replay-clock', anchor_monotonic=0, anchor_utc=self.utc(0)),
                           dispatch_monotonic=0, end_monotonic=16, limit_seconds=1200,
                           max_observer_gap_seconds=2, samples=[], sessions=[], processes=[],
                           seal=dict(started_monotonic=14, ended_monotonic=16,
                                     observer_ended_monotonic=15, storage_bytes=0,
                                     storage_limit_bytes=lc.MAX_BYTES))
        for index, name in enumerate(('initialize', 'existing')):
            base = 8 * index
            launcher = dict(pid=100 + index * 10, ppid=90, start='Mon Nov 2 00:00:%02d 2026' % base,
                            argv='/bin/bash launcher.sh')
            host = dict(pid=launcher['pid'] + 1, ppid=launcher['pid'], start=launcher['start'],
                        argv=self.executable + ' -game')
            worker = dict(pid=launcher['pid'] + 2, ppid=host['pid'], start=launcher['start'],
                          argv='/approved/python worker.py')
            self.launchers.append(launcher)
            binding = dict(self.run, session=name, host_pid=host['pid'], worker_pid=worker['pid'], generation=1)
            self.bindings[name] = binding
            for row, first in ((launcher, base + .5), (host, base + 1.5), (worker, base + 1.5)):
                wait = self.write('wait-%d.json' % row['pid'], dict(kind='actual-parent-wait',
                                  observed=True, identity=row, parent_pid=row['ppid'], exit_code=0,
                                  monotonic=base + 5))
                self.processes.append((row, first, base + 4.5))
                self.ledger['processes'].append(dict(identity=row, ownership='owned',
                    first_seen_monotonic=first, last_seen_monotonic=base + 4.5,
                    start_lower_bound=first - .5, end_upper_bound=base + 5,
                    boundary_source='parent-wait', wait_ref=wait))
            stages, start = [], base
            for kind, duration in [('build', 1), ('startup', 1), ('interaction', 2), ('shutdown', 1), ('seal', 1)]:
                stages.append(dict(stage=kind, start_monotonic=start, end_monotonic=start + duration,
                                   deadline_monotonic=start + lc.STAGES[kind]))
                start += duration
            completion = dict(card_sha256='c' * 64, normal=True, forced_cleanup=[], remaining_owned=[],
                              accepted_source=self.run['source_sha'], run_id=self.run['run_id'],
                              world_id=self.run['world_id'], authority_root=self.run['authority_root'],
                              session=name, ue_pid=host['pid'], launcher_wait_exit=0, ue_exit_code=0,
                              worker_exits=[dict(worker_pid=worker['pid'], generation=1, exit_code=0,
                              reaped=True, return_code_available=True, trace_complete=True,
                              stop_kind='normal', hard_kill_sent=False, operational_failure=False)])
            self.ledger['sessions'].append(dict(session=name, start_monotonic=base,
                end_monotonic=base + 6, binding=binding, stages=stages,
                completion_ref=self.write('completion-' + name + '.json', completion)))
        for i in range(31):
            instant = i / 2
            rows = [row for row, first, last in self.processes if first <= instant <= last]
            raw = ''.join('%d %d %s %s\n' % (r['pid'], r['ppid'], r['start'], r['argv']) for r in rows).encode()
            ref = lc.exclusive_bytes(root / ('sample-%02d.ps' % i), raw)
            self.ledger['samples'].append(dict(monotonic=instant, utc=self.utc(instant),
                                               processes=rows, raw_ref=ref))
        self.refresh_storage()

    def utc(self, seconds):
        return (self.epoch + timedelta(seconds=seconds)).isoformat()

    def write(self, name, value):
        return lc.exclusive_bytes(self.root / name, json.dumps(value, sort_keys=True).encode())

    def refresh_storage(self):
        path = self.root / 'storage.json'
        # Fixture snapshot includes its own final byte size; no runtime claims.
        size = 0
        for _ in range(20):
            files = [dict(path=str(p), bytes=p.stat().st_size) for p in sorted(self.root.iterdir())
                     if p != path and p.is_file()]
            files.append(dict(path=str(path), bytes=size))
            data = json.dumps(dict(kind='whole-storage', includes_all_attempts=True,
                                  storage_root=str(self.root), monotonic=16, files=files), sort_keys=True).encode()
            if len(data) == size:
                break
            size = len(data)
        path.write_bytes(data)
        self.ledger['seal']['storage_snapshot_ref'] = dict(path=str(path), sha256=hashlib.sha256(data).hexdigest())
        self.ledger['seal']['storage_bytes'] = sum(p.stat().st_size for p in self.root.iterdir() if p.is_file())

    def verify(self, ledger=None):
        return lc.validate_ledger(self.ledger if ledger is None else ledger,
            expected_run_binding=self.run, expected_clock_id='replay-clock',
            expected_executable=self.executable, expected_launchers=self.launchers,
            expected_session_bindings=self.bindings, expected_storage_root=str(self.root),
            expected_public_paths=[str(path) for path in self.root.iterdir() if path.is_file()])


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_identity_reparent_matches_but_pid_reuse_does_not(self):
        row = dict(pid=4, ppid=3, start='Mon Nov 2 00:00:00 2026', argv='/UE -game')
        self.assertTrue(lc.same_process(row, dict(row, ppid=1)))
        self.assertFalse(lc.same_process(row, dict(row, start='Mon Nov 2 00:00:01 2026')))
        self.assertFalse(lc.same_process(row, dict(row, argv='/UE')))
        with self.assertRaises(lc.Invalid):
            lc.process_key(dict(row, pid=True))

    def test_union_counts_overlap_once_and_keeps_nonoverlap(self):
        self.assertEqual(lc.interval_union_seconds([(0, 5), (2, 9), (20, 25)]), 14)
        for bad in [[(1, 0)], [(0, float('inf'))], [(False, 2)]]:
            with self.assertRaises(lc.Invalid):
                lc.interval_union_seconds(bad)

    def test_ps_preserves_spaced_argv_and_rejects_malformed_or_duplicate(self):
        raw = '  4 1 Mon Nov 2 00:00:00 2026 /Shared Epic/UnrealEditor -game\n'
        self.assertEqual(lc.parse_ps_snapshot(raw)[0]['argv'], '/Shared Epic/UnrealEditor -game')
        for text in [raw + raw, '4 1 bad\n']:
            with self.assertRaises(lc.Invalid):
                lc.parse_ps_snapshot(text)

    def test_orphan_same_bundle_is_contamination_not_owned(self):
        root = dict(pid=4, ppid=1, start='Mon Nov 2 00:00:00 2026', argv='/launcher')
        ue = dict(pid=5, ppid=4, start=root['start'], argv=str(self.root / 'UE') + ' -game')
        extra = dict(ue, pid=6, ppid=1)
        rows = lc.classify_processes([root, ue, extra], [root], str(self.root / 'UE'))
        self.assertEqual([r['ownership'] for r in rows], ['owned', 'owned', 'contamination'])
        rows = lc.classify_processes([dict(ue, ppid=1)], [ue], str(self.root / 'UE'))
        self.assertEqual(rows[0]['ownership'], 'owned')

    def test_exclusive_public_evidence_refuses_overwrite_symlink_and_tamper(self):
        ref = lc.exclusive_bytes(self.root / 'raw', b'first')
        with self.assertRaises(FileExistsError):
            lc.exclusive_bytes(self.root / 'raw', b'overwrite')
        (self.root / 'link').symlink_to(self.root / 'raw')
        with self.assertRaises(lc.Invalid):
            lc.exclusive_bytes(self.root / 'link', b'overwrite')
        (self.root / 'raw').write_bytes(b'other')
        with self.assertRaises(lc.Invalid):
            lc.read_ref(ref)

    def guard(self, **updates):
        run = dict(run_id='run', world_id='world', source_sha='a' * 40, authority_root=str(self.root / 'authority'))
        binding = dict(run, session='initialize', host_pid=4, worker_pid=5, generation=1)
        rows = [dict(pid=pid, ppid=1, start='Mon Nov 2 00:00:00 2026', argv='/p%d' % pid) for pid in (4, 5)]
        args = dict(now=130, dispatch=0, session_start=0, stage='interaction', stage_start=120,
                    ready_binding=binding, expected_binding=binding, live_processes=rows,
                    expected_processes=rows, tool_seconds=1, sample_monotonic=130)
        args.update(updates)
        if 'sample_monotonic' not in updates:
            args['sample_monotonic'] = args['now']
        return lc.budget_guard(**args)

    def test_guard_reserves_quit_and_does_not_treat_missing_process_as_live(self):
        self.assertEqual(self.guard()['decision'], 'allow')
        for updates in [dict(now=359, tool_seconds=1), dict(now=360), dict(tool_seconds=11)]:
            self.assertEqual(self.guard(**updates)['decision'], 'quit_due')
        for updates in [dict(live_processes=[]), dict(sample_monotonic=127), dict(contamination=True), dict(closing=True),
                        dict(stage='seal', stage_start=125), dict(now=400)]:
            self.assertEqual(self.guard(**updates)['decision'], 'stop')
        self.assertEqual(self.guard(stage='startup', stage_start=120, ready_binding=None)['decision'], 'stop')

    def test_guard_enforces_early_stage_and_global_deadlines(self):
        self.assertEqual(self.guard(now=150, stage_start=0)['decision'], 'allow')
        self.assertEqual(self.guard(now=239, stage_start=0)['decision'], 'quit_due')
        self.assertEqual(self.guard(global_limit=190)['decision'], 'quit_due')
        with self.assertRaises(lc.Invalid):
            self.guard(now=float('nan'))

    def test_observer_uses_only_fixed_ps_and_keeps_final_sample(self):
        event = threading.Event()
        captured = []
        raw = b'4 1 Mon Nov 2 00:00:00 2026 /fixed\n'
        def callback(value):
            captured.append(value)
            event.set()
        completed = type('Completed', (), {'stdout': raw})()
        with patch.object(lc.subprocess, 'run', return_value=completed) as run:
            values = lc.record_observer(event, self.root, on_sample=callback)
        self.assertEqual(len(values), 2)
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertEqual(call.args, (lc.PS_ARGV,))
            self.assertEqual(call.kwargs['timeout'], 1)
        self.assertEqual(lc.read_ref(values[-1]['raw_ref']), raw)

    def test_complete_two_session_replay_requires_independent_review(self):
        replay = Replay(self.root)
        result = replay.verify()
        self.assertEqual(result['status'], 'checks_complete_requires_review', result)
        self.assertEqual(result['wall_seconds'], 16)
        self.assertEqual(result['process_union_seconds'], 10)

    def test_ledger_rejects_source_clock_raw_and_stage_contradictions(self):
        replay = Replay(self.root)
        variants = []
        value = copy.deepcopy(replay.ledger); value['clock']['id'] = 'foreign'; variants.append(value)
        value = copy.deepcopy(replay.ledger); value['run_binding']['source_sha'] = 'b' * 40; variants.append(value)
        value = copy.deepcopy(replay.ledger); value['samples'][1]['processes'] = []; variants.append(value)
        value = copy.deepcopy(replay.ledger); value['sessions'][0]['stages'][2]['deadline_monotonic'] = 500; variants.append(value)
        value = copy.deepcopy(replay.ledger); value['processes'][0]['start_lower_bound'] = .5; variants.append(value)
        value = copy.deepcopy(replay.ledger); value['processes'].pop(); variants.append(value)
        value = copy.deepcopy(replay.ledger); value['seal']['storage_bytes'] -= 1; variants.append(value)
        for value in variants:
            with self.subTest(value=value):
                self.assertEqual(replay.verify(value)['status'], 'fail')

    def test_sample_gap_and_missing_wait_or_second_session_cannot_pass(self):
        replay = Replay(self.root)
        for edit in ('gap', 'wait', 'session'):
            value = copy.deepcopy(replay.ledger)
            if edit == 'gap':
                del value['samples'][4:9]
            elif edit == 'wait':
                value['processes'][0]['wait_ref'] = None
            else:
                value['sessions'].pop()
            result = replay.verify(value)
            self.assertNotEqual(result['status'], 'checks_complete_requires_review', result)

    def test_resource_wall_cannot_be_replaced_by_small_process_union(self):
        replay = Replay(self.root)
        value = copy.deepcopy(replay.ledger)
        value['end_monotonic'] = value['seal']['ended_monotonic'] = 1201
        self.assertEqual(replay.verify(value)['status'], 'fail')
        value = copy.deepcopy(replay.ledger)
        value['max_observer_gap_seconds'] = 3
        self.assertEqual(replay.verify(value)['status'], 'fail')

    def test_private_reference_is_rejected_before_file_read(self):
        replay = Replay(self.root)
        value = copy.deepcopy(replay.ledger)
        value['samples'][0]['raw_ref'] = dict(path=str(self.root.parent / 'private-key'), sha256='0' * 64)
        with patch.object(lc, 'read_ref', side_effect=AssertionError('must not open private input')):
            self.assertEqual(replay.verify(value)['status'], 'fail')

    def test_extra_storage_file_is_not_hidden_by_inventory_boolean(self):
        replay = Replay(self.root)
        (self.root / 'omitted.bin').write_bytes(b'unlisted')
        self.assertEqual(replay.verify()['status'], 'fail')

    def test_normal_false_unknown_exit_and_forced_cleanup_cannot_pass(self):
        replay = Replay(self.root)
        original = lc.json_ref(replay.ledger['sessions'][0]['completion_ref'])
        for index, change in enumerate([dict(normal=False), dict(ue_exit_code=None),
                                        dict(forced_cleanup=[dict(pid=101, signal='TERM')])]):
            value = copy.deepcopy(replay.ledger)
            value['sessions'][0]['completion_ref'] = replay.write('bad-completion-%d.json' % index,
                                                                  dict(original, **change))
            self.assertEqual(replay.verify(value)['status'], 'fail')

    def test_detached_selector_cannot_be_omitted_after_supervisor_exit(self):
        replay = Replay(self.root)
        value = copy.deepcopy(replay.ledger)
        extra = dict(pid=999, ppid=1, start='Mon Nov 2 00:00:14 2026', argv=replay.executable)
        sample = value['samples'][-2]
        sample['processes'] = [extra]
        sample['raw_ref'] = lc.exclusive_bytes(self.root / 'extra.ps',
                                              ('999 1 ' + extra['start'] + ' ' + extra['argv'] + '\n').encode())
        self.assertEqual(replay.verify(value)['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
