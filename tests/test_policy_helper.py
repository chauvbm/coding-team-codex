"""Policy storage and controls regression tests; all writes use temporary fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


HELPER = Path(__file__).resolve().parents[1] / 'scripts' / 'coding_team_policy.py'
SPEC = importlib.util.spec_from_file_location('coding_team_policy', HELPER)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.root = Path(self.fixture.name)
        self.state = self.root / 'custom state' / 'policy.json'

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(HELPER), *args, '--state', str(self.state)],
            capture_output=True, text=True, timeout=15,
        )

    def initialize(self):
        return policy.initialize(self.state)

    def test_initialize_defaults_and_preserves_existing_bytes(self):
        state = self.initialize()
        self.assertEqual(state['global_policy'], 'ON')
        self.assertEqual(state['chat_policies'], {})
        policy.apply_command(self.state, '/coding team off', 'first')
        before = self.state.read_bytes()
        self.assertEqual(policy.initialize(self.state)['chat_policies'], {'first': 'OFF'})
        self.assertEqual(self.state.read_bytes(), before)

    def test_all_aliases_and_normalization(self):
        expected = {'on': ('chat', 'ON'), 'off': ('chat', 'OFF'),
                    'on all': ('global', 'ON'), 'off all': ('global', 'OFF'),
                    'status': ('status', None), 'inherit': ('chat', 'INHERIT')}
        for prefix in ('/coding team', '/coding-team'):
            for suffix, result in expected.items():
                with self.subTest(prefix=prefix, suffix=suffix):
                    self.assertEqual(policy.parse_command(' \t' + prefix.upper() + '  ' + suffix.upper() + '\n'), result)

    def test_only_complete_unquoted_commands_are_accepted(self):
        for text in ('"/coding-team on"', "'/coding team off'", '`/coding-team status`',
                     'please /coding-team on', '/coding team on please', '/coding-team',
                     '/coding-team on all now', '/coding team on\n/coding team off',
                     '/coding-teams on', '/coding-team-on', '/coding-team on; echo yes'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                policy.parse_command(text)

    def test_chat_precedence_global_preservation_and_inherit(self):
        self.initialize()
        policy.apply_command(self.state, '/coding-team off', 'one')
        policy.apply_command(self.state, '/coding team on', 'two')
        for value in ('off', 'on'):
            policy.apply_command(self.state, '/coding-team ' + value + ' all', None)
            self.assertEqual(policy.load(self.state)['chat_policies'], {'one': 'OFF', 'two': 'ON'})
            self.assertEqual(policy.status(self.state, 'one')['effective_policy'], 'OFF')
            self.assertEqual(policy.status(self.state, 'two')['effective_policy'], 'ON')
            self.assertEqual(policy.status(self.state, 'three')['effective_policy'], value.upper())
        policy.apply_command(self.state, '/coding-team inherit', 'one')
        self.assertEqual(policy.load(self.state)['chat_policies'], {'two': 'ON'})
        self.assertEqual(policy.status(self.state, 'one')['chat_policy'], 'INHERIT')

    def test_status_unknown_identity_and_noop_do_not_write(self):
        self.initialize()
        before = self.state.read_bytes()
        result = policy.apply_command(self.state, '/coding-team status', None)
        self.assertEqual(result['chat_policy'], 'UNKNOWN')
        self.assertIsNone(result['effective_policy'])
        for identity in (None, '', ' bad '):
            with self.assertRaises(ValueError):
                policy.apply_command(self.state, '/coding-team off', identity)
        policy.apply_command(self.state, '/coding-team on all', None)
        policy.apply_command(self.state, '/coding-team inherit', 'absent')
        self.assertEqual(self.state.read_bytes(), before)

    def test_missing_and_corrupt_state_fail_closed_without_overwrite(self):
        for payload in (None, b'{broken', b'{}', b'[]',
                        b'{"schema_version":true,"global_policy":"ON","chat_policies":{}}',
                        b'{"schema_version":1,"global_policy":"OFF","chat_policies":{"x":"BAD"}}'):
            with self.subTest(payload=payload):
                self.state.parent.mkdir(parents=True, exist_ok=True)
                if payload is None:
                    self.state.unlink(missing_ok=True)
                else:
                    self.state.write_bytes(payload)
                for args in (('status',), ('command', '/coding-team off all')):
                    result = self.cli(*args)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertFalse(json.loads(result.stdout)['automatic_use_allowed'])
                    self.assertEqual(self.state.read_bytes() if self.state.exists() else None, payload)
                if payload is not None:
                    result = self.cli('init')
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(self.state.read_bytes(), payload)

    def test_cli_chat_identity_and_alias(self):
        self.initialize()
        result = self.cli('command', '/coding-team off', '--chat-id', 'fixture-chat')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['effective_policy'], 'OFF')

    def test_bootstrap_idempotent_preserves_unrelated_bytes_and_custom_paths(self):
        agents = self.root / 'instructions' / 'AGENTS.md'
        agents.parent.mkdir()
        prefix, suffix = b'\xef\xbb\xbf# unrelated\r\n\xff\r\n', b'\r\n# trailing\x80\n'
        agents.write_bytes(prefix + policy.START.encode() + b'old' + policy.END.encode() + suffix)
        skill = self.root / 'custom skill'
        policy.install_global_instructions(agents, skill, self.state)
        installed = agents.read_bytes()
        self.assertTrue(installed.startswith(prefix))
        self.assertTrue(installed.endswith(suffix))
        self.assertIn(policy.shell_argument(Path(sys.executable).as_posix()).encode(), installed)
        self.assertIn((skill.resolve() / 'scripts/coding_team_policy.py').as_posix().encode(), installed)
        self.assertIn(self.state.resolve().as_posix().encode(), installed)
        self.assertIn(b'before each coding-team delegation', installed)
        self.assertIn(b'Routine SOLO explanations do not require a per-turn shell status check', installed)
        self.assertNotIn(b'At the start of each user turn', installed)
        policy.install_global_instructions(agents, skill, self.state)
        self.assertEqual(agents.read_bytes(), installed)
        self.assertFalse(self.state.exists())

    def test_shell_argument_quotes_metacharacters_for_both_shells(self):
        value = 'space apostrophe\' "double" $(echo substituted); & | >'
        with mock.patch.object(policy.os, 'name', 'nt'):
            self.assertEqual(policy.shell_argument(value), "'" + value.replace("'", "''") + "'")
        with mock.patch.object(policy.os, 'name', 'posix'):
            self.assertEqual(shlex.split(policy.shell_argument(value)), [value])

    def test_generated_bootstrap_commands_execute_with_literal_special_paths(self):
        # If $() were expanded, neither literal helper nor state path would resolve.
        special = "spaces apostrophe' $(echo SUBSTITUTED)"
        if os.name != 'nt':
            special += ' "double quotes"'
        skill = self.root / special / 'skill'
        helper = skill / 'scripts' / 'coding_team_policy.py'
        helper.parent.mkdir(parents=True)
        shutil.copyfile(HELPER, helper)
        state = self.root / special / 'state file.json'
        policy.initialize(state)
        agents = self.root / 'AGENTS.md'
        policy.install_global_instructions(agents, skill, state)
        bootstrap = agents.read_text(encoding='utf-8')
        status_command = bootstrap.split('by running `', 1)[1].split('`', 1)[0]
        command_template = bootstrap.split('for every command) with `', 1)[1].split('`', 1)[0]
        env = dict(os.environ, CODEX_THREAD_ID='fixture-shell')
        if os.name == 'nt':
            shell = shutil.which('powershell') or shutil.which('pwsh')
            self.assertIsNotNone(shell, 'PowerShell is required for Windows bootstrap verification')
            shell_args = [shell, '-NoProfile', '-NonInteractive', '-Command']
        else:
            shell_args = ['/bin/sh', '-c']
        before = state.read_bytes()
        result = subprocess.run(shell_args + [status_command], env=env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)['effective_policy'], 'ON')
        self.assertEqual(state.read_bytes(), before)
        command = command_template.replace(policy.shell_argument('<exact command>'),
                                           policy.shell_argument('/coding-team off'))
        result = subprocess.run(shell_args + [command], env=env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)['effective_policy'], 'OFF')
        self.assertEqual(policy.status(state, 'fixture-shell')['effective_policy'], 'OFF')

    def test_bootstrap_append_to_missing_and_unmarked_files(self):
        for original in (None, b'', b'unrelated', b'unrelated\n'):
            with self.subTest(original=original):
                agents = self.root / 'AGENTS.md'
                agents.unlink(missing_ok=True)
                if original is not None:
                    agents.write_bytes(original)
                policy.install_global_instructions(agents, self.root, self.state)
                installed = agents.read_bytes()
                self.assertTrue(installed.startswith(original or b''))
                self.assertEqual(installed.count(policy.START.encode()), 1)
                policy.install_global_instructions(agents, self.root, self.state)
                self.assertEqual(agents.read_bytes(), installed)

    def test_bootstrap_rejects_malformed_duplicate_and_reversed_markers(self):
        start, end = policy.START.encode(), policy.END.encode()
        for original in (start, end, start + end + start + end, end + b'text' + start,
                         start + start + end, start + end + end):
            with self.subTest(original=original):
                agents = self.root / 'AGENTS.md'
                agents.write_bytes(original)
                with self.assertRaises(ValueError):
                    policy.install_global_instructions(agents, self.root, self.state)
                self.assertEqual(agents.read_bytes(), original)

    def test_atomic_replace_failure_preserves_original_and_cleans_temp(self):
        self.initialize()
        before = self.state.read_bytes()
        with mock.patch.object(policy.os, 'replace', side_effect=OSError('fixture replace failure')):
            with self.assertRaises(OSError):
                policy.apply_command(self.state, '/coding-team off all', None)
        self.assertEqual(self.state.read_bytes(), before)
        self.assertEqual(list(self.state.parent.glob('.*.tmp')), [])
        # The failure must also release the lock for a subsequent real write.
        self.assertEqual(policy.apply_command(self.state, '/coding-team off all', None)['global_policy'], 'OFF')

    def test_atomic_fsync_failure_preserves_original_and_cleans_temp(self):
        self.initialize()
        before = self.state.read_bytes()
        with mock.patch.object(policy.os, 'fsync', side_effect=OSError('fixture fsync failure')):
            with self.assertRaises(OSError):
                policy.atomic_write(self.state, b'replacement')
        self.assertEqual(self.state.read_bytes(), before)
        self.assertEqual(list(self.state.parent.glob('.*.tmp')), [])

    def start_lock_holder(self):
        ready = self.root / 'lock-ready'
        code = (
            'import importlib.util,pathlib,sys,time;'
            's=importlib.util.spec_from_file_location("policy",sys.argv[1]);'
            'm=importlib.util.module_from_spec(s);s.loader.exec_module(m);'
            'lock=m.locked(sys.argv[2]);lock.__enter__();'
            'pathlib.Path(sys.argv[3]).write_text("ready");time.sleep(30)'
        )
        process = subprocess.Popen([sys.executable, '-c', code, str(HELPER), str(self.state), str(ready)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        self.addCleanup(cleanup)
        deadline = time.monotonic() + 10
        while not ready.exists():
            if process.poll() is not None:
                self.fail('lock holder failed: ' + process.communicate()[1])
            if time.monotonic() >= deadline:
                self.fail('lock holder startup timeout')
            time.sleep(.02)
        return process

    def test_os_lock_timeout_and_process_exit_release(self):
        self.initialize()
        process = self.start_lock_holder()
        with self.assertRaises(TimeoutError):
            with policy.locked(self.state, timeout=.08):
                self.fail('another process owns the lock')
        process.kill()
        process.communicate(timeout=10)
        with policy.locked(self.state, timeout=1):
            pass
        self.assertTrue(Path(str(self.state) + '.lock').exists())

    def test_os_lock_released_when_body_raises(self):
        with self.assertRaises(RuntimeError):
            with policy.locked(self.state):
                raise RuntimeError('fixture')
        with policy.locked(self.state, timeout=.1):
            pass

    def test_concurrent_subprocess_updates_do_not_lose_chat_overrides(self):
        self.initialize()
        processes = []
        try:
            for index in range(10):
                processes.append(subprocess.Popen(
                    [sys.executable, str(HELPER), 'command', '/coding-team off',
                     '--state', str(self.state), '--chat-id', 'fixture-' + str(index)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            for process in processes:
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, stderr + stdout)
            self.assertEqual(policy.load(self.state)['chat_policies'],
                             {'fixture-' + str(index): 'OFF' for index in range(10)})
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)


if __name__ == '__main__':
    unittest.main()
