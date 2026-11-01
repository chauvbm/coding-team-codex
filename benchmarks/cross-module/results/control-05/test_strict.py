import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import dotenv
from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import parse_stream
from dotenv.variables import UndefinedVariableError, parse_variables


class RecordingEnvironment(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class StrictTests(unittest.TestCase):
    def values(self, text, **kwargs):
        return dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)

    def assert_error(self, text, kind, index, **kwargs):
        bindings = list(parse_stream(io.StringIO(text)))
        expected = bindings[index]
        with self.assertRaises(DotEnvError) as caught:
            self.values(text, **kwargs)
        error = caught.exception
        self.assertEqual((error.kind, error.line, error.original),
                         (kind, expected.original.line, expected.original.string))
        self.assertIn(kind, str(error))
        self.assertIn(str(expected.original.line), str(error))
        return error

    def test_exports(self):
        self.assertIn('DotEnvError', dotenv.__all__)
        self.assertTrue(issubclass(DotEnvError, ValueError))

    def test_parser_boundaries_and_recovery(self):
        text = 'A="first\nsecond"\n\n  broken = "oops\nC=ok\n'
        bindings = list(parse_stream(io.StringIO(text)))
        self.assertFalse(bindings[0].error)
        self.assertTrue(bindings[1].error)
        self.assertEqual(bindings[1].original.line, 3)
        self.assertEqual(bindings[1].original.string, '\n  broken = "oops\n')
        iterator = parse_stream(io.StringIO(text), strict=True)
        self.assertEqual(next(iterator), bindings[0])
        with self.assertRaises(DotEnvError) as caught:
            next(iterator)
        self.assertEqual(caught.exception.original, bindings[1].original.string)
        self.assertEqual(caught.exception.line, 3)

    def test_parser_does_not_reject_duplicates(self):
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_atoms_repeated_resolution_and_presence(self):
        atom = list(parse_variables('${MISSING}', strict=True))[0]
        for mapping in ({}, {}, {'OTHER': 'value'}):
            with self.assertRaises(UndefinedVariableError) as caught:
                atom.resolve(mapping)
            self.assertEqual(caught.exception.name, 'MISSING')
        for value, expected in ((None, ''), ('', ''), ('value', 'value')):
            self.assertEqual(atom.resolve({'MISSING': value}), expected)
        default = list(parse_variables('${MISSING:-literal${X}}', True))
        self.assertEqual(''.join(a.resolve({}) for a in default), 'literal${X}')

    def test_default_and_grammar(self):
        for value, expected in (({}, 'default'), ({'A': None}, ''), ({'A': ''}, ''),
                                ({'A': 'x'}, 'x')):
            atoms = parse_variables('${A:-default}', True)
            self.assertEqual(''.join(a.resolve(value) for a in atoms), expected)
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('$A ${A:bad}', True)),
                         '$A ${A:bad}')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('${A}')), '')

    def test_duplicate_valueless_and_decorated_keys(self):
        self.assert_error('# comment\n\nA\nexport A=2\n', 'duplicate', 2)
        self.assert_error("'A'=1\nA\n", 'duplicate', 1)

    def test_error_precedence_in_source_order(self):
        with patch.object(os, 'environ', {}):
            for text, kind, index in (
                ('A=${ABSENT}\nA=2\n', 'undefined', 0),
                ('A=1\nA=${ABSENT}\n', 'duplicate', 1),
                ('A=1\nA=2\nbad="\n', 'duplicate', 1),
                ('A=1\nA="broken\n', 'parse', 1),
                ('A=${ABSENT}\nbad="\n', 'undefined', 0),
            ):
                with self.subTest(text=text):
                    self.assert_error(text, kind, index)

    def test_reference_order_and_self_reference(self):
        with patch.object(os, 'environ', {}):
            self.assert_error('A=${LATER}\nLATER=x\n', 'undefined', 0)
            self.assert_error('A=${A}\n', 'undefined', 0)
            self.assertEqual(self.values('A\nB=${A}\nC=${A:-default}\n'),
                             {'A': None, 'B': '', 'C': ''})
        with patch.object(os, 'environ', {'A': 'outside'}):
            self.assertEqual(self.values('A=${A}\n'), {'A': 'outside'})

    def test_override_precedence(self):
        for override, expected in ((True, 'file'), (False, 'os')):
            with patch.object(os, 'environ', {'A': 'os'}):
                obj = DotEnv(None, stream=io.StringIO('A=file\nB=${A}'),
                             strict=True, override=override)
                self.assertEqual(obj.dict(), {'A': 'file', 'B': expected})

    def test_snapshot_is_before_source_read(self):
        class MutatingStream(io.StringIO):
            def read(self, *args):
                os.environ['A'] = 'changed'
                os.environ['ADDED'] = 'later'
                return super().read(*args)
        with patch.object(os, 'environ', {'A': 'before'}):
            obj = DotEnv(None, stream=MutatingStream('B=${A}\nC=${ADDED:-absent}'),
                         strict=True)
            self.assertEqual(obj.dict(), {'B': 'before', 'C': 'absent'})

    def test_no_interpolation(self):
        self.assertEqual(self.values('A=${ABSENT}\n', interpolate=False),
                         {'A': '${ABSENT}'})
        self.assert_error('A=${ABSENT}\nA\n', 'duplicate', 1, interpolate=False)
        self.assert_error('A="broken\n', 'parse', 0, interpolate=False)

    def test_failure_has_zero_writes_even_for_skipped_keys(self):
        for text in ('FIRST=1\nbad="\n', 'FIRST=1\nA\nA=x\n',
                     'FIRST=1\nA=${ABSENT}\n'):
            for override in (False, True):
                environment = RecordingEnvironment({'A': 'existing'})
                with patch.object(os, 'environ', environment):
                    with self.assertRaises(DotEnvError):
                        load_dotenv(stream=io.StringIO(text), strict=True,
                                    override=override)
                self.assertEqual(environment.writes, [])
                self.assertEqual(environment, {'A': 'existing'})

    def test_direct_commit_and_boolean_semantics(self):
        for override, expected in ((False, [('B', 'old')]),
                                   (True, [('A', 'new'), ('B', 'new')])):
            environment = RecordingEnvironment({'A': 'old'})
            with patch.object(os, 'environ', environment):
                obj = DotEnv(None, stream=io.StringIO('A=new\nB=${A}\nC\n'),
                             strict=True, override=override)
                self.assertTrue(obj.set_as_environment_variables())
            self.assertEqual(environment.writes, expected)
        with patch.object(os, 'environ', RecordingEnvironment()):
            self.assertFalse(load_dotenv(stream=io.StringIO('# only comment'), strict=True))
            self.assertTrue(load_dotenv(stream=io.StringIO('VALUELESS'), strict=True))

    def test_cache_failure_then_success(self):
        stream = io.StringIO('A=${ABSENT}')
        obj = DotEnv(None, stream=stream, strict=True)
        with patch.object(os, 'environ', {}):
            with self.assertRaises(DotEnvError):
                obj.dict()
            self.assertIsNone(obj._dict)
            stream.seek(0)
            stream.truncate()
            stream.write('A=ok')
            stream.seek(0)
            result = obj.dict()
            self.assertEqual(result, {'A': 'ok'})
            self.assertIs(result, obj.dict())
            self.assertFalse(stream.closed)

    def test_permissive_defaults_and_explicit_false(self):
        for strict in (False,):
            with patch.object(os, 'environ', {}):
                with self.assertLogs('dotenv.main', level='WARNING'):
                    self.assertEqual(dotenv_values(stream=io.StringIO(
                        'A=1\nA=2\nbad="\nB=${ABSENT}\n'), strict=strict),
                        {'A': '2', 'B': ''})
        with patch.object(os, 'environ', {}):
            self.assertEqual(dotenv_values(stream=io.StringIO('A=${ABSENT}')), {'A': ''})

    def test_missing_file_and_disabled_loading(self):
        self.assertEqual(dotenv_values('does-not-exist.env', strict=True), {})
        stream = io.StringIO('bad="\n')
        with patch.object(os, 'environ', {'PYTHON_DOTENV_DISABLED': 'true'}):
            self.assertFalse(load_dotenv(stream=stream, strict=True))
        self.assertEqual(stream.tell(), 0)

    def test_path_precedence_encoding_and_stream_ownership(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / 'encoded.env'
            path.write_text('A=caf\u00e9\n', encoding='utf-16')
            stream = io.StringIO('B=stream')
            self.assertEqual(dotenv_values(path, stream, False, True, 'utf-16', True),
                             {'A': 'caf\u00e9'})
            self.assertEqual(stream.tell(), 0)
            self.assertFalse(stream.closed)
            missing = Path(directory) / 'missing.env'
            self.assertEqual(dotenv_values(missing, stream, strict=True), {'B': 'stream'})
            self.assertFalse(stream.closed)

    def test_multiline_undefined_metadata(self):
        with patch.object(os, 'environ', {}):
            self.assert_error('A=ok\r\n\r\n B="one\r\n${ABSENT}"\r\n',
                              'undefined', 1)


if __name__ == '__main__':
    unittest.main()
