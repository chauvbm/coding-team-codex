import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dotenv
from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream
from dotenv.variables import UndefinedVariableError, parse_variables


class TrackingEnvironment(dict):
    def __init__(self, values=()):
        super().__init__(values)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class StrictTests(unittest.TestCase):
    def error(self, text, kind, index, **kwargs):
        binding = list(parse_stream(io.StringIO(text)))[index]
        with self.assertRaises(DotEnvError) as caught:
            dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)
        error = caught.exception
        self.assertEqual((error.kind, error.line, error.original),
                         (kind, binding.original.line, binding.original.string))
        self.assertIn(kind, str(error))
        self.assertIn(str(error.line), str(error))

    def test_export_and_signatures(self):
        self.assertIn('DotEnvError', dotenv.__all__)
        self.assertTrue(issubclass(DotEnvError, ValueError))
        self.assertEqual(dotenv_values(None, io.StringIO('A=1'), False, True, 'utf-8', True), {'A': '1'})
        self.assertEqual(DotEnv(None, io.StringIO('A=1'), False, None, True, True, True).dict(), {'A': '1'})

    def test_parser_preserves_binding_boundaries(self):
        text = '\n\nA="one\ntwo"\n\nBROKEN="unterminated\nNEXT=ok\n'
        bindings = list(parse_stream(io.StringIO(text)))
        iterator = parse_stream(io.StringIO(text), True)
        self.assertEqual(next(iterator), bindings[0])
        with self.assertRaises(DotEnvError) as caught:
            next(iterator)
        self.assertEqual(caught.exception.original, bindings[1].original.string)
        self.assertEqual(caught.exception.line, bindings[1].original.line)
        self.assertTrue(bindings[1].error)
        self.assertEqual(bindings[-1].key, 'NEXT')
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_errors_and_precedence(self):
        with patch.dict(os.environ, {}, clear=True):
            cases = [
                ('A=1\n\nA=2\n', 'duplicate', 1),
                ('A\nA=2\n', 'duplicate', 1),
                ('A=1\nA\n', 'duplicate', 1),
                ('A=1\nA=${MISSING}\n', 'duplicate', 1),
                ('A=1\nA="bad" junk\n', 'parse', 1),
                ('A=${MISSING}\nA=2\n', 'undefined', 0),
                ('A=${MISSING}\nBAD="unterminated\n', 'undefined', 0),
                ('\n\nA=${MISSING}\n', 'undefined', 0),
                ('A="line1\n${MISSING}"\n', 'undefined', 0),
                ('A=${A}\n', 'undefined', 0),
                ('A=${B}\nB=2', 'undefined', 0),
            ]
            for text, kind, index in cases:
                with self.subTest(text=text):
                    self.error(text, kind, index)

    def test_atoms_repeat_resolution_and_defaults(self):
        atom = list(parse_variables('${NAME}', True))[0]
        self.assertEqual(atom.resolve({'NAME': 'value'}), 'value')
        self.assertEqual(atom.resolve({'NAME': None}), '')
        self.assertEqual(atom.resolve({'NAME': ''}), '')
        with self.assertRaises(UndefinedVariableError) as caught:
            atom.resolve({})
        self.assertEqual(caught.exception.name, 'NAME')
        self.assertIsInstance(caught.exception, ValueError)
        default = list(parse_variables('${NAME:-$LITERAL}', True))[0]
        self.assertEqual(default.resolve({}), '$LITERAL')
        self.assertEqual(default.resolve({'NAME': None}), '')
        self.assertEqual(default.resolve({'NAME': ''}), '')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('$NAME ${NAME:bad}', True)), '$NAME ${NAME:bad}')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('${NAME}')), '')

    def test_snapshot_before_read_and_override_order(self):
        env = TrackingEnvironment({'A': 'os'})
        class ChangingStream(io.StringIO):
            def read(self, *args):
                env['A'] = 'changed'
                env['FUTURE'] = 'late'
                return super().read(*args)
        for override, expected in [(True, 'file'), (False, 'os')]:
            env = TrackingEnvironment({'A': 'os'})
            with patch('dotenv.main.os.environ', env):
                source = ChangingStream('FIRST=${A}\nA=file\nSECOND=${A}\nTHIRD=${FUTURE:-absent}')
                result = DotEnv(None, source, override=override, strict=True).dict()
                self.assertEqual(result, {'FIRST': 'os', 'A': 'file', 'SECOND': expected, 'THIRD': 'absent'})

    def test_values_order_none_and_literals(self):
        with patch.dict(os.environ, {}, clear=True):
            result = dotenv_values(stream=io.StringIO('#comment\n\nNONE\nA=${NONE}\nB=${ABSENT:-raw}\nC=\n'), strict=True)
            self.assertEqual(list(result), ['NONE', 'A', 'B', 'C'])
            self.assertEqual(result, {'NONE': None, 'A': '', 'B': 'raw', 'C': ''})
            self.assertEqual(dotenv_values(stream=io.StringIO('A=${MISSING}'), strict=True, interpolate=False), {'A': '${MISSING}'})
            self.error('A=1\nA=${MISSING}', 'duplicate', 1, interpolate=False)
            self.error('A="bad" junk', 'parse', 0, interpolate=False)

    def test_zero_writes_including_skipped_and_duplicate(self):
        for text in ['OK=1\nBAD="bad" junk', 'OK=1\nSKIP=${MISSING}', 'OK=1\nA\nA=2']:
            for direct in (True, False):
                with self.subTest(text=text, direct=direct):
                    env = TrackingEnvironment({'SKIP': 'existing'})
                    with patch('dotenv.main.os.environ', env):
                        with self.assertRaises(DotEnvError):
                            if direct:
                                DotEnv(None, io.StringIO(text), override=False, strict=True).set_as_environment_variables()
                            else:
                                load_dotenv(stream=io.StringIO(text), strict=True)
                    self.assertEqual(env.writes, [])

    def test_successful_commits_and_booleans(self):
        for override in (False, True):
            env = TrackingEnvironment({'A': 'os'})
            with patch('dotenv.main.os.environ', env):
                self.assertTrue(load_dotenv(stream=io.StringIO('A=file\nB=${A}\nNONE'), override=override, strict=True))
                self.assertEqual(env['A'], 'file' if override else 'os')
                self.assertEqual(env['B'], 'file' if override else 'os')
                self.assertNotIn('NONE', env)
                self.assertFalse(load_dotenv(stream=io.StringIO(''), strict=True))
                self.assertTrue(load_dotenv(stream=io.StringIO('NONE'), strict=True))

    def test_failed_and_successful_caches(self):
        stream = io.StringIO('A=1\nA=2')
        instance = DotEnv(None, stream, strict=True)
        with self.assertRaises(DotEnvError):
            instance.dict()
        self.assertIsNone(instance._dict)
        stream.seek(0)
        stream.truncate()
        stream.write('B=2')
        stream.seek(0)
        result = instance.dict()
        self.assertEqual(result, {'B': '2'})
        self.assertIs(instance.dict(), result)
        self.assertFalse(stream.closed)

    def test_path_precedence_missing_and_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vars.env'
            path.write_text('A=caf\u00e9', encoding='utf-16')
            ignored = io.StringIO('BAD="bad" junk')
            self.assertEqual(dotenv_values(path, ignored, encoding='utf-16', strict=True), {'A': 'caf\u00e9'})
            self.assertEqual(ignored.tell(), 0)
            self.assertFalse(ignored.closed)
            missing = Path(directory) / 'missing.env'
            self.assertEqual(dotenv_values(missing, strict=True), {})
            self.assertEqual(dotenv_values(missing, io.StringIO('A=fallback'), strict=True), {'A': 'fallback'})

    def test_disabled_loading_and_permissive_compatibility(self):
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': 'true'}, clear=True):
            self.assertFalse(load_dotenv(stream=io.StringIO('BAD="bad" junk'), strict=True))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs('dotenv.main', level='WARNING'):
                result = dotenv_values(stream=io.StringIO('BAD="bad" junk\nA=1\nA=2\nB=${MISSING}'))
            self.assertEqual(result, {'A': '2', 'B': ''})


if __name__ == '__main__':
    unittest.main()
