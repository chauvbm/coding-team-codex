"""Coordinator-only acceptance, frozen before benchmark dispatch."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

WORKSPACE = Path(os.environ['MAINTENANCE_WORKSPACE']).resolve()


class LedgerOperations(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'ledger.json'
        self.helper = WORKSPACE / 'scripts/task_ledger.py'
        self.state = {'schema_version': 1, 'task_id': 'test', 'project_root': str(self.root),
            'operating_state': 'ACTIVE', 'baseline': {'level': 'L2', 'spec': 's1', 'plan': 'p1',
            'snapshot': 'tree', 'gated': False, 'scopes': ['all'], 'acceptance': ['observable'],
            'writers': ['writer'], 'required_reviews': []},
            'counters': {**{k: {'reserved': 0, 'used': 0} for k in
                ('revisions', 'repairs', 'diagnostics', 'recovery_total')}, 'defects': {}, 'recoveries': {}},
            'issues': [], 'reviews': [], 'transfers': [], 'work_items': [],
            'continuation': None, 'review_deadlines': {}}
        self.input = self.root / 'input.json'
        self.input.write_text(json.dumps(self.state), encoding='utf-8')
        self.assertEqual(self.call('init', '--input', str(self.input)).returncode, 0)

    def call(self, action, *args):
        return subprocess.run([sys.executable, str(self.helper), action, '--ledger', str(self.path),
            *(['--reason', 'acceptance'] if action != 'check' else []), *args],
            capture_output=True, text=True, timeout=15)

    def review(self, **changes):
        return {'id': 'r1', 'reviewer': 'qa', 'role': 'FinalQA', 'scope': 'all', 'spec': 's1',
            'plan': 'p1', 'snapshot': 'tree', 'verdict': 'APPROVED', 'evidence': 'direct check',
            'directly_verified': True, 'issues': [], 'verified_at': '2026-10-31T12:00:00+00:00', **changes}

    def record(self, record, revision=0):
        self.input.write_text(json.dumps(record), encoding='utf-8')
        return self.call('record-review', '--input', str(self.input), '--expected-revision', str(revision))

    def test_record_review_preserves_audit_and_makes_delivery_ready(self):
        before = json.loads(self.path.read_text())
        result = self.record(self.review())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(saved['audit'][:1], before['audit'])
        self.assertEqual(len(saved['audit']), 2)
        self.assertEqual(self.call('check').returncode, 0)

    def test_stale_review_is_saved_but_cannot_pass(self):
        result = self.record(self.review(snapshot='old'))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.call('check').returncode, 1)

    def test_writer_cannot_be_independent_qa(self):
        self.assertEqual(self.record(self.review(reviewer='writer')).returncode, 0)
        self.assertEqual(self.call('check').returncode, 1)

    def test_rejected_review_remains_after_later_approval(self):
        first = self.review(verdict='REJECTED')
        self.assertEqual(self.record(first).returncode, 0)
        self.assertEqual(self.record(self.review(id='r2'), 1).returncode, 0)
        self.assertEqual(json.loads(self.path.read_text())['reviews'][0], first)

    def test_unknown_field_and_stale_revision_do_not_write(self):
        before = self.path.read_bytes()
        self.assertEqual(self.record(self.review(audit=[])).returncode, 2)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.record(self.review(), revision=9).returncode, 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_budget_reserve_then_use(self):
        for revision, phase in enumerate(('reserve', 'use')):
            result = self.call('consume-budget', '--counter', 'repairs', '--phase', phase,
                '--expected-revision', str(revision))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.path.read_text())['counters']['repairs'], {'reserved': 1, 'used': 1})

    def test_budget_invalid_input_or_unreserved_use_does_not_write(self):
        before = self.path.read_bytes()
        for args in (('--amount', '0'), ('--amount', '-1'), ('--counter', 'nope'),
                     ('--phase', 'use'), ('--phase', 'reset')):
            result = self.call('consume-budget', '--counter', 'repairs', '--expected-revision', '0', *args)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(self.path.read_bytes(), before)

    def test_budget_excess_is_recorded_and_holds(self):
        result = self.call('consume-budget', '--counter', 'repairs', '--amount', '5', '--expected-revision', '0')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.path.read_text())['counters']['repairs']['used'], 5)
        self.assertEqual(self.call('check').returncode, 1)

    def test_two_concurrent_revisions_have_one_winner(self):
        cmd = [sys.executable, str(self.helper), 'consume-budget', '--ledger', str(self.path),
            '--counter', 'repairs', '--expected-revision', '0', '--reason', 'race']
        workers = [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        try:
            for worker in workers:
                worker.communicate(timeout=15)
            self.assertEqual(sorted(w.returncode for w in workers), [0, 2])
            self.assertEqual(json.loads(self.path.read_text())['revision'], 1)
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                    worker.communicate(timeout=5)


class SafeExport(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('exporter', WORKSPACE / 'scripts/export_evaluation_inputs.py')
        self.exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.exporter)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'skill'
        self.root.mkdir()
        (self.root / 'SKILL.md').write_text('entry')
        (self.root / 'scripts').mkdir()
        self.cases = self.root.parent / 'cases.json'
        self.cases.write_text(json.dumps({'instructions': 'decide', 'cases': [{'id': 'one', 'input': 'task', 'checks': {'secret': True}}]}))
        self.out = self.root.parent / 'export'

    def link(self, source, target, directory=False):
        try:
            source.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            self.skipTest('symlink unavailable: ' + str(error))

    def reject(self):
        with self.assertRaises(ValueError):
            self.exporter.export_inputs(self.root, self.cases, self.out)
        self.assertFalse(self.out.exists(), 'rejection must precede destination creation')

    def test_normal_export_omits_oracle(self):
        self.exporter.export_inputs(self.root, self.cases, self.out)
        payload = json.loads((self.out / 'inputs/01.json').read_text())
        self.assertNotIn('checks', payload['case'])
        self.assertFalse((self.out / 'skill/tests').exists())

    def test_linked_entry_rejected_before_destination(self):
        (self.root / 'SKILL.md').unlink()
        self.link(self.root / 'SKILL.md', self.cases)
        self.reject()

    def test_nested_outside_link_rejected(self):
        self.link(self.root / 'scripts' / 'secret.json', self.cases)
        self.reject()

    def test_linked_directory_rejected(self):
        self.link(self.root / 'references', self.root / 'scripts', directory=True)
        self.reject()

    def test_broken_link_rejected(self):
        self.link(self.root / 'scripts' / 'broken', self.root / 'absent')
        self.reject()

    def test_in_root_link_also_rejected(self):
        self.link(self.root / 'scripts' / 'copy', self.root / 'SKILL.md')
        self.reject()


if __name__ == '__main__':
    unittest.main(verbosity=2)
