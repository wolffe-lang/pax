# px30 — The sound card (PCM out, and voices that sound together)

Contract: px30's, `sprints/pax/30-the-sound-card/px30-the-sound-card.md`
in wolffe-lang/wolf (planning trunk, read 2026-10-11). Branch `px30` in
pax, cut from pax trunk `5afb903` (px26 merged). §1–§3 are committed
before the first change to kernel code.

One deliverable: an unmodified static Linux program that writes PCM to
the sound device plays on PAX and the captured audio matches what it
wrote; and `play` gains a mixed mode in which a tune's chords and voices
sound together.

## 1. Forbidden, absolutely

- No kernel's, libc's, sound server's, sound library's or driver's
  source is read or searched for (ruling #22): not Linux's sound core,
  its OSS emulation or virtio-snd driver, ALSA's library, OSS, SDL,
  PulseAudio or PipeWire; never QEMU's device or audio source. Facts
  come from the OASIS VIRTIO specification (1.2 and 1.3, the sound
  device, §5.14), the uapi `linux/soundcard.h` (request numbers, the
  AFMT and DSP_CAP bits, `audio_buf_info`) and `sound/asound.h` (read
  only to size the ALSA interface for the prediction), the OSS
  programmer's guide as published, the man pages (`open(2)`,
  `ioctl(2)`, `poll(2)`, `close(2)`), QEMU's documentation (`-audiodev`,
  `-device virtio-sound-pci`) and black-box runs: Linux 7.2.8 (kasumi's
  own kernel image and modules, run, never read) under QEMU with each
  candidate device, strace of the witnesses there, and the WAV QEMU
  writes.
- The user interface is one Linux already has (OSS `/dev/dsp`, §3); no
  private system call or node. What is not implemented is refused with
  Linux's errno, by name, and counted.
- The speaker (`kernel/speaker`, KIOCSOUND, `tests/mpx3-speaker`) is
  not changed; no kernel timer rate changes.
- No word implying filming, recording (of a session), viewers or a
  demo anywhere in pax ("capture" is QEMU's `wav` backend writing what
  the device plays, for a test to read). No copyrighted music: test
  signals are sines, ramps, sweeps and the tunes already in the tree.
- Stay out of px24's (readiness), px27's (the file tree) and px29's
  (`play`'s chord syntax, tune files) work: this lane's touches of
  `kernel/files`, `kernel/user` and `user/play` are hooks a few lines
  long, kept separable for the rebase.
- Test binaries for PAX only from the `px13-ubuntu` container or the CI
  runner; no build on nomad-1; no `rm` outside `~/lanes/px30/`; no
  `git add -A`; nothing under `~/.claude`; no merge; no trailers; at
  most one CI run of this lane's at a time; strict evidence (#571);
  no "seen red" without a run id, sha, path or digest.

## 2. Inputs, verified (2026-10-11, from origin)

| input | found |
|---|---|
| pax trunk | `5afb903` (px26 merged), as the contract says. Open PRs: px24 #31 (`kernel/files` +312, `kernel/sched`, `kernel/user`, `kernel/signal`, a new `kernel/ready`), px27 #30 (`kernel/files` +1395/-407, a new `kernel/tree`, `kernel/user`). px29: no branch, no PR yet |
| the speaker and captures (px18) | KIOCSOUND/KDMKTONE on a console descriptor, PIT channel 2; QEMU's `wav` backend writes samples only while the speaker sounds; `tools/wav-notes` counts zero crossings of one channel — it cannot see two pitches at once |
| PCI and the transport (px20) | `kernel/pci` (bus 0 and bridges, BARs, capabilities), `kernel/virtio` (the 1.x capabilities mapped uncached in PML4 slot 352, one 1 MiB window per capability kind; the split virtqueue in one frame; its state words in `pax_net_state`), INTx through the 8259 pair on the firmware's line, made level-triggered (`timer.level`); MSI/MSI-X not usable. `kernel/virtio` keeps ONE device's transport words (`pax_net_state` 0-7): a second virtio device needs its own words |
| threads, waits (px26) | a system call that must wait answers `files.WAIT`; kernel/user rewinds it and parks the thread (`sched.block_pipe`, state PIPE, `W_REWOUND`) until `sched.wake_pipes`; a signal ends the wait (-EINTR, or the call again under SA_RESTART). Every process end goes through `sched.end_with` (the speaker's hook) |
| QEMU's sound devices | `-device help` on all three hosts (kasumi 11.1.1, hasu 11.1.0, nomad-1 11.1.1): AC97, ES1370, intel-hda / ich9-intel-hda with hda-output/duplex/micro, sb16, adlib, cs4231a, gus, usb-audio, **virtio-sound-pci**. Audio backends: kasumi `none wav`; hasu `none alsa dbus jack oss pa pipewire sdl spice wav`; nomad-1 `none coreaudio dbus wav`. The CI runner's QEMU is 8.2.2 (px20): not listed here; **virtio-sound-pci there is unverified** until the first CI run boots it |
| virtio-sound-pci on q35 | `info pci`/`info qtree` with the machine stopped (nomad-1 11.1.1): `1af4:1059`, subsystem `1af4:1100`, class 04.01 (audio), pin A, BAR1 32-bit memory (MSI-X), BAR4 64-bit prefetchable (the 1.x capabilities); `disable-legacy = on` (modern only, no I/O BAR); `jacks = 0`, `streams = 2`, `chmaps = 0`; `event_idx`, `indirect_desc`, `notify_on_empty`, `any_layout` offered by the transport |
| Linux with each device (the survey) | `tools/linux-sound`: kasumi's own kernel 7.2.8-1-cachyos (`f4c00d5d…`), its modules decompressed into a busybox initramfs (busybox-static from px13-ubuntu), q35, TCG `-cpu max` (the default CPU model boots nothing: the kernel needs features qemu64 lacks), `-audiodev wav`. `dsptone` (`08aa2783…`) through `/dev/dsp` (snd-pcm-oss): a 1 s 440/660 Hz stereo S16 48 kHz sine, then 0.5 s of 1 kHz mono U8 at 44.1 kHz. **virtio-sound-pci, AC97 and ES1370 sound**: their WAVs (44.1 kHz stereo S16, QEMU's default) hold both runs at 1.52 / 1.51 / 1.51 s; pitches virtio 439.92/659.94/999.94 Hz, AC97 439.93/659.94/999.94, **ES1370 446.01/669.18** (1.4% sharp at 48 kHz) (`notes/px30/linux-survey-*.pcm.txt`, `.serial.log`). **intel-hda: no card** with snd-hda-intel and the generic codec within the script's one second (`linux-survey-intel-hda.serial.log`); not pursued: it is the largest of the four (CORB/RIRB, codec verbs) and the others sound. sb16 not tried: it needs the ISA DMA controller PAX lacks |
| what an OSS writer asks (strace in the guest) | `notes/px30/linux-strace-virtio.serial.log`: `openat("/dev/dsp", O_WRONLY)`; `OSS_GETVERSION`, `SNDCTL_DSP_GETFMTS`, `GETCAPS`; `SETFMT`, `CHANNELS`, `SPEED` (in that order, the OSS guide's); `GETBLKSIZE`, `GETOSPACE`, `GETODELAY`; `write`s; `close`. With no request at all (`-n`) only open/write/close: 8000 Hz U8 mono, the OSS default. Linux's close drains: the witness's writes took 3 ms and its close 1012 ms on virtio (633 + 363 ms on AC97) for 1000 ms of sound |
| what Linux answers at the edges (`dspprobe`) | `notes/px30/linux-dspprobe-{virtio,AC97}.serial.log`, identical on both cards: a second `O_WRONLY` open while one is held **EBUSY**; `O_RDONLY` beside it ok (capture); SETFMT takes every format asked (U8, S16_LE, S16_BE, MU_LAW, S8: Linux converts in software); CHANNELS 6 → 6, 0 → 1; SPEED any rate (11000 → 11000, 1000 → 1000), 400000 → 192000; SETFRAGMENT ok; GETCAPS TRIGGER and MMAP, not DUPLEX; poll POLLOUT ready before a write; a 3-byte write (not a whole frame) answers 3; SYNC ok and GETODELAY 0 after it; RESET ok and keeps the format; GETISPACE on a playback open EINVAL; TCGETS **EINVAL**; read EBADF; lseek ESPIPE (`E?` in that log, before the probe named it) |
| ALSA's interface, by its header | `sound/asound.h`: the PCM character device takes `SNDRV_PCM_IOCTL_*` — PVERSION, INFO, TSTAMP, TTSTAMP, USER_PVERSION, HW_REFINE, HW_PARAMS, HW_FREE, SW_PARAMS, STATUS(_EXT), DELAY, HWSYNC, SYNC_PTR, CHANNEL_INFO, PREPARE, RESET, START, DROP, DRAIN, PAUSE, REWIND, FORWARD, RESUME, XRUN, WRITEI/READI/WRITEN/READN FRAMES, LINK, UNLINK — over a `snd_pcm_hw_params` of 13 masks and intervals that HW_REFINE narrows by rules, plus the mmap'd status and control pages (or SYNC_PTR), plus `/dev/snd/controlC0`'s card info; `aplay` reaches it through libasound and its configuration files. Not straced: no aplay in px13-ubuntu, kasumi's own (CachyOS, AVX-512 glibc) does not run under TCG, and lanes install nothing |
| kasumi | QEMU 11.1.1 (TCG), `/home` 96% (39 GB free), px13-ubuntu `ad896450…` (glibc 2.39, gcc 13.3) |
| hasu | `/dev/kvm`, QEMU 11.1.0 through `nix-shell -p qemu`, 279 GB free |

## 3. Prediction (committed before the first change to kernel code)

### P1. The device: virtio-sound-pci

Chosen over AC97 (the runner-up: it sounds, exactly, on every host) for
three reasons: it **reuses px20's transport** — `kernel/pci`,
`kernel/virtio`, INTx on the 8259 — so the new code is one device's
queues and its request formats, where AC97 is a second register model
(bus-master descriptor lists, the codec's mixer); its specification is
**OASIS's**, the one this repository already follows, where AC97's is
a 2002 Intel PDF that also covers a codec; and its model is the one OSS
needs — the driver hands the device whole periods and the device hands
each back when it has played it, which is the completion path, the
latency and the underrun all at once. Rejected: intel-hda (largest;
Linux found no card in a second), sb16 (ISA DMA), ES1370 (plays 48 kHz
1.4% sharp under QEMU).

How the driver uses it (VIRTIO 1.2 §5.14): `kernel/virtio` grows a
second transport record so net and sound each keep their own; the
feature word taken is **VIRTIO_F_VERSION_1 alone** (bit 32, refused by
name without it; everything else offered is declined); queues 0
(control), 1 (event), 2 (tx); the rx queue (3) is set up with no
buffers, as the device has a capture stream nothing here uses. The
control queue is synchronous: a request and its response in one frame,
notify, wait for the used entry (bounded). At start: `PCM_INFO` for
every stream, the first OUTPUT stream is the one used, its formats and
rates logged. Interrupt: INTx on the firmware's line, level, the ISR
read then the 8259's EOI; the handler collects returned tx buffers and
wakes waiting writers (`sched.wake_pipes`); no allocation.

Predicted of the device: it offers VERSION_1, EVENT_IDX (29),
INDIRECT_DESC (28) and nothing sound-specific; two streams, stream 0
OUTPUT and 1 INPUT, `channels_min` 1, `channels_max` 2; formats U8 and
S16 at least; rates 8000 to 192000 (the virtio enumeration's 8000 …
192000, i.e. not 5512 or 384000). Falsified by stream 0 not OUTPUT or
S16 or 48000 missing.

### P2. The interface: OSS `/dev/dsp`

Argued against ALSA's PCM device: a static C program speaks OSS with
`open`, three `ioctl`s and `write` (the strace above is the whole
conversation); ALSA's device takes some thirty requests over a
parameter space refined by rules, needs its mmap'd status pages or
SYNC_PTR, and every real ALSA program reaches it through libasound and
its configuration files, which no static program here carries. OSS is
Linux's own interface (snd-pcm-oss, `/dev/dsp`, character device 14:3),
still what small programs and `play`'s 30-line ioctl membrane can
speak. Rejected by the same measure: a private node.

What PAX answers (a difference from Linux is named and counted):

| request | PAX |
|---|---|
| `open("/dev/dsp", O_WRONLY[|O_NONBLOCK])` | ok; `/dev/dsp` exists (listed in `/dev`, `stat` 14:3, mode 020666) only when the device is up, else ENOENT as on Linux without a card |
| a second open while one is held | **EBUSY**, as Linux |
| `O_RDONLY` / `O_RDWR` | **ENXIO, counted** (Linux opens capture; PAX has none) |
| SETFMT | U8 and S16_LE taken; **any other format answers S16_LE** (OSS's rule: the answer is what was set; Linux converts instead), counted; AFMT_QUERY the current |
| CHANNELS / STEREO | 1 or 2; more answers 2 (Linux took 6), 0 answers 1 |
| SPEED | the device's rate nearest the request (Linux resamples: 11000 → 11000 there, **11025 here**); out of range clamps |
| GETFMTS | U8 \| S16_LE |
| GETBLKSIZE, GETOSPACE, GETODELAY, GETOPTR | the period (4096 bytes), free periods of 8, bytes queued and not yet returned by the device, bytes played |
| SETFRAGMENT, SUBDIVIDE, NONBLOCK, POST | answered 0 (the period stays 4096: counted as ignored); NONBLOCK sets O_NONBLOCK |
| SYNC | waits until everything written has been played (a wait like a pipe's) |
| RESET | stops at once, drops what is queued, keeps the format |
| GETCAPS | revision 1 and DSP_CAP_REALTIME only (no TRIGGER, no MMAP, no DUPLEX) |
| OSS_GETVERSION | 0x030802 (the header's SOUND_VERSION) |
| any other request | **EINVAL, named on the console's log once, counted** (Linux's answer for TCGETS here) |
| `write` | bytes copied into the current period; a full period is handed to the device; with all 8 at the device a blocking write waits, an O_NONBLOCK one answers EAGAIN (or the bytes it took); a partial frame at the end of a write is kept for the next |
| `read`, `lseek`, `mmap` | EBADF, ESPIPE, ENODEV |
| `close` (and `SYNC`) | **drains**: the last partial period is handed over and the call waits until the device has returned every period, then the stream is stopped and released, as Linux's close waits |
| the process ends with the device open (exit, a fault, a signal) | **no drain: the stream is stopped at once** and its queued periods dropped (the speaker's rule), one line names it |

`poll` is px24's; without it on trunk, `/dev/dsp` is not pollable here
(named in the report; ready for px24's `kernel/ready` to ask
`sound.writable`).

### P3. Formats, buffers, latency

- Formats: U8, S16_LE; 1 or 2 channels; the device's rates (P1).
  Refused or substituted: everything else, as the table says.
- Buffers: **8 periods of 4096 bytes** (32 KiB, 8 frames of
  `kernel/frames`, plus one frame of request headers and statuses),
  bounded and taken once at `start`; 21.3 ms a period and 170.7 ms in
  all at 48 kHz stereo S16. The stream starts when the second period is
  handed over (or at SYNC/close with fewer).
- Latency from a write to sound: **at most the queue ahead of it**
  (≤ 170.7 ms at 48 kHz stereo once full) plus QEMU's audio timer
  (10 ms); for the first write of a stream, the second period's 42.7 ms
  plus ≤ 10 ms. Measured as a test: GETODELAY after the writes, and the
  capture's first sample against the kernel's log of START.
- An underrun (the device returns the last period while the stream
  runs) is counted; predicted **audible as silence**: QEMU's voice stays
  open while the stream is started, so the WAV holds zeros for the gap
  (falsified if the capture closes the gap instead, as the speaker's
  does).
- Soak: an hour of sound in emulated time (TCG on kasumi, KVM on hasu)
  with the periods, the frames free and the heap's books flat; the
  driver takes no heap at all.

### P4. `play`'s mixed mode

- **When**: `/dev/dsp` opens → mixed; `play -s` forces the speaker,
  `play -m` demands the device (status 1 without it); with no device,
  the speaker path exactly as today (its tests do not move).
- **Synthesis in user space**, 48000 Hz, stereo S16, integer
  arithmetic only (wolf's `int`; a 32-bit phase accumulator per voice,
  frequency × 2^32 / 48000): waveforms **square** (the speaker's
  timbre) and **triangle** (softer: its harmonics fall as 1/n², the
  square's as 1/n); the tune's voices alternate between them unless the
  file says (`voice`); an envelope per note — 5 ms linear attack, 30 ms
  linear release inside the note's length — so no note clicks.
- **No clipping by construction**: each voice's peak is
  `0.75 × 32767 / N`, N the most notes the tune ever sounds at once
  (found when the file is checked), so the sum never exceeds 75% of
  full scale; a sample that would still exceed it is clamped and
  counted (predicted 0 in every tune).
- **Chords and voices**: px29's chord slot (its syntax, read from its
  PR; if it has not landed, written to its contract's wording and said
  so) sounds as simultaneous voices here, where the speaker
  arpeggiates it; a tune's separate `voice` lines (this lane's
  addition, agreed with px29's format) sound together.
- **CPU cost of mixing under TCG**: predicted **≤ 15% of real time**
  for four voices at 48 kHz on kasumi TCG (192,000 voice-samples a
  second at ~40 guest instructions each, TCG at a few hundred million a
  second), **≤ 1%** under KVM on hasu. `play -v` prints synthesis time
  against sound time. Falsified above 30% on TCG.

### P5. What moves

- New: `kernel/sound`, `boot/sound.S` (storage), `kernel/kmain_sound.lu`
  and a boot config if one is needed, `tests/mpx3-sound`, the CI job,
  `user/sound/*`, `tools/mksound`, `tools/linux-sound`.
- Changed: `kernel/virtio` (a second transport record: every caller
  names its device), `kernel/net` (passes its record), `kernel/interrupts`
  (the sound vector, beside net's on a shared line), `kernel/files`
  (`/dev/dsp`: a descriptor kind, open, write, ioctl, close, stat, the
  `/dev` listing), `kernel/user` (close and SYNC may wait), `kernel/sched`'s
  `end_with` (one call: the stream stops at its process's end),
  `kernel/wolf.pkg` (boot/sound.S), `kmain_console` (starts the device
  when present, so the shell image sounds), `user/play`, CI, the READMEs,
  CHANGELOG, `docs/SOURCES.md`.
- Existing tests: **none move**. Every kernel's bytes move (interrupts
  imports sound); `/dev`'s listing changes only when the device is
  attached, which no existing test does. `tests/mpx3-speaker` stays
  green unchanged.

## What was built

1. **The driver** (`kernel/sound`, `boot/sound.S`): discovery
   (`1af4:1059`), VERSION_1 alone, queues 0/1/2, `PCM_INFO`, the first
   output stream; eight 4096-byte periods (12 frames held in all, taken
   once); `SET_PARAMS`, `PREPARE`, `START` at two periods, `STOP` after a
   drain, `RELEASE` at the last close; INTx, the periods taken back in
   the interrupt; counters by cause (`sound:` summary line). Both tiers,
   BIOS and UEFI, TCG and KVM.
2. **`/dev/dsp`** (`kernel/files`, `kernel/user`): one opener, write
   (blocking and O_NONBLOCK), the OSS requests of §3's table, drain on
   the last close, silence at a process's end. `kernel/virtio` gained a
   transport record per device (`use_words`, `attach_at`).
3. **`play`'s mixed mode** (`user/play/mix.lu`, `kd.S`'s `play_dsp_*`):
   `-m`/`-s`/`-w`/`-c`; integer synthesis at 48 kHz, square and
   triangle, 5 ms attack, 30 ms release, peak 0.75 FS / N.
4. **Tests** (`tests/mpx3-sound`, S0-S7, the CI job), the witnesses
   (`user/sound/dsptone.c`, `dspprobe.c`, `tools/mksound`), the judge
   (`tools/wav-notes --pcm/--ramp/--gaps/--expect`), the Linux side
   (`tools/linux-sound`).

## 3. The prediction against the measurement

| predicted | measured |
|---|---|
| P1 virtio-sound-pci; VERSION_1 only; INTx | **right**: line 11 (vector 43) on every host and firmware; offered `0x0000010179000000` (bits 24, 27-30, 32, 40), taken `0x100000000` |
| P1 two streams, 0 OUTPUT, 1-2 channels, U8 and S16, rates 8000-192000 (not 5512, 384000) | **right but for the rates**: formats `0xe0078` (S8 U8 S16 U16 S32 U32 FLOAT), rates `0x3fff` — **all fourteen, 5512 and 384000 included** (so SPEED 1000 → 5512, 400000 → 384000) |
| P1 the CI runner's QEMU 8.2.2 has the device (unverified then) | **right**: run 38164251904's `-device help` lists `virtio-sound-pci`, and every scenario's device line and captures came from it |
| P2 OSS `/dev/dsp`; the table of answers | **right**, item by item (`user/sound/dspprobe.expect` against Linux's `notes/px30/linux-dspprobe-virtio.serial.log`: 9 lines differ, each a named difference of §3; `dsptone`'s lines equal Linux's byte for byte). **Wrong twice, fixed to Linux's**: OSS_GETVERSION — Linux answers 0x030810, not the header's 0x030802, PAX now answers Linux's; an O_NONBLOCK close — §3 had it drop the queue, Linux drains (close 1012 ms, `notes/px30/linux-close-underrun-exit.txt`), PAX now drains every last close |
| P3 8 × 4096 bytes; latency ≤ 170.7 ms after a full queue | **right**: the writes of a 1000 ms tone return 830 ms after the first, the close 170 ms later (every run, `tests/mpx3-sound` and `notes/px30/kasumi-pax-first-sound.serial.log`); Linux's virtio driver buffers about a second (writes 3 ms, close 1012 ms), its AC97 path 363 ms. First sound: START at the second period (42.7 ms of data queued) |
| P3 an underrun audible as silence in the WAV | **wrong about the WAV**: QEMU's `wav` backend writes nothing while the stream has no data (11.1.1 and Linux's own capture alike: `notes/px30/linux-close-underrun-exit.txt`, `gap` span 2000 ms for 2400 ms of run), so the gap is not in the file. Measured instead: the underrun counted (S4), the ramp exact across it (no stale or repeated frame), the program not hung (in step). QEMU 8.2.2 does write silence between streams (CI's tone capture: 1605 ms span for 1500 ms of sound) |
| P3 a process that ends mid-sound: silence at once | **right**: S5, both `_exit` and a fault: `stopped undrained … 8 periods dropped`, each tone 1340-1350 ms of the 1500 written (the dropped 170 ms never sound), the device opened and played at once by the next program |
| P3 soak flat | see §4 (hasu, KVM, an hour) |
| P4 the mixed mode, 48 kHz, square and triangle, envelope, 0.75/N | as built; 0 samples clamped in every tune (`cost` lines); chords judged by spectrum: px29's cadence 5/5 slots, each pitch of each chord present, onsets within 6 ms (`notes/px30/kasumi-chords-mixed.expect.txt`) |
| P4 CPU ≤ 15% of real time for four voices under TCG, ≤ 1% KVM | **right, by far**: 0.2-0.6% under TCG (kasumi, nomad-1, CI), four voices 0.4% (auferstehung-end 71 s in 350 ms); the clock is PAX's 10 ms tick, so a 10-20 ms figure is ±10 ms |
| P5 no existing test moves | the gauntlet and CI (§4) |
| P2 `poll` ready for px24 | not on trunk yet: `poll` is -ENOSYS (dspprobe's line); `sound.writable` is the seam |

Not predicted: QEMU returns a transmit buffer as soon as it has taken
the period, and stops at STOP with what it holds unplayed: without a
period of silence after the sound, the last 1.6 ms of a ramp was
missing (`79168f5`); every drain now queues 4096 bytes of silence
first (21 ms at 48 kHz stereo).

## 4. Evidence index

- **The device survey per host**: `-device help` on kasumi 11.1.1,
  hasu 11.1.0, nomad-1 11.1.1 (§2), CI 8.2.2 (run 38164251904's log,
  the `qemu … (apt)` step). Linux with each candidate:
  `notes/px30/linux-survey-*.serial.log` and `.pcm.txt`.
- **The straces**: `notes/px30/linux-strace-virtio.serial.log` (dsptone
  -q, -n, a 100000-byte chunk); aplay not straced (§2).
- **Linux's edges**: `notes/px30/linux-dspprobe-{virtio,AC97}.serial.log`;
  close, underrun and exit: `notes/px30/linux-close-underrun-exit.txt`.
- **Captures and verdicts**: kasumi TCG — the runs files and verdict
  lines of the gauntlet (`kasumi:~/lanes/px30/ev/g1/`) and
  `tests/mpx3-sound` (S0-S7); hasu KVM — three rounds of the kasumi
  images, 32 PASS, 0 FAIL, 0 SKIP each, 16 boots each, `accel: kvm` on
  all 16 (`hasu:~/lanes/px30/ev/hasu.log`); CI — the job's
  `pax-mpx3-sound-linux` artifact; nomad-1 —
  `notes/px30/nomad1-mixed.txt`, `nomad1-auferstehung-end.txt`.
- **The ramp, exact**: 96000 of 96000 frames on every leg, every host.
- **The WAVs for the maintainer**, nomad-1, QEMU 11.1.1, the `wav`
  backend at 48 kHz: `~/scratch/wolf/pax-sound/mixed/pax-mixed.wav`
  (`9d0a78d1…`: px29's cadence twice, then the mambo, mixed),
  `auferstehung-end.wav` (`d76ed116…`), the images `pax-mixed.iso`
  (`76a8d7e5…`) and `pax-auferstehung.iso` (`ba514432…`), and
  `HOW-TO-PLAY.txt` with the live CoreAudio commands. The chord images'
  `play` (`16700669…`) is this branch stacked on px29 at `96279d9`
  with `slot_pitches` reading px29's chords (below); this branch alone
  sounds each slot's one pitch until px29 lands.
- **The soak**: an hour of sound under KVM on hasu, both tiers at once,
  QEMU's `none` backend (`notes/px30/hasu-kvm-soak-{native,release}.serial.log`):
  691,200,000 bytes, 168,751 periods handed and 168,751 returned, 0
  underruns, 0 bad statuses, GETOPTR rising 11,520,000 bytes a minute
  to the end (`soak 3600 s written, GETOPTR bytes 691167232`), the
  writes 3,599,824 ms for 3,600 s of sound, the driver's frames 12 from
  start to end, the machine's free frames the same before and after
  (native 64033 → 64033, release 64143 → 64143). The driver takes no
  heap, so the heap's books cannot move; frames and periods are what
  could leak, and do not.
- **Planted breaks, red in CI** (each on its own run, then reverted):
  - the channels of every stereo frame swapped (`ea371df`): run
    **38167238290**, `mpx3-sound` red on S2 (440 Hz on the right) and
    S3/S4 (`swapped 96000`) on every leg
    (`notes/px30/ci-38167238290-plant-channels-swapped.txt`), about a
    minute into the job's boots; reverted in `6759f47`.
  - every sixteenth period never handed to the device (`558279d`, kept
    on branch `px30-plants`; `b154b31` after the rebase): run
    **38168844343**, red on S2, S3 (`break at frame 15360`), S4, S6 and
    S7 (`notes/px30/ci-38168844343-plant-period-dropped.txt`); reverted
    in `76a6f6b`.
  - not planted, seen: run **38164251904** red on S2 only: QEMU 8.2.2
    writes silence between streams (and U8 silence as ±255), so the
    tone's span was 1605 ms; S2 now measures loud time (5% of the peak),
    1502 ms on that capture (`notes/px30/ci-38164251904-tone.pcm.txt`).
- **The gauntlet** on kasumi (strict env, QEMU 11.1.1 TCG, wolf 0.2.27,
  the programs from `px13-ubuntu`) at `23d7df0`, before px24's rebase:
  `kasumi:~/lanes/px30/ev/g1/summary.txt`, every suite rc 0, 0 FAIL,
  0 SKIP as far as it had run at the report (named in the PR); the
  rebased head's `mpx3-sound` on kasumi native BIOS, S0-S7 PASS.
- **Boot counts**: kasumi TCG — the survey's 4 Linux boots and 9 more
  for straces and edges, about 30 single PAX boots while the driver was
  written, the test's 16 boots a full run (four full runs and three
  partial), the plants' 2; hasu KVM — 48 (three rounds of 16) and the 2
  hour-long soaks; nomad-1 TCG — 3 (two WAV renders, one through
  CoreAudio); CI — 16 a run.

## How the driver locks (px24's question)

It takes no lock word. Every entry runs with IF clear on the one CPU:
a system call from entry to its switch, the device's interrupt, the
close of every descriptor at a process's end. Nothing in it can be
preempted between a look and its change, and the interrupt cannot run
inside a system call's use of the rings. The one shared thing between
devices, `kernel/virtio`'s selected transport words, is set and put
back by each caller before it returns (`use_words`), interrupt
handlers included. On SMP this would need a lock word and is not
claimed.

## poll and non-blocking writes (px24 landed)

`dspprobe` asks `poll(POLLOUT)` before its first write (its strace on
Linux; `notes/px30/linux-strace-virtio.serial.log` is dsptone's, which
does not), so after the rebase onto px24 `/dev/dsp` answers it through
`kernel/files`' `node_poll`: POLLOUT while a period is free, the room
count moving with every period the device hands back, whose interrupt
wakes every waiter. `dspprobe.expect` now holds Linux's line for it.
O_NONBLOCK writes were already in (S6).

## Not verified

- aplay and ALSA's PCM device: not straced (no aplay in px13-ubuntu,
  none installed); the interface argument rests on `sound/asound.h`.
- Linux with intel-hda: no card within the script's second; not
  pursued, so the survey's "every device" has one hole.
- The absolute latency from a write to the Mac's speakers (CoreAudio's
  own buffer): only the queue's 170.7 ms and the WAV are measured.
- Silence during an underrun in what a listener hears: the WAV cannot
  show it (QEMU writes nothing then); the counter, the exact ramp across
  it and the program's timing are what is measured.
- `play`'s chords on this branch alone: they need px29's `Tune`; the
  chord captures and both WAVs were made from this branch stacked on
  px29 at `96279d9` with one function changed (`slot_pitches`,
  below). Not committed here; the rebase after px29 merges carries it.
- epoll on `/dev/dsp`: `node_poll` answers it as for poll, never run
  by a test here.
- The gauntlet at the final head: CI's run is the final head's evidence;
  kasumi's full gauntlet ran at `23d7df0` (before px24).

## 5. Done-when

Branch `px30`, PR #35 open, unmerged, five sections, commit shas as
bullets, a test checklist; CI at the head named in the PR;
`wolf/tools/lane-audit.sh pax px30 35` run from the org directory;
worktrees gone; kasumi, hasu and nomad-1 outputs pruned to the evidence
named above; no QEMU of this lane left running. Nothing closed.

**What the next sound lane inherits**

- The px29 seam: once px29 merges, `user/play/play.lu`'s
  `slot_pitches` reads a chord slot's pitches (`t.chord_n[i]`,
  `t.chords[t.chord_at[i] + k]`), the seven lines tested on the
  stacked branch; px29's four-pitch cap is px29's, the mixer takes any
  number (the organ's E-flat 2 and B-flat 5 of bar 51 could sound).
- Capture (the device's stream 1, INPUT, and queue 3; `O_RDONLY` is
  ENXIO today), a second stream (one opener today), a mixer device
  (`/dev/mixer`, volume: none; the device has no controls without
  VIRTIO_SND_F_CTLS, which QEMU 11.1 does not offer here), SETFRAGMENT
  honoured, `mmap` and SETTRIGGER, format conversion (S16_BE, S8, μ-law
  and rates by resampling, as Linux), the drain at a process's end if
  Linux's behaviour is wanted, the event queue's PERIOD_ELAPSED and
  XRUN (none sent by QEMU in any run here), MSI-X, SMP locking.
