"""Independent acceptance tests derived solely from coding-pilot contract s1."""

import unittest

from utilities import (
    ExpiringCache,
    apply_transfers,
    deep_merge,
    paginate,
    parse_csv_rows,
    topological_order,
)


class Task1(unittest.TestCase):
    def test_order_and_slice(self):
        self.assertEqual(paginate([9, 2, 7, 4], 1, 2), [2, 7])

    def test_end_and_empty(self):
        for offset in (3, 10):
            self.assertEqual(paginate([1, 2, 3], offset, 2), [])
        self.assertEqual(paginate([], 0, 1), [])
        self.assertEqual(paginate([1, 2], 1, 10), [2])

    def test_generator(self):
        self.assertEqual(paginate((i * 2 for i in range(5)), 2, 2), [4, 6])

    def test_invalid_ranges(self):
        for offset, limit in ((-1, 2), (0, 0), (0, -2)):
            with self.subTest(offset=offset, limit=limit):
                with self.assertRaises(ValueError):
                    paginate([1, 2], offset, limit)

    def test_result_is_new_list_and_input_unchanged(self):
        values = [1, 2, 3]
        result = paginate(values, 0, 3)
        self.assertIsInstance(result, list)
        self.assertIsNot(result, values)
        result.append(4)
        self.assertEqual(values, [1, 2, 3])


class Task2(unittest.TestCase):
    def test_recursive_merge(self):
        self.assertEqual(
            deep_merge({'a': {'x': 1, 'y': 2}, 'b': 3},
                       {'a': {'y': 9, 'z': 4}, 'c': 5}),
            {'a': {'x': 1, 'y': 9, 'z': 4}, 'b': 3, 'c': 5},
        )

    def test_replacement_types(self):
        self.assertEqual(
            deep_merge({'a': {'x': 1}, 'b': 2, 'c': [1]},
                       {'a': None, 'b': {'y': 3}, 'c': [2]}),
            {'a': None, 'b': {'y': 3}, 'c': [2]},
        )

    def test_empty_inputs(self):
        self.assertEqual(deep_merge({}, {}), {})
        self.assertEqual(deep_merge({}, {'x': 1}), {'x': 1})
        self.assertEqual(deep_merge({'x': 1}, {}), {'x': 1})

    def test_result_mutations_do_not_change_inputs(self):
        base = {'base': [{'a': [1]}], 'nested': {'kept': [2]}}
        overrides = {'override': [{'b': [3]}], 'nested': {'added': [4]}}
        result = deep_merge(base, overrides)
        result['base'][0]['a'].append(10)
        result['nested']['kept'].append(20)
        result['override'][0]['b'].append(30)
        result['nested']['added'].append(40)
        self.assertEqual(base, {'base': [{'a': [1]}], 'nested': {'kept': [2]}})
        self.assertEqual(overrides, {'override': [{'b': [3]}], 'nested': {'added': [4]}})

    def test_later_input_mutations_do_not_change_result(self):
        base = {'a': [{'v': [1]}]}
        overrides = {'b': {'v': [2]}}
        result = deep_merge(base, overrides)
        base['a'][0]['v'].append(8)
        overrides['b']['v'].append(9)
        self.assertEqual(result, {'a': [{'v': [1]}], 'b': {'v': [2]}})
        self.assertEqual(base, {'a': [{'v': [1, 8]}]})
        self.assertEqual(overrides, {'b': {'v': [2, 9]}})


class Task3(unittest.TestCase):
    def test_empty_and_single(self):
        self.assertEqual(topological_order({}), [])
        self.assertEqual(topological_order({'one': []}), ['one'])

    def test_prerequisite_only_nodes_and_duplicates(self):
        self.assertEqual(topological_order({'c': ['b', 'a', 'b']}), ['a', 'b', 'c'])

    def test_smallest_ready_node_after_each_step(self):
        self.assertEqual(topological_order({'z': [], 'b': ['a'], 'a': []}),
                         ['a', 'b', 'z'])

    def test_dependency_chain_and_input_unchanged(self):
        dependencies = {'d': ['c', 'b'], 'c': ['a'], 'b': ['a'], 'a': []}
        self.assertEqual(topological_order(dependencies), ['a', 'b', 'c', 'd'])
        self.assertEqual(dependencies, {'d': ['c', 'b'], 'c': ['a'], 'b': ['a'], 'a': []})

    def test_generator_prerequisites(self):
        self.assertEqual(topological_order({'c': (x for x in ['b', 'a', 'b'])}),
                         ['a', 'b', 'c'])

    def test_cycles(self):
        for dependencies in ({'a': ['a']}, {'a': ['b'], 'b': ['a']},
                             {'ready': [], 'a': ['b'], 'b': ['a']}):
            with self.subTest(dependencies=dependencies):
                with self.assertRaises(ValueError):
                    topological_order(dependencies)


class Task4(unittest.TestCase):
    def test_trim_headers_preserve_cells(self):
        self.assertEqual(parse_csv_rows(' name , count \n Alice ,001\n'),
                         [{'name': ' Alice ', 'count': '001'}])

    def test_quoted_commas_newlines_and_quotes(self):
        self.assertEqual(parse_csv_rows('name,note\r\n"A,B","first\nsecond ""quoted"""\r\n'),
                         [{'name': 'A,B', 'note': 'first\nsecond "quoted"'}])

    def test_empty_and_header_only(self):
        self.assertEqual(parse_csv_rows(''), [])
        self.assertEqual(parse_csv_rows('a,b\n'), [])

    def test_blank_physical_rows_are_ignored(self):
        self.assertEqual(parse_csv_rows('\na,b\n\n1,2\n\n3,4\n'),
                         [{'a': '1', 'b': '2'}, {'a': '3', 'b': '4'}])

    def test_explicit_empty_cells_are_records(self):
        self.assertEqual(parse_csv_rows('a\n""\n'), [{'a': ''}])
        self.assertEqual(parse_csv_rows('a,b\n,\n'), [{'a': '', 'b': ''}])

    def test_invalid_headers(self):
        for text in ('a,a\n1,2\n', ' a ,a \n1,2\n', 'a, \n1,2\n', '""\n'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_csv_rows(text)

    def test_missing_and_extra_cells(self):
        for text in ('a,b\n1\n', 'a,b\n1,2,3\n', 'a,b\n""\n'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_csv_rows(text)


class Task5(unittest.TestCase):
    def test_expiration_boundary(self):
        cache = ExpiringCache()
        cache.set('a', 'value', 2.5, 10)
        self.assertEqual(cache.get('a', 12.49), 'value')
        self.assertIsNone(cache.get('a', 12.5))

    def test_expired_entry_is_removed(self):
        cache = ExpiringCache()
        cache.set('a', 'value', 2, 10)
        self.assertIsNone(cache.get('a', 13))
        self.assertIsNone(cache.get('a', 11))

    def test_falsey_values(self):
        cache = ExpiringCache()
        for key, value in enumerate((False, 0, '', [], {})):
            cache.set(key, value, 5, 0)
            self.assertEqual(cache.get(key, 1), value)

    def test_update_replaces_value_and_expiration(self):
        cache = ExpiringCache()
        cache.set('a', 'old', 10, 0)
        cache.set('a', 'new', 2, 1)
        self.assertEqual(cache.get('a', 2), 'new')
        self.assertIsNone(cache.get('a', 3))
        cache.set('a', 'later', 10, 4)
        self.assertEqual(cache.get('a', 13), 'later')

    def test_invalid_ttl_preserves_existing_entry(self):
        cache = ExpiringCache()
        cache.set('a', 'original', 10, 0)
        for ttl in (0, -1):
            with self.assertRaises(ValueError):
                cache.set('a', 'bad', ttl, 2)
            self.assertEqual(cache.get('a', 9), 'original')
        self.assertIsNone(cache.get('a', 10))

    def test_instances_and_missing_keys(self):
        first, second = ExpiringCache(), ExpiringCache()
        first.set('a', 1, 10, 0)
        self.assertIsNone(second.get('a', 1))
        second.set('a', 2, 10, 0)
        self.assertEqual(first.get('a', 1), 1)
        self.assertEqual(second.get('a', 1), 2)
        self.assertIsNone(first.get('missing', 1))


class Task6(unittest.TestCase):
    def test_ordered_transfers_and_conservation(self):
        balances = {'a': 10, 'b': 0, 'c': 2}
        transfers = [('a', 'b', 10), ('b', 'c', 7)]
        result = apply_transfers(balances, transfers)
        self.assertEqual(result, {'a': 0, 'b': 3, 'c': 9})
        self.assertEqual(sum(result.values()), sum(balances.values()))
        self.assertEqual(balances, {'a': 10, 'b': 0, 'c': 2})
        self.assertEqual(transfers, [('a', 'b', 10), ('b', 'c', 7)])

    def test_empty_returns_independent_dictionary(self):
        balances = {'a': 3}
        result = apply_transfers(balances, [])
        self.assertEqual(result, balances)
        self.assertIsNot(result, balances)
        result['a'] = 4
        self.assertEqual(balances, {'a': 3})
        self.assertEqual(apply_transfers({}, []), {})

    def test_generator(self):
        self.assertEqual(apply_transfers({'a': 2, 'b': 0},
                                        (t for t in [('a', 'b', 1), ('a', 'b', 1)])),
                         {'a': 0, 'b': 2})

    def test_invalid_amount_types_and_values(self):
        for amount in (0, -1, True, False, 1.0, '1', None):
            balances = {'a': 3, 'b': 0}
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    apply_transfers(balances, [('a', 'b', amount)])
                self.assertEqual(balances, {'a': 3, 'b': 0})

    def test_missing_accounts(self):
        for source, destination in (('missing', 'b'), ('a', 'missing'), ('missing', 'missing')):
            balances = {'a': 3, 'b': 0}
            with self.subTest(source=source, destination=destination):
                with self.assertRaises(ValueError):
                    apply_transfers(balances, [(source, destination, 1)])
                self.assertEqual(balances, {'a': 3, 'b': 0})

    def test_atomic_rollback_after_valid_prefix(self):
        for invalid in (('a', 'b', 8), ('b', 'missing', 1), ('b', 'a', False)):
            balances = {'a': 10, 'b': 0}
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    apply_transfers(balances, [('a', 'b', 3), invalid])
                self.assertEqual(balances, {'a': 10, 'b': 0})

    def test_same_account_with_and_without_sufficient_funds(self):
        balances = {'a': 5, 'b': 0}
        self.assertEqual(apply_transfers(balances, [('a', 'a', 5)]), balances)
        with self.assertRaises(ValueError):
            apply_transfers(balances, [('a', 'a', 6)])
        self.assertEqual(balances, {'a': 5, 'b': 0})


if __name__ == '__main__':
    unittest.main()
