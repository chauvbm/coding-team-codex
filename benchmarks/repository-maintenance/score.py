"""Replay frozen maintenance acceptance in a separate process; no agent invocation."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        run = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker',
            '--workspace', str(args.workspace.resolve())], capture_output=True, text=True, timeout=120)
        print(run.stdout, end='')
        if run.stderr:
            print(run.stderr, file=sys.stderr, end='')
        return run.returncode
    try:
        os.environ['MAINTENANCE_WORKSPACE'] = str(args.workspace.resolve())
        spec = importlib.util.spec_from_file_location('maintenance_acceptance', Path(__file__).with_name('acceptance.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromModule(module).run(result)
        passed = result.wasSuccessful() and result.testsRun == 15
        print(json.dumps({'tests_run': result.testsRun, 'skipped': len(result.skipped),
            'passed_available_checks': passed, 'accepted': passed and not result.skipped,
            'failures': [{'test': test.id(), 'detail': detail} for test, detail in result.failures + result.errors],
            'coverage_limits': [detail for _, detail in result.skipped]}, indent=2))
        return 0 if passed else 1
    except Exception as error:
        print(json.dumps({'accepted': False, 'execution_error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
