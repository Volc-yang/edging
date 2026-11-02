"""I14 CPU-only controller/backend tests. Never UE, solver, build or UI."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scripts.universe_iteration import dispatch as d, lifecycle as lc
from tests.test_universe_iteration_lifecycle import Replay


class V2Replay(Replay):
    def write(self, name, value):
        if isinstance(value, bytes):
            return lc.exclusive_bytes(self.root / name, value)
        return super().write(name, value)

    def __init__(self, root):
        super().__init__(root)
        self.launcher_ref = self.write('launcher-source.sh', b'build_rc=${PIPESTATUS[0]}\n')
        self.policy = dict(format=lc.POLICY_V2, run_binding=self.run, clock_id='replay-clock',
            accepted_executable=self.executable, worker_executable='/approved/python',
            launcher_identities=self.launchers, launcher_source_ref=self.launcher_ref,
            session_bindings=self.bindings, storage_root=str(root), public_paths=[],
            global_limit_seconds=1200, storage_limit_bytes=lc.MAX_BYTES, observer_max_gap_seconds=2,
            sessions=deepcopy(lc.SESSION_LIMITS_V2))
        self.ledger.update(format=lc.FORMAT_V2, actual_observed_end_monotonic=16,
                           charged_end_monotonic=18, end_monotonic=18)
        for session in self.ledger['sessions']:
            for stage in session['stages']:
                stage['deadline_monotonic'] = stage['start_monotonic'] + lc.SESSION_LIMITS_V2[session['session']]['stage_seconds'][stage['stage']]
        for process in self.ledger['processes']:
            pid = process['identity']['pid']
            name = 'initialize' if pid < 110 else 'existing'
            kind = {0: 'launcher', 1: 'ue', 2: 'worker'}[pid % 10]
            process.update(role='runtime_core', core_kind=kind, session=name,
                           exit_status=0, build_parent_ref=None)
        self.refresh_storage()

    def verify_v2(self, value=None, actual=16.2):
        self.policy['public_paths'] = [str(p) for p in self.root.iterdir() if p.is_file()]
        return lc.validate_ledger_v2(self.ledger if value is None else value,
                                    expected_policy=self.policy, actual_finalized_monotonic=actual)

    def add_unknown_build(self):
        row = dict(pid=777, ppid=100, start=self.launchers[0]['start'], argv='/official/compiler --compile')
        sample = self.ledger['samples'][1]
        sample['processes'] = [*sample['processes'], row]
        raw = ''.join('%d %d %s %s\n' % (r['pid'], r['ppid'], r['start'], r['argv']) for r in sample['processes']).encode()
        sample['raw_ref'] = lc.exclusive_bytes(self.root / 'with-build.ps', raw)
        stdout = self.write('build-stdout.txt', b'[launcher] build_started\n[launcher] build_exit_code=0\n')
        raw_stdout = lc.read_ref(stdout)
        wrapper = self.write('build-parent.json', dict(format='universe-i14-build-parent.v1',
            launcher_identity=self.launchers[0], session='initialize', stdout_ref=stdout,
            line_start=raw_stdout.index(b'[launcher] build_exit_code=0'), line_end=len(raw_stdout),
            build_start_monotonic=0, build_end_monotonic=1, launcher_source_ref=self.launcher_ref))
        self.ledger['processes'].append(dict(identity=row, ownership='owned', role='build_descendant',
            first_seen_monotonic=.5, last_seen_monotonic=.5, start_lower_bound=0, end_upper_bound=1,
            boundary_source='observer-bracket', wait_ref=None, exit_status=None, build_parent_ref=wrapper))
        self.refresh_storage()


class V2LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_v2_core_actual_wait_complete_and_charged_end_is_not_exact_snapshot(self):
        replay = V2Replay(self.root)
        result = replay.verify_v2()
        self.assertEqual(result['status'], 'checks_complete_requires_review', result)
        self.assertEqual(result['wall_seconds'], 18)
        self.assertEqual(replay.verify_v2(actual=None)['status'], 'inconclusive')
        self.assertEqual(replay.verify_v2(actual=19)['status'], 'fail')

    def test_unknown_build_exit_keeps_null_without_downgrading_core(self):
        replay = V2Replay(self.root)
        replay.add_unknown_build()
        result = replay.verify_v2()
        self.assertEqual(result['status'], 'checks_complete_requires_review', result)
        for edit in ('core', 'invent_exit', 'no_parent'):
            value = deepcopy(replay.ledger)
            if edit == 'core':
                value['processes'][0]['role'] = 'build_descendant'
            elif edit == 'invent_exit':
                value['processes'][-1]['exit_status'] = 0
            else:
                value['processes'][-1]['build_parent_ref'] = None
            self.assertNotEqual(replay.verify_v2(value)['status'], 'checks_complete_requires_review')

    def test_core_missing_wait_nonzero_or_bad_parent_fails(self):
        replay = V2Replay(self.root)
        for edit in ('missing', 'exit', 'parent'):
            value = deepcopy(replay.ledger)
            if edit == 'missing':
                value['processes'][1]['wait_ref'] = None
            elif edit == 'exit':
                value['processes'][1]['exit_status'] = None
            else:
                old = lc.json_ref(value['processes'][1]['wait_ref'])
                old['parent_pid'] = 999
                value['processes'][1]['wait_ref'] = replay.write('wrong-parent.json', old)
            self.assertNotEqual(replay.verify_v2(value)['status'], 'checks_complete_requires_review')
        value = deepcopy(replay.ledger)
        sample = value['samples'][4]
        row = next(r for r in sample['processes'] if r['pid']==101)
        altered = dict(row,start='Mon Nov 2 00:00:01 2026')
        sample['processes']=[altered if r['pid']==101 else r for r in sample['processes']]
        raw=''.join('%d %d %s %s\n'%(r['pid'],r['ppid'],r['start'],r['argv']) for r in sample['processes']).encode()
        sample['raw_ref']=lc.exclusive_bytes(self.root/'pid-reuse.ps',raw)
        duplicate=deepcopy(value['processes'][1]);duplicate.update(identity=altered,first_seen_monotonic=2,
            last_seen_monotonic=2,start_lower_bound=1.5,end_upper_bound=2.5)
        wait=lc.json_ref(duplicate['wait_ref']);wait.update(identity=altered,monotonic=2.25)
        duplicate['wait_ref']=replay.write('pid-reuse-wait.json',wait)
        value['processes'].append(duplicate)
        result=replay.verify_v2(value)
        self.assertEqual(result['status'],'fail')
        self.assertIn('multiple startup identities',result['reasons'][0])

    def test_build_ancestry_and_independent_launcher_source_pin_cannot_be_faked(self):
        replay = V2Replay(self.root)
        replay.add_unknown_build()
        value = deepcopy(replay.ledger)
        wrapper = lc.json_ref(value['processes'][-1]['build_parent_ref'])
        wrapper['launcher_source_ref'] = replay.write('other-launcher.sh', b'build_rc=${PIPESTATUS[0]}\n# fake')
        value['processes'][-1]['build_parent_ref'] = replay.write('fake-parent.json', wrapper)
        self.assertEqual(replay.verify_v2(value)['status'], 'fail')
        value = deepcopy(replay.ledger)
        value['processes'][-1]['first_seen_monotonic'] = 8.5
        self.assertEqual(replay.verify_v2(value)['status'], 'fail')

    def test_v2_policy_gap_global_storage_and_omission_rejected(self):
        replay = V2Replay(self.root)
        for kind in ('wall', 'gap', 'stage', 'omit', 'tail'):
            value = deepcopy(replay.ledger)
            if kind == 'wall':
                value['charged_end_monotonic'] = value['end_monotonic'] = 1201
            elif kind == 'gap':
                del value['samples'][4:9]
            elif kind == 'stage':
                value['sessions'][0]['stages'][2]['deadline_monotonic'] = 500
            elif kind == 'tail':
                value['actual_observed_end_monotonic'] = 17.5
            else:
                value['processes'].pop()
            self.assertNotEqual(replay.verify_v2(value)['status'], 'checks_complete_requires_review')
        (self.root / 'omitted-bytes').write_bytes(b'not inventoried')
        self.assertEqual(replay.verify_v2()['status'], 'fail')


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        runner = Path(d.__file__).resolve().parents[1] / 'run_universe_slice_acceptance.py'
        self.backend = d.LegacyBackend(expected_runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest())
        self.now = 100.
        self.card = dict(run_binding=dict(run_id='i14', world_id='world', source_sha='a' * 40,
                                          authority_root=str(self.root / 'authority')),
                         controller_output=str(self.root / 'controller'), accepted_executable=str(self.root / 'UE'),
                         worker_executable=sys.executable, sessions=deepcopy(lc.SESSION_LIMITS_V2),
                         legacy_card_ref=dict(path=str(self.root / 'old-card'), sha256='b' * 64),
                         launcher_source_ref=dict(path=str(self.root / 'launcher'), sha256='c' * 64),
                         trust_anchor='d' * 64, storage_root=str(self.root), diagnostics_enabled=True)
        manifest = {'items': [dict(action_id='camera', session='initialize')]}
        # Trusted test-only issuance, explicitly bypasses production card validation.
        self.validated = d.ValidatedCard(self.card, manifest, d._CARD_SEAL)

    def controller(self):
        return d.DispatchController(self.validated, backend=self.backend, clock=lambda: self.now)

    def test_unvalidated_card_or_missing_backend_cannot_execute(self):
        with self.assertRaises(lc.Invalid):
            d.DispatchController(self.card, backend=self.backend)
        with self.assertRaises(lc.Invalid):
            d.DispatchController(self.validated, backend=None)
        controller = self.controller()
        with self.assertRaises(lc.Invalid):
            controller.begin_session('initialize')

    def test_outer_card_hash_source_expiry_execute_and_review_are_checked(self):
        def ref(name, value):
            path = self.root / name
            path.write_text(json.dumps(value))
            path.chmod(0o600)
            return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        manifest = ref('manifest.json', dict(format='universe-i14-actions.v1', request_counts={'initialize':20,'existing':5},
                       items=[dict(action_id='camera',session='initialize',phase='interaction',max_seconds=1)]))
        raw = ref('raw-review.json', dict(synthetic=True))
        review = ref('review.json', dict(format='universe-i14-runtime-review.v1',
                     product_source_sha='a'*40, tool_source_sha='a'*40, decision='ready',
                     owner='synthetic-owner', reviewer='synthetic-reviewer', evidence_refs=[raw]))
        card = dict(self.card, format=d.CARD_FORMAT, issuer='root', approved=True, execute=True,
                    tool_source_sha='a'*40, runner_sha256=self.backend.source_sha256,
                    manifest_ref=manifest, runtime_review_ref=review,
                    global_limit_seconds=1200, storage_limit_bytes=lc.MAX_BYTES,
                    issued_at=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),
                    expires_at=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat())
        arguments = dict(expected_product_source='a'*40, expected_tool_source='a'*40,
                         expected_manifest_sha256=manifest['sha256'], backend=self.backend, execute=True)
        for index, edit in enumerate(({}, {'execute':False}, {'tool_source_sha':'b'*40},
                    {'expires_at':'2000-01-01T00:00:00+00:00'}, {'format':'universe-i12-r12.v1'})):
            file_ref = ref('outer-%d.json'%index, dict(card, **edit))
            with patch.object(self.backend.runner, 'product_identity', return_value='a'*40), \
                 patch.object(self.backend.runner, 'on_devssd', return_value=True):
                if edit:
                    with self.assertRaises(lc.Invalid):
                        d.validate_card(file_ref['path'], expected_card_sha256=file_ref['sha256'], **arguments)
                else:
                    value = d.validate_card(file_ref['path'], expected_card_sha256=file_ref['sha256'], **arguments)
                    self.assertIs(type(value), d.ValidatedCard)
                    with self.assertRaises(lc.Invalid):
                        d.validate_card(file_ref['path'], expected_card_sha256='0'*64, **arguments)

    def test_actual_cpu_child_parent_wait_owner_and_independent_observer(self):
        # Only a harmless CPU Python child; the real old backend method is mocked,
        # not the Popen/wait. No UE, solver, official build or private input touched.
        controller = d.DispatchController(self.validated, backend=self.backend)
        child_codes = []
        def cpu_supervise(_):
            child = subprocess.Popen([sys.executable, '-c', 'sum(range(1000))'])
            code = child.wait(timeout=3)
            child_codes.append(code)
            return dict(normal=True, launcher_wait_exit=code)
        with patch.object(self.backend, 'finalization_connected', True), \
             patch.object(self.backend, 'prepare', return_value=dict(prior_seconds=0)), \
             patch.object(self.backend.runner, 'supervise', side_effect=cpu_supervise):
            controller.start_observer()
            try:
                handle = controller.begin_session('initialize')
                self.assertEqual(handle.wait(timeout=3)['launcher_wait_exit'], 0)
                self.assertEqual(child_codes, [0])
                self.assertTrue(controller.observer.is_alive())
                deadline = time.monotonic() + 2
                while not controller.samples and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(controller.samples)
                self.assertIsNone(controller.observer_error)
                controller.collect_session()
                with self.assertRaises(lc.Invalid):
                    controller.begin_session('existing')  # S1 has no independent actions
            finally:
                controller.stop_observer.set()
                controller.observer.join(timeout=3)
                self.assertFalse(controller.observer.is_alive())

    def test_fixed_backend_preserves_full_legacy_validate_run_and_env_whitelist(self):
        inner = dict(world_id='world', authority_root=self.card['run_binding']['authority_root'],
            context={'trust_anchor': self.card['trust_anchor']}, launcher_sha256='c' * 64,
            storage_root=str(self.root), ue_root='/UE', python_executable=sys.executable,
            budget=dict(seconds=1200, bytes=lc.MAX_BYTES,spent_seconds=0,spent_bytes=0),
            sessions={name: dict(max_seconds=slot['max_seconds'], stage_seconds={k:v for k,v in slot['stage_seconds'].items() if k != 'seal'}) for name,slot in lc.SESSION_LIMITS_V2.items()})
        self.card['accepted_executable'] = '/UE/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
        prepared = dict(card=inner, argv=['/bin/bash', '/fixed-launcher'], prior_seconds=0)
        with patch.object(self.backend.runner, 'validate_run', return_value=prepared) as validate:
            value = self.backend.prepare(self.card, 'initialize')
            validate.assert_called_once_with(str(self.root / 'old-card'), 'b' * 64, 'a' * 40, 'initialize', True)
        self.assertEqual(value['argv'][0], '/usr/bin/env')
        self.assertEqual(set(x.split('=',1)[0] for x in value['argv'][1:5]), set(d.DIAGNOSTIC_ENV))
        self.assertEqual(value['argv'][-2:], ['/bin/bash', '/fixed-launcher'])
        inner['budget']['spent_seconds']=1
        with patch.object(self.backend.runner,'validate_run',return_value=prepared):
            with self.assertRaises(lc.Invalid): self.backend.prepare(self.card,'initialize')
        inner['budget']['spent_seconds']=0
        with patch.object(self.backend.runner, 'validate_run', side_effect=lc.Invalid('private pin rejected')):
            with self.assertRaises(lc.Invalid):
                self.backend.prepare(self.card, 'initialize')

    def ready_controller(self):
        c = self.controller()
        c.session = 'initialize'; c.session_start = 100
        c.stages = [('interaction', 100)]
        c.observer = type('Observer', (), {'is_alive': lambda _: True})()
        c.handle = type('Handle', (), {'done': threading.Event()})()
        c.binding = dict(self.card['run_binding'], session='initialize', host_pid=4, worker_pid=5, generation=1)
        c.identities = [dict(pid=pid, ppid=1, start='Mon Nov 2 00:00:00 2026', argv=self.card['accepted_executable'] if pid==4 else sys.executable) for pid in (4,5)]
        c.samples = [dict(monotonic=100, processes=deepcopy(c.identities))]
        self.log = self.root / 'ue.log'; self.log.write_bytes(b'fresh\n')
        return c

    def test_permit_once_stale_pid_reuse_closing_unknown_action_and_expiry(self):
        c = self.ready_controller()
        value = c.permit('camera', 1, log_path=str(self.log), log_offset=6)
        self.assertEqual(c.consume_permit(value)['seq'], 1)
        with self.assertRaises(lc.Invalid): c.consume_permit(value)
        for edit in ('unknown', 'stale', 'reuse', 'deadline'):
            old = deepcopy(c.samples)
            self.now = 100
            if edit=='stale': self.now=103
            if edit=='reuse': c.samples[0]['processes'][0]['start']='changed'
            if edit=='deadline': self.now=580
            with self.assertRaises(lc.Invalid):
                c.permit('missing' if edit=='unknown' else 'camera', 1, log_path=str(self.log), log_offset=6)
            c.samples = old
        self.now=100
        permit = c.permit('camera',1,log_path=str(self.log),log_offset=6)
        self.now=102
        with self.assertRaises(lc.Invalid): c.consume_permit(permit)
        c.request_quit('test')
        self.assertTrue(c.closing)
        with self.assertRaises(lc.Invalid): c.permit('camera',1,log_path=str(self.log),log_offset=6)

    def test_actual_file_assembler_preserves_native_raw_and_self_counts_final_seal(self):
        replay_root = self.root / 'runtime'
        replay_root.mkdir()
        replay = V2Replay(replay_root)
        self.card.update(run_binding=replay.run, storage_root=str(replay_root),
                         controller_output=str(replay_root/'controller'),
                         accepted_executable=replay.executable, worker_executable='/approved/python',
                         launcher_source_ref=replay.launcher_ref)
        self.validated = d.ValidatedCard(self.card, {'items':[]}, d._CARD_SEAL)
        self.now = 0
        c = self.controller()
        c.clock_binding = deepcopy(replay.ledger['clock'])
        c.samples = deepcopy(replay.ledger['samples'])
        c.observer = type('StoppedObserver', (), {'is_alive':lambda _:False, 'join':lambda _,timeout:None})()
        for index,name in enumerate(('initialize','existing')):
            base = index*8
            output = replay_root/('legacy-'+name); output.mkdir()
            launcher_dir = replay_root/('launcher-'+name); launcher_dir.mkdir()
            trace = launcher_dir/'trace'; trace.mkdir()
            result = lc.json_ref(replay.ledger['sessions'][index]['completion_ref'])
            result.update(launcher_pid=replay.launchers[index]['pid'],launcher_evidence=str(launcher_dir))
            result['worker_exits'][0]['generation'] = '1'  # actual native FString
            (output/'completion.json').write_text(json.dumps(result))
            (output/'supervisor-exit.json').write_text(json.dumps(dict(result,elapsed_seconds=4.5,normal=False)))
            (output/'launcher-stdout.log').write_bytes(b'[launcher] build_exit_code=0\n[launcher] ue_exit_code=0\n')
            events = [dict(event='poll',stage='build',monotonic_seconds=base+.5,elapsed_seconds=.5)] + [dict(event='stage',stage=stage,monotonic_seconds=base+t) for stage,t in
                      [('startup',1),('interaction',2),('shutdown',4)]]
            (output/'supervisor-events.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in events))
            (trace/'exit.bin').write_text(json.dumps(result['worker_exits'][0]))
            (trace/'exit.json').write_text(json.dumps(dict(direction='worker-exit',
                host_pid=replay.bindings[name]['host_pid'],worker_pid=replay.bindings[name]['worker_pid'],
                generation='1',raw_file='exit.bin')))
            done=threading.Event(); done.set()
            c.handle=type('RawHandle',(),{'prepared':{'output':output},'finished_monotonic':base+5,'done':done})()
            c.binding=replay.bindings[name];c.session_start=base
            self.now=base+6
            c.assembled[name]=c._assemble_session(name,result)
            normalized=lc.json_ref(c.assembled[name]['session']['completion_ref'])
            self.assertEqual(normalized['worker_exits'][0]['generation'],1)
            phases=c.assembled[name]['session']['stages']
            self.assertEqual(phases[3]['end_monotonic'],base+4.5)
            self.assertLess(phases[3]['end_monotonic'],c.handle.finished_monotonic)
            self.assertEqual(phases[4]['timing_bound_source'],'preseal-poll-conservative-upper')
            self.assertEqual(lc.json_ref(normalized['original_completion_ref'])['worker_exits'][0]['generation'],'1')
        self.now=16
        policy=deepcopy(replay.policy)
        policy['public_paths']=list(c.public_refs)+[s['raw_ref']['path'] for s in c.samples]+[
            replay.launcher_ref['path'],str(c.output/'ledger-v2.json'),str(c.output/'storage-snapshot.json')]
        result=c.finalize_run(expected_policy=policy)
        self.assertEqual(result['status'],'checks_complete_requires_review',result)
        self.assertEqual(result['actual_finalized_monotonic'],16)
        ledger=json.loads((c.output/'ledger-v2.json').read_text())
        self.assertEqual(ledger['charged_end_monotonic'],18)
        self.assertEqual(ledger['seal']['storage_bytes'],sum(p.stat().st_size for p in replay_root.rglob('*') if p.is_file()))
        self.assertFalse(any(p.read_text().find('controller-read-upper-bound')==-1 for p in c.output.glob('session-*/waits/*.json')))

    def test_no_third_session_or_attempt_and_failed_s1_blocks_s2(self):
        c = self.controller()
        self.backend.finalization_connected = True
        c.observer = type('Observer', (), {'is_alive': lambda _: True})()
        c.sessions['initialize'] = dict(normal=False, actions_verified=True)
        for name in ('initialize','existing','third'):
            with self.assertRaises(lc.Invalid): c.begin_session(name)


if __name__ == '__main__':
    unittest.main()
