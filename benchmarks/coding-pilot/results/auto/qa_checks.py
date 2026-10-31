"""Independent QA derived from TASKS.md contracts s1."""
import itertools
import json
import random
from copy import deepcopy
from pathlib import Path
import utilities as u

cases = []
def check(name, fn):
    fn()
    cases.append(name)
def equal(actual, expected):
    assert actual == expected, (actual, expected)
def rejects(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError('expected ValueError')

def pagination():
    for size in range(7):
        xs = list(range(size))
        for offset in range(10):
            for limit in range(1, 6):
                equal(u.paginate(iter(xs), offset, limit), xs[offset:offset+limit])
                result = u.paginate(xs, offset, limit)
                assert result is not xs
        equal(xs, list(range(size)))
    for offset, limit in [(-1, 3), (0, 0), (0, -1), (-1, 0)]:
        rejects(lambda: u.paginate([], offset, limit))
check('paginate: 350 generator/slice cases plus rejection and ownership', pagination)

def merge():
    base = {'nested': {'keep': [1, {'x': [2]}], 'replace': 5}, 'replace': {'old': []}}
    override = {'nested': {'add': [{'y': []}]}, 'replace': [7], 'new': {'z': []}}
    before = deepcopy((base, override))
    result = u.deep_merge(base, override)
    equal(result, {'nested': {'keep': [1, {'x': [2]}], 'replace': 5, 'add': [{'y': []}]}, 'replace': [7], 'new': {'z': []}})
    result['nested']['keep'][1]['x'].append(9)
    result['nested']['add'][0]['y'].append(9)
    result['replace'].append(9)
    result['new']['z'].append(9)
    equal((base, override), before)
    snapshot = deepcopy(result)
    base['nested']['keep'].append(8)
    override['nested']['add'][0]['y'].append(8)
    override['new']['z'].append(8)
    equal(result, snapshot)
    equal(u.deep_merge({'a': [1]}, {'a': {'b': [2]}}), {'a': {'b': [2]}})
    empty = {}
    assert u.deep_merge(empty, {}) is not empty
check('deep_merge: recursive replacement and bidirectional nested independence', merge)

def topo():
    equal(u.topological_order({}), [])
    equal(u.topological_order({'z': iter(['b','b']), 'c': ['a'], 'b': []}), ['a','b','c','z'])
    for graph in [{'x':['x']}, {'a':['b'], 'b':['c'], 'c':['a']}, {'a':[], 'b':['c'], 'c':['b']}]:
        rejects(lambda: u.topological_order(graph))
    rng = random.Random(837)
    for _ in range(160):
        names = list('abcde')
        graph = {n: [p for p in names if rng.random() < .2] for n in names if rng.random() < .8}
        original = deepcopy(graph)
        nodes = set(graph).union(*(set(v) for v in graph.values()))
        orders = [p for p in itertools.permutations(sorted(nodes)) if all(p.index(dep) < p.index(n) for n, ds in graph.items() for dep in ds)]
        if orders:
            equal(u.topological_order(graph), list(min(orders)))
        else:
            rejects(lambda: u.topological_order(graph))
        equal(graph, original)
check('topological_order: prerequisite-only/duplicate/generator nodes and 160 exhaustive permutation oracle graphs', topo)

def csv_cases():
    for text in ['', '\n\r\n', 'a,b\n', '\n a , b \n\n']:
        equal(u.parse_csv_rows(text), [])
    equal(u.parse_csv_rows('\n a , b \r\n"x,y","line1\r\nline2"\r\n\r\n"", spaced \r\n'), [{'a':'x,y','b':'line1\r\nline2'}, {'a':'','b':' spaced '}])
    equal(u.parse_csv_rows('a\n\n""\n'), [{'a':''}])
    equal(u.parse_csv_rows('a,b\n,\n'), [{'a':'','b':''}])
    equal(u.parse_csv_rows('a\n"say ""hello"""\n'), [{'a':'say "hello"'}])
    for text in ['\"\"\n', 'a, \n', ' a ,a\n', 'a,b\n1\n', 'a\n1,2\n', 'a,b\n""\n', 'a\n"unterminated']:
        rejects(lambda: u.parse_csv_rows(text))
check('parse_csv_rows: physical blank versus explicit empty, multiline, whitespace, escaping, header and width validation', csv_cases)

def cache():
    c, other = u.ExpiringCache(), u.ExpiringCache()
    for i, value in enumerate([0, False, '', [], {}, None]):
        c.set(i, value, 2.5, -1)
        assert c.get(i, 1.499) is value
        equal(other.get(i, 0), None)
        equal(c.get(i, 1.5), None)
        assert i not in c.entries
    c.set('k', 'old', 10, 0)
    for ttl in [0, -1, -0.2]:
        rejects(lambda: c.set('k', 'bad', ttl, 0))
        equal(c.get('k', 1), 'old')
    c.set('k', 'new', 20, 5)
    equal(c.get('k', 10), 'new')
    equal(c.get('k', 25), None)
    equal(c.get('missing', 0), None)
check('ExpiringCache: falsey identity, fractional clocks, exact expiry removal, overwrite, invalid TTL atomicity and instance isolation', cache)

def transfers():
    original = {'a': 5, 'b': 0, 'c': 2}
    equal(u.apply_transfers(original, iter([('a','b',5),('b','c',2),('c','a',4),('a','a',4)])), {'a':4,'b':3,'c':0})
    equal(original, {'a':5,'b':0,'c':2})
    copy = u.apply_transfers(original, [])
    assert copy is not original
    bad = [('a','b',True), ('a','b',False), ('a','b',1.0), ('a','b',0), ('a','b',-1), ('x','b',1), ('a','x',1), ('a','a',6), ('a','b',6), ('a','b'), None, ([], 'b', 1)]
    for transfer in bad:
        rejects(lambda: u.apply_transfers(original, iter([('a','b',1), transfer])))
        equal(original, {'a':5,'b':0,'c':2})
    rng = random.Random(712)
    for _ in range(100):
        expected = {'a':20,'b':20,'c':20}
        sequence = []
        for _ in range(30):
            src,dst = rng.choice('abc'),rng.choice('abc')
            if expected[src] == 0:
                continue
            amount = rng.randint(1,expected[src])
            sequence.append((src,dst,amount))
            expected[src] -= amount
            expected[dst] += amount
        actual = u.apply_transfers({'a':20,'b':20,'c':20}, iter(sequence))
        equal(actual, expected)
        equal(sum(actual.values()),60)
check('apply_transfers: ordered generators, self transfers, rejected invalid suffix atomicity, 100 randomized conservation sequences', transfers)

report = {'verdict':'APPROVED', 'contract':'s1', 'independent': True, 'confirmed_defects': [], 'checks':cases, 'commands':['& python qa_checks.py'], 'limits':'Contract-scoped synthetic data; no production/general-type guarantees. Developer self-checks and peer outputs were not read.'}
Path(__file__).with_name('qa_review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
