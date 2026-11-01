"""Standard-library self-checks for the requested strict dotenv contract."""
import inspect
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dotenv import DotEnvError, dotenv_values, load_dotenv
from dotenv.main import DotEnv
from dotenv.parser import DotEnvError as ParserError, parse_stream
from dotenv.variables import UndefinedVariableError, parse_variables


class WriteTrackingDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class StrictChecks(unittest.TestCase):
    def values(self, text, **kwargs):
        return dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)

    def error(self, text, kind, **kwargs):
        with self.assertRaises(DotEnvError) as caught:
            self.values(text, **kwargs)
        error = caught.exception
        bindings = list(parse_stream(io.StringIO(text)))
        original = next(b.original for b in bindings if b.original.line == error.line)
        self.assertEqual((error.kind, error.original), (kind, original.string))
        self.assertIn(kind, str(error))
        self.assertIn(str(error.line), str(error))
        return error

    def test_public_interfaces(self):
        self.assertIs(DotEnvError, ParserError)
        self.assertTrue(issubclass(DotEnvError, ValueError))
        import dotenv
        self.assertIn('DotEnvError', dotenv.__all__)
        for function in (DotEnv, dotenv_values, load_dotenv, parse_stream, parse_variables):
            parameters = list(inspect.signature(function).parameters.values())
            self.assertEqual(parameters[-1].name, 'strict')
            self.assertIs(parameters[-1].default, False)

    def test_parser_preserves_success_and_errors(self):
        text = '\n\nA="hello\nworld"\n\nB="bad" junk\nC=ok\n'
        permissive = list(parse_stream(io.StringIO(text)))
        strict = parse_stream(io.StringIO(text), True)
        self.assertEqual(next(strict), permissive[0])
        with self.assertRaises(DotEnvError) as caught:
            next(strict)
        bad = permissive[1]
        self.assertEqual((caught.exception.kind, caught.exception.line, caught.exception.original),
                         ('parse', bad.original.line, bad.original.string))
        self.assertTrue(bad.error)
        self.assertEqual(permissive[-1].key, 'C')
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_atoms_missing_present_and_defaults(self):
        atom = list(parse_variables('${MISSING}', True))[0]
        with self.assertRaises(UndefinedVariableError) as caught:
            atom.resolve({})
        self.assertEqual(caught.exception.name, 'MISSING')
        for value in (None, ''):
            self.assertEqual(atom.resolve({'MISSING': value}), '')
        self.assertEqual(atom.resolve({'MISSING': 'yes'}), 'yes')
        with self.assertRaises(UndefinedVariableError):
            atom.resolve({})
        for strict in (False, True):
            default = list(parse_variables('${A:-literal $B}', strict))[0]
            self.assertEqual(default.resolve({}), 'literal $B')
            for value in (None, ''):
                self.assertEqual(default.resolve({'A': value}), '')
        self.assertEqual(list(parse_variables('${A}'))[0].resolve({}), '')
        text = '$A/${A:bad}/raw'
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables(text, True)), text)

    def test_duplicates_include_valueless_and_quote_export(self):
        for text in ('A=1\nA=2', 'A\nA=2', 'A=1\nA', "export A=1\n'A'=2"):
            self.assertEqual(self.error(text, 'duplicate').line, 2)
        self.assertEqual(self.values('#comment\n\nA\nB=\nC=hi'), {'A': None, 'B': '', 'C': 'hi'})

    def test_precedence_and_source_order(self):
        with patch.dict(os.environ, {}, clear=True):
            self.error('A=${MISSING}\ninvalid line\nA=2', 'undefined')
            self.error('A=1\nA=${MISSING}', 'duplicate')
            self.error('A=1\nA="bad" extra', 'parse')
            self.error('A=1\nA=2\ninvalid line', 'duplicate')
            self.error('invalid line\nA=${MISSING}', 'parse')

    def test_source_order_and_override(self):
        with patch.dict(os.environ, {'A': 'os', 'FORWARD': 'os-forward'}, clear=True):
            text = 'A=file\nB=${A}\nC=${FORWARD}\nFORWARD=later\nN\nD=${N:-default}\n'
            self.assertEqual(self.values(text), {'A': 'file', 'B': 'file', 'C': 'os-forward', 'FORWARD': 'later', 'N': None, 'D': ''})
            obj = DotEnv(None, stream=io.StringIO(text), strict=True, override=False)
            self.assertEqual(obj.dict()['B'], 'os')
            self.assertEqual(list(obj.dict()), ['A', 'B', 'C', 'FORWARD', 'N', 'D'])
        with patch.dict(os.environ, {}, clear=True):
            self.error('A=${A}', 'undefined')
            self.error('A=${B}\nB=later', 'undefined')
            self.assertEqual(self.values('A=${A:-self-default}'), {'A': 'self-default'})

    def test_snapshot_precedes_source_read(self):
        class MutatingStream(io.StringIO):
            def read(self, *args):
                os.environ['A'] = 'changed'
                return super().read(*args)
        with patch.dict(os.environ, {'A': 'before'}, clear=True):
            for override in (False, True):
                os.environ['A'] = 'before'
                obj = DotEnv(None, stream=MutatingStream('B=${A}\nC=${A}'), override=override, strict=True)
                self.assertEqual(obj.dict(), {'B': 'before', 'C': 'before'})

    def test_no_interpolation(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.values('A=${MISSING}', interpolate=False), {'A': '${MISSING}'})
            self.error('A\nA=${MISSING}', 'duplicate', interpolate=False)
            self.error('invalid line', 'parse', interpolate=False)

    def test_transaction_has_zero_writes(self):
        for text in ('GOOD=ok\ninvalid line', 'GOOD=ok\nGOOD=again', 'GOOD=ok\nBAD=${MISSING}', 'SKIP=${MISSING}'):
            for method in ('load', 'object'):
                env = WriteTrackingDict({'SKIP': 'existing'})
                with patch('dotenv.main.os.environ', env):
                    with self.assertRaises(DotEnvError):
                        if method == 'load':
                            load_dotenv(stream=io.StringIO(text), strict=True)
                        else:
                            DotEnv(None, stream=io.StringIO(text), strict=True, override=False).set_as_environment_variables()
                self.assertEqual(env.writes, [])
                self.assertEqual(env, {'SKIP': 'existing'})

    def test_commit_and_booleans(self):
        for override in (False, True):
            env = WriteTrackingDict({'A': 'os'})
            with patch('dotenv.main.os.environ', env):
                self.assertTrue(load_dotenv(stream=io.StringIO('A=file\nB=${A}\nN'), strict=True, override=override))
            self.assertEqual(env['A'], 'file' if override else 'os')
            self.assertEqual(env['B'], 'file' if override else 'os')
            self.assertNotIn('N', env)
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(load_dotenv(stream=io.StringIO('#comment'), strict=True))
            self.assertTrue(load_dotenv(stream=io.StringIO('N'), strict=True))

    def test_failed_cache_and_success_cache(self):
        stream = io.StringIO('A=${MISSING}')
        obj = DotEnv(None, stream=stream, strict=True)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DotEnvError):
                obj.dict()
            self.assertIsNone(obj._dict)
            stream.seek(0)
            os.environ['MISSING'] = 'fixed'
            result = obj.dict()
            os.environ['MISSING'] = 'changed'
            self.assertIs(obj.dict(), result)
            self.assertEqual(result, {'A': 'fixed'})
            self.assertFalse(stream.closed)

    def test_path_precedence_encoding_missing_disabled(self):
        with tempfile.TemporaryDirectory(dir='.') as folder:
            path = Path(folder) / '.env'
            path.write_text('A=caf\u00e9', encoding='utf-16')
            stream = io.StringIO('invalid line')
            self.assertEqual(dotenv_values(path, stream, False, True, 'utf-16', True), {'A': 'caf\u00e9'})
            self.assertFalse(stream.closed)
            self.assertEqual(dotenv_values(path.with_name('missing'), strict=True), {})
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': 'true'}, clear=True):
            self.assertFalse(load_dotenv(stream=io.StringIO('invalid line'), strict=True))

    def test_permissive_recovery(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs('dotenv.main', level='WARNING'):
                self.assertEqual(dotenv_values(stream=io.StringIO('A=${MISSING}\ninvalid line\nA=last\nN')), {'A': 'last', 'N': None})


if __name__ == '__main__':
    unittest.main(verbosity=2)
