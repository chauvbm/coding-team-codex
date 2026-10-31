"""Replay published recovery snapshots, not native cancellation itself."""
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RECORD = Path(__file__).resolve().parents[1] / 'evaluations/2026-11-01-native-recovery'


class RecoveryRecordTests(unittest.TestCase):
    def test_pre_and_post_repair_pass_but_injected_regression_fails(self):
        for snapshot, expected in (('C1', 0), ('C2', 1), ('C3', 0)):
            with self.subTest(snapshot=snapshot), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copy2(RECORD / (snapshot + '-billing.txt'), root / 'billing.py')
                shutil.copy2(RECORD / 'acceptance.py', root / 'acceptance.py')
                run = subprocess.run([sys.executable, 'acceptance.py'], cwd=root,
                                     capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
                self.assertIn('Ran 4 tests', run.stderr)

    def test_original_dissent_and_intermediate_failure_remain_published(self):
        original = json.loads((RECORD / 'plan-review-original.json').read_text(encoding='utf-8'))
        self.assertEqual(original['verdict'], 'REJECTED')
        for snapshot, verdict in (('C1', 'PASS'), ('C2', 'FAIL'), ('C3', 'PASS')):
            data = json.loads((RECORD / ('finalQA-' + snapshot + '.json')).read_text(encoding='utf-8'))
            self.assertEqual(data['verdict'], verdict)
        record = json.loads((RECORD / 'recovery-record.json').read_text(encoding='utf-8'))
        self.assertEqual(record['counts']['recovery_total'], 2)
        self.assertEqual(record['delivery'], 'PASS')

    def test_published_snapshot_hashes_match_original_bytes(self):
        record = json.loads((RECORD / 'recovery-record.json').read_text(encoding='utf-8'))
        for filename, hashes in record['published_snapshots'].items():
            text = (RECORD / filename).read_text(encoding='utf-8')
            self.assertEqual(hashlib.sha256(text.encode('utf-8')).hexdigest(), hashes['published_utf8_lf_sha256'])
            lines = text.splitlines(keepends=True)
            endings = hashes['original_newline_sequences']
            self.assertEqual(len(lines), len(endings))
            original = ''.join((line[:-1] if line.endswith('\n') else line) + ending
                               for line, ending in zip(lines, endings))
            self.assertEqual(hashlib.sha256(original.encode('utf-8')).hexdigest(),
                             hashes['original_bytes_sha256'])


if __name__ == '__main__':
    unittest.main()
