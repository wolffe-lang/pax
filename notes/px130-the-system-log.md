# px130 — a kernel log you can read, a quiet console, and where the system's logs live (pax#383)

Base: trunk `0e2843cf`. Queued ahead of this branch, fast-forward only: pax#379 (the console draws only what
changes), then pax#347, pax#350's successor, pax#361, pax#358, pax#359. pax#379 changes when the screen draws
(`kernel/screen`'s held write, `kernel/serial`), which is where this branch's console level sits; expect a rebase
onto it, delivered as a new branch and pull request.

## 0. The prediction (written before the first change)

**Why.** The kernel writes a line for every process its signal's default action ends (`kernel/signal`'s `die`:
`user: NAME pid N killed: SIG…[, a write to a pipe with no reader] after N runs`) through `kernel/log`, and every
byte `kernel/log` writes goes through `serial.put`, which draws it on the screen before the serial port takes it.
So a line about a program run over ssh lands wherever the console's cursor is, over the console's prompt. And
nothing keeps a kernel line once it has scrolled: no ring buffer, no `dmesg`, no `/dev/kmsg`.

**The measurement (item 1).** An installed-shape image (the burrowd suite's tree: `/bin/login` as pid 1, pelt
with its friendly prompt and lope's hook from `/etc/shrc`, den, boreutils, burrowd) booted under QEMU with the
console logged in as root and one ssh session at a pseudo-terminal as `pax`, once with `quiet` (as an installed
system boots) and once without (every exec and exit narrated, to name each pid). What I expect each piece of
ordinary work to write:

| work over ssh | line(s) expected | verdict expected |
|---|---|---|
| `yes \| head -n 3`, `seq 1 100000 \| head -n 2`, `cat BIG \| head -n 1` | the writer `killed: SIGPIPE, a write to a pipe with no reader` | correct: the writer of a pipeline whose reader ended dies of SIGPIPE on Linux too; shells say nothing |
| `ls /bin \| head -n 3` (a short writer) | none, or ls killed by SIGPIPE when its output outruns head | correct either way |
| Ctrl-C on a foreground `sleep 30`; Ctrl-\\ | `sleep … killed: SIGINT` (`SIGQUIT`) | correct |
| `exit` | pelt's `exit_group 0` (narrated only without `quiet`) | correct |
| the client dropped (its process killed) | pelt `killed: SIGHUP` (the pty hung up), and any job left in the session | correct |
| pelt's friendly prompt and lope's hook (a `cd`, a jump) | lope's exec and exit per directory change, no `killed:` | correct |
| `den init`, `add`, `commit`, `status`, `log` | each den's `exit_group 0`; none killed | correct |
| `den push` / `den fetch` to a file remote | den and its upload-pack / receive-pack helpers exit 0 | if a helper dies of SIGPIPE or SIGTERM, a den fault to file there |

Prediction: on an installed system (`quiet`) the only lines over the prompt are `killed:` lines, almost all
SIGPIPE from pipelines and SIGINT from Ctrl-C, each correct behaviour; whatever is not (a helper that should have
exited on its own) is a fault in that tool, filed there and left visible.

**The design (items 2 and 3).**
- *The ring buffer.* A new module below `kernel/log` keeps every kernel line as a record: a sequence number, a
  level (syslog's 0-7, the facility `kern`), a timestamp from the tick counter (the clock `CLOCK_MONOTONIC`
  reads, 10 ms steps, 0 before the tick starts) and the text. Fixed static storage of 128 KiB, oldest records
  overwritten; nothing survives a reboot (the boot's own bytes keep px118's separate record). A line written
  without a level gets the default level, 4 (warning), as Linux gives one; the lines of a program's ordinary life
  (killed by a signal, exec, exit, a thread's exit, the counts after a run) are written at 6 (info).
- *Readers.* `syslog(2)` (actions 0-10, as `syslog(2)` documents them) and `/dev/kmsg` (character device 1:11:
  one record per read, `PRI,SEQ,USEC,-;TEXT\n`; a reader that has caught up blocks, or answers -EAGAIN with
  O_NONBLOCK; a reader whose next record was overwritten gets -EPIPE once and goes on from the oldest; a write
  adds a record at the level its `<N>` prefix names; SEEK_SET, SEEK_END and SEEK_DATA as the kmsg document says;
  `poll` ready when a record is there). `/proc/sys/kernel/dmesg_restrict`, 1 at boot: reading is root's.
  `/proc/sys/kernel/printk` reports the console level.
- *`dmesg`* on every image: boreutils has none (coreutils carries none; util-linux does) and busybox is not on the
  images, so a small one in wolf (`user/dmesg`), reading `/dev/kmsg`: `[seconds.micro] text`, `-r` raw, `-l`
  levels, `-w` follow, `-n LEVEL` and `-C` / `-c` for root.
- *The console level.* `log` decides at a line's first byte whether the line reaches the screen: a line at or
  above the console level (less severe) goes to the serial port and the ring buffer only. Today's behaviour is
  level 8, every line shown, and stays the default: the development and test images, which boot without `quiet`,
  keep it. With `quiet` (every shipped image and every installed system) the level drops to 5 once the first
  program starts: warnings and worse (and every line with no level) still draw, info does not. `loglevel=N` on
  the command line sets it from the start; root's `dmesg -n N` (`syslog(2)` action 8) at run time. The serial
  port keeps every byte it has today: no suite's serial expectations move.

**What each row should show** (rows in `tests/mpx5-burrowd`, which already boots the installed shape with `quiet`
and drives an ssh session at a terminal, unless named):

| row | at the rows' commit (before the kernel change) | after |
|---|---|---|
| a writer killed by SIGPIPE over ssh: the console's screen unchanged (screendumps before and after equal) | red: the line is drawn | green |
| the same line in the ring buffer with a timestamp: root's `dmesg` at the console shows it | red: no `dmesg`, no buffer | green |
| `dmesg` refuses `pax` by default (`dmesg_restrict` 1) | red: no `dmesg` | green |
| a warning still reaches the screen | green by accident (every line draws) | green |
| the serial port still has the `killed:` line, byte for byte | green | green |
| `/dev/kmsg` (a kernel suite's program, against Linux's own `/dev/kmsg` where it answers): the record format, -EAGAIN, follow, -EPIPE on a wrap, a write's level, `syslog(2)` READ_ALL and SIZE_BUFFER, the refusal to a user | red: no device, -ENOSYS | green |
| the buffer wraps at its size: after more than 128 KiB of records the oldest is gone, the sequence numbers run on, the newest is whole | red | green |
| every suite that reads `killed:` lines from serial | green | green, unchanged |

The plant: the console level ignored (every line drawn again): the screen row red by name.
