"""Developer-owned behavioral self-checks; no coordinator tests imported."""
import unittest
from utilities import (paginate, deep_merge, topological_order, parse_csv_rows,
                       ExpiringCache, apply_transfers)


class UtilityChecks(unittest.TestCase):
    def test_paginate(self):
        original = [0, 1, 2, 3, 4]
        self.assertEqual(paginate(iter(original), 2, 2), [2, 3])
        self.assertEqual(paginate(original, 20, 2), [])
        self.assertEqual(paginate(original, 0, 8), original)
        self.assertIsNot(paginate(original, 0, 8), original)
        for offset, limit in [(-1, 1), (0, 0), (0, -1)]:
            with self.assertRaises(ValueError):
                paginate(original, offset, limit)
        self.assertEqual(original, [0, 1, 2, 3, 4])

    def test_merge(self):
        base = {'a': {'x': [1], 'keep': 2}, 'list': [{'n': 3}]}
        override = {'a': {'y': [4]}, 'new': [5]}
        result = deep_merge(base, override)
        self.assertEqual(result['a'], {'x': [1], 'keep': 2, 'y': [4]})
        result['a']['x'].append(6)
        result['list'][0]['n'] = 7
        self.assertEqual(base['a']['x'], [1])
        self.assertEqual(base['list'], [{'n': 3}])
        override['a']['y'].append(8)
        base['a']['x'].append(9)
        self.assertEqual(result['a']['y'], [4])
        self.assertEqual(result['a']['x'], [1, 6])
        replacement = deep_merge({'a': {'x': 1}}, {'a': [2]})
        self.assertEqual(replacement, {'a': [2]})

    def test_topology(self):
        self.assertEqual(topological_order({}), [])
        self.assertEqual(topological_order({'z': iter(['b', 'b']), 'a': []}), ['a', 'b', 'z'])
        self.assertEqual(topological_order({'a': ['b'], 'c': [], 'b': []}), ['b', 'a', 'c'])
        original = {'a': ['b', 'b']}
        self.assertEqual(topological_order(original), ['b', 'a'])
        self.assertEqual(original, {'a': ['b', 'b']})
        for graph in [{'a': ['a']}, {'a': ['b'], 'b': ['a']}, {'free': [], 'a': ['a']}]:
            with self.assertRaises(ValueError):
                topological_order(graph)

    def test_csv(self):
        self.assertEqual(parse_csv_rows(''), [])
        self.assertEqual(parse_csv_rows('\n\n'), [])
        self.assertEqual(parse_csv_rows(' a , b \n'), [])
        self.assertEqual(parse_csv_rows('\na,b\n\n"x,y","line1\nline2"\n z ,\n'),
                         [{'a': 'x,y', 'b': 'line1\nline2'}, {'a': ' z ', 'b': ''}])
        self.assertEqual(parse_csv_rows('a\n\n""\n'), [{'a': ''}])
        self.assertEqual(parse_csv_rows('a\r\n"x\r\ny"\r\n'), [{'a': 'x\r\ny'}])
        for text in ['a, a\n', ',b\n', '""\n', 'a,b\nx\n', 'a\nx,y\n']:
            with self.assertRaises(ValueError):
                parse_csv_rows(text)

    def test_cache(self):
        cache, other = ExpiringCache(), ExpiringCache()
        for key, value in enumerate([0, False, '', [], None]):
            cache.set(key, value, 2, 10)
            self.assertEqual(cache.get(key, 11), value)
            self.assertIsNone(other.get(key, 11))
            self.assertIsNone(cache.get(key, 12))
            self.assertNotIn(key, cache.entries)
        cache.set('x', 1, 5, 0)
        for ttl in [0, -1]:
            with self.assertRaises(ValueError):
                cache.set('x', 99, ttl, 1)
            self.assertEqual(cache.get('x', 1), 1)
        cache.set('x', 2, 10, 2)
        self.assertEqual(cache.get('x', 11), 2)
        self.assertIsNone(cache.get('x', 12))

    def test_transfers(self):
        balances = {'a': 10, 'b': 0, 'c': 3}
        output = apply_transfers(balances, iter([('a', 'b', 5), ('b', 'c', 2), ('c', 'c', 5)]))
        self.assertEqual(output, {'a': 5, 'b': 3, 'c': 5})
        self.assertEqual(sum(output.values()), sum(balances.values()))
        self.assertEqual(balances, {'a': 10, 'b': 0, 'c': 3})
        self.assertIsNot(apply_transfers(balances, []), balances)
        invalid = [('a', 'b', 0), ('a', 'b', -1), ('a', 'b', True), ('a', 'b', 1.0),
                   ('a', 'missing', 1), ('a', 'b', 11), ('c', 'c', 4), ('a', 'b')]
        for transfer in invalid:
            with self.assertRaises(ValueError):
                apply_transfers(balances, [('a', 'b', 1), transfer])
            self.assertEqual(balances, {'a': 10, 'b': 0, 'c': 3})


if __name__ == '__main__':
    unittest.main(verbosity=2)
