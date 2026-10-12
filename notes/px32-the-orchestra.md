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
| the base | (Superseded at the rebase, 2026-10-11: px29 and px30 merged to trunk `7c2c70e`, px32 rebased onto it, the merge and the seam commit dropped; trunk's `d32fcb2` is the same seam.) `origin/px30` `a85494b` is **not stacked on px29** (the contract says it is): `git merge-base --is-ancestor origin/px29 origin/px30` is false; their base is trunk `2a0da26`. px30's `play` has no chord parser (`slot_pitches` gives one pitch a slot; its note names the seam for px29). px31 met the same and merged the two privately (`~/lanes/px31/pax`, `d339bff`, `50d1b19`: px29 merged, `slot_pitches` reading px29's chord slots). **This lane merges `origin/px29` (`e168668`) into `px32` as its first change** so that px29's chord slots exist to keep working, with px31's eight-line seam; the merge is a commit of its own, named, and is undone by the rebase when px29 and px30 land. |
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

**P4. The study** (`user/scores/orchestra`, ≈ 30 s, this lane's own
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

## What was built

- **The format** (`notes/px32-format.md`, the spec px33 writes to):
  parts with a timbre, an optional level (mf), `pan` and `gain`; bars
  numbered one by one, each part filling each bar exactly; rests,
  ties across bars, chords in a part, dots, triplets and `xN` tuplets;
  `tempo` (with a beat unit), `rit`/`accel` over bars, fermatas at a
  bar's end or `at` a point; `ppp`-`fff`, `sfz`, `fp`, hairpins (`<`
  `>` `cresc` `dim`, ended by a dynamic or `!`); staccato, marcato,
  accent, tenuto, slur, tremolo, tie. Read by `user/play/parts.lu`
  when a file has a `part` line; every other file goes to px18/px29's
  parser untouched. 32 refusals, each by its own message and line.
- **The synthesis** (`user/play/orch.lu`, integers only): a sine table
  from a rotated fixed-point vector; additive wavetables per timbre, per
  octave band (no partial over 19 kHz), soft and bright, RMS-equal, read
  by a 32-bit phase accumulator and mixed by the level; struck partials
  (timpani modes, the bell's hum/prime/tierce/quint/nominal, tam-tam
  modes with a bloom, bass drum) with their own decays; LCG noise
  through one-pole filters (cymbal, tam-tam crash, thumps); ADSR per
  timbre by 64-frame blocks ramped per frame; vibrato; two detuned
  oscillators for strings and choir; bowed tremolo and rolls; accents,
  sfz and fp as an attack boost; constant-power pan; part `gain`; a
  look-ahead limiter that only turns peaks down; 64 voices, the
  quietest releasing one cut past that (counted); a drum or bell struck
  again rings in place. 17 timbre names (§5 of the spec).
- **`play`**: `-m` (and the default) plays a part-format tune through
  `/dev/dsp`; `-c` its cost; `-o` its frames to standard output (for
  the host tests); `-s` refuses it by name. The tune is parsed once.
- **The study** `user/scores/orchestra` (original, 31 s written, 39 s
  with the ring): 17 parts, strings' tremolo, a woodwind line, the brass
  chorale, choir, organ with pedal, pp to ff over bars 5-6, timpani,
  bells, tam-tam and cymbal at the climax; **45 voices at its peak**.
- **Tests**: `tests/mpx3-orchestra` (CI job `mpx3-orchestra`) and
  `tools/orch-check` (Goertzel power per pitch per window: present,
  absent, onset, rising, falling, flat, louder, ratio, brighter, pan,
  dip, vibrato, modulated, rms, noclip); test tunes and specs in
  `user/play/parts-test/` (checks, marks, timbres, balance, voices, the
  timing cases, the refusals, the old formats' cost lines);
  `tools/orch-stress` (230 s, 16 parts, 42 voices).
- **No kernel change.** px30's `mix.lu` and the old `perform_mixed`
  path are untouched; `play.lu` gained the hand-over and the options.

## 3. The prediction against the measurement

| prediction | measured |
|---|---|
| P1 the format as specified, old files unchanged | **right**, two additions after px33 started (both only grow it: the part's level optional with mf, `gain`), and the level step widened from 4 to 5 dB after the maintainer heard px33's preview. Old files: `play -c` of scale, mambo, entertainer and chords gives px29+px30's own lines (`parts-test/old-cost.expect`, from px31's px29+px30 binary); px30's and px29's tests unchanged |
| P2 integer wavetables, struck partials, noise, envelopes, pan, limiter | **as built**; two things learned: tables normalised by peak lost ~7 dB at brightness (RMS-normalised since `2e7d985`), and the second oscillator's detune was 0.7 cents, not 7 (fixed there) |
| P3 16 voices ≤ 15% of real time on kasumi TCG, ≤ 30% on nomad-1; real time, streamed | **right, by far**: the study (17 parts, **45 voices**) 5.6-7.0% under TCG on kasumi (CI-identical images, both tiers), 5.7% on nomad-1; the 230 s 16-part stress (**42 voices**) **10.0% on kasumi, 9.4% on nomad-1**; set-up (all wavetables) 50-80 ms; a 230 s tune parses in 20 ms. Streamed in real time: 0 underruns (px33's preview under 256 MiB: 4735 periods handed, 4735 returned, 0 underruns) |
| P3 a 230 s tune under 2 MiB of tables | **right after a fix**: at `69505c1` `amp_of` built a list literal per voice per block, so memory grew with length × voices (the 230 s stress, and px33's 101 s preview at about 70 s, ran QEMU's 256 MiB out of frames). Fixed in `dfd0754`; the parse doubled until `f34d13b`. Now play holds **352-353 frames (1.4 MiB)** at the end of the 230 s stress and of px33's preview in 256 MiB; host RSS of a 200 s two-part tune equals a 100 s one's (2.8 vs 2.9 MB) |
| P4 the study, 16+ voices | **right**: 45 |
| P5 tests, planted break red | **right**: the plant (`07d6b64`, before the rebase `8639bfc`: a hairpin holds its first level) red in run **38184258230** (job 114603105214): O4 host and every O5 capture, `rising 466.16 ... rises -0.8 dB`, `falling 659.26 ... falls 0.2 dB`, the study's crescendo `rises -0.0 dB`; reverted in `d30bf97`. The same run was also red for a real fault, found by it: `old-cost.expect` had never been committed (`3a8500e`) |

## 4. Evidence index

- **Render timings** (in the guest, `play -c`, TCG): the study
  1867648 frames, 45 voices: kasumi 2200 ms (5.6%, native BIOS) and
  2760 ms (7.0%, release UEFI) in run r5; nomad-1 2230 ms (5.7%). The
  230 s stress, 42 voices: kasumi 23730 ms (10.0%), nomad-1 22390 ms
  (9.4%). The balance tune (23 parts, 51 voices) 2.2-2.3%. Native
  (kasumi host): the study 0.4-0.7%.
- **Capture verdicts**, kasumi r5 (`~/lanes/px32/o-r5.out`, `.runs`;
  QEMU 11.1.1 TCG, tree at `9822dbb`, play `1796e149…`): every O1-O6
  PASS: 32 refusals; old formats; 6 written lengths within 5 ms (rit
  5545 ms); host checks 22/22, marks 36/36, timbres 25/25, balance
  14/14, study 11/11, 72 voices asked → 64 sound, 8 stolen, 0 clamped;
  captures: checks on native/release × BIOS/UEFI 22/22 each; marks,
  timbres, balance and the study on native BIOS and release UEFI
  36/36, 25/25, 14/14, 11/11; long (230 s, 16 parts) in 256 MiB:
  60898 → 60545 frames free (353 held), 0 clamped.
- **Measured levels** (r5's host verdicts, `9822dbb`; the captures
  pass the same specs): a part with no level equals one marked mf (0.0
  dB) and ff is 10.0 dB over it (two steps); pp held over three bars
  within 0.2 dB, ff over two within 0.2 dB, 25.2 dB apart; pp → ff
  over two bars +20.3 dB, ff → pp -20.6 dB; `gain -12` 12.1 dB down; a
  16-part tutti (29 voices) at pp **-37.2 dBFS**, at ff -12.0 dBFS (25.2
  dB apart). marks.spec: staccato 55.7 dB down at three quarters of its
  length; unmarked repeats dip 11.2 dB, tenuto 0.5 dB, a tie 0.0 dB; a
  slur wavers 0.23 dB against 2.26 for unmarked repeats; accent +6.1 dB,
  sfz +16.1, fp +12.5; pan 99.2 and -105.6 dB; the pedal's 16' present;
  the horn's fourth harmonic 7.2 dB stronger at ff than at p and the
  note 19.5 dB louder; the voice's vibrato spans 1.32%, the organ's
  0.16% (none, the estimate's floor); bowed tremolo wavers 2.11 dB,
  plain bowing 0.72; rit onsets within 8 ms of the integral.
- **px33's preview** (`~/lanes/px33/work/auferstehung-preview`, 24
  parts, 101 s) in the guest under 256 MiB with the final play: played
  whole, 32 voices, 0 stolen, 0 clamped, 0 underruns, 353 frames held
  (`kasumi:~/lanes/px32/t/pv/`).
- **The study's WAV**: `~/scratch/wolf/pax-sound/orchestra/orchestra-study.wav`
  (`e644a3dc…`, from `pax-orchestra-study.iso` `27881caf…`, nomad-1,
  QEMU 11.1.1 TCG, judged 11/11 by orchestra.spec). To hear it live:

  ```
  qemu-system-x86_64 -machine q35 -cpu max -m 256M -accel tcg -nographic \
    -drive file=$HOME/scratch/wolf/pax-sound/orchestra/pax-orchestra-study.iso,format=raw,media=cdrom,readonly=on -boot d \
    -audiodev coreaudio,id=snd0 -device virtio-sound-pci,audiodev=snd0
  ```

  (the image runs `play -c orchestra` then `play -m orchestra`, then
  halts; Ctrl-A x ends QEMU).
- **Planted break**: run 38184258230 (above).
- **CI green at head**: the PR's run (below).

## Not verified

- Listening: no person has heard these timbres; every judgement is
  spectral (orch-check) or by level. Whether the brass, the choir's
  "ah" or the tam-tam sound like their instruments is the maintainer's
  ear's call.
- KVM (hasu): not run; TCG only (kasumi, nomad-1, the CI runner).
- The CI runner's QEMU 8.2: the captures there are judged by the same
  specs in the PR run; its cost line is recorded, not compared.
- px33's full `auferstehung` (not yet written in this format): only its
  preview, its `span-partial` and `close/t.txt` drafts were played
  (parse, cost, and the preview in the guest).
- Memory is bounded by the score's size, not its length: about 0.8 KiB
  of parse per note stays for the run (a 15,000-note score would hold
  about 12 MiB); not reduced further.

## 5. Done-when

Branch `px32`, rebased on trunk `7c2c70e`; PR, CI and the audit below.
