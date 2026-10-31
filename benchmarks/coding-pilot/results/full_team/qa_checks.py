"""Independent contract-based QA for s1; no coordinator holdouts imported."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import unittest
import utilities as u

class Contracts(unittest.TestCase):
    def test_paginate(self):
        items = [1, 2, 3, 4]
        self.assertEqual(u.paginate(iter(items), 1, 2), [2, 3])
        self.assertEqual(u.paginate(items, 9, 1), [])
        self.assertEqual(u.paginate([], 0, 1), [])
        result = u.paginate(items, 0, 10)
        self.assertEqual(result, items)
        self.assertIsNot(result, items)
        for offset, limit in [(-1, 1), (0, 0), (0, -1)]:
            with self.assertRaises(ValueError): u.paginate(items, offset, limit)
        self.assertEqual(items, [1, 2, 3, 4])

    def test_deep_merge(self):
        a = {'x': {'left': [1], 'clash': {'old': [2]}}, 'keep': [{'a': 3}], 'replace': {'old': 1}}
        b = {'x': {'right': [4], 'clash': [5]}, 'replace': [6], 'new': {'arr': [7]}}
        original_a, original_b = copy.deepcopy(a), copy.deepcopy(b)
        result = u.deep_merge(a, b)
        expected = {'x': {'left': [1], 'right': [4], 'clash': [5]}, 'keep': [{'a': 3}], 'replace': [6], 'new': {'arr': [7]}}
        self.assertEqual(result, expected)
        self.assertEqual(a, original_a); self.assertEqual(b, original_b)
        result['x']['left'].append(8); result['new']['arr'].append(8)
        result['keep'][0]['a'] = 9
        self.assertEqual(a, original_a); self.assertEqual(b, original_b)
        second = u.deep_merge(a, b)
        a['x']['left'].append(10); b['x']['right'].append(11)
        self.assertEqual(second, expected)
        self.assertEqual(u.deep_merge({'a': 1}, {'a': {'v': [2]}}), {'a': {'v': [2]}})

    def test_topological_order(self):
        dependencies = {'d': ['b', 'b'], 'b': ['a'], 'c': [], 'f': ['e']}
        before = copy.deepcopy(dependencies)
        self.assertEqual(u.topological_order(dependencies), ['a', 'b', 'c', 'd', 'e', 'f'])
        self.assertEqual(dependencies, before)
        self.assertEqual(u.topological_order({'b': iter(['a', 'a'])}), ['a', 'b'])
        self.assertEqual(u.topological_order({}), [])
        for graph in [{'a': ['a']}, {'a': ['b'], 'b': ['a']}, {'c': [], 'a': ['b'], 'b': ['a']}]:
            with self.assertRaises(ValueError): u.topological_order(graph)
        rng = random.Random(41)
        names = list('abcde')
        for _ in range(80):
            graph = {name: [p for p in names if rng.random() < .16] for name in names}
            orders = [list(order) for order in itertools.permutations(names)
                      if all(order.index(p) < order.index(n) for n, ps in graph.items() for p in ps)]
            if orders: self.assertEqual(u.topological_order(graph), min(orders))
            else:
                with self.assertRaises(ValueError): u.topological_order(graph)

    def test_csv(self):
        text = '\r\n name , note \r\n"Doe, Jane","line1\r\nline2"\r\n\r\nBob,  x  \r\n'
        self.assertEqual(u.parse_csv_rows(text), [{'name': 'Doe, Jane', 'note': 'line1\r\nline2'}, {'name': 'Bob', 'note': '  x  '}])
        self.assertEqual(u.parse_csv_rows('a\n\n""\n'), [{'a': ''}])
        self.assertEqual(u.parse_csv_rows('a,b\n,\n'), [{'a': '', 'b': ''}])
        for text in ['', '\n\r\n', 'a,b\n', 'a,b\n\n']:
            self.assertEqual(u.parse_csv_rows(text), [])
        for text in ['a, a\n', ' ,b\n', 'a,\n', '""\n', 'a,b\n1\n', 'a\n1,2\n', 'a,b\n""\n']:
            with self.assertRaises(ValueError): u.parse_csv_rows(text)
        self.assertEqual(u.parse_csv_rows('a\n"a""b"\n'), [{'a': 'a"b'}])

    def test_cache(self):
        c, other = u.ExpiringCache(), u.ExpiringCache()
        for index, value in enumerate([0, False, '', [], {}, None]):
            c.set(index, value, 2.5, 10)
            self.assertIs(c.get(index, 12.499), value)
            self.assertIsNone(other.get(index, 10))
            self.assertIsNone(c.get(index, 12.5))
            self.assertIsNone(c.get(index, 10))
        c.set('x', 'old', 5, 0)
        for ttl in [0, -1]:
            with self.assertRaises(ValueError): c.set('x', 'bad', ttl, 1)
            self.assertEqual(c.get('x', 1), 'old')
        c.set('x', 'new', 20, 2)
        self.assertEqual(c.get('x', 5), 'new')
        self.assertIsNone(c.get('x', 22))
        c.set('x', 'short', 1, 30)
        self.assertIsNone(c.get('x', 31))

    def test_transfers(self):
        original = {'a': 10, 'b': 0, 'c': 5}
        result = u.apply_transfers(original, iter([('a', 'b', 7), ('b', 'c', 7), ('c', 'c', 12)]))
        self.assertEqual(result, {'a': 3, 'b': 0, 'c': 12})
        self.assertEqual(sum(result.values()), sum(original.values()))
        self.assertEqual(original, {'a': 10, 'b': 0, 'c': 5})
        self.assertIsNot(u.apply_transfers(original, []), original)
        invalid = [('a', 'b', x) for x in [True, False, 0, -1, 1.0, '1', None]]
        invalid += [('missing', 'b', 1), ('a', 'missing', 1), ('a', 'a', 11), ('a', 'b', 11), ('a', 'b'), None]
        for transfer in invalid:
            with self.assertRaises(ValueError):
                u.apply_transfers(original, iter([('a', 'b', 1), transfer]))
            self.assertEqual(original, {'a': 10, 'b': 0, 'c': 5})
        with self.assertRaises(ValueError):
            u.apply_transfers(original, [('a', 'b', 10), ('a', 'c', 1)])
        self.assertEqual(u.apply_transfers(original, [('a', 'a', 10)]), original)

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Contracts)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        'role': 'independent QA', 'spec_version': 's1', 'plan_version': 'p1',
        'stage': 'final-review', 'verdict': 'APPROVED' if result.wasSuccessful() else 'REJECTED',
        'snapshot_sha256': hashlib.sha256(Path('utilities.py').read_bytes()).hexdigest(),
        'inspected_paths': ['TASKS.md', 'utilities.py'],
        'checks_command': "& 'python' qa_checks.py",
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'findings': [{'test': str(test), 'evidence': trace} for test, trace in result.failures + result.errors],
        'coverage': 'All six contracts, including 80 small directed-graph cases checked against exhaustive valid permutations.',
        'limitations': ['Coordinator holdout acceptance remains unseen and was not run.', 'graphify query failed because workspace graph.json is absent; reviewed utilities.py directly without indexing unrelated review artifacts.'],
        'implementation_edited': False
    }
    Path('qa_review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
