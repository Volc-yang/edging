"""CPU-only owner/observer and fail-closed capability regression checks."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from universe_iteration import capability as c

class CapabilityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
 def tearDown(self):self.temp.cleanup()
 def ref(self,name,data):return c.lc.exclusive_bytes(self.root/name,c.encoded(data))
 def controller(self):
  value=c.ValidatedCapability(dict(run_id='i15-cpu',controller_output=str(self.root/'controller'),
    legacy_sources=[],public_paths=[str(self.root/'skip.json')]),dict(tool_root=str(ROOT),product_root=str(ROOT),output_root=str(self.root),
    key_directory=str(self.root/'private'),binary_pins={'ue':{'path':'/not-installed-test-editor'}}),{'items':[]},c._SEAL)
  return c.CapabilityController(value)
 def test_mac_modules_follow_actual_lib_filenames(self):
  project=self.root/'project/EdgeWorldHost.uproject';project.parent.mkdir();project.write_text('{}')
  host=project.parent/'Binaries/Mac/libUnrealEditor-EdgeWorldHost.dylib'
  plugin=project.parent/'Plugins/EdgeWorldRuntime/Binaries/Mac/libUnrealEditor-EdgeWorldRuntime.dylib'
  for path in (host,plugin):path.parent.mkdir(parents=True);path.write_bytes(b'cpu-fixture')
  actual=c.mac_binary_paths(project)
  self.assertEqual(actual,(host,plugin))
  self.assertTrue(all(p.is_file() and not p.is_symlink() for p in actual))
  self.assertEqual(host.parent.parent.parent,plugin.parent.parent.parent.parent.parent)
  self.assertFalse((host.parent/'UnrealEditor-EdgeWorldHost.dylib').exists())
  self.assertFalse((plugin.parent/'UnrealEditor-EdgeWorldRuntime.dylib').exists())
 def test_actual_observer_skip_freeze_without_startup_sleep(self):
  # Reuse N's bounded synthetic public trace fixture; run the actual manifest
  # validator and actual ps observer, with no UE or worker dispatch.
  import importlib.util
  spec=importlib.util.spec_from_file_location('i15_n_fixture',ROOT/'tests/test_universe_iteration_native_replay.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  fixture=module.NativeReplayTests();fixture.setUp()
  controller=self.controller()
  controller.card.update(run_id='test-run',legacy_sources=[fixture.source],public_paths=fixture.paths+[str(self.root/'skip.json')])
  controller.prepared.update(product_source_sha='a'*40,tool_source_sha='b'*40)
  skip=self.ref('skip.json',dict(format='universe-i15-capability-skip.v1',run_id='test-run',
   reason='ui-controller-unavailable',metal_dispatched=False,decision='inconclusive'))
  try:
   ready=controller.start_observer()
   self.assertTrue(controller.samples);self.assertTrue(Path(ready['sample_ref']['path']).is_file())
   controller.skip_metal(skip)
   result=controller.freeze_native_manifest(fixture.ref,fixture.ref['sha256'])
   self.assertEqual(len(result['cases']),1)
   # Force another real callback while skipped and pre-PID phase metadata exist.
   controller.phases['pending']={'identity':None}
   count=len(controller.samples);time.sleep(.6)
   self.assertGreater(len(controller.samples),count)
   self.assertIsNone(controller.observer_error);self.assertTrue(controller.observer.is_alive())
   self.assertFalse(controller.phases['metal']['normal']);self.assertIsNone(controller.process)
  finally:
   controller.phases.pop('pending',None)
   controller.abort('CPU skip/freeze fixture teardown');fixture.tearDown()
 def test_observer_first_sample_failure_is_preserved(self):
  controller=self.controller()
  with patch.object(c.lc,'record_observer',side_effect=OSError('synthetic ps unavailable')):
   with self.assertRaisesRegex(c.lc.Invalid,'first sample not ready'):controller.start_observer()
  self.assertIn('synthetic ps unavailable',controller.observer_error)
  self.assertTrue((controller.output/'observer-start-failure.json').is_file())
  self.assertFalse(controller.observer.is_alive())
  self.assertIsNone(controller.process);controller.abort('CPU first-sample fixture teardown')
 def test_missing_observer_first_sample_stops_thread_before_raise(self):
  controller=self.controller()
  def delayed_observer(stop_event,directory,on_sample):
   stop_event.wait(5) # bounded failure fixture, exits when the controller stops it
  with patch.object(c.lc,'record_observer',side_effect=delayed_observer):
   with self.assertRaisesRegex(c.lc.Invalid,'first sample not ready'):controller.start_observer()
  failure=json.loads((controller.output/'observer-start-failure.json').read_bytes())
  self.assertTrue(failure['stop_requested']);self.assertFalse(failure['thread_alive'])
  self.assertFalse(failure['ue_dispatched']);self.assertIsNone(controller.process)
  controller.abort('CPU missing-sample fixture teardown')
 def test_no_json_restore(self):
  with self.assertRaises(c.lc.Invalid):c.ValidatedCapability({}, {}, {}, None)
 def test_exact_public_export_keeps_original_lf(self):
  c.validate_public_export(b'{"allowed_actions":[]}\n',b'{"allowed_actions":[]}\n')
  for raw in (b'{"allowed_actions":[]}',b'{"allowed_actions":[]}\n\n',b'{"allowed_actions":[]}\r\n'):
   with self.assertRaises(c.lc.Invalid):c.validate_public_export(raw,b'{"allowed_actions":[]}\n')
 def test_owned_cpu_timeout_is_forced_cleanup_not_normal(self):
  controller=self.controller();base=time.monotonic();offset=[0]
  controller.clock=lambda:time.monotonic()+offset[0]
  controller.start_observer()
  try:
   time.sleep(.7)
   controller._spawn('native',[sys.executable,'-c','import time;time.sleep(10)'],dict(os.environ))
   offset[0]=200
   phase=controller.phases['native'];phase['thread'].join(5)
   self.assertFalse(phase['thread'].is_alive());self.assertNotEqual(phase['wait_exit'],0)
   self.assertTrue(phase['forced_cleanup']);self.assertFalse(phase['normal'])
   offset[0]=0;time.sleep(.6)
  finally:
   offset[0]=0;controller.abort('CPU timeout fixture teardown')
 def test_wrong_scope_no_dispatch(self):
  card=self.ref('bad-card.json',{'format':'old-standard-card'})
  with self.assertRaises(c.lc.Invalid):c.validate_capability_card(card['path'],expected_card_sha256=card['sha256'],
   expected_prepared_sha256='0'*64,expected_probe_manifest_sha256='0'*64,
   expected_product_source='0'*40,expected_tool_source='0'*40,expected_native_source_sha='0'*40,execute=True)
 def test_approved_native_only_skip_preserves_inconclusive_and_once(self):
  controller=self.controller()
  ref=self.ref('skip.json',dict(format='universe-i15-capability-skip.v1',run_id='i15-cpu',
   reason='approved-native-only-iteration',metal_dispatched=False,decision='inconclusive'))
  controller.skip_metal(ref)
  phase=controller.phases['metal']
  self.assertTrue(phase['skipped']);self.assertFalse(phase['normal'])
  self.assertEqual(phase['decision'],'inconclusive');self.assertNotIn('pid',phase)
  self.assertIsNone(controller.process)
  with self.assertRaises(c.lc.Invalid):controller.skip_metal(ref)
 def test_native_only_skip_rejects_unknown_reason_or_weakened_schema(self):
  controller=self.controller()
  expected=dict(format='universe-i15-capability-skip.v1',run_id='i15-cpu',
   reason='approved-native-only-iteration',metal_dispatched=False,decision='inconclusive')
  updates=[dict(reason='arbitrary-skip'),dict(reason=None),dict(metal_dispatched=True),
           dict(decision='pass'),dict(run_id='another-run'),dict(extra=True)]
  for i,update in enumerate(updates):
   with self.subTest(update=update):
    ref=self.ref('rejected-skip-%d.json'%i,dict(expected,**update))
    controller.card['public_paths'].append(ref['path'])
    with self.assertRaises(c.lc.Invalid):controller.skip_metal(ref)
    self.assertFalse(controller.phases);self.assertIsNone(controller.process)
 def test_skip_is_inconclusive_and_once(self):
  controller=self.controller()
  ref=self.ref('skip.json',dict(format='universe-i15-capability-skip.v1',run_id='i15-cpu',
   reason='ui-controller-unavailable',metal_dispatched=False,decision='inconclusive'))
  controller.skip_metal(ref)
  self.assertFalse(controller.phases['metal']['normal'])
  with self.assertRaises(c.lc.Invalid):controller.skip_metal(ref)
  with self.assertRaises(c.lc.Invalid):controller.start_native()
 def test_unlisted_skip_ref_refused_before_read(self):
  controller=self.controller()
  with patch.object(c.lc,'json_ref',side_effect=AssertionError('must refuse before read')):
   with self.assertRaises(c.lc.Invalid):controller.skip_metal({'path':str(self.root/'private/payload'),'sha256':'0'*64})
 def test_wrong_skip_cannot_look_normal(self):
  controller=self.controller()
  ref=self.ref('skip.json',dict(format='universe-i15-capability-skip.v1',run_id='i15-cpu',
   reason='ui-controller-unavailable',metal_dispatched=False,decision='pass'))
  with self.assertRaises(c.lc.Invalid):controller.skip_metal(ref)
 def test_reserved_directory_actual_child_wait_and_observer(self):
  controller=self.controller();controller.start_observer()
  try:
   time.sleep(.7)
   directory=controller.output/'native';directory.mkdir()
   value=controller._spawn_reserved('native',[sys.executable,'-c','import time;time.sleep(.9)'],dict(os.environ),directory)
   phase=controller.phases['native'];phase['thread'].join(5)
   self.assertFalse(phase['thread'].is_alive());self.assertEqual(phase['wait_exit'],0)
   self.assertGreaterEqual(phase['wait_monotonic'],phase['started'])
   self.assertIsNotNone(phase['identity']);self.assertEqual(phase['identity']['pid'],value['pid'])
   self.assertFalse(phase['normal']) # actual wait alone is not Native acceptance
   with self.assertRaises(c.lc.Invalid):controller._spawn('native',[],{})
  finally:controller.abort('CPU fixture teardown')
 def test_native_first_and_replayed_manifest_ref_rejected(self):
  controller=self.controller()
  with self.assertRaises(c.lc.Invalid):controller.start_native()
  with self.assertRaises(c.lc.Invalid):controller.freeze_native_manifest({'path':'/missing','sha256':'0'*64},'0'*64)
 def test_streaming_hash_and_redirect_rejected(self):
  path=self.root/'large.bin';path.write_bytes(b'1'*(17*1024**2));ref={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  c.hash_ref(ref,forbidden=self.root/'keys')
  ref['sha256']='0'*64
  with self.assertRaises(c.lc.Invalid):c.hash_ref(ref,forbidden=self.root/'keys')
  link=self.root/'link';link.symlink_to(path)
  with self.assertRaises(c.lc.Invalid):c.hash_ref({'path':str(link),'sha256':'0'*64},forbidden=self.root/'keys')
 def test_foreign_authority_key_is_not_read(self):
  keys=self.root/'keys';keys.mkdir();path=keys/'payload';path.write_bytes(b'private')
  with patch('os.open',side_effect=AssertionError('must refuse before open')):
   with self.assertRaises(c.lc.Invalid):c.hash_ref({'path':str(path),'sha256':'0'*64},forbidden=keys)
 def test_expired_card_refused_before_prepared_read(self):
  card=dict(format=c.FORMAT,scope=c.SCOPE,run_id='i15-cpu',issuer='root',approved=True,execute=True,
   issued_at='2000-01-01T00:00:00Z',expires_at='2000-01-02T00:00:00Z',g_b2_granted=False,standard_pair=False,
   no_retry=True,prepared_ref={},probe_manifest_ref={},controller_output=str(self.root/'x'),policy=c.POLICY,legacy_sources=[],public_paths=[str(self.root/'skip.json')])
  ref=self.ref('expired.json',card)
  with self.assertRaisesRegex(c.lc.Invalid,'expired'):c.validate_capability_card(ref['path'],expected_card_sha256=ref['sha256'],
   expected_prepared_sha256='0'*64,expected_probe_manifest_sha256='0'*64,
   expected_product_source='0'*40,expected_tool_source='0'*40,expected_native_source_sha='0'*40,execute=True)

if __name__=='__main__':unittest.main()
