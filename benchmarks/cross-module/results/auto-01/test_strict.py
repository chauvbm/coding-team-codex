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


class RecordingEnv(dict):
    def __init__(self, initial=()):
        super().__init__(initial)
        self.writes = []

    def __setitem__(self, name, value):
        self.writes.append((name, value))
        super().__setitem__(name, value)


class StrictLoadingTests(unittest.TestCase):
    def values(self, text, **kwargs):
        return dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)

    def assert_failure(self, text, kind, index):
        binding = list(parse_stream(io.StringIO(text)))[index]
        with self.assertRaises(DotEnvError) as caught:
            self.values(text)
        error = caught.exception
        self.assertEqual((error.kind, error.line, error.original),
                         (kind, binding.original.line, binding.original.string))
        self.assertIn(kind, str(error))
        self.assertIn(str(error.line), str(error))

    def test_metadata_and_source_order(self):
        for text, kind, index in [
            ('\n\nBAD="oops\n', 'parse', 0),
            ('A=1\n\nA="two\nlines"\n', 'duplicate', 1),
            ('A=1\n\nB="${MISSING}\nlines"\n', 'undefined', 1),
            ('A=1\nA=${MISSING}\nBAD="oops', 'duplicate', 1),
            ('A=${MISSING}\nA=2\n', 'undefined', 0),
            ('A=1\nA="oops\n', 'parse', 1),
            ('A\nA=2\n', 'duplicate', 1),
            ('A=1\nA\n', 'duplicate', 1),
        ]:
            with self.subTest(text=text), patch('dotenv.main.os.environ', {}):
                self.assert_failure(text, kind, index)

    def test_parser_strict_and_recovery(self):
        text = 'A=1\nBAD="oops\nZ=3\n'
        baseline = list(parse_stream(io.StringIO(text)))
        self.assertEqual([b.error for b in baseline], [False, True, False])
        it = parse_stream(io.StringIO(text), True)
        self.assertEqual(next(it), baseline[0])
        with self.assertRaises(DotEnvError):
            next(it)
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_lower_level_atoms(self):
        atom = list(parse_variables('${X}', True))[0]
        for mapping, expected in [({'X': None}, ''), ({'X': ''}, ''), ({'X': 'ok'}, 'ok')]:
            self.assertEqual(atom.resolve(mapping), expected)
        with self.assertRaises(UndefinedVariableError) as caught:
            atom.resolve({})
        self.assertEqual(caught.exception.name, 'X')
        default = list(parse_variables('${X:-literal}', True))[0]
        self.assertEqual(default.resolve({}), 'literal')
        self.assertEqual(default.resolve({'X': None}), '')
        self.assertEqual(default.resolve({'X': ''}), '')
        self.assertEqual(list(parse_variables('${X}'))[0].resolve({}), '')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('$X ${X:bad}', True)), '$X ${X:bad}')

    def test_order_precedence_and_none(self):
        source = 'A=file\nB=${A}\nN\nC=${N:-default}\nE=\nD=${E:-default}\n'
        with patch('dotenv.main.os.environ', {'A': 'os'}):
            self.assertEqual(DotEnv(None, io.StringIO(source), override=True, strict=True).dict(),
                             {'A': 'file', 'B': 'file', 'N': None, 'C': '', 'E': '', 'D': ''})
            self.assertEqual(DotEnv(None, io.StringIO(source), override=False, strict=True).dict()['B'], 'os')
        self.assertEqual(list(self.values('Z=1\nA=2')), ['Z', 'A'])

    def test_self_and_forward_references(self):
        with patch('dotenv.main.os.environ', {}):
            for text in ['A=${A}', 'A=${B}\nB=2']:
                with self.assertRaises(DotEnvError):
                    self.values(text)
        with patch('dotenv.main.os.environ', {'A': 'old', 'B': 'os'}):
            self.assertEqual(self.values('A=${A}\nC=${B}\nB=file'), {'A': 'old', 'C': 'os', 'B': 'file'})

    def test_snapshot_before_read(self):
        env = RecordingEnv({'X': 'before'})
        class MutatingStream(io.StringIO):
            def read(self, *args):
                env['X'] = 'after'
                env['NEW'] = 'new'
                return super().read(*args)
        with patch('dotenv.main.os.environ', env):
            obj = DotEnv(None, MutatingStream('A=${X}\nB=${X}'), strict=True)
            self.assertEqual(obj.dict(), {'A': 'before', 'B': 'before'})
            obj = DotEnv(None, MutatingStream('A=${NEW}'), strict=True)
            del env['NEW']
            with self.assertRaises(DotEnvError):
                obj.dict()

    def test_transaction_zero_writes(self):
        for text in ['A=1\nBAD="oops', 'A=1\nA=2', 'A=1\nB=${MISSING}', 'SKIP=${MISSING}']:
            for override in [True, False]:
                env = RecordingEnv({'SKIP': 'keep'})
                with patch('dotenv.main.os.environ', env):
                    with self.assertRaises(DotEnvError):
                        load_dotenv(stream=io.StringIO(text), strict=True, override=override)
                self.assertEqual(env.writes, [])
                self.assertEqual(env, {'SKIP': 'keep'})

    def test_successful_commit_and_returns(self):
        for override, expected in [(False, 'keep'), (True, 'new')]:
            env = RecordingEnv({'A': 'keep'})
            with patch('dotenv.main.os.environ', env):
                self.assertTrue(load_dotenv(stream=io.StringIO('A=new\nB=ok\nN'), strict=True, override=override))
                self.assertEqual(env, {'A': expected, 'B': 'ok'})
        with patch('dotenv.main.os.environ', RecordingEnv()):
            self.assertFalse(load_dotenv(stream=io.StringIO('#comment\n'), strict=True))
            self.assertTrue(load_dotenv(stream=io.StringIO('N'), strict=True))

    def test_interpolation_disabled(self):
        self.assertEqual(self.values('A=${MISSING}', interpolate=False), {'A': '${MISSING}'})
        with self.assertRaises(DotEnvError):
            self.values('A=1\nA=${MISSING}', interpolate=False)
        with self.assertRaises(DotEnvError):
            self.values('BAD="oops', interpolate=False)

    def test_cache_retry_and_stream_ownership(self):
        source = io.StringIO('A=${MISSING}')
        obj = DotEnv(None, source, strict=True)
        with patch('dotenv.main.os.environ', {}):
            with self.assertRaises(DotEnvError):
                obj.dict()
            self.assertIsNone(obj._dict)
            source.seek(0)
            source.truncate()
            source.write('A=fixed')
            source.seek(0)
            result = obj.dict()
            self.assertIs(obj.dict(), result)
            self.assertFalse(source.closed)

    def test_compatibility_missing_disabled_and_path(self):
        with self.assertLogs('dotenv.main', level='WARNING'):
            self.assertEqual(dotenv_values(stream=io.StringIO('A=1\nBAD="oops\nA=2\nB=${MISSING}')), {'A': '2', 'B': ''})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('A=caf\u00e9', encoding='utf-16')
            stream = io.StringIO('BAD="oops')
            self.assertEqual(dotenv_values(path, stream, False, True, 'utf-16', True), {'A': 'caf\u00e9'})
            self.assertEqual(stream.tell(), 0)
            self.assertEqual(dotenv_values(Path(directory) / 'missing', strict=True), {})
        with patch('dotenv.main.os.environ', {'PYTHON_DOTENV_DISABLED': 'true'}):
            self.assertFalse(load_dotenv(stream=io.StringIO('BAD="oops'), strict=True))


if __name__ == '__main__':
    unittest.main()
