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


if __name__ == "__main__":
    unittest.main()
