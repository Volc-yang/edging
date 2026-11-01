#!/usr/bin/env python3
"""Read-only proposed root-card Python pin. Never executes the interpreter or edits a card."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from run_universe_slice_acceptance import collect_python_pin

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('python_executable')
    args = parser.parse_args()
    pin = collect_python_pin(args.python_executable)
    print(json.dumps({'python_environment_pin': pin,
                      'runtime_files_suggestions': [pin['target'], pin['pyvenv_cfg']],
                      'environment_precondition': {'PYTHONHOME': 'unset-or-empty', 'PYTHONPATH': 'unset-or-empty'},
                      'scope': 'read-only proposed pin; root must approve/hash card; no mutable Host/plugin prebuild pins'},
                     sort_keys=True, indent=2))
