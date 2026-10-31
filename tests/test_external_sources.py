"""Replay external-source artifacts and verify provenance, never dispatch agents."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

PILOT = Path(__file__).resolve().parents[1] / 'benchmarks/external-sources'


def digest(path):
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


class ExternalSourceTests(unittest.TestCase):
    def test_baseline_rejected_and_four_frozen_conditions_pass(self):
        for mode in ('baseline', 'control', 'solo', 'auto', 'full_team'):
            with self.subTest(mode=mode):
                workspace = PILOT / ('baseline' if mode == 'baseline' else 'results/' + mode)
                run = subprocess.run([sys.executable, str(PILOT / 'score.py'), '--workspace', str(workspace)],
                                     capture_output=True, text=True, timeout=50)
                result = json.loads(run.stdout)
                self.assertEqual(run.returncode, 1 if mode == 'baseline' else 0, result)
                self.assertEqual(result['accepted'], mode != 'baseline')
                self.assertEqual(result['tests_run'], 18)
                self.assertEqual(result['skipped'], 0)

    def test_source_license_contract_acceptance_and_result_hashes(self):
        sources = json.loads((PILOT / 'sources.json').read_text(encoding='utf-8'))
        for source in sources:
            for filename, metadata in source['files'].items():
                path = PILOT / 'baseline' / source['name'] / filename
                self.assertEqual(digest(path), metadata['sha256_utf8_lf'])
                original = path.read_text(encoding='utf-8')
                if metadata['original_line_endings'] == 'CRLF':
                    original = original.replace('\n', '\r\n')
                self.assertEqual(hashlib.sha256(original.encode('utf-8')).hexdigest(), metadata['sha256'])
        summary = json.loads((PILOT / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(digest(PILOT / 'TASK.md'), summary['contract_sha256_utf8_lf'])
        self.assertEqual(digest(PILOT / 'acceptance.py'), summary['acceptance_sha256_utf8_lf'])
        for mode, run in summary['runs'].items():
            for filename, expected in run['file_sha256_utf8_lf'].items():
                self.assertEqual(digest(PILOT / 'results' / mode / filename), expected)
                if filename.endswith('/LICENSE'):
                    self.assertEqual(digest(PILOT / 'results' / mode / filename), digest(PILOT / 'baseline' / filename))


if __name__ == '__main__':
    unittest.main()
