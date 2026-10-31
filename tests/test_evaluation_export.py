import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/export_evaluation_inputs.py'
SPEC = importlib.util.spec_from_file_location('export_evaluation', SCRIPT)
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        (self.root / 'SKILL.md').write_text('entry')
        for folder in ('references', 'scripts', 'agents', 'tests', 'evaluations'):
            (self.root / folder).mkdir()
            (self.root / folder / 'example.txt').write_text(folder)
        self.fixture = self.root / 'tests/cases.json'
        self.fixture.write_text(json.dumps({'instructions': 'decide', 'cases': [
            {'id': 'a', 'input': 'request', 'checks': {'SECRET_ORACLE': True}}]}))
        self.output = self.root.parent / 'export'

    def test_omits_oracles_and_results_but_preserves_required_resources(self):
        out = exporter.export_inputs(self.root, self.fixture, self.output)
        payload = json.loads((out / 'inputs/01.json').read_text())
        self.assertEqual(payload, {'instructions': 'decide', 'case': {'id': 'a', 'input': 'request'}})
        self.assertFalse((out / 'skill/tests').exists())
        self.assertFalse((out / 'skill/evaluations').exists())
        self.assertTrue((out / 'skill/references/example.txt').exists())

    def test_refuses_overwrite_and_in_tree_destination(self):
        self.output.mkdir()
        marker = self.output / 'keep'
        marker.write_text('preserve')
        with self.assertRaises(FileExistsError):
            exporter.export_inputs(self.root, self.fixture, self.output)
        self.assertEqual(marker.read_text(), 'preserve')
        with self.assertRaises(ValueError):
            exporter.export_inputs(self.root, self.fixture, self.root / 'recursive')

    def test_invalid_cases_are_rejected_before_output_creation(self):
        self.fixture.write_text(json.dumps({'instructions': 'decide', 'cases': [
            {'id': 'a', 'input': 'one'}, {'id': 'a', 'input': 'two'}]}))
        with self.assertRaises(ValueError):
            exporter.export_inputs(self.root, self.fixture, self.output)
        self.assertFalse(self.output.exists())

    def test_link_preflight_precedes_explicit_and_temporary_destinations(self):
        original = Path.is_symlink
        # Match the canonical path used by export_inputs (Windows may expand 8.3 temp paths).
        linked = (self.root / 'scripts' / 'example.txt').resolve()
        with mock.patch.object(Path, 'is_symlink', lambda p: p == linked or original(p)), \
                mock.patch.object(exporter.tempfile, 'mkdtemp') as create_temp:
            for output in (self.output, None):
                with self.assertRaises(ValueError):
                    exporter.export_inputs(self.root, self.fixture, output)
            create_temp.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_real_links_are_rejected_without_copy_or_output(self):
        external = self.root.parent / 'private.txt'
        external.write_text('private')
        link = self.root / 'scripts' / 'linked'
        try:
            link.symlink_to(external)
        except OSError as error:
            self.skipTest('Host cannot create symbolic links: ' + str(error))
        with self.assertRaises(ValueError):
            exporter.export_inputs(self.root, self.fixture, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(external.read_text(), 'private')
        link.unlink()
        link.symlink_to(self.root / 'absent')
        with self.assertRaises(ValueError):
            exporter.export_inputs(self.root, self.fixture, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
