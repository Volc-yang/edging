"""Expose the CPU-only I17 regressions to the repository CI discovery command."""
import importlib.util
from pathlib import Path

_path=Path(__file__).resolve().parents[1]/'doc/evidence/universe-I17C/test_native_completion.py'
_spec=importlib.util.spec_from_file_location('i17_native_completion_checks',_path)
_module=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
CompletionTests=_module.CompletionTests
