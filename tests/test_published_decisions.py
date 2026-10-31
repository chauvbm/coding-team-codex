"""Replay historical decision artifacts; not a fresh model evaluation."""
import hashlib
import json
from pathlib import Path
import unittest

from check_behavioral_results import check_results

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'evaluations/2026-10-31-decisions'


class PublishedDecisionTests(unittest.TestCase):
    def test_historical_decisions_satisfy_their_unchanged_fixtures(self):
        for fixture, responses in (
            ('behavioral_cases.json', 'behavioral_responses.json'),
            ('sequential_cases.json', 'sequential_responses.json'),
            ('reviewer_transfer_cases.json', 'reviewer_transfer_responses.json'),
        ):
            with self.subTest(fixture=fixture):
                cases = json.loads((ROOT / 'tests' / fixture).read_text(encoding='utf-8'))['cases']
                results = json.loads((RECORD / responses).read_text(encoding='utf-8'))
                self.assertEqual(check_results(cases, results), [])

    def test_recorded_hashes_use_utf8_with_lf_newlines(self):
        summary = json.loads((RECORD / 'summary.json').read_text(encoding='utf-8'))
        for result in summary['results']:
            with self.subTest(file=result['response_file']):
                # read_text normalizes CRLF on Windows, matching committed Git blobs.
                data = (RECORD / result['response_file']).read_text(encoding='utf-8').encode('utf-8')
                self.assertEqual(hashlib.sha256(data).hexdigest(), result['sha256'])


if __name__ == '__main__':
    unittest.main()
