"""Validate model-profile structure; this does not resolve runtime capabilities."""
import argparse
import json
from pathlib import Path

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / 'references/model-profiles.json'
ROLES = frozenset(('Architect', 'Investigator', 'Developer', 'Test Engineer', 'QA / Reviewer', 'Specialist'))
# Schema v1 vocabulary, not a guarantee that a model or host supports each value.
EFFORTS = frozenset(('low', 'medium', 'high', 'xhigh', 'max', 'ultra'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def read_profiles(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique)


def validate_profiles(data):
    require(isinstance(data, dict), 'configuration must be an object')
    require(set(data) == {'schema_version', 'active_profile', 'profiles'}, 'invalid configuration fields')
    require(type(data['schema_version']) is int and data['schema_version'] == 1,
            'schema_version must be integer 1')
    profiles = data['profiles']
    require(isinstance(profiles, dict) and bool(profiles), 'profiles must be a nonempty object')
    require(all(nonempty(name) for name in profiles), 'profile names must be nonempty strings')
    active = data['active_profile']
    require(nonempty(active) and active in profiles, 'active_profile must name an existing profile')
    for name, profile in profiles.items():
        require(isinstance(profile, dict) and set(profile) == ROLES,
                'profile ' + name + ' must define exactly the six supported roles')
        for role, selection in profile.items():
            label = name + '/' + role
            require(isinstance(selection, dict) and set(selection) == {'model', 'effort'},
                    label + ' must contain only model and effort')
            model, effort = selection['model'], selection['effort']
            require(model is None or nonempty(model), label + ' model must be null or a nonempty string')
            require(effort is None or (isinstance(effort, str) and effort in EFFORTS),
                    label + ' effort must be null or one of ' + ', '.join(sorted(EFFORTS)))
    return {'valid': True, 'schema_version': 1, 'active_profile': active,
            'profile_count': len(profiles), 'roles_per_profile': len(ROLES),
            'availability_verified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args(argv)
    try:
        result = validate_profiles(read_profiles(args.input))
        print(json.dumps(result))
        return 0
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        print(json.dumps({'valid': False, 'error': str(error), 'availability_verified': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
