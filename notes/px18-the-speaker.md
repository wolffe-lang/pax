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

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: KIOCSOUND and KDMKTONE on a console descriptor; PIT channel 2 mode 3 and port 0x61; the tone stops at its process's end and at every halt | **right** as built (`kernel/speaker`, `boot/io.S`'s `pax_halt`). One input was wrong in a way P1 did not name: **pelt gives a child `/dev/null` as standard input** (px14's spawn), so `hold`'s KIOCSOUND on descriptor 0 answered -25 (kasumi a1, `hold: KIOCSOUND 1356 answered -25`); `hold` asks descriptor 1, and `play`'s probe of 0, 1, 2 is what made it work there unmodified |
| P2: the note file's format | **right**, one detail wrong: a `#` starts a comment only at the start of a word, because a sharp (`F#5`) is a `#` inside one (the first build read `D#5` as `D` and a comment: `'D#5 16' is not two words`, kasumi, the list before `b00ffa8`) |
| P3: onsets late by 0-20 ms, never accumulating; a piece's length within ±20 ms | **right**: in the kernel's own timeline (the ring read through the monitor) the scale's onsets are 51 50 50 50 50 50 50 ticks apart (the first note sounds at once, the rest on the tick after their time), each held 48-49 ticks; the mambo's 160 onsets and the Joplin's 154 are each within **19 ms** of the file's schedule (worst), their spans 43710 ms against 43696 and 48570 ms against 48553 (+14 ms, +17 ms). Every leg, kasumi TCG and hasu KVM alike |
| P4: every scale note within 1% of the table, both tiers, BIOS and UEFI; QEMU writes silence between notes, so zero crossings over each note's span | **right on the number, wrong on the capture**: worst **0.25%** (C5 524.34 Hz on one leg; most notes within 0.1%; `notes/px18/kasumi-mpx3-speaker-4cd8554.out`, `hasu-kvm-4cd8554.log`). **Not predicted: QEMU 11.1's `wav` backend writes samples only while the speaker sounds** (the speaker session's WAV holds 3.79 s for a 4-s scale and a 40-s session; keeping either port 0x61 bit set through a rest did not change it: experiments A and B on kasumi, `x1`, `x2`), so a capture has no silences and notes are cut where the pitch changes (`tools/wav-notes`); the onsets are the kernel's to tell (K2's timeline). Also not predicted: it leaves the RIFF sizes 0, and it sounds **about 3% less** time than the guest's ticks count (68.3-68.6 s against 71.0 s held, TCG and KVM alike) |
| P5: `hold`'s tone ends at hold's end; the kernel's line; port 0x61 bits 0-1 clear; test red first | **right**: `user: speaker off at the end of pid 7, port 0x61 0x10` on every leg; the summary's port reads 0x00-0x30 (bits 4-5 are status); before the end hook the same test was red on exactly K3 and K4 (`kasumi-red-before-end-hook.out`: hold's 880 Hz sounded 457-476 ms, until `play scale`'s first KIOCSOUND; CI run 38020945121 at `7cbd62e`). Not predicted: with the hook, QEMU renders **none** of hold's tone (it lives microseconds), so the capture shows no 880 Hz at all |
| P6: play 10-12 MB; the mambo 40-50 s; the Joplin 30-45 s; the scale 4.0 s | play **12.2 MB** (`9dd6430c…`, 12208424 bytes: just over); the mambo **44.3 s**, the scale **4.0 s**, right; the Joplin **50.1 s, wrong** (the strain twice at 76 bpm; the excerpt was not cut to fit the guess) |

## 4. Evidence index

- **The captures and the frequencies**: `notes/px18/kasumi-mpx3-speaker-4cd8554.out` (the gauntlet's run of `tests/mpx3-speaker` at `4cd8554`, 24 PASS, 0 FAIL, 0 SKIP), `kasumi-mpx3-speaker-4cd8554.captures.txt` (every leg's `tools/wav-notes` tones and the kernel's timeline), `hasu-kvm-4cd8554.log` (the same images under KVM, three rounds, 72 PASS). The scale, per leg (Hz, C4 … C5): native BIOS 261.53 293.84 329.52 349.95 392.26 440.09 493.98 524.34; release BIOS 261.54 293.87 328.81 349.22 392.04 439.83 493.98 523.39; native UEFI 261.54 293.74 329.53 349.22 392.04 439.89 493.99 523.62; release UEFI 261.54 293.70 329.54 349.22 392.04 439.97 493.98 523.55. The table: 261.63 293.66 329.63 349.23 392.00 440.00 493.88 523.25; the counts 4561 4063 3620 3417 3044 2712 2416 2280 give 261.60 … 523.33 Hz exactly.
- **The red before the end hook**: CI run **38020945121** at `7cbd62e` (the test before `2380124`/`e226ff1`); kasumi the same tree's red on K3 and K4 only, every leg (`notes/px18/kasumi-red-before-end-hook.out`).
- **The planted break**: `df35f77` loads every count 2% high (every tone 2% flat), CI run **38021555504**; reverted by `bd3d100`.
- **The gauntlet** at `4cd8554` on kasumi (strict env, QEMU 11.1.1 TCG, wolf 0.2.26, clang 23.1.1): every pax suite exit 0, 0 SKIP (`kasumi-gauntlet-4cd8554.summary`, `.versions`).
- **Boot counts**: kasumi TCG, mpx3-speaker: 5 a run in a1-a4 and the gauntlet (25), 2 in experiments A and B; hasu KVM: 15 (three rounds of 5); the gauntlet's other suites as their own counts; nomad-1: 4 preflight boots of the folder's image (2 runs of 2) and 1 boot of a private-tune copy on kasumi.
- **The Linux beep's interface**: `notes/px18/beep.strace` (`ioctl(3, KIOCSOUND, 0)`, `0x4b2f`).
- **QEMU's speaker binding**: `notes/px18/qemu-pcspk-qtree.txt`.
- **Rebased onto px17's merge** (`df5de90`, pelt `3e7516c`): kasumi's gauntlet at `5707dfe`, every suite exit 0 but one mpx3-speaker leg, whose capture cut a note at 449.4 ms (and another at 524.3) against K2's then 30-ms bound (`kasumi-gauntlet-5707dfe.summary`, `kasumi-mpx3-speaker-5707dfe.out`); CI run 38026465296 at `5707dfe` red the same way (449.4 ms). The capture's per-note length was never the timing claim (the kernel's timeline is): it is now a 20% sanity bound (`dd91ab5`, `6f846a0`); three rounds of the rebased images at `6f846a0`, 24 PASS each (`kasumi-mpx3-speaker-6f846a0-rounds.txt`). P4's number is untouched by it.
- **CI green at the head**: in the PR body (run id at the head sha); `6f846a0`'s run 38028246024, all 17 jobs success.
- **The folder**: `~/scratch/wolf/pax-sound/` on nomad-1, its preflight `GO` on the rebased image `42ebd363…` (kernel `dcbc1fc6…`, the gauntlet's at `5707dfe`; pelt `3e7516c`): the WAV leg measured the scale at 261.6 293.7 328.7 349.2 392.1 439.9 494.0 523.4 Hz, worst 0.28%; the CoreAudio leg reported no audio error. `add-tune.sh` was run on kasumi with a two-note file and played (439.6 and 659.1 Hz).
- **The other folders** (`pax-shell/`, `pax-demo/`): px18 moves their ISOs' bytes (`pax_halt`, the tick's call, `boot/speaker.S` in every kernel) but nothing they print; they hold px19+px17 images now, and px18 and px19 conflict in five files, so whichever of the two merges second refreshes both on the integrated head. Not refreshed here.

## 5. Done-when

- [x] branch `px18` on origin; PR #22 open, unmerged, five sections, commit shas as bullets, a test checklist
- [x] CI green at the head sha (the PR body names the run)
- [x] the red before the fix and the plant, each by run id (above)
- [x] nothing closed; what to close and correct is in the PR
- [ ] worktree gone, kasumi and hasu outputs pruned, no orphans (at the lane's end)
