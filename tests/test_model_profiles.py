"""Reject unusable profile declarations before a model-selection decision."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_model_profiles.py'
SPEC = importlib.util.spec_from_file_location('model_profile_check', SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class ModelProfileTests(unittest.TestCase):
    def setUp(self):
        self.config = checker.read_profiles(checker.DEFAULT_INPUT)

    def test_shipped_profiles_validate_without_claiming_availability(self):
        result = checker.validate_profiles(self.config)
        self.assertTrue(result['valid'])
        self.assertEqual(result['active_profile'], 'runtime')
        self.assertFalse(result['availability_verified'])

    def test_custom_model_names_and_null_inheritance_are_valid_structure(self):
        custom = copy.deepcopy(self.config['profiles']['runtime'])
        custom['Developer'] = {'model': 'organization-private-model', 'effort': 'high'}
        self.config['profiles']['custom'] = custom
        self.config['active_profile'] = 'custom'
        self.assertEqual(checker.validate_profiles(self.config)['active_profile'], 'custom')

    def test_top_level_shape_schema_and_profile_selection_are_checked(self):
        invalid = [None, [], {}, {**self.config, 'schema_version': True},
                   {**self.config, 'schema_version': 2}, {**self.config, 'unknown': 1},
                   {**self.config, 'profiles': {}}, {**self.config, 'profiles': []},
                   {**self.config, 'active_profile': 'absent'},
                   {**self.config, 'active_profile': False},
                   {**self.config, 'profiles': {' ': self.config['profiles']['runtime']}}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                checker.validate_profiles(value)

    def test_missing_unknown_roles_and_selection_fields_are_rejected(self):
        for change in ('missing_role', 'unknown_role', 'missing_field', 'unknown_field', 'not_object'):
            config = copy.deepcopy(self.config)
            roles = config['profiles']['runtime']
            if change == 'missing_role':
                del roles['QA / Reviewer']
            elif change == 'unknown_role':
                roles['Reviewer'] = {'model': None, 'effort': None}
            elif change == 'missing_field':
                del roles['Developer']['effort']
            elif change == 'unknown_field':
                roles['Developer']['temperature'] = 0.5
            else:
                roles['Developer'] = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                checker.validate_profiles(config)

    def test_model_and_effort_values_are_not_silently_inherited(self):
        for field, value in [('model', ''), ('model', '  '), ('model', True), ('model', 12),
                             ('effort', ''), ('effort', True), ('effort', []),
                             ('effort', 'maximum'), ('effort', 'HIGH')]:
            config = copy.deepcopy(self.config)
            config['profiles']['runtime']['Developer'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                checker.validate_profiles(config)

    def test_duplicate_json_keys_are_rejected_at_every_object_depth(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'profiles.json'
            for text in ('{"profiles": {}, "profiles": {}}',
                         '{"profiles": {"runtime": {"Developer": {"model": null, "model": "other"}}}}'):
                source.write_text(text, encoding='utf-8')
                with self.subTest(text=text), self.assertRaises(ValueError):
                    checker.read_profiles(source)

    def test_cli_reports_valid_invalid_and_missing_inputs_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'profiles.json'
            for config, expected in ((self.config, 0), ({**self.config, 'active_profile': 'missing'}, 2)):
                source.write_text(json.dumps(config), encoding='utf-8')
                before = source.read_bytes()
                run = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source)],
                                     capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
                self.assertEqual(json.loads(run.stdout)['valid'], expected == 0)
                self.assertEqual(source.read_bytes(), before)
            missing = Path(directory) / 'absent.json'
            run = subprocess.run([sys.executable, str(SCRIPT), '--input', str(missing)],
                                 capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(json.loads(run.stdout)['valid'])
            self.assertFalse(missing.exists())


if __name__ == '__main__':
    unittest.main()
