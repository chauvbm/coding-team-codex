"""Preserve raw evaluation scores and their exact published inputs/outputs."""
import hashlib
import json
from pathlib import Path
import unittest
from check_behavioral_results import check_results

RECORD = Path(__file__).resolve().parents[1] / 'evaluations/2026-11-01-policy'


class PolicyEvaluationRecordTests(unittest.TestCase):
    def test_hashes_and_raw_failures_are_reproducible(self):
        summary = json.loads((RECORD / 'summary.json').read_text(encoding='utf-8'))
        for name, run in summary['runs'].items():
            with self.subTest(batch=name):
                fixture_path = RECORD / (('realistic' if name == 'control' else name) + '-fixture.json')
                response_path = RECORD / (name + '-responses.json')
                for path, expected in ((fixture_path, run['fixture_sha256']),
                                       (response_path, run['response_sha256'])):
                    self.assertEqual(hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest(), expected)
                fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
                responses = json.loads(response_path.read_text(encoding='utf-8'))
                self.assertEqual(check_results(fixture['cases'], responses), run['failures'])


if __name__ == '__main__':
    unittest.main()
