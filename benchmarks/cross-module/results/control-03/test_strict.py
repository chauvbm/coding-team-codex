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


class WriteLog(dict):
    def __init__(self, values=()):
        super().__init__(values)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class StrictTests(unittest.TestCase):
    def assert_error(self, text, kind, line=None, original=None, **kwargs):
        with self.assertRaises(DotEnvError) as caught:
            dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)
        error = caught.exception
        self.assertEqual(error.kind, kind)
        self.assertIsInstance(error, ValueError)
        self.assertIn(kind, str(error))
        self.assertIn(str(error.line), str(error))
        if line is not None:
            self.assertEqual(error.line, line)
        if original is not None:
            self.assertEqual(error.original, original)
        return error

    def test_export_and_signatures(self):
        self.assertIn('DotEnvError', dotenv.__all__)
        self.assertIs(dotenv.DotEnvError, DotEnvError)
        self.assertEqual(dict(dotenv_values(None, io.StringIO('A=x'), False, True, 'utf-8', True)), {'A': 'x'})
        self.assertEqual(DotEnv(None, io.StringIO('A=x'), False, None, True, True, True).dict(), {'A': 'x'})

    def test_parser_error_boundaries_and_recovery(self):
        text = 'OK=yes\n\n  X="unterminated\nAFTER=yes\n'
        permissive = list(parse_stream(io.StringIO(text)))
        bad = next(b for b in permissive if b.error)
        iterator = parse_stream(io.StringIO(text), True)
        self.assertEqual(next(iterator).key, 'OK')
        with self.assertRaises(DotEnvError) as caught:
            next(iterator)
        self.assertEqual((caught.exception.kind, caught.exception.line, caught.exception.original), ('parse', bad.original.line, bad.original.string))
        self.assertEqual(permissive[-1].key, 'AFTER')

    def test_parser_allows_duplicate(self):
        self.assertEqual([b.key for b in parse_stream(io.StringIO('A\nA\n'), True)], ['A', 'A'])

    def test_multiline_duplicate_context(self):
        self.assert_error('A=x\n\n A="one\ntwo"\n', 'duplicate', 2, '\n A="one\ntwo"\n')

    def test_order_and_precedence(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('A=${MISSING}\nBAD="\n', 'undefined', 1)
            self.assert_error('A=x\nA=${MISSING}\n', 'duplicate', 2)
            self.assert_error('A=x\nA="x" trailing\n', 'parse', 2)
            self.assert_error('A\nA=x\n', 'duplicate', 2)
            self.assert_error('BAD="\nA=${MISSING}\n', 'parse', 1)

    def test_comments_and_blank_lines(self):
        self.assertEqual(dotenv_values(stream=io.StringIO('\n# hi\n\nA\n# hi\nB=\n'), strict=True), {'A': None, 'B': ''})

    def test_atoms_repeat_and_defaults(self):
        atom = list(parse_variables('${X}', True))[0]
        with self.assertRaises(UndefinedVariableError) as caught:
            atom.resolve({})
        self.assertEqual(caught.exception.name, 'X')
        for value in ('', None):
            self.assertEqual(atom.resolve({'X': value}), '')
        self.assertEqual(atom.resolve({'X': 'new'}), 'new')
        with self.assertRaises(UndefinedVariableError):
            atom.resolve({})
        default = list(parse_variables('${X:-literal}', True))[0]
        self.assertEqual(default.resolve({}), 'literal')
        self.assertEqual(default.resolve({'X': None}), '')
        self.assertEqual(default.resolve({'X': ''}), '')
        self.assertEqual(default.resolve({'X': 'set'}), 'set')

    def test_grammar_unchanged(self):
        for strict in (False, True):
            atoms = parse_variables('$X ${X:bad} ${X:-$LITERAL}', strict)
            self.assertEqual(''.join(a.resolve({}) for a in atoms), '$X ${X:bad} $LITERAL')
        self.assertEqual(''.join(a.resolve({}) for a in parse_variables('${X}')), '')

    def test_snapshot_and_precedence(self):
        for override, expected in ((True, 'file'), (False, 'os')):
            with self.subTest(override=override), patch.dict(os.environ, {'A': 'os'}, clear=True):
                values = DotEnv(None, io.StringIO('A=file\nB=${A}\nC\nD=${C:-fallback}\n'), strict=True, override=override).dict()
                self.assertEqual(list(values), ['A', 'B', 'C', 'D'])
                self.assertEqual(values, {'A': 'file', 'B': expected, 'C': None, 'D': ''})

    def test_snapshot_before_read_and_single_snapshot(self):
        class MutatingStream(io.StringIO):
            def read(self, *args):
                os.environ['A'] = 'changed'
                os.environ['LATER'] = 'added'
                return super().read(*args)
        with patch.dict(os.environ, {'A': 'initial'}, clear=True):
            values = dotenv_values(stream=MutatingStream('B=${A}\nC=${A}\n'), strict=True)
            self.assertEqual(values, {'B': 'initial', 'C': 'initial'})
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DotEnvError):
                dotenv_values(stream=MutatingStream('B=${LATER}\n'), strict=True)

    def test_forward_and_self_reference(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('A=${B}\nB=x\n', 'undefined')
            self.assert_error('A=${A}\n', 'undefined')
        with patch.dict(os.environ, {'A': 'os', 'B': 'forward'}, clear=True):
            self.assertEqual(dotenv_values(stream=io.StringIO('A=${A}\nC=${B}\nB=file'), strict=True), {'A': 'os', 'C': 'forward', 'B': 'file'})

    def test_interpolation_disabled(self):
        self.assertEqual(dotenv_values(stream=io.StringIO('A=${MISSING}'), strict=True, interpolate=False), {'A': '${MISSING}'})
        self.assert_error('A\nA=${MISSING}', 'duplicate', interpolate=False)
        self.assert_error('A="\n', 'parse', interpolate=False)

    def test_transaction_zero_writes(self):
        for text, kind in [('A=x\nB="\n', 'parse'), ('A=x\nA=y\n', 'duplicate'), ('A=x\nB=${MISSING}\n', 'undefined'), ('EXISTING=${MISSING}\n', 'undefined'), ('A\nA\n', 'duplicate')]:
            for override in (False, True):
                with self.subTest(text=text, override=override):
                    env = WriteLog({'EXISTING': 'old'})
                    with patch('dotenv.main.os.environ', env):
                        with self.assertRaises(DotEnvError) as caught:
                            load_dotenv(stream=io.StringIO(text), strict=True, override=override)
                    self.assertEqual(caught.exception.kind, kind)
                    self.assertEqual(env.writes, [])
                    self.assertEqual(env, {'EXISTING': 'old'})

    def test_successful_commit_and_boolean(self):
        for override in (False, True):
            env = WriteLog({'A': 'old'})
            with patch('dotenv.main.os.environ', env):
                self.assertTrue(load_dotenv(stream=io.StringIO('A=new\nB=x\nC\n'), strict=True, override=override))
            self.assertEqual(env['A'], 'new' if override else 'old')
            self.assertEqual(env['B'], 'x')
            self.assertNotIn('C', env)
        with patch('dotenv.main.os.environ', WriteLog()):
            self.assertFalse(load_dotenv(stream=io.StringIO(''), strict=True))
            self.assertTrue(load_dotenv(stream=io.StringIO('C'), strict=True))

    def test_cache_failure_and_success(self):
        with patch.dict(os.environ, {}, clear=True):
            stream = io.StringIO('A=${MISSING}')
            obj = DotEnv(None, stream, strict=True)
            with self.assertRaises(DotEnvError):
                obj.dict()
            self.assertIsNone(obj._dict)
            stream.seek(0)
            os.environ['MISSING'] = 'fixed'
            first = obj.dict()
            os.environ['MISSING'] = 'changed'
            self.assertIs(obj.dict(), first)
            self.assertEqual(first, {'A': 'fixed'})
            self.assertFalse(stream.closed)

    def test_path_precedence_missing_and_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('A=caf\u00e9', encoding='utf-8')
            stream = io.StringIO('A=stream')
            self.assertEqual(dotenv_values(path, stream=stream, strict=True), {'A': 'caf\u00e9'})
            self.assertEqual(stream.tell(), 0)
            self.assertEqual(dotenv_values(Path(directory) / 'absent', strict=True), {})
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': 'yes'}):
            self.assertFalse(load_dotenv(stream=io.StringIO('A="\n'), strict=True))

    def test_permissive_compatibility(self):
        with patch.dict(os.environ, {}, clear=True):
            for strict in (False,):
                values = dotenv_values(stream=io.StringIO('A=one\nBAD="\nA=two\nB=${MISSING}\nC\n'), strict=strict)
                self.assertEqual(values, {'A': 'two', 'B': '', 'C': None})


if __name__ == '__main__':
    unittest.main()
