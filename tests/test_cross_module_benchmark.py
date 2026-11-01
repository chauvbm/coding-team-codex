"""Replay frozen repeated trials; this never dispatches agents or measures benefit."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

RECORD = Path(__file__).resolve().parents[1] / 'benchmarks/cross-module'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def replay(workspace):
    result = subprocess.run([sys.executable, str(RECORD / 'score.py'), '--workspace', str(workspace)],
                            capture_output=True, text=True, encoding='utf-8', timeout=55)
    return result.returncode, json.loads(result.stdout)


class CrossModuleBenchmarkTests(unittest.TestCase):
    def test_frozen_contract_and_upstream_hashes(self):
        freeze = read_json(RECORD / 'freeze.json')
        for name, expected in freeze['sha256'].items():
            with self.subTest(path=name):
                content = (RECORD / name).read_text(encoding='utf-8').encode()
                self.assertEqual(hashlib.sha256(content).hexdigest(), expected)
        source = read_json(RECORD / 'sources.json')
        self.assertEqual(source['commit'], freeze['source_commit'])
        for name, metadata in source['files'].items():
            content = (RECORD / 'baseline' / name).read_text(encoding='utf-8').encode()
            self.assertEqual(hashlib.sha256(content).hexdigest(), metadata['sha256_utf8_lf'])

    def test_unmodified_upstream_rejects_requested_feature(self):
        code, actual = replay(RECORD / 'baseline')
        self.assertEqual(code, 1)
        self.assertFalse(actual['accepted'])
        self.assertEqual(actual['tests_run'], 28)
        self.assertEqual(actual['tests_passed'], 2)
        self.assertEqual(actual['skipped'], 0)

    def test_frozen_trial_artifacts_and_outcomes(self):
        summary = read_json(RECORD / 'summary.json')
        freeze = read_json(RECORD / 'freeze.json')
        names = {f'{condition}-{i:02d}' for condition in ('auto', 'control') for i in range(1, 6)}
        self.assertEqual(set(summary['trials']), names)
        self.assertEqual(freeze['trials_per_condition'], 5)
        for name, trial in summary['trials'].items():
            with self.subTest(trial=name):
                workspace = RECORD / 'results' / name
                for path, expected in trial['final_sha256_utf8_lf'].items():
                    content = (workspace / path).read_text(encoding='utf-8').encode()
                    self.assertEqual(hashlib.sha256(content).hexdigest(), expected)
                published = read_json(workspace / 'acceptance.json')
                content = (workspace / 'acceptance.json').read_text(encoding='utf-8').encode()
                self.assertEqual(hashlib.sha256(content).hexdigest(), trial['acceptance_sha256_utf8_lf'])
                code, actual = replay(workspace)
                self.assertEqual(code, trial['acceptance_exit_code'])
                for key in ('accepted', 'tests_expected', 'tests_run', 'tests_passed', 'skipped',
                            'expected_failures', 'unexpected_successes'):
                    self.assertEqual(actual.get(key), published.get(key))
                    self.assertEqual(actual.get(key), trial['outcome'].get(key))
                self.assertEqual([(r['test'], r['status']) for r in actual.get('tests', [])],
                                 [(r['test'], r['status']) for r in published.get('tests', [])])
                if 'tests' in actual:
                    self.assertEqual(len(actual['tests']), 28)
                else:
                    self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
