import io
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream
from dotenv.variables import UndefinedVariableError, parse_variables


class RecordingEnv(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def __setitem__(self, name, value):
        self.writes.append((name, value))
        super().__setitem__(name, value)


class StrictTests(unittest.TestCase):
    def values(self, text, **kwargs):
        return dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)

    def assert_error(self, text, kind, index, **kwargs):
        original = list(parse_stream(io.StringIO(text)))[index].original
        with self.assertRaises(DotEnvError) as raised:
            self.values(text, **kwargs)
        error = raised.exception
        self.assertEqual((error.kind, error.line, error.original),
                         (kind, original.line, original.string))
        self.assertIn(kind, str(error))
        self.assertIn(str(original.line), str(error))
        return error

    def test_parser_boundaries_and_recovery(self):
        text = 'A=1\n\n  BROKEN="unterminated\nNEXT=2\n'
        bindings = list(parse_stream(io.StringIO(text)))
        self.assertTrue(bindings[1].error)
        iterator = parse_stream(io.StringIO(text), True)
        self.assertEqual(next(iterator), bindings[0])
        with self.assertRaises(DotEnvError) as raised:
            next(iterator)
        self.assertEqual(raised.exception.original, bindings[1].original.string)
        self.assertEqual(raised.exception.line, 2)
        self.assertEqual(bindings[-1].key, 'NEXT')
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_variable_atoms_resolve_repeatedly(self):
        atoms = list(parse_variables('${A}|${B:-literal}|$A|${C}', True))
        with self.assertRaises(UndefinedVariableError) as raised:
            ''.join(a.resolve({}) for a in atoms)
        self.assertEqual(raised.exception.name, 'A')
        self.assertEqual(''.join(a.resolve({'A': None, 'C': ''}) for a in atoms),
                         '|literal|$A|')
        self.assertEqual(''.join(a.resolve({'A': 'x', 'B': None, 'C': 'z'}) for a in atoms),
                         'x||$A|z')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('${X}')), '')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('${A:bad} $A', True)),
                         '${A:bad} $A')

    def test_error_order_and_valueless_duplicates(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('A=${MISSING}\nBAD="x\n', 'undefined', 0)
            self.assert_error('A=1\nA=${MISSING}\n', 'duplicate', 1)
            self.assert_error('A=1\nA="bad\n', 'parse', 1)
            self.assert_error('A\n\nA\n', 'duplicate', 1)
            self.assert_error('A="x\ny"\n\nA=2\n', 'duplicate', 1)
            self.assertEqual(self.values('# hello\n\nA\nB=\n'), {'A': None, 'B': ''})

    def test_snapshot_precedes_read_and_override(self):
        class MutatingStream(io.StringIO):
            def read(self, *args):
                os.environ['BASE'] = 'changed'
                os.environ['NEW'] = 'late'
                return super().read(*args)

        for override, expected in ((True, 'file'), (False, 'os')):
            with self.subTest(override=override), patch.dict(os.environ, {'BASE': 'os'}, clear=True):
                source = MutatingStream('BASE=file\nOUT=${BASE}\nOLD=${NEW:-absent}\n')
                obj = DotEnv(None, source, override=override, strict=True)
                result = obj.dict()
                self.assertEqual(result['OUT'], expected)
                self.assertEqual(result['OLD'], 'absent')
                self.assertEqual(list(result), ['BASE', 'OUT', 'OLD'])
                self.assertIs(obj.dict(), result)
                self.assertFalse(source.closed)

    def test_forward_self_and_prior_valueless(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('A=${B}\nB=ok', 'undefined', 0)
            self.assert_error('A=${A}', 'undefined', 0)
            self.assertEqual(self.values('A\nB=${A:-fallback}'), {'A': None, 'B': ''})
        with patch.dict(os.environ, {'A': 'os'}, clear=True):
            self.assertEqual(self.values('A=${A}'), {'A': 'os'})

    def test_transaction_no_writes_even_for_skipped_key(self):
        for text, kind in [('GOOD=1\nBAD="x', 'parse'),
                           ('GOOD=1\nGOOD=2', 'duplicate'),
                           ('GOOD=1\nSKIP=${NOPE}', 'undefined')]:
            env = RecordingEnv({'SKIP': 'exists'})
            with self.subTest(kind=kind), patch('os.environ', env):
                with self.assertRaises(DotEnvError):
                    load_dotenv(stream=io.StringIO(text), strict=True)
                self.assertEqual(env.writes, [])
                self.assertEqual(env, {'SKIP': 'exists'})

    def test_success_commit_and_return_behavior(self):
        env = RecordingEnv({'A': 'os'})
        with patch('os.environ', env):
            self.assertTrue(load_dotenv(stream=io.StringIO('A=file\nB=${A}\nC\n'), strict=True))
            self.assertEqual(env.writes, [('B', 'os')])
            self.assertTrue(load_dotenv(stream=io.StringIO('A=file\nC\n'), override=True, strict=True))
            self.assertEqual(env['A'], 'file')
            self.assertTrue(load_dotenv(stream=io.StringIO('C\n'), strict=True))
            self.assertFalse(load_dotenv(stream=io.StringIO('# none\n'), strict=True))

    def test_disabled_loading_does_not_read(self):
        class Unreadable(io.StringIO):
            def read(self, *args):
                raise AssertionError('unexpected read')
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': '1'}):
            self.assertFalse(load_dotenv(stream=Unreadable(), strict=True))

    def test_interpolation_off_and_permissive_mode(self):
        self.assertEqual(self.values('A=${MISSING}', interpolate=False), {'A': '${MISSING}'})
        self.assert_error('A\nA=${MISSING}', 'duplicate', 1, interpolate=False)
        self.assert_error('A="bad', 'parse', 0, interpolate=False)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(dotenv_values(stream=io.StringIO('A=1\nA=${MISSING}\n')), {'A': ''})
        with self.assertLogs('dotenv.main', 'WARNING'):
            self.assertEqual(dotenv_values(stream=io.StringIO('BAD="x\nGOOD=1')), {'GOOD': '1'})

    def test_path_encoding_precedence_and_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'values.env'
            path.write_bytes('A=café\n'.encode('utf-16'))
            stream = io.StringIO('A=stream')
            self.assertEqual(dotenv_values(path, stream, encoding='utf-16', strict=True),
                             {'A': 'café'})
            self.assertEqual(stream.tell(), 0)
            self.assertFalse(stream.closed)
            missing = Path(directory) / 'missing.env'
            self.assertEqual(dotenv_values(missing, stream, strict=True), {'A': 'stream'})
            self.assertEqual(dotenv_values(missing, strict=True), {})

    def test_failed_cache_can_retry(self):
        stream = io.StringIO('A=${MISSING}')
        obj = DotEnv(None, stream, strict=True)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DotEnvError):
                obj.dict()
            self.assertIsNone(obj._dict)
            stream.seek(0)
            os.environ['MISSING'] = 'found'
            self.assertEqual(obj.dict(), {'A': 'found'})
            os.environ['MISSING'] = 'changed'
            self.assertEqual(obj.dict(), {'A': 'found'})


if __name__ == '__main__':
    unittest.main()
