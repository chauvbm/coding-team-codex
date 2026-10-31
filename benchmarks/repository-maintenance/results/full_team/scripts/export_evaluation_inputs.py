"""Export a skill snapshot and case inputs without expected checks for a coordinator."""
import argparse
import json
from pathlib import Path
import shutil
import stat
import tempfile


def _check_resource_links(path):
    """Inspect resource entries without following symbolic links or junctions."""
    info = path.lstat()
    linked = stat.S_ISLNK(info.st_mode) or getattr(info, 'st_reparse_tag', None) in (
        getattr(stat, 'IO_REPARSE_TAG_SYMLINK', -1),
        getattr(stat, 'IO_REPARSE_TAG_MOUNT_POINT', -1),
    )
    if linked:
        raise ValueError(f'symbolic links are not allowed in exported resources: {path}')
    if stat.S_ISDIR(info.st_mode):
        for child in path.iterdir():
            _check_resource_links(child)


def export_inputs(skill_root, cases_path, output=None):
    root = Path(skill_root).resolve()
    data = json.loads(Path(cases_path).read_text(encoding='utf-8-sig'))
    if not isinstance(data.get('instructions'), str) or not isinstance(data.get('cases'), list):
        raise ValueError('fixture requires instructions and cases')
    cases = data['cases']
    ids = [c.get('id') for c in cases if isinstance(c, dict)]
    if (len(ids) != len(cases) or not all(isinstance(i, str) and i for i in ids)
            or len(ids) != len(set(ids)) or not all(isinstance(c.get('input'), str) for c in cases)):
        raise ValueError('cases require unique string IDs and string inputs')
    # Check the complete operational snapshot before allocating either an explicit
    # destination or a temporary one. lstat also sees dangling resource links.
    _check_resource_links(root / 'SKILL.md')
    for folder in ('references', 'scripts', 'agents'):
        resource = root / folder
        try:
            resource.lstat()
        except FileNotFoundError:
            continue
        _check_resource_links(resource)
    if output is None:
        out = Path(tempfile.mkdtemp(prefix='coding-team-eval-'))
    else:
        out = Path(output).resolve()
        if out.is_relative_to(root):
            raise ValueError('export outside the skill to avoid recursive copies or accidental commits')
        out.mkdir(parents=True, exist_ok=False)
    skill = out / 'skill'
    skill.mkdir()
    shutil.copy2(root / 'SKILL.md', skill / 'SKILL.md')
    for folder in ('references', 'scripts', 'agents'):
        if (root / folder).exists():
            shutil.copytree(root / folder, skill / folder,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    inputs = out / 'inputs'
    inputs.mkdir()
    for number, case in enumerate(cases, 1):
        payload = {'instructions': data['instructions'],
                   'case': {'id': case['id'], 'input': case['input']}}
        (inputs / f'{number:02d}.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return out


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=root / 'tests/behavioral_cases.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        print(export_inputs(root, args.cases, args.output))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
