"""upgrade_screen: how upgrade.py reads the console and waits for QEMU (pax#457).

Pure functions, so tests/upgrade-screen-selftest can run them without QEMU.

A command typed at the console is echoed after the shell's prompt, and the prompt is not fixed: `$ `,
`# `, `> `, pelt's friendly `root@? ~# ` or, after a failed command, `root@? ~ [1]# `. What a wait
reads is what follows the echo of the command it just typed. An earlier run of the same command may
still be on the screen, so the echoes already there are counted before the new one is typed, and only a
further echo opens the scope. Until it shows, nothing is in scope, so the previous run's output cannot
satisfy or trip a pattern.
"""
import re
import time


class SocketWait(RuntimeError):
    pass


ECHO_PREFIX = 24


def echoes(flat, cmd):
    """Start offsets of the command's echoes: its first ECHO_PREFIX characters right after a prompt's `$ `,
    `# ` or `> `. The prefix only: a host under load drops keys, and the echo then lacks the line's tail
    (pax#457, U2d-state); the rows' own checks read what the command printed."""
    head = cmd[:ECHO_PREFIX]
    return [m.end() - len(head) for m in re.finditer(r'[$#>] ' + re.escape(head), flat)]


def echo_count(flat, cmd):
    return len(echoes(flat, cmd))


def scope_after_echo(flat, cmd, prior):
    """The screen from the newest echo of cmd, or None when no echo beyond the PRIOR earlier ones shows."""
    found = echoes(flat, cmd)
    if len(found) <= prior:
        return None
    return flat[found[-1] - 2:]


class Baseline:
    """The echoes of a command already on the screen when it is typed; follows them off a scrolled screen.

    Once the new echo has been seen it stays seen: output longer than the screen scrolls the echo off the
    top, and everything left on the screen is then after it (pax#457, a whole upgrade's output)."""

    def __init__(self, cmd, prior):
        self.cmd = cmd
        self.prior = prior
        self.seen = False

    def scope(self, flat):
        n = echo_count(flat, self.cmd)
        if n > self.prior:
            self.seen = True
            return scope_after_echo(flat, self.cmd, self.prior)
        if self.seen:
            return flat
        if n < self.prior:
            self.prior = n
        return None


def wait_for_socket(path, proc, name, timeout=60, step=.05):
    """Wait for QEMU's QMP socket to exist. A loaded host took over 10 s once (pax#457's third part):
    the wait is longer, bounded, and names the cause when it gives up."""
    end = time.monotonic() + timeout
    while True:
        if path.exists():
            return
        rc = proc.poll()
        if rc is not None:
            raise SocketWait(f'{name}: QEMU ended (exit {rc}) before it created {path.name}')
        if time.monotonic() >= end:
            raise SocketWait(f'{name}: {path.name} was not created in {timeout} s, QEMU still running: '
                             'a host too loaded to start it, not a failure of the system under test')
        time.sleep(step)
