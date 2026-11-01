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

    def fixture_readiness(self, state):
        # Older structural tests author raw reviews in memory instead of using a
        # recording transaction. Model that transaction's binding explicitly.
        candidate = copy.deepcopy(state)
        for review in candidate['reviews']:
            if (review['role'] in ledger.FINAL_ROLES and 'freshness' not in review
                    and ledger.current(review, candidate['baseline'])):
                review['freshness'] = ledger.freshness(candidate, self.path)
        return ledger.readiness(candidate, self.path)

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
        result = self.fixture_readiness(state)
        self.assertEqual(result['delivery'], 'HOLD')
        self.assertIn('missing independent final QA: all', result['blockers'])

    def test_quota_pause_blocks_even_otherwise_ready_delivery(self):
        state = self.start()
        self.review(state)
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        state['operating_state'] = 'PAUSED'
        self.assertEqual(self.fixture_readiness(state)['gate'], 'HOLD')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')

    def test_ready_auto_and_gated_current_independent_approvals(self):
        for gated in (False, True):
            with self.subTest(gated=gated):
                state = self.initial(gated)
                state.update(revision=0, audit=[])
                ledger.event(state, 'init', 'fixture')
                for role in (('Architect', 'Developer', 'QA') if gated else ()):
                    self.review(state, role, role.lower())
                self.review(state)
                self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')

    def test_gated_core_roles_cannot_share_one_declared_identity(self):
        state = self.initial(True)
        for request in state['baseline']['required_reviews']:
            request['reviewer'] = 'same-person'
        for role in ('Architect', 'Developer', 'QA', 'FinalQA'):
            self.review(state, role, 'same-person')
        with self.assertRaisesRegex(ValueError, 'distinct identities'):
            ledger.initialize(self.path, state)
        self.assertFalse(self.path.exists())

    def test_unfinished_required_work_blocks_delivery_only(self):
        state = self.start()
        self.review(state)
        for status in ('PENDING', 'ACTIVE', 'DONE', 'CANCELLED'):
            state['work_items'] = [{'id': 'job', 'owner': 'writer', 'files': ['a.py'], 'status': status}]
            result = self.fixture_readiness(state)
            self.assertEqual(result['gate'], 'PASS')
            self.assertEqual(result['delivery'], 'PASS' if status == 'DONE' else 'HOLD')
        state['work_items'][0]['required'] = False
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')

    def test_required_work_cannot_be_deleted_or_cancelled_to_evade_completion(self):
        state = self.start()
        state['work_items'] = [{'id': 'job', 'owner': 'writer', 'files': ['a.py'], 'status': 'ACTIVE'}]
        ledger.update(self.path, state, 0, 'assign')
        state = ledger.read_json(self.path)
        for change in ('delete', 'optional', 'cancel', 'changed_acceptance'):
            candidate = copy.deepcopy(state)
            work = candidate['work_items'][0]
            if change == 'delete': candidate['work_items'] = []
            elif change == 'optional': work['required'] = False
            else:
                work['status'] = 'CANCELLED'
                if change == 'changed_acceptance':
                    work['cancellation'] = {'reason': 'scope removed', 'authority': 'user request U1',
                        'spec': 's1', 'plan': 'p1', 'snapshot': 'tree1', 'acceptance_unchanged': False}
            before = self.path.read_bytes()
            with self.subTest(change=change), self.assertRaises(ValueError):
                ledger.update(self.path, candidate, 1, 'invalid cancellation')
            self.assertEqual(self.path.read_bytes(), before)
        state['work_items'][0].update(status='CANCELLED', cancellation={
            'reason': 'duplicate investigation not needed', 'authority': 'user request U1',
            'spec': 's1', 'plan': 'p1', 'snapshot': 'tree1', 'acceptance_unchanged': True})
        ledger.update(self.path, state, 1, 'record cancellation claim')
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['audit'][-1]['work_states'], saved['work_items'])

    def test_final_qa_rejection_cannot_be_hidden_by_another_reviewer(self):
        state = self.start()
        self.review(state, person='qa-a', verdict='REJECTED')
        self.review(state, person='qa-b')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, person='qa-a', snapshot='old')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, person='qa-a', directly_verified=False)
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, person='qa-a')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')

    def test_final_qa_transfer_requires_current_independent_direct_successor(self):
        state = self.start()
        self.review(state, person='original', verdict='REJECTED')
        self.transfer(state)
        state['review_deadlines']['QA/all']['role'] = 'FinalQA'
        state['transfers'][0]['role'] = 'FinalQA'
        self.review(state, person='successor')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        state['reviews'][-1]['verified_at'] = '2026-10-31T10:02:00+00:00'
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        state['reviews'][-1]['verified_at'] = '2026-10-31T10:00:00+00:00'
        state['baseline']['writers'].append('successor')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')

    def legacy_duplicate(self):
        state = self.start(True)
        for request in state['baseline']['required_reviews']:
            request['reviewer'] = 'same'
        # Emulate a ledger accepted before distinct identities were enforced.
        for role in ('Architect', 'Developer', 'QA', 'FinalQA'):
            self.review(state, role, 'same')
        self.path.write_text(json.dumps(state), encoding='utf-8')
        return state

    def repair_payload(self):
        return {'spec': 's2', 'plan': 'p2', 'snapshot': 'tree2', 'required_reviews': [
            {'role': role, 'reviewer': role.lower(), 'scope': 'all'}
            for role in ('Architect', 'Developer', 'QA')]}

    def test_legacy_duplicate_check_and_explicit_migration_preserve_evidence(self):
        old = self.legacy_duplicate()
        self.assertEqual(self.fixture_readiness(old)['gate'], 'HOLD')
        backup = self.root / 'backup.json'
        before = self.path.read_bytes()
        result = ledger.repair_responsibilities(self.path, self.repair_payload(), 0, 'correct old assignment', backup)
        saved = ledger.read_json(self.path)
        self.assertEqual(backup.read_bytes(), before)
        self.assertEqual(saved['reviews'], old['reviews'])
        self.assertEqual(saved['audit'][:1], old['audit'])
        self.assertEqual(saved['counters'], old['counters'])
        self.assertEqual(saved['audit'][-1]['previous_required_reviews'], old['baseline']['required_reviews'])
        self.assertEqual(result['gate'], 'HOLD')  # old approvals never carried forward
        for role in ('Architect', 'Developer', 'QA', 'FinalQA'):
            self.review(saved, role, role.lower())
        ledger.update(self.path, saved, 1, 'new explicit current reviews')
        self.assertEqual(self.fixture_readiness(ledger.read_json(self.path))['delivery'], 'PASS')

    def test_migration_rejects_stale_missing_roles_reused_versions_and_backup_overwrite(self):
        self.legacy_duplicate()
        before = self.path.read_bytes()
        backup = self.root / 'backup.json'
        for change in ('stale', 'missing_role', 'same_version', 'extra_field', 'backup_exists'):
            payload = self.repair_payload()
            revision = 1 if change == 'stale' else 0
            if change == 'missing_role': payload['required_reviews'].pop()
            if change == 'same_version': payload.update(spec='s1', plan='p1', snapshot='tree1')
            if change == 'extra_field': payload['verification'] = 'self_check'
            if change == 'backup_exists': backup.write_text('preserve')
            with self.subTest(change=change), self.assertRaises((ValueError, FileExistsError)):
                ledger.repair_responsibilities(self.path, payload, revision, 'invalid migration', backup)
            self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(backup.read_text(), 'preserve')

    def test_migration_atomic_failure_keeps_original_and_exact_backup(self):
        self.legacy_duplicate()
        before = self.path.read_bytes()
        backup = self.root / 'backup.json'
        with mock.patch('os.replace', side_effect=OSError('fail')):
            with self.assertRaises(OSError):
                ledger.repair_responsibilities(self.path, self.repair_payload(), 0, 'repair', backup)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(backup.read_bytes(), before)
        ledger.repair_responsibilities(self.path, self.repair_payload(), 0, 'retry', self.root / 'retry.json')

    def test_reviewer_transfer_cannot_merge_independent_core_roles(self):
        state = self.start(True)
        for role in ('Architect', 'Developer', 'QA'):
            self.review(state, role, role.lower())
        self.review(state)
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        self.transfer(state)
        state['review_deadlines']['QA/all']['reviewer'] = 'qa'
        state['transfers'][0].update({'from': 'qa', 'to': 'architect'})
        self.review(state, 'QA', 'architect')
        result = self.fixture_readiness(state)
        self.assertEqual(result['gate'], 'HOLD')
        self.assertIn('effective gated core representatives are not independent: all', result['blockers'])
        # A genuinely separate successor can reassess, without requiring a fourth plan role.
        state['transfers'][0]['to'] = 'successor'
        self.review(state, 'QA', 'successor')
        self.review(state, 'FinalQA', 'successor')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')

    def test_self_check_policy_supports_solo_but_reports_its_kind(self):
        state = self.initial()
        state['baseline']['verification'] = 'self_check'
        result = ledger.initialize(self.path, state)
        self.assertEqual(result['gate'], 'PASS')
        self.assertEqual(result['delivery'], 'HOLD')
        state = ledger.read_json(self.path)
        review = self.review(state, 'SelfCheck', 'writer')
        result = ledger.update(self.path, state, 0, 'direct SOLO verification')
        self.assertEqual(result['delivery'], 'PASS')
        self.assertEqual(result['verification'], 'self_check')
        self.assertFalse(result['authority_claims_verified'])
        saved = ledger.read_json(self.path)
        self.assertEqual([{k: v for k, v in row.items() if k != 'freshness'}
                          for row in saved['reviews']], [review])
        self.assertEqual(saved['reviews'][0]['freshness'], {'files': [], 'work': []})
        self.assertEqual(len(saved['audit']), 2)

    def test_self_check_needs_current_direct_latest_evidence_per_scope(self):
        state = self.initial()
        state['baseline'].update(verification='self_check', scopes=['all', 'other'])
        ledger.initialize(self.path, state)
        state = ledger.read_json(self.path)
        self.review(state, 'SelfCheck', 'writer')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        other = self.review(state, 'SelfCheck', 'writer', scope='other', directly_verified=False)
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        other['directly_verified'] = True
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        self.review(state, 'SelfCheck', 'writer', verdict='REJECTED')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, 'SelfCheck', 'writer', snapshot='old-tree')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, 'SelfCheck', 'writer')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        state['baseline']['snapshot'] = 'tree2'
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')

    def test_self_check_does_not_close_a_material_issue_or_masquerade_as_qa(self):
        state = self.initial()
        state['baseline']['verification'] = 'self_check'
        ledger.initialize(self.path, state)
        state = ledger.read_json(self.path)
        self.material(state)
        closure = self.review(state, 'SelfCheck', 'writer', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=closure['id'])
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.assertIn('unresolved material issue: bug', self.fixture_readiness(state)['blockers'])
        closure = self.review(state, 'QA', 'original', issues=['bug'])
        state['issues'][0]['closed_by'] = closure['id']
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')

    def test_self_check_rejects_required_gate_or_review_responsibilities(self):
        for gated in (False, True):
            state = self.initial(gated)
            state['baseline']['verification'] = 'self_check'
            if not gated:
                state['baseline']['required_reviews'] = [{'role': 'QA', 'reviewer': 'qa', 'scope': 'all'}]
            with self.subTest(gated=gated), self.assertRaisesRegex(ValueError, 'self_check requires ungated'):
                ledger.initialize(self.path, state)
            self.assertFalse(self.path.exists())

    def test_legacy_verification_and_explicit_independence_cannot_be_downgraded(self):
        state = self.start()
        self.review(state, 'SelfCheck', 'writer')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.assertEqual(self.fixture_readiness(state)['verification'], 'independent_final_qa')
        before = self.path.read_bytes()
        state['baseline'].update(verification='self_check', plan='p2')
        with self.assertRaisesRegex(ValueError, 'cannot be downgraded'):
            ledger.update(self.path, state, 0, 'evade legacy independent QA')
        self.assertEqual(self.path.read_bytes(), before)

    def test_self_check_can_upgrade_and_cannot_return_to_self_review(self):
        state = self.initial()
        state['baseline']['verification'] = 'self_check'
        ledger.initialize(self.path, state)
        state = ledger.read_json(self.path)
        self.review(state, 'SelfCheck', 'writer')
        state['baseline']['verification'] = 'independent_final_qa'
        with self.assertRaisesRegex(ValueError, 'fresh version'):
            ledger.update(self.path, state, 0, 'silent policy change')
        state['baseline']['plan'] = 'p2'
        result = ledger.update(self.path, state, 0, 'upgrade independent review')
        self.assertEqual(result['delivery'], 'HOLD')
        state = ledger.read_json(self.path)
        self.review(state)
        result = ledger.update(self.path, state, 1, 'independent current check')
        self.assertEqual(result['delivery'], 'PASS')
        state = ledger.read_json(self.path)
        state['baseline'].update(verification='self_check', plan='p3')
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'cannot be downgraded'):
            ledger.update(self.path, state, 2, 'discard independent requirement')
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_verification_policy_rejects_cli_write_without_mutation(self):
        state = self.start()
        before = self.path.read_bytes()
        for policy in ('none', False, None, {}, []):
            candidate = copy.deepcopy(state)
            candidate['baseline'].update(verification=policy, plan='p2')
            path = self.root / 'candidate.json'
            path.write_text(json.dumps(candidate), encoding='utf-8')
            result = subprocess.run([sys.executable, str(HELPER), 'update', '--ledger', str(self.path),
                '--input', str(path), '--expected-revision', '0', '--reason', 'invalid policy'],
                capture_output=True, text=True, timeout=15)
            with self.subTest(policy=policy):
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(self.path.read_bytes(), before)

    def test_implementation_developer_can_accept_design_but_cannot_be_qa(self):
        state = self.start(True)
        state['baseline']['writers'].extend(['developer', 'architect'])
        for role in ('Architect', 'Developer', 'QA'):
            self.review(state, role, role.lower())
        self.assertEqual(self.fixture_readiness(state)['gate'], 'PASS')
        self.review(state, 'FinalQA', 'developer')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, 'FinalQA', 'independent')
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        self.review(state, 'QA', 'qa')
        state['baseline']['writers'].append('qa')
        self.assertEqual(self.fixture_readiness(state)['gate'], 'HOLD')

    def test_writer_originator_confirmation_requires_independent_qa_closure(self):
        state = self.start()
        self.material(state)
        state['issues'][0]['originators'] = [{'reviewer': 'writer', 'role': 'Developer', 'statement': 'original defect'}]
        confirmation = self.review(state, 'Developer', 'writer', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=confirmation['id'])
        self.review(state)
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        closure = self.review(state, 'QA', 'independent', issues=['bug'])
        state['issues'][0]['closed_by'] = closure['id']
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')

    def test_stale_pair_snapshot_and_self_qa_hold(self):
        state = self.start()
        review = self.review(state)
        for key, value in (('spec', 'old'), ('plan', 'old'), ('snapshot', 'old'), ('reviewer', 'writer'), ('directly_verified', False)):
            candidate = copy.deepcopy(state)
            candidate['reviews'][0][key] = value
            with self.subTest(key=key):
                self.assertEqual(self.fixture_readiness(candidate)['delivery'], 'HOLD')

    def test_summary_approval_does_not_erase_material_issue(self):
        state = self.start()
        self.material(state)
        self.review(state)
        self.assertIn('unresolved material issue: bug', self.fixture_readiness(state)['blockers'])
        state['issues'][0]['status'] = 'RESOLVED'
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')

    def test_valid_transfer_requires_direct_current_evidence_preserves_dissent(self):
        state = self.start()
        self.material(state)
        self.review(state, 'QA', 'original', verdict='REJECTED', issues=['bug'])
        ledger.update(self.path, state, 0, 'original finding')
        state = ledger.read_json(self.path)
        self.transfer(state)
        self.review(state)
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
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
                self.assertEqual(self.fixture_readiness(bad)['delivery'], 'HOLD')

    def test_transfer_retains_original_deadline_and_rejects_late_verification(self):
        state = self.start()
        self.material(state)
        self.transfer(state)
        ledger.update(self.path, state, 0, 'original deadline retained')
        state = ledger.read_json(self.path)
        self.review(state)
        closure = self.review(state, 'QA', 'successor', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=closure['id'])
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        closure['verified_at'] = '2026-10-31T10:01:01+00:00'
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        state['review_deadlines']['QA/all']['at'] = '2026-10-31T10:02:00+00:00'
        with self.assertRaisesRegex(ValueError, 'deadline cannot be renewed'):
            ledger.update(self.path, state, 1, 'renewed successor deadline')
        state['review_deadlines'] = {}
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')

    def test_historical_closure_cannot_hide_latest_closer_or_other_dissent(self):
        state = self.start()
        self.material(state)
        self.review(state, 'QA', 'original', issues=['bug'])
        closure = self.review(state, 'QA', 'closer', issues=['bug'])
        state['issues'][0].update(status='RESOLVED', closed_by=closure['id'])
        self.review(state)
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        self.review(state, 'QA', 'closer', verdict='REJECTED', issues=['bug'])
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, 'QA', 'closer', issues=['bug'])
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')
        self.review(state, 'Developer', 'new-dissenter', verdict='REJECTED', issues=['bug'])
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        # Another role's summary approval does not settle the disputed issue.
        self.review(state, 'QA', 'new-dissenter', issues=['bug'])
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        self.review(state, 'Developer', 'new-dissenter', issues=['bug'])
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'PASS')

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
            self.fixture_readiness(state)

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
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')
        state['continuation'] = {'source': 'human message reference', 'scope': 'task', 'repair_extension': True}
        result = self.fixture_readiness(state)
        self.assertEqual(result['delivery'], 'PASS')
        self.assertFalse(result['authority_claims_verified'])
        state['counters']['recovery_total']['reserved'] = ledger.defaults()['recovery_total'] + 1
        self.assertEqual(self.fixture_readiness(state)['delivery'], 'HOLD')

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

    def narrow_cli(self, action, revision, payload=None, *extra):
        command = [sys.executable, str(HELPER), action, '--ledger', str(self.path),
                   '--expected-revision', str(revision), '--reason', 'targeted ledger operation']
        if payload is not None:
            source = self.root / 'operation.json'
            source.write_text(json.dumps(payload), encoding='utf-8')
            command += ['--input', str(source)]
        return subprocess.run(command + list(extra), capture_output=True, text=True, timeout=15)

    def test_record_review_preserves_history_and_stale_approval_holds(self):
        state = self.start()
        original_audit = copy.deepcopy(state['audit'])
        rejection = self.review(state, verdict='REJECTED')
        first = self.narrow_cli('record-review', 0, rejection)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        stale = {**rejection, 'id': 'stale', 'verdict': 'APPROVED', 'snapshot': 'old-tree'}
        second = self.narrow_cli('record-review', 1, stale)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(json.loads(second.stdout)['delivery'], 'HOLD')
        saved = ledger.read_json(self.path)
        self.assertEqual([{k: v for k, v in row.items() if k != 'freshness'}
                          for row in saved['reviews']], [rejection, stale])
        self.assertIn('freshness', saved['reviews'][0])
        self.assertNotIn('freshness', saved['reviews'][1])
        self.assertEqual(saved['audit'][:1], original_audit)
        self.assertEqual(saved['audit'][-1]['action'], 'record-review')
        current = {**rejection, 'id': 'current', 'verdict': 'APPROVED'}
        third = self.narrow_cli('record-review', 2, current)
        self.assertEqual(json.loads(third.stdout)['delivery'], 'PASS')

    def test_issue_operations_cannot_supply_independent_closure(self):
        state = self.start()
        self.material(state)
        issue = state['issues'][0]
        result = self.narrow_cli('add-issue', 0, issue)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        writer = self.review(state, person='writer', issues=['bug'])
        self.assertEqual(self.narrow_cli('record-review', 1, writer).returncode, 0)
        result = self.narrow_cli('update-issue', 2,
                                 {'id': 'bug', 'status': 'RESOLVED', 'closed_by': writer['id']})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['delivery'], 'HOLD')
        qa = self.review(state, issues=['bug'])
        self.assertEqual(self.narrow_cli('record-review', 3, qa).returncode, 0)
        result = self.narrow_cli('update-issue', 4, {'id': 'bug', 'closed_by': qa['id']})
        self.assertEqual(json.loads(result.stdout)['delivery'], 'HOLD')  # original dissent remains
        origin = self.review(state, person='original', issues=['bug'])
        result = self.narrow_cli('record-review', 5, origin)
        self.assertEqual(json.loads(result.stdout)['delivery'], 'PASS')
        self.assertEqual(ledger.read_json(self.path)['issues'][0]['originators'], issue['originators'])

    def test_issue_attribution_appends_and_cannot_be_rewritten(self):
        state = self.start()
        self.material(state)
        self.assertEqual(self.narrow_cli('add-issue', 0, state['issues'][0]).returncode, 0)
        extra = {'reviewer': 'other', 'statement': 'same reproduced failure'}
        result = self.narrow_cli('update-issue', 1,
                                 {'id': 'bug', 'append_aliases': ['duplicate'], 'append_originators': [extra]})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['issues'][0]['originators'], state['issues'][0]['originators'] + [extra])
        before = self.path.read_bytes()
        result = self.narrow_cli('update-issue', 2, {'id': 'bug', 'originators': [extra]})
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_narrow_invalid_payloads_preserve_file(self):
        state = self.start()
        review = self.review(state)
        for payload in (None, [], {}, {**review, 'audit': []}, {**review, 'issues': ['missing']},
                        {**review, 'directly_verified': 1}):
            before = self.path.read_bytes()
            # None must still be delivered as JSON null, not omitted CLI input.
            source = self.root / 'invalid.json'
            source.write_text(json.dumps(payload), encoding='utf-8')
            command = [sys.executable, str(HELPER), 'record-review', '--ledger', str(self.path),
                       '--input', str(source), '--expected-revision', '0', '--reason', 'invalid']
            with self.subTest(payload=payload):
                result = subprocess.run(command, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(self.path.read_bytes(), before)

    def test_budget_operations_reserve_use_and_recovery_totals(self):
        self.start()
        reserve = self.narrow_cli('consume-budget', 0, None, '--counter', 'recoveries',
                                  '--key', 'QA/all', '--phase', 'reserve')
        self.assertEqual(reserve.returncode, 0, reserve.stdout + reserve.stderr)
        used = self.narrow_cli('consume-budget', 1, None, '--counter', 'recoveries',
                               '--key', 'QA/all', '--phase', 'use')
        self.assertEqual(used.returncode, 0, used.stdout + used.stderr)
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['counters']['recoveries']['QA/all'], {'reserved': 1, 'used': 1})
        self.assertEqual(saved['counters']['recovery_total'], {'reserved': 1, 'used': 1})
        extra = self.narrow_cli('consume-budget', 2, None, '--counter', 'recoveries', '--key', 'QA/all')
        self.assertEqual(extra.returncode, 0)
        self.assertEqual(json.loads(extra.stdout)['gate'], 'HOLD')  # recorded excess never waived

    def test_invalid_budget_operations_never_reset_or_write(self):
        self.start()
        for options in ({'amount': 0}, {'amount': -1}, {'amount': True}, {'counter_name': 'unknown'},
                        {'counter_name': 'defects'}, {'key': 'not-allowed'}, {'phase': 'reset'},
                        {'phase': 'use'}):
            before = self.path.read_bytes()
            kwargs = {'counter_name': 'repairs', **options}
            with self.subTest(options=options), self.assertRaises(ValueError):
                ledger.mutate(self.path, 'consume-budget', 0, 'invalid', **kwargs)
            self.assertEqual(self.path.read_bytes(), before)

    def test_concurrent_narrow_mutations_have_one_cas_winner(self):
        self.start()
        command = [sys.executable, str(HELPER), 'consume-budget', '--ledger', str(self.path),
                   '--expected-revision', '0', '--reason', 'concurrent reservation',
                   '--counter', 'repairs', '--phase', 'reserve']
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for _ in range(2)]
        try:
            outputs = [p.communicate(timeout=15) for p in processes]
            self.assertEqual(sorted(p.returncode for p in processes), [0, 2], outputs)
            saved = ledger.read_json(self.path)
            self.assertEqual(saved['revision'], 1)
            self.assertEqual(saved['counters']['repairs'], {'reserved': 1, 'used': 0})
            self.assertEqual(len(saved['audit']), 2)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)


    def declared_review(self, *, status='ACTIVE', self_check=False, no_work=False):
        """Record actual helper-bound evidence for a dirty/untracked local file."""
        delivered = self.root / 'result.py'
        delivered.write_text('original bytes\n', encoding='utf-8')
        state = self.initial()
        state['baseline']['writers'].append('other-writer')
        if self_check:
            state['baseline']['verification'] = 'self_check'
        if no_work:
            state['delivery_files'] = ['result.py']
        else:
            state['work_items'] = [{'id': 'job', 'owner': 'writer', 'files': ['result.py'], 'status': status}]
        ledger.initialize(self.path, state)
        state = ledger.read_json(self.path)
        review = self.review(state, role='SelfCheck' if self_check else 'FinalQA',
                             person='writer' if self_check else 'qa')
        ledger.mutate(self.path, 'record-review', 0, 'verify actual current bytes', review)
        return ledger.read_json(self.path), delivered

    def test_byte_change_with_unchanged_label_invalidates_delivery_and_completion(self):
        state, delivered = self.declared_review()
        original_binding = copy.deepcopy(state['reviews'][0]['freshness'])
        delivered.write_text('changed after review\n', encoding='utf-8')
        state['work_items'][0]['status'] = 'DONE'
        result = ledger.update(self.path, state, 1, 'mark complete without changing snapshot label')
        self.assertEqual(result['gate'], 'PASS')
        self.assertEqual(result['delivery'], 'HOLD')
        self.assertTrue(any('stale final content binding' in item for item in result['blockers']))
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['reviews'][0]['freshness'], original_binding)
        review = self.review(saved, id='fresh-after-completion')
        self.assertEqual(ledger.mutate(self.path, 'record-review', 2, 'verify completed work', review)['delivery'], 'PASS')
        delivered.write_text('changed again without any ledger update\n', encoding='utf-8')
        result = subprocess.run([sys.executable, str(HELPER), 'check', '--ledger', str(self.path)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['valid'])

    def test_metadata_only_completion_preserves_review_content_binding(self):
        state, _ = self.declared_review()
        binding = copy.deepcopy(state['reviews'][0]['freshness'])
        state['work_items'][0]['status'] = 'DONE'
        self.assertEqual(ledger.update(self.path, state, 1, 'metadata completion')['delivery'], 'PASS')
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['reviews'][0]['freshness'], binding)
        saved['work_items'][0]['owner'] = 'other-writer'
        self.assertEqual(ledger.update(self.path, saved, 2, 'change ownership frontier')['delivery'], 'HOLD')
        saved = ledger.read_json(self.path)
        review = self.review(saved, id='review-new-frontier')
        ledger.mutate(self.path, 'record-review', 3, 'verify changed frontier', review)
        saved = ledger.read_json(self.path)
        saved['work_items'].append({'id': 'extra', 'owner': 'writer', 'files': [], 'status': 'DONE'})
        self.assertEqual(ledger.update(self.path, saved, 4, 'new completed work')['delivery'], 'HOLD')

    def test_self_check_and_no_work_declared_files_are_content_bound(self):
        state, delivered = self.declared_review(self_check=True, no_work=True)
        self.assertEqual(ledger.readiness(state, self.path)['delivery'], 'PASS')
        self.assertEqual(state['reviews'][0]['freshness']['work'], [])
        delivered.unlink()
        self.assertEqual(ledger.readiness(state, self.path)['delivery'], 'HOLD')
        review = self.review(state, role='SelfCheck', person='writer', id='verify-deletion')
        result = ledger.mutate(self.path, 'record-review', 1, 'verify intentional deletion', review)
        self.assertEqual(result['delivery'], 'PASS')
        self.assertEqual(ledger.read_json(self.path)['reviews'][-1]['freshness']['files'],
                         [{'path': 'result.py', 'sha256': None}])

    def test_no_declared_files_has_explicit_empty_binding_and_legacy_holds(self):
        state = self.start()
        review = self.review(state)
        ledger.mutate(self.path, 'record-review', 0, 'non-file task verification', review)
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['reviews'][0]['freshness'], {'files': [], 'work': []})
        del saved['reviews'][0]['freshness']
        self.path.write_text(json.dumps(saved), encoding='utf-8')  # legacy persisted evidence
        self.assertEqual(ledger.readiness(saved, self.path)['delivery'], 'HOLD')
        result = subprocess.run([sys.executable, str(HELPER), 'check', '--ledger', str(self.path)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)['valid'])
        review = self.review(saved, id='repaired')
        self.assertEqual(ledger.mutate(self.path, 'record-review', 1, 'repair legacy evidence', review)['delivery'], 'PASS')
        self.assertNotIn('freshness', ledger.read_json(self.path)['reviews'][0])

    def test_freshness_injection_is_rejected_by_all_review_recording_routes(self):
        state = self.initial()
        self.review(state, freshness={'files': [], 'work': []})
        with self.assertRaisesRegex(ValueError, 'helper-managed'):
            ledger.initialize(self.path, state)
        state = self.start()
        review = self.review(state, freshness={'files': [], 'work': []})
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'helper-managed'):
            ledger.update(self.path, state, 0, 'forged binding')
        with self.assertRaisesRegex(ValueError, 'unknown operation'):
            ledger.mutate(self.path, 'record-review', 0, 'forged binding', review)
        self.assertEqual(self.path.read_bytes(), before)

    def test_stale_new_review_is_historical_without_current_content_binding(self):
        state, _ = self.declared_review(status='DONE')
        review = self.review(state, id='stale', snapshot='old')
        ledger.mutate(self.path, 'record-review', 1, 'record historical evidence', review)
        self.assertNotIn('freshness', ledger.read_json(self.path)['reviews'][-1])

    def test_unreadable_or_unsafe_content_holds_without_invalidating_history(self):
        state, delivered = self.declared_review(status='DONE')
        original_open = Path.open
        def unreadable(path, *args, **kwargs):
            if path == delivered:
                raise PermissionError('file cannot be read')
            return original_open(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', unreadable):
            result = ledger.readiness(state, self.path)
        self.assertTrue(result['valid'])
        self.assertEqual(result['delivery'], 'HOLD')
        self.assertTrue(any('cannot verify' in item for item in result['blockers']))
        with mock.patch.object(Path, 'is_symlink', return_value=True):
            self.assertEqual(ledger.readiness(state, self.path)['delivery'], 'HOLD')
        delivered.unlink()
        delivered.mkdir()
        self.assertEqual(ledger.readiness(state, self.path)['delivery'], 'HOLD')

    def test_delivery_paths_cannot_escape_or_hash_ledger_itself(self):
        for filename in ('../escape.py', str(self.root / 'absolute.py'), 'C:relative.py', '*.py', 'ledger.json'):
            state = self.initial()
            state['delivery_files'] = [filename]
            self.review(state)
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                ledger.initialize(self.path, state)
            self.assertFalse(self.path.exists())

    def test_delivery_reparse_point_ancestor_holds_even_without_symlink_flag(self):
        state, _ = self.declared_review(status='DONE')
        original_lstat = Path.lstat
        def reparse(path, *args, **kwargs):
            if path == self.root / 'result.py':
                return mock.Mock(st_file_attributes=0x400)
            return original_lstat(path, *args, **kwargs)
        with mock.patch.object(Path, 'is_symlink', return_value=False), mock.patch.object(Path, 'lstat', reparse):
            result = ledger.readiness(state, self.path)
        self.assertTrue(result['valid'])
        self.assertEqual(result['delivery'], 'HOLD')
        self.assertTrue(any('junctions/reparse points' in item for item in result['blockers']))

    @unittest.skipUnless(sys.platform == 'win32', 'native Windows junction test')
    def test_native_junction_ancestor_cannot_receive_final_content_binding(self):
        actual = self.root / 'actual'
        actual.mkdir()
        (actual / 'result.py').write_text('delivered bytes\n', encoding='utf-8')
        alias = self.root / 'alias'
        created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(actual)],
                                 capture_output=True, text=True, timeout=15)
        if created.returncode != 0:
            self.skipTest('native junction creation unavailable: ' + created.stderr.strip())
        self.assertTrue(alias.is_junction())
        self.assertFalse(alias.is_symlink())
        state = self.initial()
        state['delivery_files'] = ['alias/result.py']
        self.review(state)
        with self.assertRaisesRegex(ValueError, 'junctions/reparse points'):
            ledger.initialize(self.path, state)
        self.assertFalse(self.path.exists())

    def stopped(self, operating_state='STOP_HOLD'):
        state = self.start()
        state['operating_state'] = operating_state
        state['counters']['repairs'] = {'reserved': 1, 'used': 1}
        self.material(state)
        ledger.update(self.path, state, 0, 'quota low' if operating_state == 'PAUSED' else 'repair evidence missing')
        return ledger.read_json(self.path)

    def resume_claim(self, state):
        reference, cause = ledger.stopped_reference(state)
        return {'stop_ref': reference, 'prior_cause': cause or 'recorded legacy stop cause',
                'changed_condition': 'required evidence is now available',
                'evidence': 'saved verification result E1',
                'authority': {'source': 'actual user instruction U1, checked by coordinator', 'scope': 'task'},
                **({'quota_ready': True} if state['operating_state'] == 'PAUSED' else {})}

    def test_plain_update_cannot_resume_or_launder_stopped_state(self):
        state = self.stopped()
        before = self.path.read_bytes()
        for operating_state in ('ACTIVE', 'EVIDENCE_MODE', 'PASS', 'PAUSED'):
            candidate = copy.deepcopy(state)
            candidate['operating_state'] = operating_state
            with self.subTest(operating_state=operating_state), self.assertRaisesRegex(ValueError, 'dedicated resume'):
                ledger.update(self.path, candidate, 1, 'continue')
            self.assertEqual(self.path.read_bytes(), before)

    def test_structured_resume_keeps_stop_cause_history_and_obligations(self):
        state = self.stopped()
        # A record made during HOLD must not replace the original stop cause.
        ledger.mutate(self.path, 'consume-budget', 1, 'reserve necessary repair', counter_name='repairs')
        state = ledger.read_json(self.path)
        claim = self.resume_claim(state)
        self.assertEqual(claim['stop_ref'], 'r1')
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'original stopped audit event'):
            ledger.resume(self.path, {**claim, 'stop_ref': 'r2'}, 2, 'launder cause through benign update')
        self.assertEqual(self.path.read_bytes(), before)
        result = self.narrow_cli('resume', 2, claim)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        saved = ledger.read_json(self.path)
        self.assertEqual(saved['operating_state'], 'ACTIVE')
        self.assertEqual(saved['counters'], state['counters'])
        self.assertEqual(saved['issues'], state['issues'])
        self.assertEqual(saved['reviews'], state['reviews'])
        self.assertEqual(saved['review_deadlines'], state['review_deadlines'])
        self.assertEqual(saved['audit'][:-1], state['audit'])
        self.assertEqual(saved['audit'][-1]['resume'], {**claim, 'prior_state': 'STOP_HOLD'})
        self.assertEqual(json.loads(result.stdout)['delivery'], 'HOLD')
        self.assertFalse(json.loads(result.stdout)['authority_claims_verified'])

    def test_resume_rejects_malformed_claims_cas_and_quota_without_write(self):
        state = self.stopped('PAUSED')
        valid = self.resume_claim(state)
        invalid = [None, [], {}, {**valid, 'stop_ref': 'r0'}, {**valid, 'prior_cause': 'continue'},
                   {**valid, 'changed_condition': ''}, {**valid, 'evidence': ''},
                   {**valid, 'authority': {'source': 'user', 'scope': 'other'}},
                   {**valid, 'quota_ready': False}, {k: v for k, v in valid.items() if k != 'quota_ready'},
                   {**valid, 'reset_counters': True}]
        before = self.path.read_bytes()
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                ledger.resume(self.path, payload, 1, 'resume claim')
            self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'stale expected revision'):
            ledger.resume(self.path, valid, 0, 'stale resume')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(ledger.resume(self.path, valid, 1, 'quota replenishment checked')['delivery'], 'HOLD')

    def test_resume_atomic_failure_preserves_prior_state_and_releases_lock(self):
        state = self.stopped()
        claim = self.resume_claim(state)
        before = self.path.read_bytes()
        with mock.patch('os.replace', side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                ledger.resume(self.path, claim, 1, 'resume')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.*.tmp')), [])
        ledger.resume(self.path, claim, 1, 'retry same resume')

    def test_legacy_stopped_record_has_explicit_resume_repair_route(self):
        state = self.stopped()
        for event in state['audit']:
            event.pop('operating_state', None)
        self.path.write_text(json.dumps(state), encoding='utf-8')
        self.assertEqual(ledger.readiness(state, self.path)['delivery'], 'HOLD')
        claim = self.resume_claim(state)
        self.assertEqual(claim['stop_ref'], 'legacy:1')
        ledger.resume(self.path, claim, 1, 'resume legacy record with saved evidence')
        self.assertEqual(ledger.read_json(self.path)['audit'][:-1], state['audit'])


if __name__ == '__main__':
    unittest.main()
