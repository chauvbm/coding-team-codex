import unittest
from utilities import *


class UtilityChecks(unittest.TestCase):
    def test_paginate(self):
        self.assertEqual(paginate(iter(range(8)), 2, 3), [2, 3, 4])
        self.assertEqual(paginate([1], 3, 2), [])
        for offset, limit in [(-1, 2), (0, 0), (0, -1)]:
            with self.assertRaises(ValueError):
                paginate([], offset, limit)
        values = [1, 2]
        self.assertIsNot(paginate(values, 0, 2), values)

    def test_merge(self):
        base = {'a': {'b': [1], 'keep': 2}, 'x': [3]}
        overrides = {'a': {'c': [4]}, 'new': {'z': [5]}}
        result = deep_merge(base, overrides)
        self.assertEqual(result, {'a': {'b': [1], 'keep': 2, 'c': [4]}, 'x': [3], 'new': {'z': [5]}})
        result['a']['b'].append(9)
        result['a']['c'].append(9)
        base['x'].append(9)
        overrides['new']['z'].append(9)
        self.assertEqual(base['a']['b'], [1])
        self.assertEqual(overrides['a']['c'], [4])
        self.assertEqual(result['x'], [3])
        self.assertEqual(result['new']['z'], [5])
        self.assertEqual(deep_merge({'a': {}}, {'a': 3}), {'a': 3})

    def test_order(self):
        self.assertEqual(topological_order({'z': ['a', 'a'], 'b': ['a'], 'c': []}), ['a', 'b', 'c', 'z'])
        self.assertEqual(topological_order({'a': iter(['b']), 'c': []}), ['b', 'a', 'c'])
        self.assertEqual(topological_order({}), [])
        for dependencies in [{'a': ['a']}, {'a': ['b'], 'b': ['a']}]:
            with self.assertRaises(ValueError):
                topological_order(dependencies)

    def test_csv(self):
        self.assertEqual(parse_csv_rows('\n a , b \r\n"x,y","line1\nline2"\r\n\r\n ,value\r\n'), [{'a': 'x,y', 'b': 'line1\nline2'}, {'a': ' ', 'b': 'value'}])
        self.assertEqual(parse_csv_rows('a\n""\n'), [{'a': ''}])
        for text in ['', '\n\r\n', 'a,b\n']:
            self.assertEqual(parse_csv_rows(text), [])
        for text in [' ,b\n', 'a, a\n', 'a,b\n1\n', 'a\n1,2\n', '""\n']:
            with self.assertRaises(ValueError):
                parse_csv_rows(text)

    def test_cache(self):
        cache = ExpiringCache()
        other = ExpiringCache()
        cache.set('a', False, 2, 10)
        self.assertIs(cache.get('a', 11), False)
        self.assertIsNone(other.get('a', 11))
        for ttl in [0, -1]:
            with self.assertRaises(ValueError):
                cache.set('a', 8, ttl, 10)
        self.assertIs(cache.get('a', 11), False)
        self.assertIsNone(cache.get('a', 12))
        self.assertNotIn('a', cache.entries)
        cache.set('a', 0, 1, 20)
        cache.set('a', '', 3, 20)
        self.assertEqual(cache.get('a', 22), '')
        self.assertIsNone(cache.get('a', 23))

    def test_transfers(self):
        balances = {'a': 10, 'b': 0}
        result = apply_transfers(balances, iter([('a', 'b', 7), ('b', 'a', 2), ('a', 'a', 5)]))
        self.assertEqual(result, {'a': 5, 'b': 5})
        self.assertEqual(balances, {'a': 10, 'b': 0})
        self.assertEqual(sum(result.values()), sum(balances.values()))
        self.assertIsNot(apply_transfers(balances, []), balances)
        for transfer in [('a', 'b', 0), ('a', 'b', -1), ('a', 'b', True), ('a', 'b', 1.0), ('x', 'b', 1), ('a', 'x', 1), ('a', 'b', 11), ('a', 'a', 11), ('a',), None]:
            with self.assertRaises(ValueError):
                apply_transfers(balances, [('a', 'b', 1), transfer])
            self.assertEqual(balances, {'a': 10, 'b': 0})


if __name__ == '__main__':
    unittest.main()
