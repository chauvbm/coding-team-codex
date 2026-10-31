"""Optional task ledger: structural/readiness checks, not authorization or orchestration."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path, PureWindowsPath
import sys

try:
    from coding_team_policy import locked, atomic_write
except ImportError:  # also support importlib-based test consumers
    import importlib.util
    _spec = importlib.util.spec_from_file_location('ledger_policy_storage', Path(__file__).with_name('coding_team_policy.py'))
    _storage = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_storage)
    locked, atomic_write = _storage.locked, _storage.atomic_write

DEFAULTS = Path(__file__).resolve().parents[1] / 'references' / 'governance-defaults.json'
COUNTERS = ('revisions', 'repairs', 'diagnostics', 'recovery_total')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    require(nonempty(value), 'timestamp required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, 'timestamp requires timezone')
    return parsed


def fields(record, names, label):
    require(isinstance(record, dict), label + ' must be an object')
    require(all(nonempty(record.get(name)) for name in names), label + ' needs ' + ', '.join(names))


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def defaults():
    result = read_json(DEFAULTS)
    require(result.get('schema_version') == 1, 'unsupported governance defaults')
    return result


def counter(value):
    require(isinstance(value, dict) and set(value) == {'reserved', 'used'}, 'counter needs reserved and used')
    require(all(type(n) is int and n >= 0 for n in value.values()), 'counter must be nonnegative integers')
    require(value['used'] <= value['reserved'], 'used exceeds reserved counter')


def current(record, baseline):
    return all(record.get(k) == baseline[k] for k in ('spec', 'plan', 'snapshot'))


def owned_path(root, value):
    require(nonempty(value), 'owned path must be a relative file')
    path = Path(value)
    win = PureWindowsPath(value)
    require(not path.is_absolute() and not win.is_absolute() and not win.drive and not win.root,
            'absolute owned path is forbidden')
    require('..' not in value.replace('\\', '/').split('/'), 'parent traversal is forbidden')
    require(not any(c in value for c in '*?[]'), 'ownership requires explicit file paths')
    resolved = (root / path).resolve()
    require(resolved != root and resolved.is_relative_to(root), 'owned path escapes project root')
    require(not resolved.is_dir(), 'owned path must name a file')
    return str(resolved).casefold()  # conservative collision handling across hosts


def validate(state):
    require(isinstance(state, dict), 'ledger must be an object')
    require(type(state.get('schema_version')) is int and state['schema_version'] == 1, 'schema_version must be 1')
    fields(state, ('task_id', 'project_root', 'operating_state'), 'ledger')
    require(type(state.get('revision')) is int and state['revision'] >= 0, 'invalid revision')
    require(state['operating_state'] in ('ACTIVE', 'EVIDENCE_MODE', 'STOP_HOLD', 'PAUSED', 'PASS'), 'invalid operating_state')
    root = Path(state['project_root'])
    require(root.is_absolute() and root.is_dir(), 'project_root must be an existing absolute directory')
    root = root.resolve()
    b = state.get('baseline')
    fields(b, ('level', 'spec', 'plan', 'snapshot'), 'baseline')
    require(b['level'] in ('L0', 'L1', 'L2', 'L3'), 'invalid level')
    require(type(b.get('gated')) is bool, 'gated must be boolean')
    require(isinstance(b.get('scopes'), list) and b['scopes'] and all(nonempty(x) for x in b['scopes'])
            and len(set(b['scopes'])) == len(b['scopes']), 'invalid scopes')
    require(isinstance(b.get('acceptance'), list) and b['acceptance'] and all(nonempty(x) for x in b['acceptance']), 'acceptance required')
    require(isinstance(b.get('writers'), list) and all(nonempty(x) for x in b['writers']), 'writers required')
    require(isinstance(b.get('required_reviews'), list), 'required_reviews required')
    roles = set()
    for request in b['required_reviews']:
        fields(request, ('role', 'reviewer', 'scope'), 'required review')
        require(request['scope'] in b['scopes'], 'unknown review scope')
        key = (request['role'], request['scope'])
        require(key not in roles, 'duplicate review responsibility')
        roles.add(key)
    if b['gated']:
        for scope in b['scopes']:
            require(all((role, scope) in roles for role in ('Architect', 'Developer', 'QA')), 'gated scope requires three core roles')
    counts = state.get('counters')
    require(isinstance(counts, dict) and set(counts) == set(COUNTERS) | {'defects', 'recoveries'}, 'invalid counters')
    for key in COUNTERS:
        counter(counts[key])
    for group in ('defects', 'recoveries'):
        require(isinstance(counts[group], dict), 'invalid counter group')
        for key, value in counts[group].items():
            require(nonempty(key), 'invalid counter ID')
            counter(value)
    require(sum(v['reserved'] for v in counts['recoveries'].values()) <= counts['recovery_total']['reserved'], 'recovery total below reservations')
    require(sum(v['used'] for v in counts['recoveries'].values()) <= counts['recovery_total']['used'], 'recovery total below used attempts')
    for key in ('issues', 'reviews', 'transfers', 'work_items', 'audit'):
        require(isinstance(state.get(key), list), key + ' must be a list')
        ids = [row.get('id') for row in state[key] if isinstance(row, dict)]
        require(len(ids) == len(state[key]) and all(nonempty(i) for i in ids) and len(ids) == len(set(ids)), key + ' needs unique IDs')
    for issue in state['issues']:
        fields(issue, ('id', 'scope', 'severity', 'status', 'closure_criteria'), 'issue')
        require(issue['scope'] in b['scopes'], 'unknown issue scope')
        require(issue['severity'] in ('BLOCKER', 'MAJOR', 'MINOR', 'SUGGESTION'), 'invalid severity')
        require(issue['status'] in ('OPEN', 'CONTESTED', 'RESOLVED'), 'invalid issue status')
        require(isinstance(issue.get('originators'), list) and issue['originators'], 'issue originators required')
        for origin in issue['originators']:
            fields(origin, ('reviewer', 'statement'), 'originator')
        require(isinstance(issue.get('aliases'), list) and all(nonempty(x) for x in issue['aliases']), 'aliases required')
    for review in state['reviews']:
        fields(review, ('id', 'reviewer', 'role', 'scope', 'spec', 'plan', 'snapshot', 'evidence'), 'review')
        require(review['scope'] in b['scopes'], 'unknown review scope')
        require(review.get('verdict') in ('APPROVED', 'REJECTED'), 'invalid verdict')
        require(type(review.get('directly_verified')) is bool, 'directly_verified must be boolean')
        require(isinstance(review.get('issues'), list) and all(nonempty(i) for i in review['issues']), 'review issues required')
        require(set(review['issues']) <= {i['id'] for i in state['issues']}, 'review references unknown issue')
        if 'verified_at' in review:
            timestamp(review['verified_at'])
    deadlines = state.get('review_deadlines', {})
    require(isinstance(deadlines, dict), 'review_deadlines must be an object')
    for key, deadline in deadlines.items():
        require(nonempty(key), 'deadline key required')
        fields(deadline, ('reviewer', 'role', 'scope', 'at'), 'original review deadline')
        require(deadline['scope'] in b['scopes'], 'unknown deadline scope')
        timestamp(deadline['at'])
    for transfer in state['transfers']:
        fields(transfer, ('id', 'role', 'scope', 'from', 'to', 'reason', 'spec', 'plan', 'snapshot', 'recovery_key'), 'transfer')
        require(transfer['scope'] in b['scopes'] and transfer['from'] != transfer['to'], 'invalid transfer')
        require(transfer.get('unavailable') is True, 'transfer requires unavailable predecessor')
        require(type(transfer.get('attempt')) is int and transfer['attempt'] > 0, 'transfer attempt required')
    attempts = [(t['recovery_key'], t['attempt']) for t in state['transfers']]
    require(len(attempts) == len(set(attempts)), 'a recovery attempt cannot appoint multiple replacements')
    for transfer in state['transfers']:
        require(not any(previous['to'] == transfer['from'] and previous['role'] == transfer['role']
                        and previous['scope'] == transfer['scope'] for previous in state['transfers']),
                'chained reviewer replacement is unsupported; retain original responsibility and deadline')
    owners = {}
    for work in state['work_items']:
        fields(work, ('id', 'owner', 'status'), 'work item')
        require(work['status'] in ('PENDING', 'ACTIVE', 'DONE', 'CANCELLED'), 'invalid work status')
        require(isinstance(work.get('files'), list), 'files required')
        for filename in work['files']:
            path = owned_path(root, filename)
            if work['status'] == 'ACTIVE':
                require(path not in owners, 'duplicate active file ownership: ' + filename)
                owners[path] = work['owner']
        require(work['owner'] in b['writers'] or not work['files'], 'file owner missing from writers')
    require(state.get('continuation') is None or isinstance(state['continuation'], dict), 'invalid continuation')
    if state.get('continuation'):
        fields(state['continuation'], ('source', 'scope'), 'continuation claim')
        require(type(state['continuation'].get('repair_extension')) is bool, 'repair_extension must be boolean')
    for index, event in enumerate(state['audit']):
        fields(event, ('id', 'at', 'reason', 'action'), 'audit event')
        require(event.get('revision') == index, 'audit revision sequence invalid')
    require(len(state['audit']) == state['revision'] + 1, 'audit length does not match revision')
    return state


def approved(review, baseline):
    return current(review, baseline) and review['verdict'] == 'APPROVED' and review['directly_verified']


def readiness(state):
    validate(state)
    d, b, c = defaults(), state['baseline'], state['counters']
    blockers = []
    def block(condition, message):
        if condition:
            blockers.append(message)
    continuation = state.get('continuation') or {}
    extension = continuation.get('repair_extension') is True and continuation.get('scope') == state['task_id']
    block(c['revisions']['reserved'] > d['revision_cycles'][b['level']] and not extension, 'revision allowance exceeded without continuation claim')
    block((c['repairs']['reserved'] > d['repair_batches'] or any(v['reserved'] > d['repair_attempts_per_defect'] for v in c['defects'].values())) and not extension, 'repair allowance exceeded without continuation claim')
    block(c['diagnostics']['reserved'] > d['diagnostic_dispatches'], 'diagnostic allowance exceeded')
    recovery_ok = c['recovery_total']['reserved'] <= d['recovery_total'] and all(v['reserved'] <= d['recovery_per_role_or_operation'] for v in c['recoveries'].values())
    block(not recovery_ok, 'recovery allowance exceeded')
    block(state['operating_state'] in ('STOP_HOLD', 'PAUSED'), 'operating state is ' + state['operating_state'])
    deadlines = state.get('review_deadlines', {})
    valid_transfers = [t for t in state['transfers'] if current(t, b) and recovery_ok
                       and t['to'] not in b['writers'] and t['recovery_key'] in c['recoveries']
                       and t['attempt'] <= c['recoveries'][t['recovery_key']]['used']
                       and t['attempt'] <= d['recovery_per_role_or_operation']
                       and t['recovery_key'] in deadlines
                       and deadlines[t['recovery_key']]['reviewer'] == t['from']
                       and deadlines[t['recovery_key']]['role'] == t['role']
                       and deadlines[t['recovery_key']]['scope'] == t['scope']]
    def accepted_review(review):
        if not approved(review, b):
            return False
        if review['role'] in ('QA', 'FinalQA') and review['reviewer'] in b['writers']:
            return False
        inherited = [t for t in valid_transfers if t['to'] == review['reviewer']
                     and t['role'] == review['role'] and t['scope'] == review['scope']]
        return all('verified_at' in review and timestamp(review['verified_at']) <= timestamp(deadlines[t['recovery_key']]['at'])
                   for t in inherited)
    def responsible(person, role, scope):
        seen = {person}
        while True:
            matches = [t for t in valid_transfers if t['from'] == person and t['role'] == role and t['scope'] == scope]
            if not matches:
                return person
            if len(matches) != 1 or matches[0]['to'] in seen:
                return None
            person = matches[0]['to']
            seen.add(person)
    for request in b['required_reviews']:
        person = responsible(request['reviewer'], request['role'], request['scope'])
        reviews = [r for r in state['reviews'] if current(r, b) and r['reviewer'] == person and r['role'] == request['role'] and r['scope'] == request['scope']]
        block(not reviews or not accepted_review(reviews[-1]), 'missing current applicable approval: ' + request['role'] + '/' + request['scope'])
    for issue in state['issues']:
        if issue['severity'] not in ('BLOCKER', 'MAJOR'):
            continue
        closure = next((r for r in state['reviews'] if r['id'] == issue.get('closed_by')), None)
        accepted = issue['status'] == 'RESOLVED' and closure is not None and accepted_review(closure) and closure['role'] in ('QA', 'FinalQA') and issue['id'] in closure['issues'] and closure['scope'] == issue['scope']
        if accepted:
            # A historical closure cannot hide a later rejection by its closer or another reviewer.
            obligations = {(origin['reviewer'], origin.get('role', closure['role']))
                           for origin in issue['originators']}
            obligations.add((closure['reviewer'], closure['role']))
            obligations.update((r['reviewer'], r['role']) for r in state['reviews']
                               if current(r, b) and r['scope'] == issue['scope']
                               and issue['id'] in r['issues'] and r['verdict'] == 'REJECTED')
            for reviewer, role in obligations:
                person = responsible(reviewer, role, issue['scope'])
                confirmations = [r for r in state['reviews'] if r['reviewer'] == person and r['role'] == role and r['scope'] == issue['scope'] and issue['id'] in r['issues'] and current(r, b)]
                accepted = accepted and bool(confirmations) and accepted_review(confirmations[-1])
        block(not accepted, 'unresolved material issue: ' + issue['id'])
    gate_blockers = list(blockers)
    for scope in b['scopes']:
        qa = [r for r in state['reviews'] if r['role'] == 'FinalQA' and r['scope'] == scope and current(r, b)]
        block(not qa or not accepted_review(qa[-1]), 'missing independent final QA: ' + scope)
    return {'valid': True, 'revision': state['revision'], 'gate': 'HOLD' if gate_blockers else 'PASS',
            'delivery': 'HOLD' if blockers else 'PASS', 'gate_blockers': gate_blockers, 'blockers': blockers,
            'authority_claims_verified': False}


def monotonic(old, new):
    for key, value in old.items():
        require(key in new, 'counter history cannot be deleted')
        if isinstance(value, dict):
            monotonic(value, new[key])
        else:
            require(new[key] >= value, 'cumulative counters cannot decrease')


def transition(old, new):
    for key in ('task_id', 'project_root', 'schema_version', 'revision', 'audit'):
        require(new.get(key) == old[key], key + ' is helper-managed or immutable')
    require(old['baseline']['level'] == new['baseline']['level'], 'task level cannot reset allowances')
    require(set(old['baseline']['writers']) <= set(new['baseline']['writers']), 'writer attribution cannot be removed')
    require(set(old['baseline']['scopes']) <= set(new['baseline']['scopes']), 'scope history cannot be removed')
    require(not old['baseline']['gated'] or new['baseline']['gated'], 'required gate cannot be removed')
    require(all(request in new['baseline']['required_reviews'] for request in old['baseline']['required_reviews']), 'review responsibilities cannot be removed; use scoped transfers')
    for key, deadline in old.get('review_deadlines', {}).items():
        require(new.get('review_deadlines', {}).get(key) == deadline, 'original review deadline cannot be renewed or removed')
    old_pair = tuple(old['baseline'][key] for key in ('spec', 'plan', 'snapshot'))
    new_pair = tuple(new['baseline'][key] for key in ('spec', 'plan', 'snapshot'))
    if old['baseline'] != new['baseline']:
        require(old_pair != new_pair, 'changed baseline requires a fresh version/snapshot')
        historical = [tuple(e['baseline'][key] for key in ('spec', 'plan', 'snapshot'))
                      for e in old['audit'] if isinstance(e.get('baseline'), dict)]
        require(new_pair not in historical, 'historical version/snapshot cannot be reused')
    for key in ('reviews', 'transfers'):
        require(new[key][:len(old[key])] == old[key], key + ' history cannot be rewritten')
    for issue in old['issues']:
        updated = next((i for i in new['issues'] if i['id'] == issue['id']), None)
        require(updated is not None, 'issue history cannot be deleted')
        for key in ('scope', 'severity', 'closure_criteria'):
            require(updated[key] == issue[key], 'original issue field cannot change: ' + key)
        for key in ('originators', 'aliases'):
            require(updated[key][:len(issue[key])] == issue[key], 'issue attribution cannot be rewritten')
    monotonic(old['counters'], new['counters'])


def event(state, action, reason):
    require(nonempty(reason), 'reason required')
    state['audit'].append({'id': 'r' + str(state['revision']), 'revision': state['revision'],
                           'at': datetime.now(timezone.utc).isoformat(), 'action': action, 'reason': reason,
                           'baseline': copy.deepcopy(state['baseline']),
                           'counters': copy.deepcopy(state['counters']),
                           'continuation': copy.deepcopy(state.get('continuation')),
                           'review_deadlines': copy.deepcopy(state.get('review_deadlines', {})),
                           'issue_states': [{k: i[k] for k in ('id', 'status', 'closed_by') if k in i} for i in state['issues']]})


def save(path, state):
    validate(state)
    atomic_write(path, (json.dumps(state, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))


def initialize(path, candidate, reason='initial baseline'):
    with locked(path):
        require(not Path(path).exists(), 'ledger already exists; never reset it')
        state = copy.deepcopy(candidate)
        require('audit' not in state and 'revision' not in state, 'init revision/audit are helper-managed')
        state.update(revision=0, audit=[])
        event(state, 'init', reason)
        result = readiness(state)
        save(path, state)
        return result


def update(path, candidate, expected_revision, reason):
    with locked(path):
        old = validate(read_json(path))
        require(type(expected_revision) is int and old['revision'] == expected_revision, 'stale expected revision')
        new = copy.deepcopy(candidate)
        validate(new)
        transition(old, new)
        new['revision'] += 1
        event(new, 'update', reason)
        result = readiness(new)
        save(path, new)
        return result


def mutate(path, expected_revision, reason, action, change):
    """Apply a focused edit to the latest state under the ledger's write lock."""
    with locked(path):
        old = validate(read_json(path))
        require(type(expected_revision) is int and old['revision'] == expected_revision, 'stale expected revision')
        new = copy.deepcopy(old)
        change(new)
        validate(new)
        transition(old, new)
        new['revision'] += 1
        event(new, action, reason)
        result = readiness(new)
        save(path, new)
        return result


def record_review(path, review, expected_revision, reason):
    allowed = {'id', 'reviewer', 'role', 'scope', 'spec', 'plan', 'snapshot',
               'evidence', 'verdict', 'directly_verified', 'issues', 'verified_at'}
    require(isinstance(review, dict), 'review must be an object')
    require(set(review) <= allowed, 'unknown review fields')
    return mutate(path, expected_revision, reason, 'record-review',
                  lambda state: state['reviews'].append(copy.deepcopy(review)))


def consume_budget(path, expected_revision, reason, counter, amount=1, phase='both'):
    require(counter in COUNTERS, 'invalid counter')
    require(type(amount) is int and amount > 0, 'amount must be a positive integer')
    require(phase in ('reserve', 'use', 'both'), 'invalid phase')

    def change(state):
        value = state['counters'][counter]
        if phase in ('reserve', 'both'):
            value['reserved'] += amount
        if phase in ('use', 'both'):
            value['used'] += amount

    return mutate(path, expected_revision, reason, 'consume-budget', change)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('init', 'update', 'check', 'record-review', 'consume-budget'):
        command = sub.add_parser(name)
        command.add_argument('--ledger', required=True, type=Path)
        if name == 'check':
            command.add_argument('--stage', choices=('gate', 'delivery'), default='delivery')
        if name != 'check':
            command.add_argument('--reason', required=True)
            if name != 'consume-budget':
                command.add_argument('--input', required=True, type=Path)
        if name in ('update', 'record-review', 'consume-budget'):
            command.add_argument('--expected-revision', required=True, type=int)
        if name == 'consume-budget':
            command.add_argument('--counter', required=True, choices=COUNTERS)
            command.add_argument('--amount', type=int, default=1)
            command.add_argument('--phase', choices=('reserve', 'use', 'both'), default='both')
    args = parser.parse_args(argv)
    try:
        if args.action == 'init':
            result = initialize(args.ledger, read_json(args.input), args.reason)
        elif args.action == 'update':
            result = update(args.ledger, read_json(args.input), args.expected_revision, args.reason)
        elif args.action == 'record-review':
            result = record_review(args.ledger, read_json(args.input), args.expected_revision, args.reason)
        elif args.action == 'consume-budget':
            result = consume_budget(args.ledger, args.expected_revision, args.reason,
                                    args.counter, args.amount, args.phase)
        else:
            result = readiness(read_json(args.ledger))
        print(json.dumps(result, ensure_ascii=False))
        return 1 if args.action == 'check' and result[args.stage] != 'PASS' else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'valid': False, 'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
