"""Coordinator-only external-source acceptance; frozen before dispatch."""
import importlib.util
import io
import itertools
import math
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(os.environ['EXTERNAL_WORKSPACE'])


def load(name):
    spec = importlib.util.spec_from_file_location('bench_' + name, ROOT / name / 'module.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Clamp(unittest.TestCase):
    def setUp(self): self.m = load('boltons')

    def test_boundaries(self):
        self.assertEqual(list(self.m.clamp_iter(iter([-3, 0, 2, 9]), 0, 3)), [0, 0, 2, 3])

    def test_streaming(self):
        consumed = []
        def source():
            for n in itertools.count():
                consumed.append(n)
                yield n
        result = self.m.clamp_iter(source(), 1, 5)
        self.assertEqual(consumed, [])
        self.assertIs(iter(result), result)
        self.assertEqual(list(itertools.islice(result, 3)), [1, 1, 2])
        self.assertEqual(consumed, [0, 1, 2])

    def test_empty_reversed_bounds(self):
        with self.assertRaises(ValueError): next(iter(self.m.clamp_iter([], 5, 2)))

    def test_comparable_strings(self):
        self.assertEqual(list(self.m.clamp_iter(['a', 'm', 'z'], 'b', 'y')), ['b', 'm', 'y'])

    def test_defaults_and_empty(self):
        self.assertEqual(list(self.m.clamp_iter([])), [])
        self.assertEqual(list(self.m.clamp_iter([-1.5, 2])), [-1.5, 2])

    def test_scalar_compatibility(self):
        self.assertEqual(self.m.clamp(10, 0, 2), 2)
        self.assertEqual(self.m.ceil(3.5, [2, 4, 8]), 4)
        self.assertEqual(self.m.floor(3.5, [2, 4, 8]), 2)


class Combination(unittest.TestCase):
    def setUp(self): self.m = load('more_itertools')

    def test_all_small_ranks(self):
        for n in range(7):
            for r in range(n + 1):
                for rank, positions in enumerate(itertools.combinations(range(n), r)):
                    self.assertEqual(self.m.combination_index(n, positions), rank)
                    self.assertEqual(self.m.nth_combination(range(n), r, rank), positions)

    def test_one_shot_empty(self):
        self.assertEqual(self.m.combination_index(0, iter(())), 0)
        self.assertEqual(self.m.combination_index(5, (x for x in [0, 3, 4])), 5)

    def test_large_first_and_last_without_pool(self):
        self.assertEqual(self.m.combination_index(10**9, [0, 1]), 0)
        self.assertEqual(self.m.combination_index(10**9, [10**9 - 2, 10**9 - 1]), math.comb(10**9, 2) - 1)

    def test_invalid_order_and_bounds(self):
        for n, indices in [(-1, []), (3, [2, 1]), (3, [1, 1]), (3, [-1]), (3, [3])]:
            with self.subTest(n=n, indices=indices), self.assertRaises(ValueError):
                self.m.combination_index(n, indices)

    def test_type_checks(self):
        for n, indices in [(True, []), (3.0, []), (3, [False]), (3, [1.0]), (3, ['1'])]:
            with self.subTest(n=n, indices=indices), self.assertRaises(TypeError):
                self.m.combination_index(n, indices)

    def test_public_export_and_old_negative_rank(self):
        self.assertIn('combination_index', self.m.__all__)
        self.assertEqual(self.m.nth_combination(range(4), 2, -1), (2, 3))


class Mapping(unittest.TestCase):
    def setUp(self): self.m = load('dotenv')
    def parse(self, value, **kwargs): return self.m.parse_mapping(io.StringIO(value), **kwargs)

    def test_values_comments_and_key_only(self):
        self.assertEqual(self.parse('# comment\nA=1\nBARE\nEMPTY=\n'), {'A': '1', 'BARE': None, 'EMPTY': ''})

    def test_duplicate_insertion_order(self):
        result = self.parse('A=1\nB=2\nA=3\n')
        self.assertEqual(result, {'A': '3', 'B': '2'})
        self.assertEqual(list(result), ['A', 'B'])

    def test_quotes_multiline_escape_and_no_interpolation(self):
        self.assertEqual(self.parse('A="one\ntwo"\nB="x\\ny"\nC=${SECRET}\n'),
                         {'A': 'one\ntwo', 'B': 'x\ny', 'C': '${SECRET}'})

    def test_non_strict_skips_bad_line(self):
        self.assertEqual(self.parse('A=1\nBAD="unterminated\nC=3\n'), {'A': '1', 'C': '3'})

    def test_strict_reports_start_line(self):
        with self.assertRaises(ValueError) as caught:
            self.parse('A="one\ntwo"\nBAD="unterminated\nC=3\n', strict=True)
        self.assertIn('3', str(caught.exception))

    def test_existing_parser_unchanged(self):
        bindings = list(self.m.parse_stream(io.StringIO('A=1\nBAD="unterminated\nC=3\n')))
        self.assertEqual([(b.key, b.value, b.error) for b in bindings],
                         [('A', '1', False), (None, None, True), ('C', '3', False)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
