# px123 — a terminal over ssh, and Ctrl-C reaching what runs on it

burrow#24 (ab34042) gives burrowd's sessions a terminal: `ssh host` from a terminal gets the login shell on a
pseudo-terminal of its own (px111's ptys), the slave its controlling terminal and its group the foreground, the
client's window changes applied. The first image that carried it showed one row red: Ctrl-C (and Ctrl-\) typed
into the session reached nothing. This note says which layer dropped it, the fix, and the rows that hold the
terminal now.

## 1. Which layer

Measured on an installed disk upgraded to that image, booted under KVM, read over ssh as its user (`/proc/PID/stat`
and `/proc/PID/status`, PAX's own, Linux's fields):

| layer | what it showed | verdict |
|---|---|---|
| the pty's line discipline | `^C` echoed; Ctrl-Z stopped the job (`[1] + Stopped sleep 40`); a resize from 33x97 to 41x120 reached `stty size` | right |
| the foreground group | the foreground `sleep`'s process group was the terminal's (`tpgid`), its session pelt's, its terminal the pty | right |
| pelt | `set -o` says `monitor on`; it put each job in a group of its own and gave it the terminal | right |
| burrowd's session | the shell leads a session of its own with the slave as its controlling terminal (`/dev/tty` opens; `tty` names `/dev/pts/0`) | right |
| the signal's disposition | `SigIgn: 0000000000000006` (SIGINT and SIGQUIT ignored) in burrowd and in every program of every session; `kill -INT` from another session did nothing either, `kill -TERM` ended it | **the cause** |

Where the ignore came from: `/etc/pax-boot.d/burrowd` starts burrowd's restart loop as `( ... ) &` in a shell with no
job control. POSIX (XCU 2.11) has such an asynchronous list start with SIGINT and SIGQUIT ignored, pelt does exactly
that, an ignored signal stays ignored across exec, and burrowd resets only SIGPIPE in a session's program. So every
program run over ssh had both ignored, and the keys that send them did nothing. Nothing in the kernel, pelt or
burrow's pty handling was wrong.

## 2. The fix

The hook starts burrowd with both at their defaults: `/bin/env --default-signal=INT,QUIT /bin/burrowd ...` (boreutils'
`env`, GNU's option), and refuses to start without `/bin/env`. On a copy of the same disk with the hook changed and
nothing else: burrowd's `SigIgn` is `0x1000` (its own SIGPIPE), a session's program shows none, Ctrl-C ends a
foreground `sleep 30` with status 130, Ctrl-\ with 131, Ctrl-Z stops it. burrow's own hardening, a session's program
starting with every signal at its default however burrowd was started, is burrow#26 (7aa182f), which this branch
pins: both layers are fixed, so a session's program is right even when burrowd is started some other way, and
burrowd itself no longer runs with the two ignored.

The `?` in the prompt (`wolf@? ~> `) is not ssh's: pelt shows `?` where the host name goes when nothing names the
host, and PAX names none (no `/etc/hostname` on the images, no `/proc/sys/kernel/hostname`, `hostname` and
`uname -n` refuse: wolf-lang#907). The console's pelt reads the same places. pax#351.

## 3. The rows

`tests/mpx5-burrowd` B19-B27, one `ssh host` at a 33x97 pseudo-terminal of the rows' own (OpenSSH's client), typed
into as a person types and read off what the terminal shows: B19 the prompt and a typed line run; B20 `tty` a
`/dev/pts/N`; B21 `stty size` the client's, and after a resize to 41x120 the new one; B22 Ctrl-C ends a foreground
`sleep 30` (130); B23 Ctrl-\ (131); B24 Ctrl-Z stops it and `jobs` lists it; B25 a bare `sudo` asks on the session
and runs with the password typed there; B26 `/proc/sys/kernel/pty/nr` is 0 after the session; B27 burrowd's own
`SigIgn` (its pid `/var/run/burrowd.pid`'s) has neither SIGINT nor SIGQUIT. With burrow 7aa182f a session's program
starts with its defaults whatever burrowd has, so B22 and B23 hold burrow's layer and B27 holds the hook's. B12 now holds the
sessions with no pty (`ssh -T host`, `ssh host COMMAND`: not a tty), B15 a bare `sudo` in a command over ssh finding
no terminal and saying so (it used to stop on the console), and B9 no longer looks for a refused pty in the log.
The suite's image gains boreutils' `stty` and `tty`.

**The plant:** the hook's line put back as it was, one commit, one file, one hunk: B27 red by name (B22 and B23
stay green: burrow's layer holds them).

## 4. Evidence

Development takes on the Linux build host, `tests/mpx5-burrowd --tier native --firmware bios` in the burrowd suite's
rig container (QEMU 8.2.2, OpenSSH 9.6p1, dnsmasq) under a block's two lock names.

The dev compiler and its std are `user/wolf.pin`'s (v0.2.36), built by `tools/mkwolf` and `tools/mkwolf-std`
(`PASS the build reproduces user/wolf.sums`) and handed to the suite by `PAX_DEV_WOLF_DIR` and `PAX_DEV_STD_DIR`.

With burrow 7aa182f a session's program starts with SIGINT and SIGQUIT at their defaults whatever burrowd has, so
B22 and B23 hold burrow's layer and pass with the hook as it was; B27, burrowd's own `SigIgn`, holds the hook's.

- **Red at the rows commit** `c21ed819` (the hook as it was): `mpx5-burrowd native bios: FAIL B27`, every other row
  green; B27 `burrowd (pid=10): SigIgn 0000000000001006, SIGINT ignored, SIGQUIT ignored`, B22 `B22=130 after 1.3
  s` (log sha256 `8bea8466…`).
- **Green at the fix** (`662bd69f`, the branch's head before the evidence went in): `mpx5-burrowd native bios:
  PASS`; B27 `SigIgn 0000000000001000, SIGINT default, SIGQUIT default` (burrowd's own SIGPIPE), B22 `B22=130`, B23
  `B23=131`, B24 `[1] + Stopped sleep 30`, B25 `[sudo] password for pax:` then `B25-ran` (log sha256 `ab2494bd…`).
- **The plant** (`75102b90`, local, the hook's line put back): `mpx5-burrowd native bios: FAIL B27`, B27 `SigIgn
  0000000000001006, SIGINT ignored, SIGQUIT ignored`, B22 `B22=130` and B23 `B23=131` green (log sha256
  `bc903c33…`).
- With burrow at ab34042 (burrow#24 alone), before burrow#26: the rows commit was red on B22 and B23 (`B22: ^C`
  echoed, the sleep ran its 30 s), the fix green; that pair is what found the hook.
- At the second half's head (wolf 0.2.39, pelt b80d6570, den 291011dd, the dev compiler's std 2411d868):
  `mpx5-burrowd native bios: PASS` (log sha256 `1c469881…`).

The diagnosis in §1 and the check of the fix in §2 ran on a copy of an installed disk upgraded over ssh to the first
image that carried burrowd's terminal, booted under KVM with OpenSSH 10.2p1 as the client; the rows above are the
suite's own image.

## 5. The rebase

The branch was rebased from trunk `309036ec` onto `48ea81ba`, the head of pax#349 (a USB device plugged in after
boot gets a record), which reached trunk first. The seven commits before it are kept on `px123-before-rebase` (head
`d10ae117`), and the plant take's commit with its parent on `px123-plant-before-rebase` (head `75102b90`, on
`662bd69f`, whose tree is `d10ae117`'s but for this note's §4); the shas §4 cites are theirs. Two files conflicted,
both prose, and each kept both sides:
- `CHANGELOG.md`: the terminal's paragraph heads the Unreleased list, above pax#349's;
- `docs/SOURCES.md`: px123's section follows px120's.

`git range-diff` shows the other five patches unchanged. pax#349 changes the kernel's frame allocator and xHCI
driver, which the burrowd suite's image carries, so the records at this branch's head are taken afresh, not carried
from §4.
