# px32 — The orchestra (independent parts, dynamics and timbres in `play -m`)

Contract: px32's, `sprints/pax/32-the-orchestra/px32-the-orchestra.md`
in wolffe-lang/wolf (planning trunk, read 2026-10-11). Branch `px32` in
pax, cut from `origin/px30` (`a85494b`). §1–§3 and the format
(`notes/px32-format.md`) are committed before the first change.

One deliverable: the tune format carries independent parts (each with
its own notes, rhythms, ties and rests), dynamics (per-note level and
hairpins) and articulation, and `play -m` renders them with instrument
timbres and envelopes through px30's sound device — at least 16
sounding voices, measured within the time budget under TCG on nomad-1
and kasumi.

## 1. Forbidden, absolutely

- Clean-room (ruling #22): no kernel's, libc's, synthesiser's,
  tracker's, sound library's or music engine's source (no SoundFont
  player, MIDI synthesiser or tracker). The synthesis is built from
  first principles and the textbook methods, named where used: additive
  synthesis (a waveform as a sum of sine partials), wavetable lookup
  with a phase accumulator, ADSR envelopes, a linear-congruential noise
  generator, one-pole and two-pole (resonator) filters, vowel formants
  as fixed spectral envelopes, the published partial series of church
  and tubular bells (hum, prime, tierce, quint, nominal), constant-power
  panning, a look-ahead peak limiter.
- No recorded samples, no sound fonts or sample sets: every timbre is
  computed in wolf at start-up from arithmetic.
- The existing formats keep working exactly: one-voice tunes and px29's
  chord slots, on the speaker and on `-m` (px30's `perform_mixed` path
  is not touched for them); `tests/mpx3-speaker` and px30's
  `tests/mpx3-sound` stay green unchanged.
- No word implying filming, recording, viewers or a demo anywhere in
  pax. No copyrighted music: the test pieces are this lane's own short
  studies.
- No kernel change unless measured necessary (stated first). px29's
  tune files are not touched (px33 owns `auferstehung*`).
- Builds on kasumi (fish: `bash -c`; `setsid` and a pid file; kill by
  pid; disk at 95%, pruned); nomad-1 for rehearsals only, audio to WAV,
  never coreaudio, no `setsid` there (`nohup … & disown`, pid recorded);
  no QEMU left running. No `rm` outside `~/lanes/px32/`; no `git add
  -A`; nothing under `~/.claude`; no merge; no attribution trailers; at
  most one CI run of this lane's at a time; strict evidence (#571).

## 2. Inputs, verified (2026-10-11, from origin)

| input | found |
|---|---|
| the base | `origin/px30` `a85494b` is **not stacked on px29** (the contract says it is): `git merge-base --is-ancestor origin/px29 origin/px30` is false; their base is trunk `2a0da26`. px30's `play` has no chord parser (`slot_pitches` gives one pitch a slot; its note names the seam for px29). px31 met the same and merged the two privately (`~/lanes/px31/pax`, `d339bff`, `50d1b19`: px29 merged, `slot_pitches` reading px29's chord slots). **This lane merges `origin/px29` (`e168668`) into `px32` as its first change** so that px29's chord slots exist to keep working, with px31's eight-line seam; the merge is a commit of its own, named, and is undone by the rebase when px29 and px30 land. |
| px30's mixed mode | `user/play/mix.lu`: 48000 Hz, stereo S16_LE through kd.S's `play_dsp_frame` (one call a frame, 4096-byte buffer to `write(2)`); voices are slot pitches from a 32-bit phase accumulator; square and triangle; 5 ms attack, 30 ms release, linear; peak 0.75 × 32767 / N, N the most pitches in any slot, so it never clips; left = right. Its time is the frame count: sample-accurate, no sleep (the 10 ms tick only paces `time_now_ms`). |
| px30's cost under TCG | its note: 0.2–0.6% of real time (kasumi, nomad-1, CI), four voices 0.4% (`auferstehung-end`, 71 s in 350 ms); the clock is PAX's 10 ms tick. |
| px30's device | OSS `/dev/dsp`, virtio-sound; 8 periods of 4096 bytes (170.7 ms at 48 kHz stereo S16) taken once; a blocking write waits while all 8 are at the device; close drains. QEMU's `wav` backend writes nothing while the stream has no data. |
| px29's format | `title`, `tempo` (anywhere), `gap`, `<note> <length>`, `r <length>`, chords `C4,E4,G4 2` (2-4 pitches), `arp`, `order`, lengths 1-32 with `.`, `t` and `+`; dynamics refused by name (`user/play/refused/dynamic`). A file with no `part` line keeps meaning exactly this. |
| tests | `tests/mpx3-sound` S7 judges `play -m scale` by `tools/wav-notes --expect` (one pitch at a time); `tests/mpx3-speaker` (px29) judges the arpeggio on the speaker. px32 adds its own test and tool and edits neither. `play` is a static Linux x86-64 program, so the parser and the synthesis can also be run on the CI host directly (no QEMU), writing the PCM to a file. |
| memory per tune | the Mahler span (≈ 230 s, 8-16 parts, a few thousand events): a few hundred KiB of event tables; the wavetables are made lazily per timbre used (§3). |

## 3. Prediction (committed before the first change)

**P1. The format** is `notes/px32-format.md`, complete as written there
(parts, bars, events, ties, rests, tuplets, tempo, rit/accel, fermatas,
`ppp`–`fff`, `sfz`, `fp`, hairpins, articulations, 17 timbre names over
the eight the contract asks for). It is read by a new parser
(`user/play/parts.lu`) chosen by the presence of a `part` line; the old
parser is not changed except to hand such a file over. Old files parse
and sound identically: the same `playing` line, the same frames.

**P2. The synthesis** (`user/play/orch.lu`), all integer arithmetic as
px30's, no floating point:
- **Wavetables** (2048 entries, one cycle) made by additive synthesis
  from a sine table, per timbre, per octave band (so no partial passes
  20 kHz: band-limited), in two brightnesses (soft and bright) for the
  timbres whose colour follows their level; a voice reads both and
  mixes them by its level. Inharmonic timbres (bells, timpani) are a
  few sine partials of their own, each with its own decay; tam-tam,
  cymbal and drum are filtered noise (and, for the tam-tam, a few
  low partials).
- **Envelopes**: per-timbre attack, decay, sustain, release, evaluated
  once a block of 64 frames and ramped per frame; hairpins and dynamics
  as a level per part per block, interpolated in steps so a held note
  swells; accents and sfz as an attack boost; tremolo as amplitude
  re-articulation at ~13 Hz with jitter (rolls ~16 Hz); vibrato as a
  phase-increment wobble, 5-6 Hz.
- **Stereo** by constant-power pan per part; **a look-ahead limiter**
  over one 64-frame block, so the gain falls before a loud block
  arrives and nothing is clamped.
- Predicted cost per voice-sample: about 3× px30's (two table reads,
  the brightness mix, a ramped gain, two channels).

**P3. Performance.** 16 voices at 48 kHz in real time under TCG:
predicted **≤ 15% of real time on kasumi and ≤ 30% on nomad-1** (px30's
four voices at 0.4% × 4 voices × 3 per voice-sample ≈ 5%, rounded up
for the per-block work and the percussion's extra partials); start-up
(the wavetables) ≤ 2 s under TCG. So the choice is **real time,
streamed** (not rendered ahead). Falsified if 16 voices pass 50% of
real time on either host, and then the fallback is render-ahead with the
wait stated. A 230 s 16-part tune parses in under 1 s under TCG and
holds under 2 MiB of tables.

**P4. The study** (`user/tunes/orchestra`, ≈ 30 s, this lane's own
music): a brass chorale (horns, trumpets, trombones) over string
tremolo, woodwind lines, organ with pedal, choir, a crescendo pp → ff,
bells, timpani and tam-tam at the climax; at least 16 voices at its
peak.

**P5. Tests** (`tests/mpx3-orchestra`, a new CI job; px30's and px29's
tests unchanged): on the CI host, the parser's refusals and acceptances
and the synthesis written to a file; under QEMU (kmain_console with the
sound device, both tiers, BIOS and UEFI) `play -m` of the study and
of test tunes captured and judged by a new tool (`tools/orch-check`,
Goertzel power per pitch per window): each part's pitch present where
written and absent where it rests, onsets per part independent (two
parts with different rhythms each found at their own onsets within
10 ms), level rising monotonically through a hairpin (≥ 12 dB over pp →
ff), no clamping. **Planted break**: a hairpin that does not change the
level, red in CI by run id, then reverted.

**What moves**: nothing in the kernel; `user/play` (two new files, the
parser's hand-over, the options), `user/tunes` (the study only),
`tests/`, `tools/`, CI (one job).
