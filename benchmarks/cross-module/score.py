"""Replay coordinator-held cross-module acceptance without network or model calls."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TEST_NAMES = (
    'test_public_error_export',
    'test_parser_strict_success_preserves_bindings',
    'test_parser_error_context_with_leading_blank',
    'test_parser_does_not_reject_duplicates',
    'test_parser_permissive_recovery',
    'test_variables_missing_is_typed',
    'test_variables_defaults_none_empty_and_literals',
    'test_variables_atoms_can_be_reused',
    'test_variables_permissive_unchanged',
    'test_values_ordered_resolution_and_valueless',
    'test_first_duplicate_context',
    'test_valueless_duplicate_is_duplicate',
    'test_earliest_undefined_wins_later_parse',
    'test_multiline_undefined_context',
    'test_forward_reference_and_self_reference',
    'test_os_snapshot_precedes_source_read',
    'test_override_false_resolution_and_successful_commit',
    'test_override_true_resolution_and_successful_commit',
    'test_late_parse_error_has_zero_writes',
    'test_late_duplicate_error_has_zero_writes',
    'test_late_undefined_error_has_zero_writes',
    'test_skipped_override_key_still_validates',
    'test_no_interpolation_keeps_literals_checks_duplicates',
    'test_no_interpolation_still_checks_syntax',
    'test_dotenv_direct_atomic_and_failure_not_cached',
    'test_path_encoding_precedence_and_stream_ownership',
    'test_empty_valueless_and_disabled_return_behavior',
    'test_permissive_public_warning_duplicates_and_undefined',
)
EXPECTED_IDS = tuple(sorted('cross_module_acceptance.StrictDotenvAcceptance.' + name
    for name in TEST_NAMES))


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


class Result(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.started = []
        self.passed = []

    def startTest(self, test):
        self.started.append(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.passed.append(test.id())
        super().addSuccess(test)


def worker(workspace):
    sys.dont_write_bytecode = True
    captured = io.StringIO()
    try:
        os.environ['CROSS_MODULE_WORKSPACE'] = str(workspace)
        with redirect_stdout(captured), redirect_stderr(captured):
            spec = importlib.util.spec_from_file_location('cross_module_acceptance',
                Path(__file__).with_name('acceptance.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            suite = unittest.defaultTestLoader.loadTestsFromModule(module)
            ids = tuple(sorted(test.id() for test in flatten(suite)))
            if ids != EXPECTED_IDS:
                raise RuntimeError('acceptance inventory changed')
            result = Result()
            suite.run(result)
        accepted = (result.wasSuccessful() and tuple(sorted(result.started)) == EXPECTED_IDS
            and tuple(sorted(result.passed)) == EXPECTED_IDS and not result.skipped
            and not result.expectedFailures and not result.unexpectedSuccesses)
        failures = result.failures + result.errors + result.expectedFailures
        details = {test.id(): detail[-8000:] for test, detail in failures}
        skipped = {test.id(): reason for test, reason in result.skipped}
        rows = []
        for identifier in EXPECTED_IDS:
            status = ('passed' if identifier in result.passed else
                'skipped' if identifier in skipped else
                'failed' if identifier in details else 'not_completed')
            row = {'test': identifier, 'status': status}
            if identifier in details:
                row['detail'] = details[identifier]
            if identifier in skipped:
                row['detail'] = skipped[identifier]
            rows.append(row)
        payload = {'accepted': accepted, 'tests_expected': len(EXPECTED_IDS),
            'tests_run': result.testsRun, 'tests_passed': len(result.passed),
            'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures),
            'unexpected_successes': len(result.unexpectedSuccesses), 'tests': rows,
            'fixture_failures': [{'test': test.id(), 'detail': detail[-8000:]}
                for test, detail in failures if test.id() not in EXPECTED_IDS],
            'captured_output': captured.getvalue()[-8000:]}
        return payload, 0 if accepted else 1
    except BaseException as error:
        return {'accepted': False, 'execution_error': type(error).__name__ + ': ' + str(error),
            'tests_expected': len(EXPECTED_IDS),
            'captured_output': captured.getvalue()[-8000:]}, 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.worker:
        payload, code = worker(workspace)
    else:
        try:
            with tempfile.TemporaryDirectory(prefix='cross-module-score-') as directory:
                completed = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                    '--worker', '--workspace', str(workspace)], cwd=directory,
                    capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
            payload = json.loads(completed.stdout)
            if not isinstance(payload, dict) or not isinstance(payload.get('accepted'), bool):
                raise ValueError('worker did not emit an acceptance object')
            code = completed.returncode
            if code not in (0, 1, 2) or (payload['accepted'] != (code == 0)):
                payload = {'accepted': False, 'execution_error': 'worker exit/result mismatch',
                    'worker_exit': code}
                code = 2
            if completed.stderr:
                payload['worker_stderr'] = completed.stderr[-8000:]
        except subprocess.TimeoutExpired:
            payload, code = {'accepted': False,
                'execution_error': 'acceptance exceeded 45 seconds'}, 2
        except BaseException as error:
            payload, code = {'accepted': False,
                'execution_error': type(error).__name__ + ': ' + str(error)}, 2
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
