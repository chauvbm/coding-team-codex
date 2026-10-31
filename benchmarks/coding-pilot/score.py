"""Run the published pilot acceptance in a fresh Python process for one workspace."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest


class Results(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.outcomes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append({'test': test.id(), 'task': type(test).__name__, 'passed': True})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.outcomes.append({'test': test.id(), 'task': type(test).__name__, 'passed': False,
                              'detail': self._exc_info_to_string(error, test)})

    def addError(self, test, error):
        super().addError(test, error)
        self.outcomes.append({'test': test.id(), 'task': type(test).__name__, 'passed': False,
                              'detail': self._exc_info_to_string(error, test)})

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        if error:
            self.outcomes.append({'test': subtest.id(), 'task': type(test).__name__, 'passed': False,
                                  'detail': self._exc_info_to_string(error, test)})


def score(workspace, acceptance):
    sys.path.insert(0, str(workspace.resolve()))
    spec = importlib.util.spec_from_file_location('pilot_acceptance', acceptance)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    result = Results()
    started = time.perf_counter()
    suite.run(result)
    expected_tasks = {f'Task{i}' for i in range(1, 7)}
    tasks = {name: bool([r for r in result.outcomes if r['task'] == name]) and
                   all(r['passed'] for r in result.outcomes if r['task'] == name)
             for name in sorted(expected_tasks)}
    return {'tests_run': result.testsRun, 'tasks': tasks,
            'tasks_passed': sum(tasks.values()), 'task_count': len(tasks),
            'accepted': result.wasSuccessful() and all(tasks.values()) and not result.skipped,
            'acceptance_runtime_seconds': time.perf_counter() - started,
            'failures': [r for r in result.outcomes if not r['passed']],
            'skipped': len(result.skipped)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--acceptance', type=Path,
                        default=Path(__file__).with_name('acceptance') / 'test_contract.py')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker',
                                  '--workspace', str(args.workspace.resolve()), '--acceptance',
                                  str(args.acceptance.resolve())], capture_output=True, text=True,
                                 timeout=60)
        print(process.stdout, end='')
        if process.stderr:
            print(process.stderr, file=sys.stderr, end='')
        return process.returncode
    try:
        result = score(args.workspace, args.acceptance)
        print(json.dumps(result, indent=2))
        return 0 if result['accepted'] else 1
    except Exception as error:
        print(json.dumps({'accepted': False, 'execution_error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
