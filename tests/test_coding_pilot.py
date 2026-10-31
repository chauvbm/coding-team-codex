"""Replay actual pilot snapshots and verify acceptance cannot hide skipped cases."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'benchmarks/coding-pilot'


class CodingPilotTests(unittest.TestCase):
    def run_score(self, workspace, acceptance=None):
        command = [sys.executable, str(PILOT / 'score.py'), '--workspace', str(workspace)]
        if acceptance is not None:
            command += ['--acceptance', str(acceptance)]
        process = subprocess.run(command, capture_output=True, text=True, timeout=60)
        return process.returncode, json.loads(process.stdout)

    def test_seeded_baseline_fails_every_task(self):
        code, result = self.run_score(PILOT / 'baseline')
        self.assertEqual(code, 1)
        self.assertEqual(result['tasks_passed'], 0)
        self.assertEqual(result['tests_run'], 36)

    def test_published_snapshots_pass_with_matching_hashes(self):
        import hashlib
        summary = json.loads((PILOT / 'results/summary.json').read_text())
        for mode in ('solo', 'auto', 'full_team'):
            with self.subTest(mode=mode):
                workspace = PILOT / 'results' / mode
                self.assertEqual(hashlib.sha256((workspace / 'utilities.py').read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                                 summary['runs'][mode]['implementation_sha256'])
                code, result = self.run_score(workspace)
                self.assertEqual(code, 0, result)
                self.assertEqual(result['tasks_passed'], 6)
                self.assertEqual(result['tests_run'], 36)

    def test_skipped_acceptance_and_import_error_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            acceptance = Path(temporary) / 'test_cases.py'
            source = 'import unittest\n'
            for number in range(1, 7):
                source += (f'class Task{number}(unittest.TestCase):\n'
                           ' def test_ok(self): pass\n'
                           ' @unittest.skip("not executed")\n'
                           ' def test_missing(self): pass\n')
            acceptance.write_text(source, encoding='utf-8')
            code, result = self.run_score(PILOT / 'baseline', acceptance)
            self.assertEqual(code, 1)
            self.assertFalse(result['accepted'])
            self.assertEqual(result['skipped'], 6)
            acceptance.write_text('raise RuntimeError("fixture failed import")', encoding='utf-8')
            code, result = self.run_score(PILOT / 'baseline', acceptance)
            self.assertEqual(code, 2)
            self.assertIn('execution_error', result)
