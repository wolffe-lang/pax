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
