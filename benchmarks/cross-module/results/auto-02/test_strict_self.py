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


class WriteRecordingEnvironment(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class StrictTests(unittest.TestCase):
    def values(self, source, **kwargs):
        return dotenv_values(stream=io.StringIO(source), strict=True, **kwargs)

    def assert_error(self, source, kind, index, **kwargs):
        binding = list(parse_stream(io.StringIO(source)))[index]
        with self.assertRaises(DotEnvError) as caught:
            self.values(source, **kwargs)
        error = caught.exception
        self.assertEqual((error.kind, error.line, error.original),
                         (kind, binding.original.line, binding.original.string))
        self.assertIn(kind, str(error))
        self.assertIn(str(error.line), str(error))
        self.assertIsInstance(error, ValueError)

    def test_export(self):
        self.assertIn('DotEnvError', dotenv.__all__)
        self.assertIs(dotenv.DotEnvError, DotEnvError)

    def test_parser_and_binding_boundaries(self):
        source = 'A=ok\r\n\r\n  B="first\nsecond" trailing\nC=ok\n'
        ordinary = list(parse_stream(io.StringIO(source)))
        self.assertTrue(ordinary[1].error)
        iterator = parse_stream(io.StringIO(source), True)
        self.assertEqual(next(iterator), ordinary[0])
        with self.assertRaises(DotEnvError) as caught:
            next(iterator)
        self.assertEqual(caught.exception.original, ordinary[1].original.string)
        self.assertEqual(caught.exception.line, ordinary[1].original.line)
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_duplicate_and_valueless(self):
        for source in ['A=1\nA=2', 'A\nA=2', 'A=1\nA', "A=1\nexport 'A'=2"]:
            with self.subTest(source=source):
                self.assert_error(source, 'duplicate', 1)
        self.assertEqual(self.values('# A=1\n\nA\nB=${A:-fallback}'), {'A': None, 'B': ''})

    def test_order_of_failures(self):
        for source, kind, index in [
            ('A=${MISSING}\nB="unterminated', 'undefined', 0),
            ('A=1\nA=${MISSING}\nB="unterminated', 'duplicate', 1),
            ('A=1\nA="unterminated', 'parse', 1),
            ('A=1\nB="unterminated\nA=2', 'parse', 1),
        ]:
            with self.subTest(source=source):
                self.assert_error(source, kind, index)

    def test_atom_missing_presence_defaults_and_reuse(self):
        atom = list(parse_variables('${NO_SUCH_NAME}', True))[0]
        for mapping, expected in [({'NO_SUCH_NAME': None}, ''), ({'NO_SUCH_NAME': ''}, ''),
                                  ({'NO_SUCH_NAME': 'yes'}, 'yes')]:
            self.assertEqual(atom.resolve(mapping), expected)
        for _ in range(2):
            with self.assertRaises(UndefinedVariableError) as caught:
                atom.resolve({})
            self.assertEqual(caught.exception.name, 'NO_SUCH_NAME')
        default_atom = list(parse_variables('${A:-${B}}', True))[0]
        self.assertEqual(default_atom.resolve({}), '${B')
        for mapping, expected in [({}, 'fallback'), ({'A': None}, ''), ({'A': ''}, '')]:
            self.assertEqual(list(parse_variables('${A:-fallback}', True))[0].resolve(mapping), expected)
        self.assertEqual(''.join(x.resolve({}) for x in parse_variables('$A ${A:bad}', True)), '$A ${A:bad}')
        self.assertEqual(''.join(x.resolve({}) for x in parse_variables('${A}')), '')

    def test_override_resolution_and_self_reference(self):
        with patch.dict(os.environ, {'A': 'os', 'SELF': 'old'}, clear=True):
            source = 'A=file\nB=${A}\nSELF=${SELF}\nNOVALUE\nC=${NOVALUE:-x}'
            self.assertEqual(self.values(source), {'A': 'file', 'B': 'file', 'SELF': 'old', 'NOVALUE': None, 'C': ''})
            result = DotEnv(None, io.StringIO(source), override=False, strict=True).dict()
            self.assertEqual(result['B'], 'os')
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('SELF=${SELF}', 'undefined', 0)
            self.assert_error('FIRST=${SECOND}\nSECOND=later', 'undefined', 0)

    def test_snapshot_precedes_read_and_is_stable(self):
        class MutatingStream(io.StringIO):
            def read(self, *args, **kwargs):
                os.environ['A'] = 'changed'
                os.environ['NEW'] = 'late'
                return super().read(*args, **kwargs)
        with patch.dict(os.environ, {'A': 'original'}, clear=True):
            obj = DotEnv(None, MutatingStream('B=${A}\nC=${A}'), strict=True)
            self.assertEqual(obj.dict(), {'B': 'original', 'C': 'original'})
        with patch.dict(os.environ, {}, clear=True):
            obj = DotEnv(None, MutatingStream('B=${NEW}'), strict=True)
            with self.assertRaises(DotEnvError):
                obj.dict()

    def test_interpolation_disabled(self):
        self.assertEqual(self.values('A=${MISSING}\nB', interpolate=False), {'A': '${MISSING}', 'B': None})
        self.assert_error('A=${MISSING}\nA', 'duplicate', 1, interpolate=False)
        self.assert_error('A=${MISSING}\nB="unterminated', 'parse', 1, interpolate=False)

    def test_zero_writes_before_any_failure_even_skipped_keys(self):
        cases = ['GOOD=1\nBAD="unterminated', 'GOOD=1\nGOOD=2',
                 'GOOD=1\nSKIP=${MISSING}', 'SKIP=ok\nSKIP=again']
        for source in cases:
            for override in [False, True]:
                with self.subTest(source=source, override=override):
                    environment = WriteRecordingEnvironment({'SKIP': 'existing'})
                    with patch('dotenv.main.os.environ', environment):
                        with self.assertRaises(DotEnvError):
                            load_dotenv(stream=io.StringIO(source), strict=True, override=override)
                    self.assertEqual(environment.writes, [])
                    self.assertEqual(environment, {'SKIP': 'existing'})

    def test_commit_and_boolean_behavior(self):
        for override, expected in [(False, 'old'), (True, 'new')]:
            environment = WriteRecordingEnvironment({'A': 'old'})
            with patch('dotenv.main.os.environ', environment):
                self.assertTrue(load_dotenv(stream=io.StringIO('A=new\nB=${A}\nC'), strict=True, override=override))
            self.assertEqual(environment['A'], expected)
            self.assertEqual(environment['B'], expected)
            self.assertNotIn('C', environment)
        self.assertFalse(DotEnv(None, io.StringIO('# comment'), strict=True).set_as_environment_variables())
        self.assertTrue(DotEnv(None, io.StringIO('VALUELESS'), strict=True).set_as_environment_variables())

    def test_cache_success_and_failure(self):
        source = io.StringIO('A=${MISSING}')
        obj = DotEnv(None, source, strict=True)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DotEnvError):
                obj.dict()
            self.assertIsNone(obj._dict)
            source.seek(0)
            source.truncate()
            source.write('A=good')
            source.seek(0)
            first = obj.dict()
            source.close()
            self.assertIs(obj.dict(), first)
            self.assertEqual(first, {'A': 'good'})

    def test_path_stream_ownership_encoding_and_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('UNICODE=héllo', encoding='utf-16')
            stream = io.StringIO('STREAM=value')
            self.assertEqual(dotenv_values(path, stream, encoding='utf-16', strict=True), {'UNICODE': 'héllo'})
            self.assertFalse(stream.closed)
            self.assertEqual(stream.tell(), 0)
            self.assertEqual(dotenv_values(Path(folder) / 'missing', strict=True), {})
            self.assertEqual(dotenv_values(Path(folder) / 'missing', stream, strict=True), {'STREAM': 'value'})
            self.assertFalse(stream.closed)

    def test_disabled_and_permissive(self):
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': 'true'}):
            self.assertFalse(load_dotenv(stream=io.StringIO('BAD="unterminated'), strict=True))
        source = 'A=1\nA=2\nBAD="unterminated\nB=${ABSENT}'
        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs('dotenv.main', level='WARNING'):
                self.assertEqual(dotenv_values(stream=io.StringIO(source)), {'A': '2', 'B': ''})


if __name__ == '__main__':
    unittest.main()
