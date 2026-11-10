"""CPU input-boundary checks. No unreal mocks, UE execution or Native claims."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

from scripts.realism_import import common as c

REPO=Path(__file__).resolve().parents[1]
INDEX=REPO/'doc/evidence/universe-I20A/asset-index.json'


class RealismImportInputTests(unittest.TestCase):
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
