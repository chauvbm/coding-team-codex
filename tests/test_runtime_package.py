import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/build_runtime_package.py'
SPEC = importlib.util.spec_from_file_location('runtime_builder', SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class RuntimePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        for name in ('LICENSE', 'SKILL.md'):
            (self.root / name).write_bytes(b'example\r\n')
        for name in ('scripts', 'references', 'agents', 'tests', 'benchmarks', 'evaluations', 'graphify-out', '.git'):
            (self.root / name).mkdir()
            (self.root / name / 'marker.txt').write_text(name)
        cache = self.root / 'scripts/__pycache__'
        cache.mkdir()
        (cache / 'ignore.pyc').write_bytes(b'cache')
        backups = self.root / 'scripts/backups'
        backups.mkdir()
        (backups / 'private.txt').write_text('do not distribute')
        self.out = self.root.parent / 'runtime.zip'

    def test_only_operational_resources_and_matching_manifest(self):
        builder.build_package(self.root, self.out)
        with zipfile.ZipFile(self.out) as archive:
            names = set(archive.namelist())
            self.assertEqual(names, {'coding-team/' + n for n in ('LICENSE', 'SKILL.md',
                'scripts/marker.txt', 'references/marker.txt', 'agents/marker.txt', 'runtime-package.json')})
            manifest = json.loads(archive.read('coding-team/runtime-package.json'))
            self.assertIsNone(manifest['source_git_head'])
            self.assertEqual(archive.read('coding-team/SKILL.md'), b'example\n')
            for name, metadata in manifest['files'].items():
                data = archive.read('coding-team/' + name)
                self.assertEqual(metadata, {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})

    def test_existing_output_and_in_tree_output_are_preserved(self):
        self.out.write_bytes(b'keep')
        with self.assertRaises(FileExistsError): builder.build_package(self.root, self.out)
        self.assertEqual(self.out.read_bytes(), b'keep')
        with self.assertRaises(ValueError): builder.build_package(self.root, self.root / 'recursive.zip')

    def test_link_preflight_happens_before_output_allocation(self):
        target = (self.root / 'scripts/marker.txt').resolve()
        original = Path.is_symlink
        with mock.patch.object(Path, 'is_symlink', lambda p: p == target or original(p)), \
                mock.patch.object(builder.tempfile, 'mkdtemp') as allocate:
            with self.assertRaises(ValueError): builder.build_package(self.root)
            allocate.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_publication_failure_leaves_no_partial_file(self):
        with mock.patch.object(builder.os, 'link', side_effect=OSError('no hard links')):
            with self.assertRaises(OSError): builder.build_package(self.root, self.out)
        self.assertFalse(self.out.exists())
        self.assertEqual(list(self.out.parent.glob('.runtime-*.zip')), [])

    def test_real_broken_link_is_rejected_before_output(self):
        link = self.root / 'scripts/linked'
        try: link.symlink_to(self.root / 'absent')
        except OSError as error: self.skipTest(str(error))
        with self.assertRaises(ValueError): builder.build_package(self.root, self.out)
        self.assertFalse(self.out.exists())


if __name__ == '__main__': unittest.main()
