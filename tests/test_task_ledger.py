"""Ledger regression tests; all persistent writes are temporary fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HELPER = Path(__file__).resolve().parents[1] / 'scripts' / 'task_ledger.py'
SPEC = importlib.util.spec_from_file_location('task_ledger', HELPER)
ledger = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ledger)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.root = Path(self.fixture.name)
        self.path = self.root / 'ledger.json'

    def initial(self, gated=False):
        return {'schema_version': 1, 'task_id': 'task', 'project_root': str(self.root),
                'operating_state': 'ACTIVE',
                'baseline': {'level': 'L2', 'spec': 's1', 'plan': 'p1', 'snapshot': 'tree1',
                             'gated': gated, 'scopes': ['all'], 'acceptance': ['meaningful behavior'],
                             'writers': ['writer'], 'required_reviews': [
                                 {'role': role, 'reviewer': role.lower(), 'scope': 'all'}
                                 for role in ('Architect', 'Developer', 'QA')] if gated else []},
                'counters': {**{k: {'reserved': 0, 'used': 0} for k in ledger.COUNTERS},
                             'defects': {}, 'recoveries': {}},
                'issues': [], 'reviews': [], 'transfers': [], 'work_items': [], 'continuation': None,
                'review_deadlines': {}}

    def start(self, gated=False):
        ledger.initialize(self.path, self.initial(gated))
        return ledger.read_json(self.path)

    def review(self, state, role='FinalQA', person='qa', **extra):
        review = {'id': 'review-' + str(len(state['reviews'])), 'reviewer': person,
                  'role': role, 'scope': 'all', 'spec': state['baseline']['spec'],
                  'plan': state['baseline']['plan'], 'snapshot': state['baseline']['snapshot'],
                  'verdict': 'APPROVED', 'evidence': 'observed targeted check',
                  'directly_verified': True, 'issues': [], 'verified_at': '2026-10-31T10:00:00+00:00'}
        review.update(extra)
        state['reviews'].append(review)
        return review

    def material(self, state):
        state['issues'].append({'id': 'bug', 'scope': 'all', 'severity': 'MAJOR', 'status': 'OPEN',
                                'closure_criteria': 'reproduce then verify repair', 'aliases': [],
                                'originators': [{'reviewer': 'original', 'statement': 'original dissent'}]})

    def transfer(self, state):
        state['review_deadlines']['QA/all'] = {'reviewer': 'original', 'role': 'QA',
                                               'scope': 'all', 'at': '2026-10-31T10:01:00+00:00'}
        for key in ('recovery_total',):
            state['counters'][key] = {'reserved': 1, 'used': 1}
        state['counters']['recoveries']['QA/all'] = {'reserved': 1, 'used': 1}
        state['transfers'].append({'id': 'replacement', 'role': 'QA', 'scope': 'all',
                                   'from': 'original', 'to': 'successor', 'reason': 'original unavailable at deadline',
                                   'unavailable': True, 'spec': 's1', 'plan': 'p1', 'snapshot': 'tree1',
                                   'recovery_key': 'QA/all', 'attempt': 1})

    def test_missing_final_qa_and_false_pass(self):
        state = self.start()
        state['operating_state'] = 'PASS'
        state['gate'] = 'PASS'  # caller claims never supply readiness
        result = ledger.readiness(state)
        self.assertEqual(result['delivery'], 'HOLD')
        self.assertIn('missing independent final QA: all', result['blockers'])

    def test_quota_pause_blocks_even_otherwise_ready_delivery(self):
        state = self.start()
        self.review(state)
        self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')
        state['operating_state'] = 'PAUSED'
        self.assertEqual(ledger.readiness(state)['gate'], 'HOLD')
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')

    def test_ready_auto_and_gated_current_independent_approvals(self):
        for gated in (False, True):
            with self.subTest(gated=gated):
                state = self.initial(gated)
                state.update(revision=0, audit=[])
                ledger.event(state, 'init', 'fixture')
                for role in (('Architect', 'Developer', 'QA') if gated else ()):
                    self.review(state, role, role.lower())
                self.review(state)
                self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')

    def test_implementation_developer_can_accept_design_but_cannot_be_qa(self):
        state = self.start(True)
        state['baseline']['writers'].extend(['developer', 'architect'])
        for role in ('Architect', 'Developer', 'QA'):
            self.review(state, role, role.lower())
        self.assertEqual(ledger.readiness(state)['gate'], 'PASS')
        self.review(state, 'FinalQA', 'developer')
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        self.review(state, 'FinalQA', 'independent')
        self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')
        self.review(state, 'QA', 'qa')
        state['baseline']['writers'].append('qa')
        self.assertEqual(ledger.readiness(state)['gate'], 'HOLD')

    def test_writer_originator_confirmation_requires_independent_qa_closure(self):
        state = self.start()
        self.material(state)
        state['issues'][0]['originators'] = [{'reviewer': 'writer', 'role': 'Developer', 'statement': 'original defect'}]
        confirmation = self.review(state, 'Developer', 'writer', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=confirmation['id'])
        self.review(state)
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        closure = self.review(state, 'QA', 'independent', issues=['bug'])
        state['issues'][0]['closed_by'] = closure['id']
        self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')

    def test_stale_pair_snapshot_and_self_qa_hold(self):
        state = self.start()
        review = self.review(state)
        for key, value in (('spec', 'old'), ('plan', 'old'), ('snapshot', 'old'), ('reviewer', 'writer'), ('directly_verified', False)):
            candidate = copy.deepcopy(state)
            candidate['reviews'][0][key] = value
            with self.subTest(key=key):
                self.assertEqual(ledger.readiness(candidate)['delivery'], 'HOLD')

    def test_summary_approval_does_not_erase_material_issue(self):
        state = self.start()
        self.material(state)
        self.review(state)
        self.assertIn('unresolved material issue: bug', ledger.readiness(state)['blockers'])
        state['issues'][0]['status'] = 'RESOLVED'
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')

    def test_valid_transfer_requires_direct_current_evidence_preserves_dissent(self):
        state = self.start()
        self.material(state)
        self.review(state, 'QA', 'original', verdict='REJECTED', issues=['bug'])
        ledger.update(self.path, state, 0, 'original finding')
        state = ledger.read_json(self.path)
        self.transfer(state)
        self.review(state)
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        closure = self.review(state, 'QA', 'successor', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=closure['id'])
        self.assertEqual(ledger.update(self.path, state, 1, 'successor verified reproduction')['delivery'], 'PASS')
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['issues'][0]['originators'][0]['statement'], 'original dissent')
        self.assertEqual(saved['reviews'][0]['verdict'], 'REJECTED')
        self.assertEqual(saved['audit'][1]['issue_states'][0]['status'], 'OPEN')
        for mutate in ('blind', 'stale', 'writer', 'exhausted', 'wrong_scope'):
            bad = copy.deepcopy(saved)
            if mutate == 'blind':
                bad['reviews'][-1]['directly_verified'] = False
            elif mutate == 'stale':
                bad['transfers'][0]['plan'] = 'old'
            elif mutate == 'writer':
                bad['baseline']['writers'].append('successor')
            elif mutate == 'wrong_scope':
                bad['transfers'][0]['role'] = 'Architect'
            else:
                limit = ledger.defaults()['recovery_per_role_or_operation']
                bad['counters']['recoveries']['QA/all'] = {'reserved': limit + 1, 'used': 1}
                bad['counters']['recovery_total']['reserved'] = limit + 1
            with self.subTest(mutate=mutate):
                self.assertEqual(ledger.readiness(bad)['delivery'], 'HOLD')

    def test_transfer_retains_original_deadline_and_rejects_late_verification(self):
        state = self.start()
        self.material(state)
        self.transfer(state)
        ledger.update(self.path, state, 0, 'original deadline retained')
        state = ledger.read_json(self.path)
        self.review(state)
        closure = self.review(state, 'QA', 'successor', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=closure['id'])
        self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')
        closure['verified_at'] = '2026-10-31T10:01:01+00:00'
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        state['review_deadlines']['QA/all']['at'] = '2026-10-31T10:02:00+00:00'
        with self.assertRaisesRegex(ValueError, 'deadline cannot be renewed'):
            ledger.update(self.path, state, 1, 'renewed successor deadline')
        state['review_deadlines'] = {}
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')

    def test_historical_closure_cannot_hide_latest_closer_or_other_dissent(self):
        state = self.start()
        self.material(state)
        self.review(state, 'QA', 'original', issues=['bug'])
        closure = self.review(state, 'QA', 'closer', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=closure['id'])
        self.review(state)
        self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')
        self.review(state, 'QA', 'closer', verdict='REJECTED', issues=['bug'])
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        self.review(state, 'QA', 'closer', issues=['bug'])
        self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')
        self.review(state, 'Developer', 'new-dissenter', verdict='REJECTED', issues=['bug'])
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        # Another role's summary approval does not settle the disputed issue.
        self.review(state, 'QA', 'new-dissenter', issues=['bug'])
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        self.review(state, 'Developer', 'new-dissenter', issues=['bug'])
        self.assertEqual(ledger.readiness(state)['delivery'], 'PASS')

    def test_chained_successors_cannot_renew_original_deadline_via_new_key(self):
        state = self.start()
        self.material(state)
        self.transfer(state)
        self.review(state)
        second = copy.deepcopy(state['transfers'][0])
        second.update(id='second-replacement', **{'from': 'successor', 'to': 'successor2'},
                      recovery_key='QA/new-key')
        state['transfers'].append(second)
        state['review_deadlines']['QA/new-key'] = {'reviewer': 'successor', 'role': 'QA',
                                                  'scope': 'all', 'at': '2026-10-31T10:05:00+00:00'}
        state['counters']['recoveries']['QA/new-key'] = {'reserved': 1, 'used': 1}
        state['counters']['recovery_total'] = {'reserved': 2, 'used': 2}
        closure = self.review(state, 'QA', 'successor2', issues=['bug'], verified_at='2026-10-31T10:04:00+00:00')
        state['issues'][0].update(status='RESOLVED', closed_by=closure['id'])
        with self.assertRaisesRegex(ValueError, 'chained reviewer replacement'):
            ledger.readiness(state)

    def test_history_attribution_counters_and_responsibilities_cannot_reset(self):
        state = self.start(True)
        self.material(state)
        self.review(state)
        state['counters']['repairs'] = {'reserved': 1, 'used': 1}
        ledger.update(self.path, state, 0, 'first batch')
        saved = ledger.read_json(self.path)
        for kind in ('issue', 'origin', 'review', 'audit', 'counter', 'writers', 'gate', 'responsibility', 'level'):
            candidate = copy.deepcopy(saved)
            if kind == 'issue': candidate['issues'] = []
            if kind == 'origin': candidate['issues'][0]['originators'][0]['statement'] = 'rewritten'
            if kind == 'review': candidate['reviews'] = []
            if kind == 'audit': candidate['audit'][0]['reason'] = 'rewrite'
            if kind == 'counter': candidate['counters']['repairs'] = {'reserved': 0, 'used': 0}
            if kind == 'writers': candidate['baseline']['writers'] = []
            if kind == 'gate': candidate['baseline']['gated'] = False
            if kind == 'responsibility': candidate['baseline']['required_reviews'] = []
            if kind == 'level': candidate['baseline']['level'] = 'L3'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                ledger.update(self.path, candidate, 1, 'attempted reset')
        self.assertEqual(ledger.read_json(self.path), saved)

    def test_checkpoint_claim_does_not_extend_recovery_or_grant_approval(self):
        state = self.start()
        state['counters']['repairs']['reserved'] = ledger.defaults()['repair_batches'] + 1
        self.review(state)
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')
        state['continuation'] = {'source': 'human message reference', 'scope': 'task', 'repair_extension': True}
        result = ledger.readiness(state)
        self.assertEqual(result['delivery'], 'PASS')
        self.assertFalse(result['authority_claims_verified'])
        state['counters']['recovery_total']['reserved'] = ledger.defaults()['recovery_total'] + 1
        self.assertEqual(ledger.readiness(state)['delivery'], 'HOLD')

    def test_ownership_and_path_escapes(self):
        state = self.start()
        def item(path, ident='work'):
            return {'id': ident, 'owner': 'writer', 'status': 'ACTIVE', 'files': [path]}
        for path in ('../outside.py', 'sub/../../outside.py', str(self.root / 'absolute.py'), 'C:\\outside.py', '\\outside.py', 'C:relative.py', '*.py', '.'):
            candidate = copy.deepcopy(state)
            candidate['work_items'] = [item(path)]
            with self.subTest(path=path), self.assertRaises(ValueError):
                ledger.validate(candidate)
        state['work_items'] = [item('source.py'), item('./SOURCE.py', 'second')]
        with self.assertRaises(ValueError):
            ledger.validate(state)
        state['work_items'][1]['status'] = 'DONE'
        ledger.validate(state)

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as external:
            try:
                (self.root / 'link').symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest('host cannot create symlinks')
            state = self.start()
            state['work_items'] = [{'id': 'work', 'owner': 'writer', 'status': 'ACTIVE', 'files': ['link/out.py']}]
            with self.assertRaises(ValueError):
                ledger.validate(state)

    def test_stale_concurrent_revision_preserves_winner(self):
        candidate = self.start()
        ledger.update(self.path, candidate, 0, 'winner')
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'stale expected revision'):
            ledger.update(self.path, candidate, 0, 'stale writer')
        self.assertEqual(self.path.read_bytes(), before)

    def test_concurrent_cli_writers_have_one_cas_winner(self):
        state = self.start()
        candidate = self.root / 'candidate.json'
        candidate.write_text(json.dumps(state), encoding='utf-8')
        command = [sys.executable, str(HELPER), 'update', '--ledger', str(self.path),
                   '--input', str(candidate), '--expected-revision', '0', '--reason', 'concurrent update']
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        try:
            results = [process.communicate(timeout=15) for process in processes]
            self.assertEqual(sorted(p.returncode for p in processes), [0, 2], results)
            self.assertEqual(ledger.read_json(self.path)['revision'], 1)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_changed_acceptance_and_reverted_versions_cannot_reuse_approvals(self):
        state = self.start()
        self.review(state)
        ledger.update(self.path, state, 0, 'original QA')
        state = ledger.read_json(self.path)
        state['baseline']['acceptance'].append('new behavior')
        with self.assertRaisesRegex(ValueError, 'fresh version'):
            ledger.update(self.path, state, 1, 'silent material change')
        state['baseline']['plan'] = 'p2'
        self.assertEqual(ledger.update(self.path, state, 1, 'new version')['delivery'], 'HOLD')
        state = ledger.read_json(self.path)
        state['baseline']['plan'] = 'p1'
        with self.assertRaisesRegex(ValueError, 'cannot be reused'):
            ledger.update(self.path, state, 2, 'reuse historical signoff')

    def test_corrupt_store_and_init_never_reset(self):
        for payload in (b'{broken', b'{}', b'[]', b'{"schema_version":1,"schema_version":1}'):
            self.path.write_bytes(payload)
            with self.assertRaises((ValueError, TypeError)):
                ledger.initialize(self.path, self.initial())
            with self.assertRaises((ValueError, TypeError)):
                ledger.update(self.path, {}, 0, 'reset')
            self.assertEqual(self.path.read_bytes(), payload)

    def test_atomic_failure_preserves_previous_state(self):
        state = self.start()
        before = self.path.read_bytes()
        # The imported helper retains its own os module namespace.
        with mock.patch('os.replace', side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                ledger.update(self.path, state, 0, 'failure')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.*.tmp')), [])
        ledger.update(self.path, state, 0, 'lock released')

    def test_cli_distinguishes_hold_malformed_and_ready(self):
        state = self.start()
        command = [sys.executable, str(HELPER), 'check', '--ledger', str(self.path)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(json.loads(result.stdout)['valid'])
        self.review(state)
        ledger.update(self.path, state, 0, 'verified')
        self.assertEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)
        self.path.write_text('{broken', encoding='utf-8')
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)['valid'])

    def test_cli_plan_gate_succeeds_before_final_delivery(self):
        state = self.start(True)
        for role in ('Architect', 'Developer', 'QA'):
            self.review(state, role, role.lower())
        ledger.update(self.path, state, 0, 'current plan approvals')
        command = [sys.executable, str(HELPER), 'check', '--ledger', str(self.path)]
        gate = subprocess.run(command + ['--stage', 'gate'], capture_output=True, text=True, timeout=15)
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        result = json.loads(gate.stdout)
        self.assertEqual(result['gate'], 'PASS')
        self.assertEqual(result['delivery'], 'HOLD')
        self.assertEqual(result['gate_blockers'], [])
        delivery = subprocess.run(command + ['--stage', 'delivery'], capture_output=True, text=True, timeout=15)
        self.assertEqual(delivery.returncode, 1, delivery.stdout + delivery.stderr)


if __name__ == '__main__':
    unittest.main()
