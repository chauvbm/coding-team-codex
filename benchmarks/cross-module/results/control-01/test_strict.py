import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream
from dotenv.variables import UndefinedVariableError, parse_variables


class RecordingEnvironment(dict):
    def __init__(self, values=()):
        super().__init__(values)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class StrictTests(unittest.TestCase):
    def values(self, text, **kwargs):
        return dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)

    def test_parser_boundaries(self):
        text = 'A="two\nlines"\n\n  bad syntax\nB=ok\n'
        bindings = list(parse_stream(io.StringIO(text)))
        self.assertTrue(bindings[1].error)
        iterator = parse_stream(io.StringIO(text), True)
        self.assertEqual(next(iterator), bindings[0])
        with self.assertRaises(DotEnvError) as caught:
            next(iterator)
        error = caught.exception
        self.assertEqual((error.kind, error.line, error.original),
                         ('parse', bindings[1].original.line, bindings[1].original.string))
        self.assertIn(str(error.line), str(error))
        self.assertIn('parse', str(error))

    def test_variable_missing_present_and_repeat(self):
        atom = list(parse_variables('${X}', True))[0]
        with self.assertRaises(UndefinedVariableError) as caught:
            atom.resolve({})
        self.assertEqual(caught.exception.name, 'X')
        for mapping, expected in [({'X': None}, ''), ({'X': ''}, ''), ({'X': 'ok'}, 'ok')]:
            self.assertEqual(atom.resolve(mapping), expected)
        self.assertEqual(list(parse_variables('${X}'))[0].resolve({}), '')

    def test_variable_defaults_and_literals(self):
        for mapping, expected in [({}, 'fallback'), ({'X': None}, ''), ({'X': ''}, '')]:
            self.assertEqual(''.join(a.resolve(mapping) for a in parse_variables('${X:-fallback}', True)), expected)
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('$X ${X:bad}', True)), '$X ${X:bad}')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('${X:-$Y}', True)), '$Y')

    def test_error_source_order_and_precedence(self):
        with patch.dict(os.environ, {}, clear=True):
            cases = [('A=${MISSING}\nbad syntax\n', 'undefined', 1),
                     ('bad syntax\nA=${MISSING}\n', 'parse', 1),
                     ('A=ok\nA=${MISSING}\n', 'duplicate', 2),
                     ('A=ok\nA="unterminated\n', 'parse', 2),
                     ('A\nA=two\n', 'duplicate', 2),
                     ('A=one\n\nA\n', 'duplicate', 2)]
            for text, kind, line in cases:
                with self.subTest(text=text):
                    bindings = list(parse_stream(io.StringIO(text)))
                    with self.assertRaises(DotEnvError) as caught:
                        self.values(text)
                    self.assertEqual((caught.exception.kind, caught.exception.line), (kind, line))
                    self.assertEqual(caught.exception.original, bindings[1 if len(bindings) > 1 and line == 2 else 0].original.string)

    def test_resolution_precedence_and_order(self):
        with patch.dict(os.environ, {'A': 'os'}, clear=True):
            text = 'A=file\nB=${A}\nN\nC=${N:-fallback}\nD=${ABSENT:-ok}\n'
            self.assertEqual(self.values(text), {'A': 'file', 'B': 'file', 'N': None, 'C': '', 'D': 'ok'})
            env = DotEnv(None, stream=io.StringIO(text), override=False, strict=True)
            self.assertEqual(env.dict()['B'], 'os')
            self.assertEqual(list(env.dict()), ['A', 'B', 'N', 'C', 'D'])

    def test_forward_and_self_references(self):
        with patch.dict(os.environ, {}, clear=True):
            for text in ['A=${B}\nB=later', 'A=${A}']:
                with self.assertRaises(DotEnvError) as caught:
                    self.values(text)
                self.assertEqual(caught.exception.kind, 'undefined')
        with patch.dict(os.environ, {'A': 'os'}, clear=True):
            self.assertEqual(self.values('A=${A}'), {'A': 'os'})

    def test_snapshot_before_read(self):
        class MutatingStream(io.StringIO):
            def read(self, *args):
                os.environ['X'] = 'changed'
                return super().read(*args)
        with patch.dict(os.environ, {'X': 'original'}, clear=True):
            self.assertEqual(dotenv_values(stream=MutatingStream('A=${X}\nB=${X}'), strict=True),
                             {'A': 'original', 'B': 'original'})

    def test_transaction_has_zero_writes(self):
        for text in ['A=ok\nbad syntax\n', 'A=ok\nA=second', 'A=ok\nB=${MISSING}', 'A=ok\nEXISTS=${MISSING}']:
            env = RecordingEnvironment({'EXISTS': 'old'})
            with patch('dotenv.main.os.environ', env):
                with self.assertRaises(DotEnvError):
                    load_dotenv(stream=io.StringIO(text), strict=True)
            self.assertEqual(env.writes, [])
            self.assertEqual(env, {'EXISTS': 'old'})

    def test_successful_commits(self):
        for override in (False, True):
            env = RecordingEnvironment({'A': 'old'})
            with patch('dotenv.main.os.environ', env):
                self.assertTrue(load_dotenv(stream=io.StringIO('A=new\nB=ok\nN'), override=override, strict=True))
            self.assertEqual(env.writes, ([('A', 'new')] if override else []) + [('B', 'ok')])
        self.assertFalse(load_dotenv(stream=io.StringIO(''), strict=True))
        self.assertTrue(load_dotenv(stream=io.StringIO('VALUELESS'), strict=True))

    def test_no_interpolation(self):
        self.assertEqual(self.values('A=${MISSING}', interpolate=False), {'A': '${MISSING}'})
        with self.assertRaises(DotEnvError):
            self.values('A\nA=${MISSING}', interpolate=False)
        with self.assertRaises(DotEnvError):
            self.values('bad syntax', interpolate=False)

    def test_caching_and_retry(self):
        source = io.StringIO('A=${MISSING}')
        env = DotEnv(None, source, strict=True)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DotEnvError):
                env.dict()
        self.assertIsNone(env._dict)
        source.seek(0)
        source.truncate()
        source.write('A=ok')
        source.seek(0)
        first = env.dict()
        self.assertIs(first, env.dict())
        self.assertFalse(source.closed)

    def test_paths_streams_missing_and_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('A=caf\u00e9', encoding='utf-8')
            stream = io.StringIO('A=stream')
            self.assertEqual(dotenv_values(path, stream, encoding='utf-8', strict=True)['A'], 'caf\u00e9')
            self.assertEqual(stream.tell(), 0)
            self.assertEqual(dotenv_values(Path(directory) / 'missing', strict=True), {})
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': 'true'}):
            self.assertFalse(load_dotenv(stream=io.StringIO('bad syntax'), strict=True))

    def test_permissive_recovery(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs('dotenv.main', level='WARNING'):
                values = dotenv_values(stream=io.StringIO('bad syntax\nA=first\nA=${MISSING}\nN'))
            self.assertEqual(values, {'A': '', 'N': None})


if __name__ == '__main__':
    unittest.main()
