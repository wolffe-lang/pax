#!/usr/bin/env python3
"""The lifecycle rows must reject missing/malformed observations."""
import contextlib
import importlib.util
import io
import pathlib
import sys
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('init_rows', pathlib.Path(__file__).with_name('rows.py'))
rows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows)


def stat(pid=1, state='S', parent=0, sid=1, start=42, comm='init'):
    fields = [state, str(parent), '1', str(sid)] + ['0'] * 15 + [str(start)]
    return '%d (%s) %s' % (pid, comm, ' '.join(fields))


class Console:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.commands = []

    def command(self, command, *args, **kwargs):
        self.commands.append(command)
        return next(self.responses)


class LifecycleReadings(unittest.TestCase):
    def setUp(self):
        rows.FAILS.clear()
        rows.ARGS = types.SimpleNamespace(tier='unit', leg='unit')

    def test_proc_stat_uses_last_closing_parenthesis(self):
        f = rows.proc_fields(stat(comm='a)b'))
        self.assertEqual((f[0], f[2], f[4], f[20]), ('1', '0', '1', '42'))

    def test_proc_stat_refuses_missing_error_and_short_data(self):
        for text in ('', 'cat: permission denied', '1 (init) S 0 1 1', stat(state='?')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                rows.proc_fields(text)

    def test_console_identity_needs_pid_one_and_shell(self):
        for response in (None, '', '7\n', '7\n' + stat(pid=2), '7\n' + stat(state='Z')):
            with self.subTest(response=response), self.assertRaises(ValueError):
                rows.console_identity(Console([response]), 1)

    def test_missing_initial_orphan_observation_fails_before_release(self):
        for observation in (None, '', 'GONE 9\n'):
            con = Console(['7\n' + stat(), 'READY 9 9\n', observation])
            rows.FAILS.clear()
            with mock.patch.object(rows, 'login', return_value=True), contextlib.redirect_stdout(io.StringIO()):
                rows.orphan_before_logout(con)
            self.assertEqual(rows.FAILS, ['I14'])
            self.assertFalse(any('release 9' in cmd for cmd in con.commands))

    def test_live_adoption_must_precede_successful_release(self):
        con = Console(['7\n' + stat(), 'READY 9 9\n', 'PRESENT ' + stat(pid=9, parent=1, sid=9),
                       'GONE 9\nORPHAN-RC=0\n', '7\n' + stat()])
        with mock.patch.object(rows, 'login', return_value=True), contextlib.redirect_stdout(io.StringIO()):
            rows.orphan_before_logout(con)
        self.assertEqual(rows.FAILS, [])
        self.assertTrue(any('orphan release 9' in cmd for cmd in con.commands))

    def test_missing_release_result_fails(self):
        con = Console(['7\n' + stat(), 'READY 9 9\n', 'PRESENT ' + stat(pid=9, parent=1, sid=9),
                       None, '7\n' + stat()])
        with mock.patch.object(rows, 'login', return_value=True), contextlib.redirect_stdout(io.StringIO()):
            rows.orphan_before_logout(con)
        self.assertEqual(rows.FAILS, ['I14'])

    def test_second_start_snapshot_requires_all_sections_and_live_service(self):
        valid = 'HOOK\nhook\nSTATUS\nrecord\nSERVICE\n9\n%s\nSENTINEL\nkeep\nDONE\n' % stat(pid=9)
        self.assertEqual(rows.second_start_snapshot(Console([valid]), 1),
                         (['hook'], ['record'], ('9', '42'), ['keep']))
        for response in (None, '', valid.replace('DONE\n', ''), valid.replace('9 (init) S', '9 (init) Z'),
                         valid.replace('SERVICE\n9\n', 'SERVICE\n')):
            with self.subTest(response=response), self.assertRaises(ValueError):
                rows.second_start_snapshot(Console([response]), 1)


class LogoutRecord(unittest.TestCase):
    """I16's verdict on what PAX's last prints (user/last: util-linux's columns, -e PAX's own)."""
    BOOT = 'reboot   system boot  2026-11-17T04:00:00+00:00   still running'

    def lines(self, end):
        return '\n'.join([
            'root     console      2026-11-17T04:01:10+00:00   still logged in  [still logged in]',
            'root     console      2026-11-17T04:01:00+00:00 - %s  (00:00)  [logout]' % end,
            self.BOOT, '', 'wtmp begins 2026-11-17T04:00:00+00:00'])

    def test_a_logout_record_of_its_own_holds(self):
        held, why = rows.logout_verdict(self.lines('2026-11-17T04:01:06+00:00'))
        self.assertTrue(held, why)

    def test_a_session_closed_only_by_the_next_login_is_red_by_name(self):
        held, why = rows.logout_verdict(self.lines('2026-11-17T04:01:10+00:00'))
        self.assertFalse(held)
        self.assertIn('no record of the logout', why)

    def test_missing_sessions_or_a_second_boot_record_are_red(self):
        one = self.lines('2026-11-17T04:01:06+00:00')
        for text in ('', None, one.replace(self.BOOT, ''), one + '\n' + self.BOOT,
                     one.replace('[logout]', '[signal 9]')):
            with self.subTest(text=text):
                self.assertFalse(rows.logout_verdict(text)[0])


if __name__ == '__main__':
    unittest.main()
