"""Build a runtime-only skill ZIP without installing or changing configuration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEXT = {'.py', '.md', '.json', '.yaml', '.yml', '.txt'}
EXCLUDED = {'__pycache__', '.git', 'backups', 'tests', 'benchmarks', 'evaluations', 'graphify-out', 'vendor'}


def reject_link(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    reparse = getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)
    if path.is_symlink() or reparse or (hasattr(path, 'is_junction') and path.is_junction()):
        raise ValueError('linked resource rejected: ' + path.name)


def resources(source_root):
    root = Path(source_root).absolute()
    reject_link(root)
    root = root.resolve()
    selected = []
    for name in ('LICENSE', 'SKILL.md', 'agents', 'references', 'scripts'):
        path = root / name
        reject_link(path)
        if not path.exists():
            raise ValueError('missing runtime resource: ' + name)
        if (name in ('LICENSE', 'SKILL.md') and not path.is_file()) or (name not in ('LICENSE', 'SKILL.md') and not path.is_dir()):
            raise ValueError('incorrect runtime resource type: ' + name)
        pending = [path]
        while pending:
            entry = pending.pop()
            reject_link(entry)
            if entry.is_dir():
                pending.extend(entry.iterdir())
            elif entry.is_file():
                rel = entry.relative_to(root)
                if not EXCLUDED.intersection(rel.parts) and entry.suffix not in ('.pyc', '.pyo'):
                    selected.append(entry)
            else:
                raise ValueError('unsupported runtime resource: ' + entry.name)
    return root, sorted(selected)


def source_revision(root):
    try:
        top = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True, timeout=5)
        if top.returncode or Path(top.stdout.strip()).resolve() != root:
            return None
        run = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                             capture_output=True, text=True, timeout=5)
        return run.stdout.strip() if run.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def build_package(source_root=ROOT, output=None):
    root, files = resources(source_root)  # Complete preflight before allocating output.
    payloads = {}
    for path in files:
        data = path.read_bytes()
        if path.name == 'LICENSE' or path.suffix in TEXT:
            data = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
        payloads[path.relative_to(root).as_posix()] = data
    manifest = {'schema_version': 1, 'source_git_head': source_revision(root),
                'source_kind': 'working_tree', 'text_encoding': 'UTF-8/LF',
                'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                          for name, data in payloads.items()}}
    default_dir = None
    if output is None:
        if Path(tempfile.gettempdir()).resolve().is_relative_to(root):
            raise ValueError('temporary directory is inside the source project; specify an external output')
        default_dir = Path(tempfile.mkdtemp(prefix='coding-team-runtime-'))
        destination = default_dir / 'coding-team-runtime.zip'
    else:
        destination = Path(output).absolute()
        if destination.resolve().is_relative_to(root):
            raise ValueError('output must be outside the source project')
    temporary = None
    try:
        if destination.exists() or destination.is_symlink():
            raise FileExistsError('output already exists')
        fd, name = tempfile.mkstemp(prefix='.runtime-', suffix='.zip', dir=destination.parent)
        temporary = Path(name)
        with os.fdopen(fd, 'w+b') as stream:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, data in payloads.items():
                    archive.writestr('coding-team/' + name, data)
                archive.writestr('coding-team/runtime-package.json',
                                 json.dumps(manifest, indent=2).encode('utf-8') + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        # Same-directory hard-link publication is atomic and refuses an existing name.
        os.link(temporary, destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if default_dir is not None and not destination.exists():
            default_dir.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        print(build_package(output=args.output))
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
