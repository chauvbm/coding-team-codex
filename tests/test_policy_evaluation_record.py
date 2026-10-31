"""Preserve raw evaluation scores and their exact published inputs/outputs."""
import hashlib
import json
from pathlib import Path
import unittest
from check_behavioral_results import check_results

RECORD = Path(__file__).resolve().parents[1] / 'evaluations/2026-11-01-policy'


class PolicyEvaluationRecordTests(unittest.TestCase):
    def test_v3_frozen_scores_are_reproducible(self):
        record = RECORD.parent / '2026-11-01-protocol-v3'
        fixture_path = record / 'fixture.json'
        fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
        freeze = json.loads((record / 'freeze.json').read_text(encoding='utf-8'))
        summary = json.loads((record / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(fixture['protocol_version'], 3)
        self.assertEqual(len(fixture['cases']), 16)
        self.assertEqual(hashlib.sha256(fixture_path.read_text(encoding='utf-8').encode()).hexdigest(),
                         freeze['fixture_sha256_lf'])
        self.assertEqual(summary['source_commit'], freeze['source_commit'])
        for name, run in summary['runs'].items():
            with self.subTest(condition=name):
                path = record / (name + '-responses.json')
                self.assertEqual(hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest(),
                                 run['response_sha256_utf8_lf'])
                responses = json.loads(path.read_text(encoding='utf-8'))
                failures = check_results(fixture['cases'], responses)
                self.assertEqual(failures, run['failures'])
                failed_ids = sorted({failure.split(':')[0] for failure in failures})
                self.assertEqual(failed_ids, run['failed_case_ids'])
                self.assertEqual(len(responses), run['responses'])
                self.assertEqual(len(fixture['cases']), run['cases'])
                self.assertEqual(len(fixture['cases']) - len(failed_ids), run['passed'])

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
