import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class UnrealMacLauncherTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        scripts = self.repository / "scripts"
        scripts.mkdir(parents=True)
        self.launcher = scripts / "launch_edgeworld_ue_mac.sh"
        source = Path(__file__).resolve().parents[1] / "scripts" / self.launcher.name
        shutil.copy2(source, self.launcher)
        project = self.repository / "engine_platforms/unreal/EdgeWorldHost"
        project.mkdir(parents=True)
        (project / "EdgeWorldHost.uproject").write_text("{}")
        worker = self.repository / "engine/edgeworld_worker/abstract_causal_worker.py"
        worker.parent.mkdir(parents=True)
        worker.write_text("")
        engine = self.root / "UE/Engine"
        build = engine / "Build/BatchFiles/Mac/Build.sh"
        build.parent.mkdir(parents=True)
        build.write_text('#!/bin/bash\ntouch "$MOCK_BUILD_STARTED"\nexit "${MOCK_BUILD_EXIT:-0}"\n')
        (engine / "Build/Build.version").write_text(json.dumps({
            "MajorVersion": 5, "MinorVersion": 8, "PatchVersion": 3, "Changelist": 58210709,
        }))
        (engine / "Build/InstalledBuild.txt").touch()
        editor = engine / "Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
        editor.parent.mkdir(parents=True)
        editor.write_text(
            '#!/bin/bash\nprintf "%s\\n" "$@" > "$MOCK_ARGUMENTS"\n'
            'for argument in "$@"; do\n'
            'case "$argument" in -abslog=*) logfile=${argument#-abslog=};; esac\n'
            'done\nprintf "%s\\n" '
            '"Engine is initialized. Leaving FEngineLoop::Init()" '
            '"Causal world: Space advances;" '
            '"Causal world stg-demo observed tick 0, revision 0" > "$logfile"\n'
        )
        editor.chmod(0o755)
        commands = self.root / "commands"
        commands.mkdir()
        uname = commands / "uname"
        uname.write_text("#!/bin/bash\necho Darwin\n")
        uname.chmod(0o755)
        self.arguments = self.root / "editor-arguments.txt"
        self.build_started = self.root / "build-started"
        self.environment = dict(os.environ, UE5_ROOT=str(engine.parent),
                                EDGEWORLD_CAUSAL_PYTHON=sys.executable,
                                MOCK_ARGUMENTS=str(self.arguments),
                                MOCK_BUILD_STARTED=str(self.build_started),
                                PATH=str(commands) + os.pathsep + os.environ["PATH"])

    def launch(self, *arguments):
        return subprocess.run(["/bin/bash", str(self.launcher), *arguments],
                              env=self.environment, capture_output=True, text=True, timeout=15)

    def test_default_only_builds(self):
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.arguments.exists())
        self.assertIn("runtime_not_tested", result.stdout)

    def test_launch_keeps_engine_default(self):
        result = self.launch("--launch")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("-norenderthread", self.arguments.read_text().splitlines())
        self.assertNotIn("-EWDiagPreflushViewport", self.arguments.read_text().splitlines())
        self.assertIn("render_mode=engine_default", result.stdout)
        self.assertIn("viewport_preflush=disabled", result.stdout)

    def test_workaround_is_explicit_and_disclosed(self):
        result = self.launch("--launch", "--no-render-thread")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        arguments = self.arguments.read_text().splitlines()
        self.assertEqual(arguments.count("-norenderthread"), 1)
        self.assertNotIn("-EWDiagPreflushViewport", arguments)
        self.assertIn("experimental_workaround_not_root_fix", result.stdout)
        self.assertIn("performance_unmeasured_may_degrade", result.stdout)

    def test_failed_build_does_not_launch_workaround(self):
        self.environment["MOCK_BUILD_EXIT"] = "23"
        result = self.launch("--launch", "--no-render-thread")
        self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
        self.assertFalse(self.arguments.exists())
        self.assertIn("UE was not launched", result.stdout)

    def test_viewport_preflush_is_explicit_and_forwarded_once(self):
        result = self.launch("--launch", "--viewport-preflush", "--viewport-preflush")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        arguments = self.arguments.read_text().splitlines()
        self.assertEqual(arguments.count("-EWDiagPreflushViewport"), 1)
        self.assertNotIn("-norenderthread", arguments)
        self.assertIn("render_mode=engine_default; viewport_preflush=enabled", result.stdout)
        self.assertIn("default_rendering_threads_retained", result.stdout)
        self.assertIn("limited_project_workaround_not_root_fix", result.stdout)
        self.assertIn("performance_cost_unmeasured", result.stdout)
        self.assertNotIn("render_mode=no_render_thread", result.stdout)

    def test_conflicting_modes_rejected_before_build_or_launch(self):
        for mode in ("--build-only", "--launch"):
            for flags in (("--viewport-preflush", "--no-render-thread"),
                          ("--no-render-thread", "--viewport-preflush")):
                with self.subTest(mode=mode, flags=flags):
                    result = self.launch(mode, *flags)
                    self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
                    self.assertIn("mutually exclusive", result.stderr)
                    self.assertFalse(self.build_started.exists())
                    self.assertFalse(self.arguments.exists())

    def test_failed_build_does_not_launch_viewport_preflush(self):
        self.environment["MOCK_BUILD_EXIT"] = "23"
        result = self.launch("--launch", "--viewport-preflush")
        self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
        self.assertTrue(self.build_started.exists())
        self.assertFalse(self.arguments.exists())
        self.assertIn("UE was not launched", result.stdout)
        self.assertNotIn("viewport_preflush=enabled", result.stdout)

    def test_build_only_with_viewport_preflush_does_not_claim_runtime(self):
        result = self.launch("--build-only", "--viewport-preflush")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.build_started.exists())
        self.assertFalse(self.arguments.exists())
        self.assertIn("runtime_not_tested", result.stdout)
        self.assertNotIn("viewport_preflush=enabled", result.stdout)



class UniverseMacLauncherTest(unittest.TestCase):
    """Synthetic launcher mocks, not a real worker/world or runtime provenance.

    The export mock supplies only public metadata shaped like a deployment; no
    physics records are relabelled and no production fake switch is introduced.
    """
    def setUp(self):
        UnrealMacLauncherTest.setUp(self)
        self.owner = self.root / 'owner config.json'
        self.owner.write_text('PRIVATE CONFIG MUST ONLY BE READ BY REAL I10 OWNER LOADER')
        module = self.repository / 'engine/universe_authority/worker.py'
        module.parent.mkdir(parents=True)
        (module.parent / '__init__.py').write_text('')
        (module.parent.parent / '__init__.py').write_text('')
        module.write_text('''import json,os,sys
assert sys.argv[1:]==['--owner-config',os.environ['MOCK_OWNER'],'--print-public-pins']
x={'domain':'edgeworld.universe.authority','version':'0.2','profile':'composite-rigid-support.v0.2','world_id':'test-world','authority_root':'/mock-authority/test-world','trust_algorithm':'local-hmac-sha256.v0.2','trust_anchor':'a'*64,'artifact_class':'genesis-runtime','expected_build':'b'*64,'expected_options':'c'*64,'principal':'mock-owner','allowed_actions':['physics_step','retain_snapshot']}
mode=os.environ.get('MOCK_PINS_MODE','')
if mode=='synthetic':x['artifact_class']='synthetic-contract-only'
if mode=='extra':x['can_initialize']=True
raw=json.dumps(x,sort_keys=True,separators=(',',':'))
if mode=='noncanonical':raw=json.dumps(x)
if mode=='duplicate':raw=raw.replace('"version":"0.2"','"version":"0.2","version":"0.2"')
print(raw)
''')
        self.environment.update(EDGEWORLD_UNIVERSE_PYTHON=sys.executable,MOCK_OWNER=str(self.owner),
                                EDGEWORLD_UNIVERSE_WORKER='/wrong/stale-worker',
                                EDGEWORLD_UNIVERSE_INITIALIZE='1')
        self.child_environment=self.root/'child-env.json'
        editor=self.root/'UE/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
        editor.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys
pathlib.Path(os.environ['MOCK_ARGUMENTS']).write_text('\\n'.join(sys.argv[1:]))
pathlib.Path(os.environ['MOCK_CHILD_ENV']).write_text(json.dumps({k:v for k,v in os.environ.items() if k.startswith('EDGEWORLD_UNIVERSE_')}))
log=next(x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('-abslog='))
pathlib.Path(log).write_text('Engine is initialized. Leaving FEngineLoop::Init()\\nUniverse world: 1 weak;\\nUniverse world test-world observed tick 0, revision 0\\n')
''')
        editor.chmod(0o755)
        self.environment['MOCK_CHILD_ENV']=str(self.child_environment)

    def launch(self, *arguments):
        return UnrealMacLauncherTest.launch(self, *arguments)

    def test_universe_explicit_mode_and_safe_public_pins(self):
        result=self.launch('--launch','--universe','--owner-config',str(self.owner))
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        args=self.arguments.read_text();env=json.loads(self.child_environment.read_text())
        self.assertIn('EdgeWorldUniverseGameMode',args)
        self.assertNotIn('EdgeWorldCausalGameMode',args)
        self.assertEqual('0',env['EDGEWORLD_UNIVERSE_INITIALIZE'])
        self.assertEqual(str((self.repository/'engine/universe_authority/worker.py').resolve()),env['EDGEWORLD_UNIVERSE_WORKER'])
        self.assertEqual(str(self.owner),env['EDGEWORLD_UNIVERSE_OWNER_CONFIG'])
        pins=Path(env['EDGEWORLD_UNIVERSE_PINS']);raw=pins.read_bytes()
        self.assertFalse(raw.endswith(b'\n'))
        self.assertEqual(0o600,pins.stat().st_mode&0o777)
        self.assertEqual(0o700,pins.parent.stat().st_mode&0o777)
        self.assertEqual(1,pins.stat().st_nlink)
        self.assertEqual(12,len(json.loads(raw)))
        trace=Path(env['EDGEWORLD_UNIVERSE_TRACE'])
        self.assertTrue(trace.is_dir())
        self.assertEqual(0o700,trace.stat().st_mode&0o777)
        self.assertEqual([],list(trace.iterdir()))
        import hashlib
        self.assertEqual(hashlib.sha256(raw).hexdigest(),env['EDGEWORLD_UNIVERSE_PINS_SHA256'])
        self.assertNotIn('PRIVATE CONFIG',result.stdout+result.stderr+raw.decode())
        self.assertIn('validated_observation_seen',result.stdout)

    def test_explicit_initialize_requires_both_flags(self):
        result=self.launch('--launch','--universe','--owner-config',str(self.owner),'--universe-initialize')
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertEqual('1',json.loads(self.child_environment.read_text())['EDGEWORLD_UNIVERSE_INITIALIZE'])

    def test_private_option_without_universe_rejected_before_build(self):
        for flags in (('--owner-config',str(self.owner)),('--universe-initialize',)):
            with self.subTest(flags=flags):
                r=self.launch('--launch',*flags)
                self.assertEqual(64,r.returncode)
                self.assertFalse(self.build_started.exists())
                self.assertFalse(self.arguments.exists())

    def test_universe_missing_owner_rejected_before_build(self):
        r=self.launch('--universe','--launch')
        self.assertEqual(64,r.returncode)
        self.assertFalse(self.build_started.exists())

    def test_bad_pins_rejected_before_build_or_editor(self):
        for mode in ('synthetic','extra','noncanonical','duplicate'):
            with self.subTest(mode=mode):
                self.environment['MOCK_PINS_MODE']=mode
                r=self.launch('--launch','--universe','--owner-config',str(self.owner))
                self.assertNotEqual(0,r.returncode)
                self.assertFalse(self.build_started.exists())
                self.assertFalse(self.arguments.exists())

    def test_universe_trace_run_is_exclusive(self):
        roots=[]
        for unused in range(2):
            result=self.launch('--launch','--universe','--owner-config',str(self.owner))
            self.assertEqual(0,result.returncode,result.stdout+result.stderr)
            trace=Path(json.loads(self.child_environment.read_text())['EDGEWORLD_UNIVERSE_TRACE'])
            roots.append(trace)
            (trace/'preserved.bin').write_bytes(b'original raw\x00\xff')
        self.assertNotEqual(roots[0],roots[1])
        self.assertEqual(b'original raw\x00\xff',(roots[0]/'preserved.bin').read_bytes())

    def test_universe_build_only_does_not_export_or_launch(self):
        r=self.launch('--universe')
        self.assertEqual(0,r.returncode,r.stdout+r.stderr)
        self.assertFalse(self.arguments.exists())
        self.assertFalse(self.child_environment.exists())


if __name__ == "__main__":
    unittest.main()
