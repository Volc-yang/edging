"""CPU input-boundary checks. No unreal mocks, UE execution or Native claims."""
from pathlib import Path
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.realism_import import common as c

REPO=Path(__file__).resolve().parents[1]
INDEX=REPO/'doc/evidence/universe-I20A/asset-index.json'


class RealismImportInputTests(unittest.TestCase):
    def test_i22_probe_binding_is_exact_and_incomplete_results_reject(self):
        # Synthetic JSON consistency cases only: these never represent Native API success.
        job={'probe_job_sha256':'a'*64,'recipe_sha256':'b'*64,'source_scripts':{'reviewed.py':'c'*64}}
        probe={'format':'edgeworld.i22.native-import-result.v0.1','mode':'probe','status':'PASS',
            'job_sha256':'a'*64,'recipe_sha256':'b'*64,'source_index_sha256':c.INDEX_SHA,
            'source_scripts':job['source_scripts'],'capability':{'complete':True,
                'subsystem':{'fixture':'synthetic-only'},'mesh_before':{'fixture':1},'mesh_restored':{'fixture':1},
                'texture_calls':[{'fixture':'synthetic-only'}],'material_links':{'fixture':1},
                'actual_alpha_disconnected':True,'actual_alpha_restored':True,
                'texture_restoration':[{'before':{'fixture':1},'after':{'fixture':1}} for _ in range(3)],
                'original_fixture_getters_before':{'fixture':1},'original_fixture_getters_after':{'fixture':1},
                'pipeline_observed':{'collision':False,'build_nanite':False}}}
        self.assertTrue(c.check_probe_result(probe,job))
        for key,value in (('status','FAIL'),('mode','import'),('job_sha256','d'*64),('source_scripts',{'changed.py':'e'*64})):
            with self.assertRaises(ValueError):c.check_probe_result({**probe,key:value},job)
        with self.assertRaisesRegex(ValueError,'actual getter evidence missing'):
            c.check_probe_result({**probe,'capability':{**probe['capability'],'texture_calls':[]}},job)
        with self.assertRaisesRegex(ValueError,'texture restoration'):
            c.check_probe_result({**probe,'capability':{**probe['capability'],'texture_restoration':[]}},job)
        recipe=json.loads((REPO/'scripts/realism_import/recipe.json').read_bytes())
        self.assertIs(recipe['import_policy']['build_nanite'],False)
        self.assertEqual(c.OUTPUT.name,'I23-20261110-import')

    def test_file_map_keeps_regular_nested_files_and_requires_root(self):
        with tempfile.TemporaryDirectory(prefix='i23-map-',dir=Path(tempfile.gettempdir()).resolve()) as td:
            root=Path(td);self.assertEqual(c.file_map(root),{})
            (root/'nested').mkdir();(root/'first').write_bytes(b'abc');(root/'nested/second').write_bytes(b'defg')
            self.assertEqual(c.file_map(root),{'first':{'bytes':3,'sha256':c.sha(b'abc')},
                'nested/second':{'bytes':4,'sha256':c.sha(b'defg')}})
            with self.assertRaises(FileNotFoundError):c.file_map(root/'absent')
            with self.assertRaisesRegex(ValueError,'root must be a directory'):c.file_map(root/'first')

    def test_file_map_rejects_links_and_special_files(self):
        tmp_root=Path('/private/tmp') if Path('/private/tmp').is_dir() else Path(tempfile.gettempdir()).resolve()
        with tempfile.TemporaryDirectory(prefix='i23-map-',dir=tmp_root) as td:
            root=Path(td);(root/'regular').write_bytes(b'ok')
            link=root/'link';link.symlink_to(root/'regular')
            with self.assertRaisesRegex(ValueError,'non-regular'):c.file_map(root)
            link.unlink()
            if hasattr(os,'mkfifo'):
                fifo=root/'fifo';os.mkfifo(fifo)
                with self.assertRaisesRegex(ValueError,'non-regular'):c.file_map(root)
                fifo.unlink()
            # Actual AF_UNIX bind is forbidden in this sandbox. Inject only its lstat
            # type bits, and device type bits, to cover rejection without network IPC.
            actual_stat=os.lstat
            for special in (stat.S_IFSOCK,stat.S_IFCHR,stat.S_IFBLK):
                def special_stat(path,*args,**kwargs):
                    result=actual_stat(path,*args,**kwargs)
                    if Path(path)==root/'regular':
                        values=list(result);values[0]=special|0o600;return os.stat_result(values)
                    return result
                with patch.object(c.os,'lstat',side_effect=special_stat):
                    with self.assertRaisesRegex(ValueError,'non-regular'):c.file_map(root)

    def test_file_map_propagates_enumeration_stat_and_open_errors(self):
        with tempfile.TemporaryDirectory(prefix='i23-map-',dir=Path(tempfile.gettempdir()).resolve()) as td:
            root=Path(td);nested=root/'nested';nested.mkdir();(root/'first').write_bytes(b'ok')
            actual_scan=os.scandir
            def deny_nested(path):
                if Path(path)==nested:raise PermissionError('enumeration denied')
                return actual_scan(path)
            with patch.object(c.os,'scandir',side_effect=deny_nested):
                with self.assertRaisesRegex(PermissionError,'enumeration denied'):c.file_map(root)
            actual_stat=os.lstat
            def deny_file(path,*args,**kwargs):
                if Path(path)==root/'first':raise PermissionError('stat denied')
                return actual_stat(path,*args,**kwargs)
            with patch.object(c.os,'lstat',side_effect=deny_file):
                with self.assertRaisesRegex(PermissionError,'stat denied'):c.file_map(root)
            with patch.object(c.os,'open',side_effect=PermissionError('read open denied')):
                with self.assertRaisesRegex(PermissionError,'read open denied'):c.file_map(root)
            actual_fdopen=os.fdopen
            class ReadFailure:
                def __init__(self,fd,*args):self.stream=actual_fdopen(fd,*args)
                def __enter__(self):self.stream.__enter__();return self
                def __exit__(self,*args):return self.stream.__exit__(*args)
                def fileno(self):return self.stream.fileno()
                def read(self):raise OSError('stream read failed')
            with patch.object(c.os,'fdopen',side_effect=ReadFailure):
                with self.assertRaisesRegex(OSError,'stream read failed'):c.file_map(root)

    def test_real_pinned_source_files(self):
        if not c.SOURCE.is_dir():self.skipTest('I20 DevSSD source root unavailable on this host')
        self.assertEqual(len(c.validate_sources(INDEX)['files']),20)

    def test_missing_alpha_and_corruption_rejected(self):
        if not c.SOURCE.is_dir():self.skipTest('I20 DevSSD source root unavailable on this host')
        index=c.validate_sources(INDEX)
        with tempfile.TemporaryDirectory(prefix='i21-source-negative-',dir=Path(tempfile.gettempdir()).resolve()) as td:
            root=Path(td)
            for entry in index['files']:
                dest=c.child(root,entry['path']);dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(c.child(c.SOURCE,entry['path']),dest)
            alpha=root/'assets/fern_02/textures/fern_02_alpha_2k.png';original=alpha.read_bytes();alpha.unlink()
            with self.assertRaisesRegex(ValueError,'missing source:.*alpha'):c.validate_sources(INDEX,root)
            alpha.write_bytes(original)
            data=bytearray(alpha.read_bytes());data[-1]^=1;alpha.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'source identity mismatch:.*alpha'):c.validate_sources(INDEX,root)

    def test_paths_json_and_exclusive_evidence(self):
        with tempfile.TemporaryDirectory(prefix='i21-path-negative-',dir=Path(tempfile.gettempdir()).resolve()) as td:
            root=Path(td)
            for relative in ('../escape','/absolute','x\\y'):
                with self.assertRaises(ValueError):c.child(root,relative)
            link=root/'link';link.symlink_to(root/'absent')
            with self.assertRaises(ValueError):c.child(root,'link')
            path=root/'result.json';c.write_new(path,{'status':'first'})
            with self.assertRaises(FileExistsError):c.write_new(path,{'status':'overwrite'})
            self.assertEqual(c.load(path),{'status':'first'})
            for raw in ('{"v":1e999}','{"v":1,"v":2}'):
                path.write_text(raw)
                with self.assertRaises(ValueError):c.load(path)

    def test_startup_and_environment_refuse_user_injection(self):
        env=c.clean_environment({'HOME':'/unchanged','PYTHONPATH':'bad','UE_PYTHONPATH':'bad',
            'EDGEWORLD_TEST':'bad','DYLD_INSERT_LIBRARIES':'bad','PATH':'bad'})
        self.assertEqual(env,{'HOME':'/unchanged','PATH':'/usr/bin:/bin:/usr/sbin:/sbin'})
        with tempfile.TemporaryDirectory(prefix='i21-startup-negative-',dir=Path(tempfile.gettempdir()).resolve()) as td:
            root=Path(td);engine=root/'Engine';(engine/'Plugins').mkdir(parents=True)
            content=engine/'Content/Python';content.mkdir(parents=True);(content/'init_unreal.py').write_text('# installed fixture, never executed\n')
            doc=root/'Documents';user=doc/'UnrealEngine/Python';user.mkdir(parents=True)
            inventory=c.startup_inventory(engine,doc)
            self.assertEqual(len(inventory['scripts']),1)
            (user/'init_unreal.py').write_text('raise RuntimeError("must never execute")\n')
            with self.assertRaisesRegex(ValueError,'unreviewed user/project startup'):c.startup_inventory(engine,doc)

    def test_enabled_plugin_requirements_rejected(self):
        with tempfile.TemporaryDirectory(prefix='i21-plugin-negative-',dir=Path(tempfile.gettempdir()).resolve()) as td:
            engine=Path(td)/'Engine';plugins=engine/'Plugins';plugins.mkdir(parents=True)
            (plugins/'A.uplugin').write_text(json.dumps({'Plugins':[{'Name':'B','Enabled':True}]}))
            path=plugins/'B.uplugin';path.write_text('\ufeff{"Description":"literal , } stays", "Modules":[],}')
            descriptor={'DisableEnginePluginsByDefault':True,'Plugins':[{'Name':'A','Enabled':True}]}
            self.assertEqual(set(c.plugin_inventory(descriptor,engine)),{'A','B'})
            path.write_text(json.dumps({'PythonRequirements':[{'Requirements':['unexpected-package']}]}))
            with self.assertRaisesRegex(ValueError,'pip requirements: B'):c.plugin_inventory(descriptor,engine)


if __name__=='__main__':unittest.main()
