import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream
from dotenv.variables import UndefinedVariableError, parse_variables


class TrackingEnvironment(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class StrictTests(unittest.TestCase):
    def values(self, source, **kwargs):
        return dotenv_values(stream=io.StringIO(source), strict=True, **kwargs)

    def assert_failure(self, source, kind, index, **kwargs):
        bindings = list(parse_stream(io.StringIO(source)))
        with self.assertRaises(DotEnvError) as caught:
            self.values(source, **kwargs)
        exc = caught.exception
        self.assertEqual((exc.kind, exc.line, exc.original),
                         (kind, bindings[index].original.line, bindings[index].original.string))
        self.assertIn(kind, str(exc))
        self.assertIn(str(exc.line), str(exc))

    def test_parser_context_and_recovery(self):
        source = 'A=ok\n\n  BAD value\nB="two\nlines"\n'
        loose = list(parse_stream(io.StringIO(source)))
        self.assertTrue(loose[1].error)
        iterator = parse_stream(io.StringIO(source), True)
        self.assertEqual(next(iterator), loose[0])
        with self.assertRaises(DotEnvError) as caught:
            next(iterator)
        self.assertEqual(caught.exception.original, '\n  BAD value\n')
        self.assertEqual(caught.exception.line, 2)
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_atom_absence_defaults_and_reuse(self):
        atom, = parse_variables('${M}', True)
        with self.assertRaises(UndefinedVariableError) as caught:
            atom.resolve({})
        self.assertEqual(caught.exception.name, 'M')
        for value in [None, '']:
            self.assertEqual(atom.resolve({'M': value}), '')
        self.assertEqual(atom.resolve({'M': 'yes'}), 'yes')
        with self.assertRaises(UndefinedVariableError):
            atom.resolve({})
        default, = parse_variables('${M:-literal}', True)
        self.assertEqual(default.resolve({}), 'literal')
        self.assertEqual(default.resolve({'M': None}), '')
        self.assertEqual(default.resolve({'M': ''}), '')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('$M ${M:x} ${M}')), '$M ${M:x} ')

    def test_source_order_and_same_binding_precedence(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_failure('A=1\nA=${M}\nBAD value\n', 'duplicate', 1)
            self.assert_failure('A=${M}\nA=2\n', 'undefined', 0)
            self.assert_failure('A=1\nA="x" trailing\n', 'parse', 1)
            self.assert_failure('A\nA\n', 'duplicate', 1)
            self.assert_failure('\n\nA="hello\n${M}"\n', 'undefined', 0)
            self.assert_failure('A=${B}\nB=ok\n', 'undefined', 0)
            self.assert_failure('A=${A}\n', 'undefined', 0)

    def test_snapshot_and_override_order(self):
        class MutatingStream(io.StringIO):
            def read(self, *args):
                os.environ['A'] = 'changed'
                os.environ['LATE'] = 'late'
                return super().read(*args)
        with patch.dict(os.environ, {'A': 'os'}, clear=True):
            for override, expected in [(True, 'file'), (False, 'os')]:
                os.environ['A'] = 'os'
                obj = DotEnv(None, stream=MutatingStream('A=file\nB=${A}\n'), strict=True, override=override)
                self.assertEqual(obj.dict()['B'], expected)
            os.environ.pop('LATE', None)
            obj = DotEnv(None, stream=MutatingStream('B=${LATE}\n'), strict=True)
            with self.assertRaises(DotEnvError):
                obj.dict()

    def test_valueless_and_no_interpolation(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.values('# hi\nA\nB=${A:-fallback}\nC=${Z:-literal}\n'),
                             {'A': None, 'B': '', 'C': 'literal'})
            self.assertEqual(self.values('A=${M}\n', interpolate=False), {'A': '${M}'})
            self.assert_failure('A=${M}\nA=2', 'duplicate', 1, interpolate=False)
            self.assert_failure('BAD value', 'parse', 0, interpolate=False)

    def test_no_writes_on_any_validation_failure_including_skips(self):
        for source in ['GOOD=1\nBAD value\n', 'GOOD=1\nGOOD=2\n', 'GOOD=1\nSKIP=${M}\n']:
            env = TrackingEnvironment({'SKIP': 'existing'})
            with patch('os.environ', env):
                with self.assertRaises(DotEnvError):
                    load_dotenv(stream=io.StringIO(source), strict=True)
            self.assertEqual(env.writes, [])

    def test_success_commit_and_return(self):
        env = TrackingEnvironment({'A': 'os'})
        with patch('os.environ', env):
            self.assertTrue(load_dotenv(stream=io.StringIO('A=file\nB=${A}\nC\n'), strict=True))
            self.assertEqual(env.writes, [('B', 'os')])
            self.assertTrue(load_dotenv(stream=io.StringIO('C\n'), strict=True))
            self.assertFalse(load_dotenv(stream=io.StringIO('# comment\n'), strict=True))
            self.assertTrue(load_dotenv(stream=io.StringIO('A=file'), override=True, strict=True))
            self.assertEqual(env['A'], 'file')

    def test_failed_cache_retry_and_success_cache(self):
        with patch.dict(os.environ, {}, clear=True):
            stream = io.StringIO('A=${M}\n')
            obj = DotEnv(None, stream=stream, strict=True)
            with self.assertRaises(DotEnvError):
                obj.dict()
            self.assertIsNone(obj._dict)
            stream.seek(0)
            os.environ['M'] = 'found'
            result = obj.dict()
            self.assertIs(obj.dict(), result)
            self.assertFalse(stream.closed)

    def test_source_precedence_missing_and_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.env'
            path.write_text('A=caf\u00e9', encoding='utf-8')
            stream = io.StringIO('A=stream')
            self.assertEqual(dotenv_values(path, stream, False, True, 'utf-8', True), {'A': 'caf\u00e9'})
            self.assertEqual(stream.tell(), 0)
            self.assertEqual(dotenv_values(path.with_name('missing'), strict=True), {})
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': 'true'}):
            self.assertFalse(load_dotenv(stream=io.StringIO('BAD value'), strict=True))

    def test_permissive_unchanged(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs('dotenv.main', level='WARNING'):
                result = dotenv_values(stream=io.StringIO('A=${M}\nBAD value\nA=last\nC\n'))
            self.assertEqual(result, {'A': 'last', 'C': None})
            self.assertEqual(list(result), ['A', 'C'])


if __name__ == '__main__':
    unittest.main()
