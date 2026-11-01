"""Coordinator-only acceptance. Keep outside every participant workspace."""
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


def load_candidate():
    root = Path(os.environ['CROSS_MODULE_WORKSPACE']).resolve()
    package = root / 'dotenv'
    for name in list(sys.modules):
        if name == 'dotenv' or name.startswith('dotenv.'):
            del sys.modules[name]
    spec = importlib.util.spec_from_file_location('dotenv', package / '__init__.py',
        submodule_search_locations=[str(package)])
    module = importlib.util.module_from_spec(spec)
    sys.modules['dotenv'] = module
    spec.loader.exec_module(module)
    from dotenv import main, parser, variables
    for item in (module, main, parser, variables):
        if not Path(item.__file__).resolve().is_relative_to(package):
            raise RuntimeError('candidate import escaped workspace')
    return module, main, parser, variables


class StrictDotenvAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api, cls.main, cls.parser, cls.variables = load_candidate()

    def setUp(self):
        self.environ = patch.dict(os.environ, {}, clear=True)
        self.environ.start()
        self.addCleanup(self.environ.stop)

    def values(self, text, **kwargs):
        return self.api.dotenv_values(stream=io.StringIO(text), strict=True, **kwargs)

    def error(self, function, kind, line, original):
        with self.assertRaises(self.api.DotEnvError) as found:
            function()
        error = found.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual((error.kind, error.line, error.original), (kind, line, original))
        self.assertIn(kind, str(error))
        self.assertIn(str(line), str(error))

    def atomic_error(self, text, kind, line, original, **kwargs):
        os.environ['KEEP'] = 'ambient'
        before = dict(os.environ)
        with patch.object(type(os.environ), '__setitem__', autospec=True) as writes:
            self.error(lambda: self.api.load_dotenv(stream=io.StringIO(text), strict=True,
                **kwargs), kind, line, original)
            writes.assert_not_called()
        self.assertEqual(dict(os.environ), before)

    def test_public_error_export(self):
        self.assertIs(self.api.DotEnvError, self.parser.DotEnvError)
        self.assertIn('DotEnvError', self.api.__all__)
        self.assertTrue(issubclass(self.api.DotEnvError, ValueError))

    def test_parser_strict_success_preserves_bindings(self):
        text = '\ufeff# heading\r\n\r\nexport A="one\ntwo"\r\nBARE\r\n'
        ordinary = list(self.parser.parse_stream(io.StringIO(text)))
        strict = list(self.parser.parse_stream(io.StringIO(text), strict=True))
        self.assertEqual(strict, ordinary)
        self.assertEqual([(b.key, b.value) for b in strict],
            [(None, None), ('A', 'one\ntwo'), ('BARE', None)])

    def test_parser_error_context_with_leading_blank(self):
        text = 'A=ok\r\n\r\nBROKEN="x" junk\r\nTAIL=ok\r\n'
        self.error(lambda: list(self.parser.parse_stream(io.StringIO(text), strict=True)),
            'parse', 2, '\r\nBROKEN="x" junk\r\n')

    def test_parser_does_not_reject_duplicates(self):
        bindings = list(self.parser.parse_stream(io.StringIO('A=1\nA=2\n'), strict=True))
        self.assertEqual([b.value for b in bindings], ['1', '2'])

    def test_parser_permissive_recovery(self):
        bindings = list(self.parser.parse_stream(io.StringIO('A=1\nBAD="x" junk\nC=3\n')))
        self.assertEqual([b.error for b in bindings], [False, True, False])
        self.assertEqual(bindings[-1].key, 'C')

    def test_variables_missing_is_typed(self):
        atoms = list(self.variables.parse_variables('pre${ABSENT}post', strict=True))
        with self.assertRaises(self.variables.UndefinedVariableError) as found:
            ''.join(atom.resolve({}) for atom in atoms)
        self.assertEqual(found.exception.name, 'ABSENT')
        self.assertIsInstance(found.exception, ValueError)

    def test_variables_defaults_none_empty_and_literals(self):
        text = '${N:-fallback}/${E:-fallback}/${M:-fallback}/$M'
        atoms = self.variables.parse_variables(text, strict=True)
        self.assertEqual(''.join(atom.resolve({'N': None, 'E': ''}) for atom in atoms),
            '//fallback/$M')

    def test_variables_atoms_can_be_reused(self):
        atoms = list(self.variables.parse_variables('${X}', strict=True))
        self.assertEqual(''.join(a.resolve({'X': 'first'}) for a in atoms), 'first')
        self.assertEqual(''.join(a.resolve({'X': 'second'}) for a in atoms), 'second')
        with self.assertRaises(self.variables.UndefinedVariableError):
            ''.join(a.resolve({}) for a in atoms)

    def test_variables_permissive_unchanged(self):
        atoms = self.variables.parse_variables('x${MISSING}y${MISSING:-d}')
        self.assertEqual(''.join(a.resolve({}) for a in atoms), 'xyd')

    def test_values_ordered_resolution_and_valueless(self):
        os.environ.update({'A': 'ambient', 'B': 'ambient-b'})
        result = self.values('A=file\nB=${A}\nNONE\nEMPTY=\nC=${NONE:-n}/${EMPTY:-e}/${Z:-z}\n')
        self.assertEqual(list(result.items()), [('A', 'file'), ('B', 'file'),
            ('NONE', None), ('EMPTY', ''), ('C', '//z')])
        self.assertEqual(dict(os.environ), {'A': 'ambient', 'B': 'ambient-b'})

    def test_first_duplicate_context(self):
        self.error(lambda: self.values('A=one\nA=two\nBAD="x" junk\n'),
            'duplicate', 2, 'A=two\n')
        self.error(lambda: self.values('A=one\nA=${MISSING}\n'),
            'duplicate', 2, 'A=${MISSING}\n')
        self.error(lambda: self.values('A=one\nA="${MISSING}" junk\n'),
            'parse', 2, 'A="${MISSING}" junk\n')

    def test_valueless_duplicate_is_duplicate(self):
        self.error(lambda: self.values('NONE\nNONE=now\n'), 'duplicate', 2, 'NONE=now\n')

    def test_earliest_undefined_wins_later_parse(self):
        self.error(lambda: self.values('A=${NOPE}\nBAD="x" junk\n'),
            'undefined', 1, 'A=${NOPE}\n')

    def test_multiline_undefined_context(self):
        self.error(lambda: self.values('A=ok\nB="top\n${NOPE}"\n'),
            'undefined', 2, 'B="top\n${NOPE}"\n')

    def test_forward_reference_and_self_reference(self):
        self.error(lambda: self.values('A=${B}\nB=after\n'), 'undefined', 1, 'A=${B}\n')
        os.environ['A'] = 'old'
        self.assertEqual(self.values('A=${A}/new\n'), {'A': 'old/new'})

    def test_os_snapshot_precedes_source_read(self):
        os.environ['EXTERNAL'] = 'before'
        class MutatingStream(io.StringIO):
            def read(inner, *args, **kwargs):
                os.environ['EXTERNAL'] = 'during-read'
                return super().read(*args, **kwargs)
        result = self.api.dotenv_values(stream=MutatingStream('A=${EXTERNAL}\nB=${EXTERNAL}\n'), strict=True)
        self.assertEqual(result, {'A': 'before', 'B': 'before'})

    def test_override_false_resolution_and_successful_commit(self):
        os.environ['A'] = 'ambient'
        result = self.api.load_dotenv(stream=io.StringIO('A=file\nB=${A}\nNONE\nEMPTY=\n'), strict=True)
        self.assertTrue(result)
        self.assertEqual(dict(os.environ), {'A': 'ambient', 'B': 'ambient', 'EMPTY': ''})

    def test_override_true_resolution_and_successful_commit(self):
        os.environ['A'] = 'ambient'
        self.assertTrue(self.api.load_dotenv(stream=io.StringIO('A=file\nB=${A}\n'),
            strict=True, override=True))
        self.assertEqual(dict(os.environ), {'A': 'file', 'B': 'file'})

    def test_late_parse_error_has_zero_writes(self):
        self.atomic_error('A=good\nBAD="x" junk\n', 'parse', 2, 'BAD="x" junk\n')

    def test_late_duplicate_error_has_zero_writes(self):
        self.atomic_error('A=good\nA=again\n', 'duplicate', 2, 'A=again\n')

    def test_late_undefined_error_has_zero_writes(self):
        self.atomic_error('A=good\nB=${UNSET}\n', 'undefined', 2, 'B=${UNSET}\n')

    def test_skipped_override_key_still_validates(self):
        self.atomic_error('A=good\nKEEP=${UNSET}\n', 'undefined', 2,
            'KEEP=${UNSET}\n', override=False)

    def test_no_interpolation_keeps_literals_checks_duplicates(self):
        self.assertEqual(self.values('A=${UNSET}\n', interpolate=False), {'A': '${UNSET}'})
        self.error(lambda: self.values('A=${UNSET}\nA=again\n', interpolate=False),
            'duplicate', 2, 'A=again\n')

    def test_no_interpolation_still_checks_syntax(self):
        self.error(lambda: self.values('A=${UNSET}\nBAD="x" junk\n', interpolate=False),
            'parse', 2, 'BAD="x" junk\n')

    def test_dotenv_direct_atomic_and_failure_not_cached(self):
        stream = io.StringIO('A=good\nB=${NOPE}\n')
        dotenv = self.main.DotEnv(None, stream=stream, strict=True)
        with patch.object(type(os.environ), '__setitem__', autospec=True) as writes:
            self.error(dotenv.set_as_environment_variables, 'undefined', 2, 'B=${NOPE}\n')
            writes.assert_not_called()
        stream.seek(0)
        stream.truncate(0)
        stream.write('A=repaired\n')
        stream.seek(0)
        self.assertEqual(dotenv.dict(), {'A': 'repaired'})
        stream.close()
        self.assertEqual(dotenv.dict(), {'A': 'repaired'})

    def test_path_encoding_precedence_and_stream_ownership(self):
        stream = io.StringIO('IGNORED=${MISSING}\n')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_bytes('A=caf\xe9\n'.encode('latin-1'))
            self.assertEqual(self.api.dotenv_values(path, stream=stream, encoding='latin-1',
                strict=True), {'A': 'caf\xe9'})
            self.assertEqual(stream.tell(), 0)
            missing = Path(folder) / 'absent'
            self.assertEqual(self.api.dotenv_values(missing, stream=io.StringIO('A=fallback\n'),
                strict=True), {'A': 'fallback'})
        self.assertFalse(stream.closed)

    def test_empty_valueless_and_disabled_return_behavior(self):
        self.assertFalse(self.api.load_dotenv(stream=io.StringIO('# empty\n'), strict=True))
        self.assertTrue(self.api.load_dotenv(stream=io.StringIO('BARE\n'), strict=True))
        self.assertNotIn('BARE', os.environ)
        stream = io.StringIO('A=${MISSING}\n')
        os.environ['PYTHON_DOTENV_DISABLED'] = 'yes'
        self.assertFalse(self.api.load_dotenv(stream=stream, strict=True))
        self.assertEqual(stream.tell(), 0)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.api.dotenv_values(Path(folder) / 'missing', strict=True), {})

    def test_permissive_public_warning_duplicates_and_undefined(self):
        with self.assertLogs('dotenv.main', level='WARNING') as logs:
            result = self.api.dotenv_values(stream=io.StringIO(
                'A=first\nB=${A}\nA=last\nBAD="x" junk\nC=${MISSING}\n'))
        self.assertEqual(result, {'A': 'last', 'B': 'first', 'C': ''})
        self.assertIn('line 4', '\n'.join(logs.output))
        self.assertEqual(self.api.dotenv_values(stream=io.StringIO('X=${MISSING}\n'),
            strict=False), {'X': ''})
