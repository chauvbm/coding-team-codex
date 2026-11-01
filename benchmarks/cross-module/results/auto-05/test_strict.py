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


class RecordingEnvironment(dict):
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

    def test_parser_preserves_context_and_yields_before_failure(self):
        source = 'A=1\n\n\nBAD="unterminated\nC=3\n'
        permissive = list(parse_stream(io.StringIO(source)))
        strict = parse_stream(io.StringIO(source), True)
        self.assertEqual(next(strict), permissive[0])
        with self.assertRaises(DotEnvError) as caught:
            next(strict)
        self.assertEqual(caught.exception.line, permissive[1].original.line)
        self.assertEqual(caught.exception.original, permissive[1].original.string)

    def test_duplicate_valueless_export_and_multiline_context(self):
        self.assert_error('A\n\nexport A="line\nline"\n', 'duplicate', 1)

    def test_undefined_context(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('A=1\n\n B="line\n${MISSING}"\n', 'undefined', 1)

    def test_source_order_and_duplicate_before_undefined(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('A=${MISSING}\nBAD="\n', 'undefined', 0)
            self.assert_error('A=1\nA=${MISSING}\nBAD="\n', 'duplicate', 1)
            self.assert_error('A=1\nA="bad\n', 'parse', 1)
            self.assert_error('A=1\nA=2\nBAD="\n', 'duplicate', 1)

    def test_defaults_presence_and_reusable_atoms(self):
        atom = next(parse_variables('${X}', strict=True))
        with self.assertRaises(UndefinedVariableError) as caught:
            atom.resolve({})
        self.assertEqual(caught.exception.name, 'X')
        for value, expected in [(None, ''), ('', ''), ('yes', 'yes')]:
            self.assertEqual(atom.resolve({'X': value}), expected)
        default = next(parse_variables('${X:-literal}', True))
        self.assertEqual(default.resolve({}), 'literal')
        self.assertEqual(default.resolve({'X': None}), '')
        self.assertEqual(default.resolve({'X': ''}), '')
        self.assertEqual(next(parse_variables('${X}')).resolve({}), '')

    def test_no_new_grammar_or_recursive_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.values('A=$X\nB=${X:bad}\nC=${X:-$Y}\n'),
                             {'A': '$X', 'B': '${X:bad}', 'C': '$Y'})

    def test_override_order_and_own_definition(self):
        source = 'A=file\nB=${A}\nN\nC=${N:-default}\nD=${D}\n'
        with patch.dict(os.environ, {'A': 'os', 'D': 'self'}, clear=True):
            for override, expected in [(True, 'file'), (False, 'os')]:
                result = DotEnv(None, io.StringIO(source), override=override, strict=True).dict()
                self.assertEqual(result['B'], expected)
                self.assertIsNone(result['N'])
                self.assertEqual(result['C'], '')
                self.assertEqual(result['D'], 'self')
                self.assertEqual(list(result), ['A', 'B', 'N', 'C', 'D'])

    def test_forward_reference_and_missing_self(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assert_error('A=${B}\nB=later\n', 'undefined', 0)
            self.assert_error('A=${A}\n', 'undefined', 0)

    def test_snapshot_before_read(self):
        class MutatingStream(io.StringIO):
            def read(self, *args):
                os.environ['X'] = 'after'
                os.environ['NEW'] = 'after'
                return super().read(*args)
        with patch.dict(os.environ, {'X': 'before'}, clear=True):
            stream = MutatingStream('A=${X}\nB=${NEW:-missing}\n')
            self.assertEqual(dotenv_values(stream=stream, strict=True),
                             {'A': 'before', 'B': 'missing'})
            self.assertFalse(stream.closed)

    def test_no_interpolation_still_validates(self):
        self.assertEqual(self.values('A=${MISSING}\n', interpolate=False), {'A': '${MISSING}'})
        self.assert_error('A\nA\n', 'duplicate', 1, interpolate=False)
        self.assert_error('BAD="\n', 'parse', 0, interpolate=False)

    def test_zero_writes_on_all_error_types_even_skipped_definition(self):
        for source in ['GOOD=yes\nBAD="\n', 'GOOD=yes\nGOOD=again\n',
                       'GOOD=yes\nEXISTS=${MISSING}\n']:
            env = RecordingEnvironment({'EXISTS': 'os'})
            with patch.object(os, 'environ', env):
                with self.assertRaises(DotEnvError):
                    load_dotenv(stream=io.StringIO(source), strict=True)
            self.assertEqual(env.writes, [])
            self.assertEqual(env, {'EXISTS': 'os'})

    def test_success_commit_and_returns(self):
        env = RecordingEnvironment({'A': 'os'})
        with patch.object(os, 'environ', env):
            self.assertTrue(load_dotenv(stream=io.StringIO('A=file\nB=${A}\nN\n'), strict=True))
            self.assertEqual(env.writes, [('B', 'os')])
            self.assertTrue(load_dotenv(stream=io.StringIO('N\n'), strict=True))
            self.assertFalse(load_dotenv(stream=io.StringIO('# comment\n'), strict=True))
            self.assertTrue(load_dotenv(stream=io.StringIO('A=file\n'), override=True, strict=True))
            self.assertEqual(env['A'], 'file')

    def test_failed_computation_is_retryable_success_is_cached(self):
        with patch.dict(os.environ, {}, clear=True):
            stream = io.StringIO('A=${X}\n')
            dotenv = DotEnv(None, stream, strict=True)
            with self.assertRaises(DotEnvError):
                dotenv.dict()
            self.assertIsNone(dotenv._dict)
            stream.seek(0)
            os.environ['X'] = 'first'
            result = dotenv.dict()
            os.environ['X'] = 'second'
            self.assertIs(dotenv.dict(), result)
            self.assertEqual(result['A'], 'first')

    def test_permissive_recovery_and_duplicates_remain(self):
        source = 'A=1\nBAD="\nA=${MISSING}\nN\n'
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(dotenv_values(stream=io.StringIO(source)), {'A': '', 'N': None})
            self.assertTrue(any(binding.error for binding in parse_stream(io.StringIO(source))))

    def test_path_precedence_encoding_missing_file_and_disabled(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            path = Path(directory) / 'env'
            path.write_text('A=café\n', encoding='utf-16')
            stream = io.StringIO('A=stream\n')
            self.assertEqual(dotenv_values(path, stream, encoding='utf-16', strict=True), {'A': 'café'})
            self.assertEqual(stream.tell(), 0)
            self.assertEqual(dotenv_values(path.parent / 'missing', strict=True), {})
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': 'yes'}, clear=True):
            self.assertFalse(load_dotenv(stream=io.StringIO('BAD="\n'), strict=True))


if __name__ == '__main__':
    unittest.main()
