"""Replay the frozen repository pilot; this never dispatches model workers."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

PILOT = Path(__file__).resolve().parents[1] / 'benchmarks/repository-maintenance'


class RepositoryMaintenanceTests(unittest.TestCase):
    def score(self, workspace):
        run = subprocess.run([sys.executable, str(PILOT / 'score.py'), '--workspace', str(workspace)],
                             capture_output=True, text=True, timeout=120)
        return run.returncode, json.loads(run.stdout)

    def test_unmodified_repository_baseline_is_rejected(self):
        code, result = self.score(PILOT / 'baseline')
        self.assertEqual(code, 1)
        self.assertFalse(result['passed_available_checks'])
        self.assertTrue(result['failures'])

    def test_all_published_implementations(self):
        for mode in ('solo', 'auto', 'full_team'):
            with self.subTest(mode=mode):
                code, result = self.score(PILOT / 'results' / mode)
                self.assertEqual(code, 0, result)
                self.assertEqual(result['tests_run'], 15)
                self.assertTrue(result['passed_available_checks'])
                if os.name != 'nt':
                    self.assertEqual(result['skipped'], 0, result)
                    self.assertTrue(result['accepted'])

    def test_frozen_contract_acceptance_and_implementation_hashes(self):
        summary = json.loads((PILOT / 'results/summary.json').read_text(encoding='utf-8'))
        def digest(path):
            return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
        self.assertEqual(digest(PILOT / 'TASK.md'), summary['contract_sha256'])
        self.assertEqual(digest(PILOT / 'acceptance.py'), summary['acceptance_sha256'])
        for mode, run in summary['runs'].items():
            for filename, expected in run['implementation_sha256'].items():
                self.assertEqual(digest(PILOT / 'results' / mode / 'scripts' / filename), expected)


if __name__ == '__main__':
    unittest.main()
