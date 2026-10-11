# px29 — The chord (harmony on one bit, and the end of Mahler's Second)

Contract: px29's, `sprints/pax/29-the-chord/px29-the-chord.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-11). Branch `px29` in
pax, cut from pax trunk `5afb903` (px26 merged). §1–§3 are committed
before the first change to `play`, the tunes or the tests.

One deliverable: `play` takes chords (several pitches in one time
slot, sounded as a fast arpeggio on the speaker's one voice), and a
tune `auferstehung` is in the tree: the close of the finale of Mahler's
Symphony No. 2, from "Bereite dich" to the last bar, arranged for that
voice. User space only: `user/play`, `user/tunes`, the speaker test and
its session files; no kernel change.

## 1. Forbidden, absolutely

- **Sources and rights.** The symphony (composed 1888-1894, published
  by Hofmeister in 1897; Mahler died in 1911) and its text (the
  "Auferstehung" ode's first strophes after Klopstock, the rest
  Mahler's own) are in the public domain. The arrangement is made from
  a scan of the **first edition** of the full score, and from nothing
  else: no modern critical edition, no MIDI, MusicXML, kern or
  LilyPond encoding, no sound file of a performance. Notes from memory are never
  presented as transcription: every bar of the tune is checked against
  the scan, and a bar that could not be read is listed in the
  reduction note, not guessed. No other composer's music is added.
- None of the contract's forbidden words (its list of words for
  capturing a session on camera) appears anywhere in pax. ("Capture" here, as in px18, means QEMU's `wav` audio backend
  writing the speaker's samples to a file a test reads.)
- Clean-room (ruling #22): no kernel's, libc's, sound library's,
  tracker's or music engine's source is read or searched for. The
  arpeggio is written from its musical definition (a chord's notes
  sounded one after another, fast and repeating) and from the
  measurements in §2.
- No kernel change. If the 10 ms tick makes the arpeggio unusable, that
  is measured and reported (what resolution would be needed), not
  fixed here. px24's, px27's, px28's and px30's files are not touched;
  the change to `user/play/play.lu` is kept small and in its own
  commits so px30 can rebase over it.
- The existing tunes (`mambo`, `entertainer`, `scale`) play exactly as
  before, to the tick: the format only grows, and an old file parses
  to the same notes and lengths. `tests/mpx3-speaker`'s existing
  assertions (K0-K7) stay as they are and green; the only edit to an
  existing expected output is the `play` listing in
  `user/console/speaker.expect`, which gains a line for each new tune
  (its three old lines unchanged).
- No `rm` outside `~/lanes/px29/`; no scratch in `/tmp` on any host; no
  `git add -A`; nothing under `~/.claude`; no merge, no tag, no issue
  filed or closed; no trailer of any kind on a commit or the PR.
  Builds on kasumi in the `px13-ubuntu` container (`setsid`, a pid
  file, killed by that pid only), never on nomad-1; hasu runs QEMU
  under KVM (`nix-shell -p qemu`) and builds nothing; QEMU on nomad-1
  only for the WAV the maintainer listens to. Strict evidence
  (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, full output kept, SKIP counted.
  At most two CI runs of this lane at once; a chunk is pushed when it
  is whole.

## 2. Inputs, verified (2026-10-11)

| input | found |
|---|---|
| pax trunk | `5afb903` (px26 merged), as the contract says |
| the format | `user/play/play.lu`'s header and `notes/px18-the-speaker.md`: `title` (before the tempo), `tempo` (20-400 quarter notes a minute), `gap` (0-100 ms cut from each note's end, default 20), `<note> <length>` (C-B, `#`/`b`, octave 2-7), `r <length>`; lengths 1 2 4 8 16 32, `.` dots, `+` ties. Read as written: a `tempo` line is accepted anywhere, so a tempo change inside a tune already works (each later length uses the newest tempo); a tie across a slot exists only inside one length word |
| `/bin/play` | a static glibc wolf program (`tools/mkplay`, wolf 0.2.27); KIOCSOUND on the first of descriptors 0-2 that accepts it; an absolute schedule from `time_now_ms`; the speaker silenced at each note's end (`tone(fd, 0)`) and before every exit; `play` alone lists `/usr/share/tunes` with title and length |
| the kernel's time | the tick is 10.0002 ms; `clock_gettime` steps per tick; a sleep ends on the tick after its target; kernel/speaker logs every change (tick, on/off, count) in a 1024-entry ring read from the halted machine (`tests/mpx3-speaker` K2) |
| the capture | QEMU 11.1's `wav` backend writes samples only while the speaker sounds (px18), and renders about 3% short; `tools/wav-notes` cuts tones where the pitch changes by over 3% (four periods each side) and drops anything under 20 ms, so it cannot see a 20 ms arpeggio step (measured below: it reported 84 tones for 120 sub-notes and lost every A4 of the 20 ms probe) |
| `tests/mpx3-speaker` | K0-K7 as px18 and px21a left them; sessions `speaker` and `beep` on both tiers and firmwares, `tunes` (mambo, entertainer) native BIOS only; K1 compares each session to `user/console/*.expect` byte for byte, so the `play` listing is part of K1 |
| the shortest tone | **measured with trunk's `play`** (no change), probe image `img-t1` (kernel `da074b94…`, play `68a7866d…`): five tunes of 24 notes alternating A4 and C#5 with `gap 0`, at 18.75, 20, 25, 30 and 40 ms (`notes/px29/probe-tunes/`), typed at pelt, on kasumi (QEMU 11.1.1, TCG) and hasu (KVM). **The kernel's timeline is identical on both**: a 20 ms note is held exactly 2 ticks (23 of 24; the first 3), 30 ms 3 ticks, 40 ms 4 ticks; 25 ms alternates 2 and 3; 18.75 ms is ragged (2 or 3 ticks, and 3 of 24 notes held **0** ticks: two changes in one tick). So a step that is a whole number of ticks is exact, and anything else jitters by a tick. **The capture**, read period by period (`notes/px29/runs.py`: every rising crossing's period named for the nearest asked pitch within 3%): 117 of 120 sub-notes are seen in order on each host, with their pitches right; QEMU renders a 20 ms step as 15.9-21.7 ms (its own steps of about 1.9 ms), and 3 of 120 steps are merged into a neighbour. Files: `notes/px29/probe-t1-{kasumi,hasu}.{timeline,tones,runs,summary}`; the WAVs (`2706433…`, `85a89d9…`) stay on the hosts. A 10 ms step cannot be asked of trunk's `play` (its shortest length is 18.75 ms at tempo 400); it is measured after the change (§3 P1). nomad-1 is measured inside the session that makes the maintainer's WAV (its only QEMU use) |
| the score | Gustav Mahler, *II. Symphonie* (C minor), full score, Leipzig: Friedrich Hofmeister, c1897 (the first edition; 209 pages; caption title), the University of Toronto Music Library copy (call number M1001 .M21 no. 2 1897, barcode 31761057935728, lacks its title page), scanned by the Internet Archive in 2022 as `symphonieno200mahl` (https://archive.org/details/symphonieno200mahl): the PDF `symphonieno200mahl.pdf` (19,020,096 bytes, sha256 `cab6fa78…`) and the page images `symphonieno200mahl_jp2.zip` (images 0198-0211 = printed pages 196-209). The same edition is IMSLP's file #415748 (Hofmeister 1897, reprinted by Universal Edition, public domain); IMSLP's download needs a browser, so the Archive's scan is the one read. **Public domain**: published 1897, the composer died 1911 |
| where it falls | printed p. 196: after **43** *Langsamer. Misterioso.* ("Hör' auf zu beben!"), the tenors and basses enter *ff*, *Schneller.*, on "Be-rei-te" in the page's last two bars: the span starts there. Then p. 197 *Langsamer.* (Bereite dich zu leben!, chorus a cappella, then alto solo), **44** *Mit Aufschwung, aber nicht eilen* (alto solo, "O Schmerz! Du Alldurchdringer!"), p. 198 **45** (soprano and alto solo, "O Tod! Du Allbezwinger!", "Mit Flügeln, die ich mir errungen"), p. 199 *Vorwärts. Drängend. Nicht schleppen.* ("in heissem Liebesstreben werd' ich entschweben zum Licht"), p. 200 **46** *Langsam.* (chorus, "Mit Flügeln…"), p. 201 *Etwas drängend. Langsam steigern.*, p. 202 *Wieder etwas zurückhaltend.*, p. 203 **47** *Più mosso* ("Sterben werd' ich, um zu leben!"), *Ritenuto*, p. 204 **48** *Pesante* (full orchestra and organ, "Aufersteh'n, ja aufersteh'n wirst du, mein Herz, in einem Nu!"), *Etwas schneller*, p. 205 **49** *Wieder zurückhaltend. Rit.* ("zu Gott wird es dich tragen!"), p. 206 *Molto rit.*, *Etwas bewegter*, p. 207 (orchestra, bells, organ), p. 208 **50** *Più mosso*, *Noch schneller*, p. 209 **51** *Noch einmal so langsam*, *Mit höchster Kraftentfaltung*, the last bar |
| keys and forces | five flats at "Bereite dich" (D-flat/B-flat minor; chorus a cappella), a new signature at 44 and again at 46 (three flats, E-flat major, to the end); forces: chorus alone, then alto solo and orchestra, the two soloists, the full chorus from 46, the full orchestra with organ, ten horns and six trumpets (the off-stage players brought in) from 48, bells and tam-tams to the end. Bar count and time: counted page by page as the bars are read (the reduction note's bar table); the score gives no metronome marks, only words, so every tempo in the tune is the arranger's reading of them |
| hosts | kasumi: `/home` 96% (39 GB free), `px13-ubuntu`, QEMU 11.1.1 TCG, 16 cpus. hasu: KVM, 279 GB free. nomad-1: QEMU 11.1.1 (Homebrew), CoreAudio, no build |

## 3. Prediction (committed before the first change)

**P1. The rate.** A chord's pitches are sounded one after another,
each for one *step*, repeating until the slot ends; the default step
is **20 ms** (two ticks, 50 pitches a second), settable per tune.
20 ms reads as one chord, not a trill: a three-note chord cycles at
16.7 Hz and a four-note one at 12.5 Hz, above the roughly 10 Hz where
a repeating figure is heard as separate notes. A 30 ms step (11 Hz for
three notes) is a trill-like shimmer, 40 ms an audible figure. 10 ms
(one tick) is held exactly one tick by the kernel nearly always, but
the capture will show it badly: QEMU renders in steps of about 1.9 ms
and merged 3 of 120 of the 20 ms steps, so at 10 ms (4-5 periods of
A4) I predict over 10% of steps merged or lost in the capture. Steps
that are not a whole number of ticks jitter by a tick (measured: 25
ms), so the step is refused unless it is a multiple of 10 ms.
Falsified by a 20 ms step held other than 2 ticks in the kernel's
timeline, or the chord test's capture missing a pitch.

**P2. How many pitches.** Three reads as a chord; four still does at
20 ms; five (10 Hz cycle) begins to read as a figure, so a chord
carries **at most four** pitches and `play` refuses a fifth by name.

**P3. The order.** Low to high by default (`up`), settable per tune
(`up`, `down`, or as written). No silence between steps; the slot's
`gap` silence comes at its end, as for a note. A slot not a whole
number of cycles ends mid-cycle.

**P4. The tune.** The span is about 150 bars (printed pp. 196-209)
and, at tempi read from the words, about **6 minutes** (5-7). One voice
carries the sung line (chorus or soloist) and the first violins or
trumpets where no one sings; chords where the texture is a chorale or
a held tutti sonority. About **700 lines** of notes and chords (a
chord is one line), about **9-12 KB** of text. A cut of about a
minute ends with the last bars (from 51, or from 50 if 51 alone is
too short). Reduces well: the a cappella "Bereite dich" chorale (a
chord a beat), "Aufersteh'n" at 48 (chorus in octaves over held
chords), the closing E-flat chords. Reduces badly: the soloists' duet
at 45 (two lines in imitation; one is dropped), the harps and bells
(a one-bit speaker has no sustain or decay), every crescendo and the
*fff* (no dynamics), and the tremolo strings under the chorus.

**P5. Old files.** `mambo`, `entertainer` and `scale` produce the same
counts and microsecond lengths, so `tests/mpx3-speaker` K2 and K6 pass
unchanged: K2 and K6
read the kernel's timeline against the files to the tick, so they are
that check.

**P6. Sizes.** `play` grows by under 1% (12.2 MB, the runtime
dominates).

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: 20 ms a step reads as one chord; each step held exactly 2 ticks; 10 ms usable in the kernel but lossy in the capture | **right for 20 ms**: the chord study's 192 steps are held exactly 2 ticks in 191 (the slot's first step 3: play's first KIOCSOUND lands mid-tick), on both tiers, BIOS and UEFI, kasumi TCG (`tests/mpx3-speaker` K8, run c1) and nomad-1 TCG (the Mahler cut: 1015 of the last 1016 steps 2 ticks, `notes/px29/nomad1-m1.timeline`); the capture hears every pitch, 45-48 of 47 changes in order per chord. **10 ms is unusable, worse than predicted**: the capture of a 10 ms arpeggio (`notes/px29/probe-t2-kasumi.arp-check`) has 44 of 274 changes in order and steps of 17-30 ms median: a sleep ends on the tick after its target and the clock steps 10 ms, so a 10 ms step lands 0, 1 or 2 ticks late. A 10 ms step would need a clock and a sleep resolved to about 1 ms (a 1 kHz tick, or a one-shot timer for user sleeps): a kernel change, px30's or a ruling, not made here. `play` refuses nothing at 10 ms (it is still a multiple of the tick) but the default stays 20. 30 and 40 ms were held exactly 3 and 4 ticks (probe t1) |
| P2: at most four pitches | implemented as predicted (a fifth is refused by name, `/etc/refused/big-chord`, K1). Not measured by ear: no listener. The four-note chord of the study (12.5 Hz cycle) is judged by the capture as for three |
| P3: order up by default, settable; gap at the slot's end | right as built (`order up/down/written`); K8 judges the order from both the timeline (count for count) and the capture |
| P4: about 150 bars, 6 minutes, ~700 lines, 9-12 KB; a one-minute cut | **not met**: only the cut is delivered (`auferstehung-end`: 21 bars, 71.0 s, 37 slots, 1786 tones, 2149 bytes). The whole span was read from p. 196 to p. 202 for its sung lines but not checked bar by bar to the standard of §1, and pp. 203-208 (47, 49, 50) were not read; the maintainer's priority moved to the cut and its WAV. See the reduction note |
| P5: old tunes unchanged | **right**: K2 and K6 pass unchanged on the rebased head (the mambo's 160 and the Joplin's 154 onsets each within 19 ms, as px18 measured); the `play` listing's column widens to `auferstehung-end`'s name, so the three old lines' padding moves (titles and lengths unchanged) |
| P6: `play` grows under 1% | **wrong**: 12,208,424 → 12,911,592 bytes (+5.8%; px29's `play` `a668c286…` before rebase). Not investigated |
