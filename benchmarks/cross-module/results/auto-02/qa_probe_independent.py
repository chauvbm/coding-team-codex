import inspect
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


class RecordingEnv(dict):
    def __init__(self, initial=()):
        super().__init__(initial)
        self.writes = []

    def __setitem__(self, key, value):
        self.writes.append((key, value))
        super().__setitem__(key, value)


class IndependentQA(unittest.TestCase):
    def values(self, text, **kw):
        return DotEnv(None, stream=io.StringIO(text), strict=True, **kw).dict()

    def test_interfaces(self):
        self.assertIs(dotenv.DotEnvError, DotEnvError)
        self.assertIn('DotEnvError', dotenv.__all__)
        self.assertTrue(issubclass(DotEnvError, ValueError))
        self.assertTrue(issubclass(UndefinedVariableError, ValueError))
        for function in (DotEnv.__init__, dotenv_values, load_dotenv, parse_stream, parse_variables):
            parameters = list(inspect.signature(function).parameters.values())
            self.assertEqual(parameters[-1].name, 'strict')
            self.assertIs(parameters[-1].default, False)

    def test_low_level_atoms(self):
        for name in ('A', '', 'A B', 'a.b', 'x-y'):
            atoms = list(parse_variables('${' + name + '}', strict=True))
            self.assertEqual(len(atoms), 1)
            atom = atoms[0]
            for value in ('yes', '', None):
                self.assertEqual(atom.resolve({name: value}), value or '')
            with self.assertRaises(UndefinedVariableError) as caught:
                atom.resolve({})
            self.assertEqual(caught.exception.name, name)
            self.assertEqual(atom.resolve({name: 'later'}), 'later')
        for default in ('', 'literal', '${NESTED'):
            atom = list(parse_variables('${M:-' + default + '}', True))[0]
            self.assertEqual(atom.resolve({}), default)
            self.assertEqual(atom.resolve({'M': None}), '')
            self.assertEqual(atom.resolve({'M': ''}), '')
        for text in ('$A', '${A-default}', '${A:default}', '${UNCLOSED', 'hello'):
            # Recognized grammar remains whatever the permissive upstream parser recognizes.
            strict = list(parse_variables(text, True))
            permissive = list(parse_variables(text))
            self.assertEqual(strict, permissive)
            env = {'A-default': 'ok'}
            self.assertEqual(''.join(x.resolve(env) for x in strict), ''.join(x.resolve(env) for x in permissive))

    def test_error_context_and_first_failure(self):
        inputs = [
            ('\n A=one\n\n A=two\n', 'duplicate', 1),
            ('A\nA=two\n', 'duplicate', 1),
            ('A=one\nA=${MISSING}\n', 'duplicate', 1),
            ('A=${MISSING}\nA=two\n', 'undefined', 0),
            ('A=${MISSING}\nBAD="unterminated\n', 'undefined', 0),
            ('A=one\nA="x" trailing\n', 'parse', 1),
            ('# hi\n\nA="line1\n${MISSING}\nline3"\n', 'undefined', 1),
            ('A=one\r\n\r\nA=two\r\n', 'duplicate', 1),
        ]
        with patch.dict(os.environ, {}, clear=True):
            for text, kind, index in inputs:
                with self.subTest(text=text):
                    binding = list(parse_stream(io.StringIO(text)))[index]
                    with self.assertRaises(DotEnvError) as caught:
                        self.values(text)
                    error = caught.exception
                    self.assertEqual((error.kind, error.line, error.original), (kind, binding.original.line, binding.original.string))
                    self.assertIn(kind, str(error))
                    self.assertIn(str(error.line), str(error))

    def test_parser_recovery_and_duplicate_independence(self):
        text = 'A=1\n\nBROKEN="no\nB=2\nA=3\n'
        permissive = list(parse_stream(io.StringIO(text)))
        self.assertTrue(any(x.error for x in permissive))
        generator = parse_stream(io.StringIO(text), True)
        self.assertEqual(next(generator), permissive[0])
        with self.assertRaises(DotEnvError) as caught:
            next(generator)
        self.assertEqual(caught.exception.original, permissive[1].original.string)
        self.assertEqual(len(list(parse_stream(io.StringIO('A=1\nA=2'), True))), 2)

    def test_resolution_override_self_forward_and_none(self):
        with patch.dict(os.environ, {'A': 'OS', 'SELF': 'base', 'FORWARD': 'osfuture'}, clear=True):
            text = 'A=file\nB=${A}\nSELF=${SELF}x\nX=${FORWARD}\nFORWARD=filefuture\nN\nY=${N:-unused}\nEMPTY=\nZ=${EMPTY:-unused}\n'
            for override in (True, False):
                result = self.values(text, override=override)
                self.assertEqual(result['B'], 'file' if override else 'OS')
                self.assertEqual(result['SELF'], 'basex')
                self.assertEqual(result['X'], 'osfuture')
                self.assertIsNone(result['N'])
                self.assertEqual(result['Y'], '')
                self.assertEqual(result['Z'], '')
                self.assertEqual(list(result), ['A', 'B', 'SELF', 'X', 'FORWARD', 'N', 'Y', 'EMPTY', 'Z'])
        with patch.dict(os.environ, {}, clear=True):
            for text in ('A=${A}\n', 'A=${B}\nB=future\n'):
                with self.assertRaises(DotEnvError):
                    self.values(text)

    def test_snapshot_before_stream_read(self):
        class MutatingStream(io.StringIO):
            reads = 0
            def read(self, *args):
                self.reads += 1
                os.environ['SNAP'] = 'after'
                return super().read(*args)
        for override in (True, False):
            env = RecordingEnv({'SNAP': 'before'})
            stream = MutatingStream('A=${SNAP}\nB=${SNAP}\n')
            with patch('dotenv.main.os.environ', env):
                result = DotEnv(None, stream=stream, override=override, strict=True).dict()
            self.assertEqual(result, {'A': 'before', 'B': 'before'})
            self.assertEqual(stream.reads, 1)
            self.assertFalse(stream.closed)

    def test_zero_writes_on_each_failure_for_both_entrypoints(self):
        texts = ('NEW=ok\nBAD="no\n', 'NEW=ok\nOLD\nOLD=x\n', 'NEW=ok\nOLD=${MISSING}\n')
        for text in texts:
            for override in (False, True):
                for use_load in (False, True):
                    env = RecordingEnv({'OLD': 'existing'})
                    with patch('dotenv.main.os.environ', env):
                        with self.assertRaises(DotEnvError):
                            if use_load:
                                load_dotenv(stream=io.StringIO(text), strict=True, override=override)
                            else:
                                DotEnv(None, stream=io.StringIO(text), strict=True, override=override).set_as_environment_variables()
                    self.assertEqual(env.writes, [])
                    self.assertEqual(env, {'OLD': 'existing'})

    def test_interpolation_off_still_validates_and_permissive_unchanged(self):
        self.assertEqual(self.values('A=${UNDEFINED}\n', interpolate=False), {'A': '${UNDEFINED}'})
        for text, kind in (('A\nA=x', 'duplicate'), ('A="unterminated', 'parse')):
            with self.assertRaises(DotEnvError) as caught:
                self.values(text, interpolate=False)
            self.assertEqual(caught.exception.kind, kind)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(dotenv_values(stream=io.StringIO('A=${M}\nA=last\nBAD="no\nB=ok')), {'A': 'last', 'B': 'ok'})

    def test_cache_success_and_retry_after_failure(self):
        for text in ('A=${MISSING}', 'A=x\nA=y', 'A="no'):
            stream = io.StringIO(text)
            instance = DotEnv(None, stream=stream, strict=True)
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(DotEnvError):
                    instance.dict()
            self.assertIsNone(instance._dict)
            stream.seek(0)
            stream.truncate()
            stream.write('FIXED=yes')
            stream.seek(0)
            self.assertEqual(instance.dict(), {'FIXED': 'yes'})
            stream.seek(0)
            self.assertIs(instance.dict(), instance.dict())
        stream = io.StringIO('')
        instance = DotEnv(None, stream=stream, strict=True)
        result = instance.dict()
        stream.write('A=new')
        stream.seek(0)
        self.assertIs(instance.dict(), result)
        self.assertEqual(result, {})

    def test_source_encoding_ownership_and_commit_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.env'
            path.write_text('A=caf\u00e9\n', encoding='utf-16')
            supplied = io.StringIO('BAD="unterminated')
            self.assertEqual(dotenv_values(path, supplied, encoding='utf-16', strict=True), {'A': 'caf\u00e9'})
            self.assertEqual(supplied.tell(), 0)
            self.assertFalse(supplied.closed)
            self.assertEqual(dotenv_values(path.with_name('missing'), strict=True), {})
        for override in (False, True):
            env = RecordingEnv({'A': 'old'})
            with patch('dotenv.main.os.environ', env):
                self.assertTrue(load_dotenv(stream=io.StringIO('A=new\nN\nB=\n'), strict=True, override=override))
                self.assertEqual(env, {'A': 'new' if override else 'old', 'B': ''})
                self.assertFalse(load_dotenv(stream=io.StringIO('#empty\n'), strict=True))
                self.assertTrue(load_dotenv(stream=io.StringIO('N'), strict=True))
        env = RecordingEnv({'PYTHON_DOTENV_DISABLED': 'true'})
        stream = io.StringIO('BAD="unterminated')
        with patch('dotenv.main.os.environ', env):
            self.assertFalse(load_dotenv(stream=stream, strict=True))
        self.assertEqual(stream.tell(), 0)
        self.assertEqual(env.writes, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
