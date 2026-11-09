"""I19 explicit slice admission and full controller timing; CPU only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from universe_iteration import capability as c, probe_actions as p


class SliceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.now=[100.0]
        self.manifest_ref={'path':'/synthetic/manifest.json','sha256':'0'*64}

    def tearDown(self):self.temp.cleanup()

    def pair(self,version2=True):
        card=dict(format=c.FORMAT_V2 if version2 else c.FORMAT,
                  scope=c.SCOPE_V2 if version2 else c.SCOPE,probe_manifest_ref=deepcopy(self.manifest_ref))
        prepared=dict(format=c.PREPARED_FORMAT_V2 if version2 else 'universe-i15-prepared.v1',
                      probe_manifest_ref=deepcopy(self.manifest_ref))
        return card,prepared,p.probe_manifest_v2() if version2 else p.probe_manifest()

    def controller(self,version2=True):
        card,prepared,manifest=self.pair(version2)
        card.update(run_id='i19-cpu',controller_output=str(self.root/'controller'))
        prepared.update(tool_root=str(ROOT),product_root=str(ROOT),output_root=str(self.root),
                        binary_pins={'ue':{'path':'/synthetic/editor'}})
        token=c.ValidatedCapability(card,prepared,manifest,c._SEAL)
        controller=c.CapabilityController(token,clock=lambda:self.now[0])
        controller.phase='metal';controller.phases['metal']={'started':100.0}
        controller.process=Mock(poll=Mock(return_value=None));controller.binding={'synthetic':True}
        controller.identity=dict(pid=9001,ppid=1,start='synthetic-start',argv='/synthetic/editor')
        controller.worker_identity=dict(pid=9002,ppid=9001,start='synthetic-start',argv='/synthetic/python')
        controller.samples=[dict(monotonic=self.now[0],processes=[controller.identity,controller.worker_identity])]
        controller._trace=Mock()
        controller.snapshot=Mock(side_effect=lambda label:{'label':label,'monotonic':self.now[0]})
        directory=controller.output/'controller-inputs';directory.mkdir()
        path=directory/'cua.json';path.write_bytes(b'{"synthetic_cua":"CPU only"}\n')
        self.raw_ref=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        return controller

    def snapshot_delay(self,controller,before=0,after=0):
        def snapshot(label):
            self.now[0]+=before if label=='before' else after
            controller.samples[-1]['monotonic']=self.now[0] # synthetic continuously fresh observer
            return dict(label=label,monotonic=self.now[0])
        controller.snapshot.side_effect=snapshot

    def test_only_explicit_new_card_scope_prepared_and_exact_manifest_get_twenty_seconds(self):
        card,prepared,manifest=self.pair()
        self.assertTrue(c._slice_version(card));self.assertEqual(c._probe_step_limit(card,prepared,manifest),20)
        old_card,old_prepared,old_manifest=self.pair(False)
        self.assertFalse(c._slice_version(old_card))
        self.assertEqual(c._probe_step_limit(old_card,old_prepared,old_manifest),10)
        for update in (dict(format=c.FORMAT),dict(scope=c.SCOPE),dict(format='unknown'),dict(scope='arbitrary')):
            with self.subTest(update=update),self.assertRaises(c.lc.Invalid):c._slice_version(dict(card,**update))
        with self.assertRaises(c.lc.Invalid):c._probe_step_limit(card,old_prepared,manifest)
        with self.assertRaises(c.lc.Invalid):c._probe_step_limit(old_card,old_prepared,manifest)
        with self.assertRaises(c.lc.Invalid):c._probe_step_limit(card,prepared,old_manifest)

    def test_fixed_manifest_refuses_arbitrary_commands_costs_subset_and_type_changes(self):
        card,prepared,manifest=self.pair()
        variants=[]
        for transform in (
            lambda m:m['items'][1]['commands'][0].update(text='arbitrary console command'),
            lambda m:m['items'][1]['commands'][0].update(max_seconds=21),
            lambda m:m['items'].pop(),lambda m:m['items'].reverse(),
            lambda m:m.update(optional_actions=['arbitrary']),lambda m:m.update(image_count=True),
            lambda m:m.update(logical_step_count=14.0),lambda m:m.update(extra='unreviewed')):
            candidate=deepcopy(manifest);transform(candidate);variants.append(candidate)
        for candidate in variants:
            with self.subTest(candidate=candidate),self.assertRaises(c.lc.Invalid):
                c._probe_step_limit(card,prepared,candidate)
        prepared['probe_manifest_ref']['path']='/different-path-same-sha'
        with self.assertRaises(c.lc.Invalid):c._probe_step_limit(card,prepared,manifest)

    def test_old_controller_cannot_get_new_twenty_second_permits(self):
        controller=self.controller(False)
        with self.assertRaises(c.lc.Invalid):controller.begin_action('p1.history','p1.history/00',20)
        self.assertIsNone(controller.active);controller.snapshot.assert_not_called()

    def test_new_permit_rejects_over_limit_nonfinite_and_unknown_step(self):
        controller=self.controller()
        for timeout in (20.001,21,0,-1,True,float('nan'),float('inf'),'20'):
            with self.subTest(timeout=timeout),self.assertRaises(c.lc.Invalid):
                controller.begin_action('p1.history','p1.history/00',timeout)
        self.assertIsNone(controller.active);controller.snapshot.assert_not_called()
        with self.assertRaises(StopIteration):controller.begin_action('p1.camera','p1.camera/00',20)

    def test_new_card_does_not_relax_global_or_normal_quit_reserve(self):
        controller=self.controller();self.now[0]=441.0;controller.samples[-1]['monotonic']=441.0
        with self.assertRaisesRegex(c.lc.Invalid,'normal quit reserve'):
            controller.begin_action('p1.history','p1.history/00',20)
        self.assertEqual(c.POLICY,{'global_seconds':900,'bytes':2*1024**3,
            'metal':{'start':60,'interaction':300,'quit':40,'seal':20,'max':420},
            'native':{'start':60,'tests':60,'quit':40,'seal':20,'max':180},
            'handoff_seconds':120,'final_seal':90,'exception':90})

    def test_v2_started_time_precedes_before_map_and_success_counts_raw_ref_after_map(self):
        controller=self.controller();self.snapshot_delay(controller,before=2,after=3)
        token=controller.begin_action('p1.history','p1.history/00',20)
        self.assertEqual(token['issued_monotonic'],100.0);self.assertEqual(token['started_monotonic'],100.0)
        self.assertEqual(self.now[0],102.0);self.now[0]+=5
        original=controller.read_public
        def read(reference):
            data=original(reference);self.now[0]+=1;return data
        with patch.object(controller,'read_public',side_effect=read):result=controller.end_action(token['seq'],self.raw_ref)
        self.assertEqual(result['completed_monotonic'],111.0);self.assertEqual(result['status'],'recorded')
        self.assertEqual(result['after']['monotonic'],111.0)
        self.assertFalse(controller.closing)
        with self.assertRaises(c.lc.Invalid):controller.begin_action('p1.history','p1.history/00',20)

    def test_v2_slow_after_map_times_out_and_retains_raw_and_maps(self):
        controller=self.controller();self.snapshot_delay(controller,before=7,after=6)
        token=controller.begin_action('p1.history','p1.history/00',20)
        self.now[0]+=5;original=controller.read_public
        def read(reference):
            data=original(reference);self.now[0]+=3;return data
        with patch.object(controller,'read_public',side_effect=read):result=controller.end_action(token['seq'],self.raw_ref)
        self.assertEqual(result['completed_monotonic'],121.0);self.assertEqual(result['status'],'timeout')
        self.assertEqual(result['started_monotonic'],100.0)
        self.assertTrue(controller.closing);self.assertIsNone(controller.active)
        saved=json.loads(Path(result['receipt_ref']['path']).read_bytes())
        self.assertEqual(saved['raw_tool_ref'],self.raw_ref)
        self.assertEqual(saved['before']['monotonic'],107.0);self.assertEqual(saved['after']['monotonic'],121.0)
        self.assertEqual(saved['status'],'timeout')
        with self.assertRaises(c.lc.Invalid):controller.begin_action('p1.final','p1.final/00',20)

    def test_v2_trace_check_cost_also_counts_towards_end_time(self):
        controller=self.controller();token=controller.begin_action('p1.history','p1.history/00',20)
        self.now[0]=119.0
        controller._trace.side_effect=lambda:self.now.__setitem__(0,self.now[0]+2)
        result=controller.end_action(token['seq'],self.raw_ref)
        self.assertEqual(result['completed_monotonic'],121.0);self.assertEqual(result['status'],'timeout')

    def test_v1_timestamps_and_two_second_manifest_limit_are_unchanged(self):
        controller=self.controller(False);self.snapshot_delay(controller,before=.3,after=.9)
        token=controller.begin_action('p1.history','p1.history/00',2)
        self.assertAlmostEqual(token['started_monotonic'],100.3);self.now[0]+=.8
        result=controller.end_action(token['seq'],self.raw_ref)
        self.assertAlmostEqual(result['completed_monotonic'],101.1)
        self.assertAlmostEqual(result['after']['monotonic'],102.0);self.assertEqual(result['status'],'recorded')

    def test_v2_snapshot_cannot_expire_permit_then_be_consumed(self):
        controller=self.controller();self.snapshot_delay(controller,before=21)
        with self.assertRaisesRegex(c.lc.Invalid,'stale/replayed/revoked'):
            controller.begin_action('p1.history','p1.history/00',20)
        self.assertIsNone(controller.active)

    def test_card_prepared_version_mismatch_rejected_before_runtime_or_owner_audit(self):
        card,prepared,manifest=self.pair()
        now=datetime.now(timezone.utc)
        card.update(run_id='i19-cpu',issuer='root',approved=True,execute=True,issued_at=now.isoformat(),
                    expires_at=(now+timedelta(hours=1)).isoformat(),g_b2_granted=False,standard_pair=False,no_retry=True,
                    prepared_ref={'path':'/synthetic/prepared','sha256':'1'*64},controller_output='/synthetic/controller',
                    policy=deepcopy(c.POLICY),legacy_sources=[],public_paths=[])
        names='format run_id product_source_sha tool_source_sha native_source_sha tool_root product_root allowed_untracked output_root key_directory authority_root runtime_files native_source_pins source_pins binary_pins project ue_root python_executable python_environment_pin original_owner_ref readonly_owner_ref context inputs original_inputs scratch_root pins_ref original_pins_ref before_map_ref head_ref key_metadata probe_manifest_ref launcher_ref preparation_ref build_ref created_at helper_ref'.split()
        fake={name:None for name in names};fake.update(prepared,run_id='i19-cpu',product_source_sha='a'*40,
            tool_source_sha='b'*40,native_source_sha='c'*40,format='universe-i15-prepared.v1')
        with patch.object(c.lc,'json_ref',side_effect=[card,fake]),patch.object(c,'_common') as common:
            with self.assertRaisesRegex(c.lc.Invalid,'prepared source/run binding'):
                c.validate_capability_card('/synthetic/card',expected_card_sha256='2'*64,
                    expected_prepared_sha256='1'*64,expected_probe_manifest_sha256='0'*64,
                    expected_product_source='a'*40,expected_tool_source='b'*40,expected_native_source_sha='c'*40,execute=True)
        common.assert_not_called()


if __name__=='__main__':unittest.main()
