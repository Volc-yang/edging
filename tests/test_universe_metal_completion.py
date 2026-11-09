"""I19 CPU-only Metal process/evidence boundaries; never launches UE or a worker."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from universe_iteration import capability as c

ROOT=Path(__file__).resolve().parents[1]


class MetalCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='/private/tmp' if Path('/private/tmp').exists() else '/tmp')
        self.root=Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def controller(self):
        token=c.ValidatedCapability(dict(run_id='i19-cpu',controller_output=str(self.root/'controller')),
            dict(tool_root=str(ROOT),product_root=str(ROOT),output_root=str(self.root),
                 key_directory=str(self.root/'keys'),binary_pins={'ue':{'path':'/not-an-installed-test-editor'}},
                 python_executable=sys.executable,readonly_owner_ref={'path':'/never-read-owner'},
                 pins_ref={'path':'/synthetic/public-pins','sha256':'0'*64},product_source_sha='0'*40,
                 project=str(ROOT/'synthetic.uproject')),
            {'items':[]},c._SEAL)
        return c.CapabilityController(token)

    def evidence(self,controller):
        directory=controller.output/'metal';directory.mkdir();(directory/'trace').mkdir()
        (directory/'console.log').write_text('CPU console\n')
        (directory/'ue.log').write_text('CPU log\n')
        (directory/'trace/000001.raw').write_bytes(b'{"synthetic":true}\n')
        (directory/'trace/000001.json').write_bytes(b'{}\n')
        controller.phases['metal']=dict(directory=str(directory),started=controller.clock(),
            wait_monotonic=controller.clock(),wait_exit=0,forced_cleanup=[],identity={'synthetic':True},
            thread=Mock(is_alive=Mock(return_value=False)))
        return directory

    def freeze(self,controller):
        fingerprints=controller._metal_fingerprints();controller.phases['metal'].update(
            frozen_files=fingerprints['files'],frozen_trace_directories=fingerprints['trace_directories'])
        return fingerprints

    def barrier_with_samples(self,controller,*,quiet=True,change=None,repeat=False,post_wait=True):
        now=[controller.clock()]
        controller.clock=lambda:now[0]
        phase=controller.phases['metal'];phase['wait_monotonic']=now[0]
        controller.observer=Mock(is_alive=Mock(return_value=True))
        start=now[0];counter=[0]
        def sample():
            moment=start if repeat else now[0]
            if not post_wait:moment=start-1
            controller.samples.append(dict(monotonic=moment,raw_ref={'path':'/synthetic/sample','sha256':'0'*64}))
        def advance(_seconds):
            now[0]+=.5;counter[0]+=1
            if change and counter[0]==2:change()
            sample()
        sample()
        with patch.object(controller,'_quiet',return_value=quiet),patch.object(c.time,'sleep',side_effect=advance):
            result=controller._metal_writer_barrier(start+4)
        return result

    def test_metal_no_trace_and_distinct_exclusive_cache_preserve_native_binding(self):
        controller=self.controller();native,args=c.native_cache_arguments(self.root,'i19-cpu',controller.output)
        def spawn(name,argv,env,directory):
            controller.phases[name]={};return argv
        with patch.object(controller,'_private_preflight'),patch.object(controller,'_spawn_reserved',side_effect=spawn):
            argv=controller.start_metal()
        metal=Path(controller.phases['metal']['ddc_path'])
        self.assertNotEqual(metal,native);self.assertTrue(metal.is_dir());self.assertFalse(native.exists())
        self.assertLess(len(str(metal)),119)
        self.assertIn('-notraceserver',argv);self.assertIn('-traceautostart=0',argv)
        self.assertIn('-DDC-NoDefaultGraph',argv)
        self.assertIn('Type=FileSystem,Path='+str(metal),next(x for x in argv if x.startswith('-DDC=(')))
        self.assertEqual(c.native_cache_arguments(self.root,'i19-cpu',controller.output),(native,args))

    def test_preexisting_metal_cache_refused_before_spawn(self):
        controller=self.controller();ddc,_=c.native_cache_arguments(self.root,'i19-cpu',controller.output/'metal')
        ddc.mkdir()
        with patch.object(controller,'_private_preflight'),patch.object(controller,'_spawn_reserved') as spawn:
            with self.assertRaises(FileExistsError):controller.start_metal()
        spawn.assert_not_called();self.assertFalse((controller.output/'metal').exists())

    def test_inventory_detects_added_removed_modified_and_replaced_trace_files(self):
        controller=self.controller();directory=self.evidence(controller);self.freeze(controller)
        controller._verify_metal_frozen_files()
        original=directory/'trace/000001.raw'
        operations=[lambda:(directory/'trace/late.raw').write_bytes(b'late'),
                    lambda:original.unlink(),lambda:original.write_bytes(b'modified'),
                    lambda:os.replace(directory/'replacement.raw',original)]
        for operation in operations:
            for leaf in (directory/'trace').iterdir():leaf.unlink()
            original.write_bytes(b'original');(directory/'replacement.raw').write_bytes(b'original')
            self.freeze(controller);operation()
            with self.subTest(operation=operation),self.assertRaisesRegex(c.lc.Invalid,'mutated'):
                controller._verify_metal_frozen_files()

    def test_inventory_rejects_trace_symlinks(self):
        controller=self.controller();directory=self.evidence(controller)
        (directory/'trace/alias').symlink_to(directory/'console.log')
        with self.assertRaises(c.lc.Invalid):controller._metal_fingerprints()

    def test_barrier_requires_fresh_post_wait_quiet_observations(self):
        for options in ({'repeat':True},{'post_wait':False},{'quiet':False}):
            with self.subTest(options=options):
                controller=self.controller();self.evidence(controller)
                result=self.barrier_with_samples(controller,**options)
                self.assertFalse(result['complete']);self.assertEqual(result['files'],[])
                # Each case needs its own exclusive controller output.
                controller.output.rename(controller.output.with_name('used-'+str(len(list(self.root.iterdir())))))

    def test_barrier_resets_quiet_period_after_late_trace_and_log_write(self):
        controller=self.controller();directory=self.evidence(controller)
        def late():
            with (directory/'console.log').open('ab') as stream:stream.write(b'late console')
            (directory/'trace/late.raw').write_bytes(b'late trace')
        result=self.barrier_with_samples(controller,change=late)
        self.assertTrue(result['complete']);self.assertGreaterEqual(len(result['observations']),5)
        self.assertGreaterEqual(result['stable_since_monotonic'],controller.phases['metal']['wait_monotonic']+1)
        self.assertGreaterEqual(result['confirmed_monotonic']-result['stable_since_monotonic'],.75)
        self.assertIn(str(directory/'trace/late.raw'),[row['path'] for row in result['files']])

    def test_real_cpu_child_writer_is_quiet_before_logs_and_trace_are_frozen(self):
        controller=self.controller();directory=controller.output/'metal'
        directory.mkdir();(directory/'trace').mkdir();(directory/'ue.log').write_bytes(b'CPU log\n')
        (directory/'trace/initial.raw').write_bytes(b'initial')
        child="import pathlib,time;time.sleep(1.7);pathlib.Path(%r).write_bytes(b'late');print('late-child-output',flush=True)"%str(directory/'trace/late.raw')
        parent="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',%r]);time.sleep(.9);print('parent-exit',flush=True)"%child
        controller.start_observer()
        try:
            controller._spawn_reserved('metal',[sys.executable,'-c',parent],dict(os.environ),directory)
            phase=controller.phases['metal'];phase['thread'].join(5)
            self.assertEqual(phase['wait_exit'],0)
            result=controller._metal_writer_barrier(controller.clock()+6)
            self.assertTrue(result['complete'])
            self.assertGreater(result['confirmed_monotonic'],phase['wait_monotonic']+.8)
            self.assertIn(b'late-child-output',(directory/'console.log').read_bytes())
            self.assertIn(str(directory/'trace/late.raw'),[row['path'] for row in result['files']])
            self.assertTrue(any(not row['all_owned_quiet'] for row in result['observations']))
        finally:controller.abort('CPU child fixture teardown')

    def finish_fixture(self,controller,*,exit_code=0,forced=False,log=None):
        directory=self.evidence(controller);phase=controller.phases['metal']
        phase.update(wait_exit=exit_code,forced_cleanup=[{'kind':'synthetic forced'}] if forced else [],
                     ddc_path=str(self.root/'cache'))
        (directory/'ue.log').write_text(log if log is not None else
            'Isolated: Using data cache path '+phase['ddc_path']+': Writable\n')
        controller.phase='metal';controller.closing=True
        fingerprints=controller._metal_fingerprints()
        return dict(complete=True,**fingerprints)

    def finish(self,controller,barrier):
        with patch.object(controller,'_metal_writer_barrier',return_value=barrier),\
             patch.object(controller,'snapshot'),patch.object(controller,'_quiet',return_value=True),\
             patch('universe_iteration.actions.load_trace',return_value=[]):
            ref=controller.finish_metal()
        return json.loads(Path(ref['path']).read_bytes())

    def test_successful_wait_requires_actual_writable_cache_and_no_zen_launch(self):
        for kind,log in (('no-cache','CPU log only\n'),('wrong-cache','Isolated: Using data cache path /other: Writable\n'),
                         ('zen',None)):
            controller=self.controller();barrier=self.finish_fixture(controller,log=log)
            if kind=='zen':
                path=controller.output/'metal/ue.log'
                with path.open('a') as stream:stream.write('LogZenServiceInstance: Launching service\n')
                barrier.update(controller._metal_fingerprints())
            result=self.finish(controller,barrier)
            self.assertFalse(result['normal']);self.assertTrue(result['errors'])
            controller.output.rename(controller.output.with_name('used-'+kind))

    def test_exit_zero_without_stable_barrier_never_publishes_trace_refs(self):
        controller=self.controller();self.finish_fixture(controller)
        result=self.finish(controller,dict(complete=False,files=[],trace_directories=[]))
        self.assertFalse(result['normal']);self.assertFalse(result['evidence_frozen'])
        self.assertEqual(result['trace_refs'],[])

    def test_nonzero_or_forced_wait_never_normal_even_with_frozen_evidence(self):
        for code,forced in ((7,False),(0,True)):
            controller=self.controller();barrier=self.finish_fixture(controller,exit_code=code,forced=forced)
            result=self.finish(controller,barrier)
            self.assertFalse(result['normal']);self.assertTrue(result['evidence_frozen'])
            controller.output.rename(controller.output.with_name('used-'+str(code)))

    def test_live_parent_thread_cannot_be_finished(self):
        controller=self.controller();self.finish_fixture(controller)
        controller.phases['metal']['thread'].is_alive.return_value=True
        with self.assertRaisesRegex(c.lc.Invalid,'parent wait'):controller.finish_metal(timeout=0)
        self.assertFalse((controller.output/'metal-execution.json').exists())

    def test_frozen_metal_rechecked_before_manifest_native_dispatch_and_final_seal(self):
        controller=self.controller();directory=self.evidence(controller);self.freeze(controller)
        controller.phases['metal'].update(sealed_monotonic=controller.clock())
        controller.phase=None;controller.native_manifest={'path':'/synthetic','sha256':'0'*64}
        (directory/'trace/late.raw').write_bytes(b'late')
        with self.assertRaisesRegex(c.lc.Invalid,'mutated'):controller.start_native()
        controller.native_manifest=None
        with patch.object(controller,'_quiet',return_value=True),self.assertRaisesRegex(c.lc.Invalid,'mutated'):
            controller.freeze_native_manifest({'path':'/synthetic','sha256':'0'*64},'0'*64)
        controller.phases['native']=dict(sealed_monotonic=controller.clock())
        with self.assertRaisesRegex(c.lc.Invalid,'mutated'):controller.seal()
        self.assertFalse((controller.output/'resource.json').exists())

    def test_frozen_metal_rechecked_after_final_observer_join(self):
        controller=self.controller();directory=self.evidence(controller);self.freeze(controller)
        controller.phases['native']=dict(sealed_monotonic=controller.clock())
        controller.phase=None;controller.observer=Mock(is_alive=Mock(return_value=False))
        controller.observer.join.side_effect=lambda _timeout:(directory/'trace/late.raw').write_bytes(b'late')
        with patch.object(controller,'_quiet',return_value=True),self.assertRaisesRegex(c.lc.Invalid,'mutated'):
            controller.seal()
        self.assertFalse((controller.output/'resource.json').exists())


if __name__=='__main__':unittest.main()
