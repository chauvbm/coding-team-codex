"""Developer checks derived only from the public TASKS.md contracts."""
import unittest

from utilities import (
    ExpiringCache, apply_transfers, deep_merge, paginate, parse_csv_rows,
    topological_order,
)


class ContractChecks(unittest.TestCase):
    def test_pagination(self):
        self.assertEqual(paginate(iter(range(10)), 3, 2), [3, 4])
        self.assertEqual(paginate([1], 4, 2), [])
        self.assertEqual(paginate([], 0, 1), [])
        for offset, limit in [(-1, 2), (0, 0), (0, -1)]:
            with self.assertRaises(ValueError):
                paginate([], offset, limit)

    def test_merge_independence(self):
        base = {'a': {'x': [1], 'y': 2}, 'b': [{'n': 3}]}
        override = {'a': {'y': [4]}, 'c': [{'m': 5}]}
        result = deep_merge(base, override)
        self.assertEqual(result, {
            'a': {'x': [1], 'y': [4]}, 'b': [{'n': 3}], 'c': [{'m': 5}]})
        result['a']['x'].append(2)
        result['c'][0]['m'] = 9
        base['b'][0]['n'] = 8
        override['a']['y'].append(6)
        self.assertEqual(base['a']['x'], [1])
        self.assertEqual(override['c'], [{'m': 5}])
        self.assertEqual(result['b'], [{'n': 3}])
        self.assertEqual(result['a']['y'], [4])
        self.assertEqual(deep_merge({'a': []}, {'a': {'b': 1}}), {'a': {'b': 1}})

    def test_topology(self):
        dependencies = {'z': ['a', 'a'], 'a': ['b'], 'c': []}
        self.assertEqual(topological_order(dependencies), ['b', 'a', 'c', 'z'])
        self.assertEqual(dependencies['z'], ['a', 'a'])
        self.assertEqual(topological_order({'c': iter(['a', 'b'])}), ['a', 'b', 'c'])
        self.assertEqual(topological_order({}), [])
        for graph in [{'a': ['a']}, {'a': ['b'], 'b': ['a']}, {'a': [], 'b': ['c'], 'c': ['b']}]:
            with self.assertRaises(ValueError):
                topological_order(graph)

    def test_csv(self):
        self.assertEqual(parse_csv_rows('\n name , note\r\n"A,B"," x\r\ny "\r\n\r\n'),
                         [{'name': 'A,B', 'note': ' x\r\ny '}])
        self.assertEqual(parse_csv_rows('a\n\n""\n'), [{'a': ''}])
        for text in ['', '\n\r\n', 'a,b\n']:
            self.assertEqual(parse_csv_rows(text), [])
        for text in ['a, a\n', ',b\n', '""\n', 'a,b\n1\n', 'a\n1,2\n', 'a\n"unfinished']:
            with self.assertRaises(ValueError):
                parse_csv_rows(text)

    def test_cache(self):
        cache = ExpiringCache()
        other = ExpiringCache()
        for i, value in enumerate([0, False, '', [], None]):
            cache.set(i, value, 5, 10)
            self.assertIs(cache.get(i, 14), value)
            self.assertIsNone(other.get(i, 14))
            self.assertIsNone(cache.get(i, 15))
            self.assertNotIn(i, cache.entries)
        cache.set('x', 'old', 10, 0)
        for ttl in [0, -1]:
            with self.assertRaises(ValueError):
                cache.set('x', 'bad', ttl, 1)
        self.assertEqual(cache.get('x', 2), 'old')
        cache.set('x', 'new', 20, 2)
        self.assertEqual(cache.get('x', 21), 'new')
        self.assertIsNone(cache.get('x', 22))

    def test_transfers(self):
        balances = {'a': 10, 'b': 0, 'c': 4}
        result = apply_transfers(balances, iter([('a', 'b', 7), ('b', 'c', 3), ('c', 'c', 7)]))
        self.assertEqual(result, {'a': 3, 'b': 4, 'c': 7})
        self.assertEqual(sum(result.values()), sum(balances.values()))
        self.assertEqual(balances, {'a': 10, 'b': 0, 'c': 4})
        self.assertIsNot(apply_transfers(balances, []), balances)
        for invalid in [('a', 'b', 0), ('a', 'b', -1), ('a', 'b', True),
                        ('a', 'b', 1.5), ('a', 'q', 1), ('a', 'a', 11),
                        ('b', 'a', 4), ('a',), None, ([], 'a', 1)]:
            with self.assertRaises(ValueError):
                apply_transfers(balances, [('a', 'b', 3), invalid])
            self.assertEqual(balances, {'a': 10, 'b': 0, 'c': 4})


if __name__ == '__main__':
    unittest.main()
