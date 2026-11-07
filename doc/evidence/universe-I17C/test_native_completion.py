"""I17 CPU reproduction checks. No UE, Genesis, world, UI or credentials."""
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


class CompletionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
 def tearDown(self):self.temp.cleanup()
 def pin(self,path):return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 def registrations(self,extra=''):
  path=self.root/'project/engine_platforms/unreal/Source/Tests.cpp';path.parent.mkdir(parents=True,exist_ok=True)
  text='\n'.join('IMPLEMENT_SIMPLE_AUTOMATION_TEST(Test%d,"%s",1)'%(i,s) for i,s in enumerate(c.SELECTORS))
  path.write_text(text+'\n'+extra);return [self.pin(path)],self.root/'project'
 def controller(self):
  token=c.ValidatedCapability(dict(run_id='i17-cpu',controller_output=str(self.root/'controller')),
    dict(tool_root=str(ROOT),product_root=str(ROOT),output_root=str(self.root),
         key_directory=str(self.root/'keys'),binary_pins={'ue':{'path':'/not-an-installed-test-editor'}}),
    {'items':[]},c._SEAL)
  return c.CapabilityController(token)
 def test_mac_quote_conversion_preserves_all_new_filters(self):
  old='+'.join('^'+s+'$' for s in c.SELECTORS)
  self.assertEqual(old.replace('$','"').split('"')[0],'^'+c.SELECTORS[0])
  new='+'.join('^'+s for s in c.SELECTORS)
  self.assertEqual(new.replace('$','"').split('+'),['^'+s for s in c.SELECTORS])
 def test_inventory_unique_and_source_sha_bound(self):
  pins,product=self.registrations('// IMPLEMENT_SIMPLE_AUTOMATION_TEST(Fake,"'+c.SELECTORS[0]+'.ignored",1)')
  inventory=c.native_test_inventory(pins,product)
  self.assertEqual(len(inventory['registrations']),4)
  Path(pins[0]['path']).write_text('changed')
  with self.assertRaises(c.lc.Invalid):c.native_test_inventory(pins,product)
 def test_inventory_rejects_ambiguous_complex_or_nonliteral(self):
  extras=['IMPLEMENT_SIMPLE_AUTOMATION_TEST(Extra,"'+c.SELECTORS[0]+'.extra",1)',
          'IMPLEMENT_SIMPLE_AUTOMATION_TEST(CaseVariant,"'+c.SELECTORS[0].upper()+'.extra",1)',
          'IMPLEMENT_COMPLEX_AUTOMATION_TEST(Dynamic,"edgeWorld.UniverseHost",1)',
          'IMPLEMENT_SIMPLE_AUTOMATION_TEST(Unparsed,DYNAMIC_NAME,1)']
  for extra in extras:
   pins,product=self.registrations(extra)
   with self.subTest(extra=extra),self.assertRaises(c.lc.Invalid):c.native_test_inventory(pins,product)
 def test_actual_project_inventory_parses_pinned_source(self):
  pins=[]
  for folder in ('engine_platforms/unreal/EdgeWorldHost/Source','engine_platforms/unreal/EdgeWorldHost/Plugins/EdgeWorldRuntime/Source'):
   pins += [self.pin(p) for p in sorted((ROOT/folder).rglob('*')) if p.is_file()]
  inventory=c.native_test_inventory(pins,ROOT)
  self.assertEqual(len(inventory['registrations']),23)
  for selector in c.SELECTORS:
   self.assertEqual([r['name'] for r in inventory['registrations'] if r['name'].startswith(selector)],[selector])
 def test_ddc_bound_to_run_and_controller_without_default_graph(self):
  path,args=c.native_cache_arguments(self.root,'i17-run',self.root/'controller')
  self.assertTrue(path.is_relative_to(self.root));self.assertLess(len(str(path)),119)
  self.assertIn('Type=FileSystem,Path='+str(path),args[0]);self.assertEqual(args[1],'-DDC-NoDefaultGraph')
  another,_=c.native_cache_arguments(self.root,'i17-run',self.root/'controller2')
  self.assertNotEqual(path,another)
  for root,controller in ((self.root/'has space',self.root/'has space/c'),
                          (self.root/'x',self.root.parent/'foreign'),
                          (self.root/('x'*120),self.root/('x'*120)/'controller')):
   with self.subTest(root=root),self.assertRaises(c.lc.Invalid):c.native_cache_arguments(root,'i17-run',controller)
 def test_fingerprint_rejects_symlink_and_mutation(self):
  path=self.root/'console';path.write_bytes(b'initial');before=c.file_fingerprint(path)
  path.write_bytes(b'changed');self.assertNotEqual(c.file_fingerprint(path),before)
  link=self.root/'alias';link.symlink_to(path)
  with self.assertRaises(c.lc.Invalid):c.file_fingerprint(link)
 def spawn_writer(self,controller,child_seconds):
  directory=controller.output/'native';directory.mkdir()
  (directory/'ue.log').write_text('CPU synthetic log\n');(directory/'replay-result.json').write_text('{}\n')
  child="import time;time.sleep(%s);print('late-child-output',flush=True)"%child_seconds
  parent="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',%r]);time.sleep(.9);print('parent-exit',flush=True)"%child
  environment=dict(os.environ)
  environment.update(dict(zip(c.REPLAY_ENV,('1','/synthetic/manifest','0'*64,'/synthetic/output'))))
  controller._spawn_reserved('native',[sys.executable,'-c',parent],environment,directory)
  phase=controller.phases['native'];phase['thread'].join(5)
  self.assertEqual(phase['wait_exit'],0);return phase
 def test_real_child_writer_waits_and_mutated_seal_is_refused(self):
  controller=self.controller();controller.start_observer()
  try:
   phase=self.spawn_writer(controller,1.7)
   result=controller._native_writer_barrier(controller.clock()+6)
   self.assertTrue(result['complete']);self.assertGreater(result['confirmed_monotonic'],phase['wait_monotonic']+.8)
   console=Path(phase['directory'])/'console.log';self.assertIn(b'late-child-output',console.read_bytes())
   self.assertTrue(any(not row['all_owned_quiet'] for row in result['observations']))
   self.assertEqual({Path(row['path']).name for row in result['files']},{'console.log','ue.log','replay-result.json'})
   phase.update(frozen_files=result['files'],normal=True,sealed_monotonic=controller.clock());controller.phase=None
   with console.open('ab') as stream:stream.write(b'post-freeze-write\n')
   with self.assertRaisesRegex(c.lc.Invalid,'mutated'):controller.seal()
   self.assertFalse((controller.output/'resource.json').exists())
  finally:controller.abort('CPU writer fixture teardown')
 def test_writer_budget_expiry_is_not_normal_or_frozen(self):
  controller=self.controller();controller.start_observer()
  try:
   phase=self.spawn_writer(controller,3)
   result=controller._native_writer_barrier(controller.clock()+.25)
   self.assertFalse(result['complete']);self.assertFalse(phase['normal'])
   self.assertFalse((controller.output/'native-execution.json').exists())
  finally:controller.abort('CPU timeout writer fixture teardown')
 def test_failed_writer_barrier_never_publishes_mutable_file_refs(self):
  controller=self.controller();controller.start_observer()
  try:
   phase=self.spawn_writer(controller,3)
   failed=dict(format='universe-i17-native-writer-barrier.v1',complete=False,
               confirmed_monotonic=controller.clock(),observations=[],files=[])
   with patch.object(controller,'_native_writer_barrier',return_value=failed):
    reference=controller.wait_native(timeout=5)
   result=json.loads(Path(reference['path']).read_bytes())
   self.assertFalse(result['normal']);self.assertFalse(result['evidence_frozen'])
   self.assertIsNone(result['console_ref']);self.assertIsNone(result['log_ref']);self.assertIsNone(result['result_ref'])
   self.assertEqual(len(result['deferred_evidence_paths']),3)
   self.assertTrue(result['parent_wait']['observed']);self.assertEqual(result['parent_wait']['exit_code'],0)
  finally:controller.abort('CPU mutable-ref fixture teardown')


if __name__=='__main__':unittest.main()
