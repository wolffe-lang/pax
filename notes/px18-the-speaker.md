# px18 — The speaker (PAX plays music)

Contract: px18's, `sprints/pax/18-the-speaker/px18-the-speaker.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-09). Branch `px18` in
pax, cut from pax trunk `ef4c3ca` (px16 merged). §1–§3 are committed
before the first change to the kernel, the tools, the tests or the
image.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source
  is read (ruling #22); the refs clone's sparse checkout is never
  widened. Read for this lane: the uapi `include/uapi/linux/kd.h` (two
  request numbers, KIOCSOUND 0x4B2F and KDMKTONE 0x4B30), man-pages
  `ioctl_kd(2)` (what the two requests take), Intel's 8254 data sheet
  as the PC wires it (channel 2's gate and output on port 0x61 bits 0
  and 1, the control word, mode 3), QEMU's documented options
  (`-audiodev`, the machine's `pcspk-audiodev`), and black-box runs:
  Linux's `beep` under strace (`notes/px18/beep.strace`) and QEMU's
  own `info qtree` (`notes/px18/qemu-pcspk-qtree.txt`).
- **Music.** pax ships only (a) one original mambo-flavoured tune this
  lane writes from rhythm and style (clave, montuno-style syncopation,
  a brass-like hook), a new melody, not a transcription, arrangement or
  paraphrase of any existing work, and in particular **never** the
  "Mambo" of *West Side Story*; and (b) public-domain pieces composed
  before 1929, each with its source and date in `docs/SOURCES.md`, and
  never a later copyrighted arrangement of one (for Joplin: the 1902
  publication's melody, not Marvin Hamlisch's 1973 adaptation).
- Nothing in pax names any use of the image or the tunes beyond
  running them (the contract's word list); notes of that kind live only
  outside the repository. ("Capture" here means QEMU's `wav` audio
  backend writing the speaker's samples to a file a test reads.)
- No `region` held open across a yield, a switch or a return to user
  mode (wolf-lang#611): the speaker's state is `.bss` words read and
  written volatile, touched with IF clear (a system call or the tick).
- Test binaries for PAX (pelt, boreutils, play) are built in the
  `px13-ubuntu` container on kasumi or on the CI runner, never with
  kasumi's CachyOS glibc. No build on nomad-1.
- No `rm` outside `~/lanes/px18/` and this lane's worktrees; no `git
  add -A`; nothing under `~/.claude`; no merge; no attribution
  trailers; no "seen red" without a run id, sha, path or digest.
- px17 (pipes) is open and merges first: this lane avoids its files
  (`kernel/files`, `kernel/process`, `kernel/sched`'s pipe code,
  `tests/mpx3-shell`, `user/pelt.pin`) where it can, touches
  `kernel/user` and `kernel/sched` by a line each, and rebases after
  it. px19 (the screen) runs in parallel: whichever merges second
  rebases.

## 2. Inputs, verified (2026-10-09, from origin)

| input | found |
|---|---|
| pax trunk | `ef4c3ca` (px16 merged, PR #19), as the contract says; trunk CI green at `ef4c3ca` (run 37999687276) |
| px17 | open, PR #20, branch `px17` (`df5de90`): touches `kernel/files` (+843), `kernel/process`, `kernel/sched`, `kernel/user`, `boot/user.S`, `kernel/paging`, `tests/mpx3-shell`, `tests/tour`, `user/pelt.pin`. Not `kernel/console`, `kernel/interrupts`, `kernel/timer`, `boot/io.S`, `kernel/wolf.pkg`, `tools/mkuser` |
| px19 | no branch on origin yet |
| the timer | `kernel/timer`: PIT channel 0, mode 2, divisor 11932 (99.998 Hz, a tick every 10.0002 ms), the 8259 line 0; channel 2 and port 0x61 untouched anywhere in the tree (`grep -rn '0x61\|0x42' kernel boot` finds nothing) |
| port I/O | `boot/io.S`: `pax_outb`, `pax_inb`; `pax_halt` (`cli; hlt` loop) is every halt's end, the panic's included (`kernel/panic`'s `halt`, `fail`, `wolf_trap`) |
| sleeps and clocks | `kernel/user`: `clock_nanosleep`/`nanosleep` sleep to the tick after the target (`sleep_until`: "a partial tick never shortens a sleep"), so a relative sleep of d ends between d and d + 20 ms; `clock_gettime` reads the tick count (10 ms steps) |
| ioctl | `kernel/user` → `kernel/files.ioctl` → `kernel/console.ioctl` on a console descriptor (0-2 of a fresh process): TCGETS, TCSETS*, TIOCGWINSZ, TIOCSWINSZ; anything else `refused: tty ioctl 0x…`, -ENOTTY |
| the process model | px14: pelt pid 1 runs programs by clone3/execve/wait4; every process end (`exit`, `exit_group`, a fault's kill) goes through `sched.end_with` |
| the shell image | `tests/mpx3-shell` builds kmain_console + an initramfs (`/bin`: pelt, boreutils' nine; `/etc/motd`, `/etc/pax-run`) on both tiers, BIOS and UEFI, plus a `quiet` variant |
| wolf | `kernel/wolf.pin`: 0.2.26 archive. No `ioctl` builtin in 0.2.26's prelude (134 names, `wolf prelude`); `[abi.asm.link]`: a hosted root `wolf.pkg` may list assembly, assembled by the link's `cc`, called through a bodyless `extern "c" fn` in `unsafe` |
| Linux's beep | Ubuntu 24.04 `beep` 1.4.9, strace (`notes/px18/beep.strace`): its console driver opens the device `O_WRONLY` (default `/dev/tty0`, then `/dev/vc/0`) and asks `ioctl(fd, KIOCSOUND, 0)` (`0x4b2f`); its evdev driver asks `EVIOCGSND`. KIOCSOUND is the console shape a Linux beep program uses |
| QEMU on nomad-1 | 11.1.1 (Homebrew); audio drivers `none coreaudio dbus wav`; the q35 machine has an `isa-pcspk` at 0x61 whose `audiodev` is set by `-machine pcspk-audiodev=ID` (qtree: `audiodev = "snd0"`); `-audio driver=…` leaves it `""` (`notes/px18/qemu-pcspk-qtree.txt`). So the command is `-audiodev coreaudio,id=snd0 -machine q35,pcspk-audiodev=snd0` |
| QEMU on kasumi | 11.1.1, drivers `none wav`; `pcspk-audiodev` binds the same; TCG (no /dev/kvm) |
| kasumi | `/home` 97% (29 GB free); `px13-ubuntu` (Ubuntu 24.04, glibc 2.39) present |

Drift from the contract's inputs: none of substance. The contract's
"`-audiodev coreaudio,id=… -machine pcspk-audiodev=…` or the
version's equivalent" is exactly 11.1.1's spelling; `-audio` is not an
equivalent for the speaker (it binds nothing in the qtree).

## 3. Prediction (committed before the first change)

### P1. The interface: Linux's console ioctls

**KIOCSOUND (0x4B2F) and KDMKTONE (0x4B30) on a console descriptor**,
as `ioctl_kd(2)` describes them: KIOCSOUND's low 16 bits are the PIT's
count (1193180 / frequency per the man page; the PC's 8254 input is
1193182 Hz), 0 is silence; KDMKTONE's low 16 bits are the count, its
high 16 the duration in milliseconds, 0 silence, and the call returns
at once (the tick ends the tone). Argued: a Linux beep program asks
exactly KIOCSOUND of a console descriptor (strace above), so a program
written for Linux's console runs unmodified, and a device file
(`/dev/speaker`) would be a PAX invention no Linux program knows. The
console here is descriptors 0-2 (PAX has no `/dev/tty0` yet; adding it
is `kernel/files`, px17's file, and is left to a later lane), so
`/bin/play` asks KIOCSOUND of the first of 0, 1, 2 that accepts it.
On PAX the request is answered once the console is started (every
kernel that runs pelt); before that, -ENOTTY as today.

The kernel side (`kernel/speaker`): PIT channel 2 in mode 3 (square
wave), control word 0xB6 to port 0x43, the count low then high to
0x42, then port 0x61 bits 0 (the gate) and 1 (the speaker's data
enable) set; silence clears both. **One deliberate difference from
Linux**: the tone stops when the process that started it ends (exit,
`exit_group` or a fault), from `sched.end_with` — Linux leaves it
sounding. And every halt silences it: `pax_halt` clears the two bits
before its `hlt` loop, so a panic never leaves a note hanging.

### P2. The note file

Plain text, one item a line, `#` to the end of a line a comment:

    title <words>        optional, before tempo
    tempo <bpm>          quarter notes a minute, 20-400; required before the first note
    gap <ms>             optional, 0-100 (default 20): silence cut from the end of each note
    <note> <length>      note: C D E F G A B, then # or b, then the octave 2-7 (A4 = 440 Hz)
    r <length>           a rest
    length: 1 2 4 8 16 32 (whole … thirty-second), a trailing `.` dots it; `+` ties (`4+16`)

`play FILE-OR-NAME` (a bare name is `/usr/share/tunes/NAME`) reads the
whole file, validates every line before a sound (a bad line is
`play: <path>: line <n>: <what>`, status 2, and nothing plays), then
plays it; `play` alone lists `/usr/share/tunes`, one line a tune: its
name, its title, its length in seconds.

### P3. Timing at the PIT's tick

`play` keeps an absolute schedule (each note's start = the first
note's start + the lengths before it, from `time_now_ms`) and sleeps
the difference, so an error never accumulates. Each note's onset is
late by **0 to 20 ms** (a relative sleep ends on the tick after its
target, `sleep_until`; the clock it reads steps every 10 ms); the
whole piece's length is the file's to within **±20 ms**. Falsified by
any onset more than 30 ms from schedule in the capture, or a piece
whose length is off by more than 30 ms.

### P4. The frequencies

The scale (`/usr/share/tunes/scale`, C4 D4 E4 F4 G4 A4 B4 C5, quarters
at 120) captured through `-audiodev wav` (QEMU's default 44100 Hz,
16-bit), each note's frequency measured by counting rising zero
crossings across its sounding span (first to last crossing over their
count, so the error is about one sample in the span: < 0.01 Hz on a
0.48 s note), will match the equal-tempered table (A4 = 440) **within
1%** for every note on both tiers, BIOS and UEFI. The PIT's own
quantisation (an integer count) is at most 0.02% in this range; the
rest of the budget is QEMU's rendering of a square wave at its sample
rate, which I have not measured and will not predict closer.
Falsified by any note more than 1% off, or a note missing.

### P5. The gate after exit

A program that starts a tone and exits without stopping it
(`user/elf/hold.S`, KIOCSOUND at 880 Hz, then `exit_group(0)`) leaves
the speaker silent: the kernel's line `user: hold pid <n> speaker: off
at its end` names it, port 0x61 read back after the write has bits 0
and 1 clear, and the capture's 880 Hz tone ends within one tick of the
program's end (the next prompt), not at the halt. Seen red first: the
test lands before the kernel's end hook and fails exactly there.

### P6. Sizes and lengths

`play` built by wolf 0.2.26 is a static glibc ET_EXEC of the same order
as boreutils' (about 10-12 MB, the runtime linked whole). The original
tune runs **40-50 s** (34 bars at 184 bpm is 44.3 s); the Joplin
excerpt 30-45 s; the scale 4.0 s.
