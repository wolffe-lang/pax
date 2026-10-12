# px33 — Auferstehung: the close of Mahler's Second in parts

Lane px33 re-arranges the finale of Gustav Mahler's Symphony No. 2 from
"Bereite dich" to the last bar for `play -m`'s part format (px32,
`notes/px32-format.md` at `899303d`): every bar read from the score, the
orchestra reduced to independent parts, the soloists and the chorus as
lines, dynamics, hairpins, tempo words and fermatas carried.

## 1. Sources and rights

**The search for a machine-readable score (2026-10-11).** Each
candidate, with its licence as the source states it:

| candidate | what is there | licence as stated | used |
|---|---|---|---|
| IMSLP, `Symphony_No.2_(Mahler,_Gustav)` | PDF scans and recordings only; no MIDI, MusicXML, MEI, kern, LilyPond or notation-program file is listed on the work page | the 1897 Hofmeister full score: "Public Domain" | the scan's edition, yes (below); no encoding exists there |
| Mutopia Project (composer search `MahlerG`) | "Sorry, no matches were found" | n/a | no |
| CPDL (`Gustav_Mahler`, and its search) | the server refused the lane's requests (HTTP 403); nothing could be read | not read | no |
| OpenScore (MuseScore's public-domain projects), GitHub code search | no encoding of this symphony found; GitHub hits for "Auferstehn" are folk songs and texts | n/a | no |
| Sao Mai Music Library (MusicXML for blind readers) | a catalogue that "mostly" carries public-domain or sharable files; no licence stated for a Mahler 2 finale encoding the lane could find | not stated | no |

No candidate is public domain or CC0 with a stated licence, so none is
used. **The source is the printed first edition**: Gustav Mahler,
*Symphonie No. 2*, full score, Leipzig: Friedrich Hofmeister, 1897
(University of Toronto Faculty of Music Library, call number
M1001 .M21 no. 2 1897), scanned by the Internet Archive as
`symphonieno200mahl`; printed pages 196-209 = the item's page images
0198-0211 (`symphonieno200mahl_jp2.zip`), fetched by this lane one by
one, sha256 in `notes/px33/source-jp2.sha256`. Public domain: published
1897, the composer died in 1911; IMSLP lists this edition as "Public
Domain". Nothing else is read: no modern critical edition, no
encoding, no recording, no notes from memory. A bar or a part that
cannot be read is listed in the check list as such, never guessed.

Clean-room as px32: the lane writes tune files only; no code.

## 2. Inputs, verified

- px29's `notes/px29/reduction.md` (pax branch `px29`): read from the
  same edition; carried the sopranos at 48 bars 1-8 and the organ at 51
  as an arpeggio, cut 48 bar 9 to 50 and p. 202-203 as unread. Its
  doubts are re-read here, not inherited. One difference already: px29
  counts "Be-rei-te" as 43 bars 6-7; this lane counts 43 from the bar
  after the fermata bar on p. 196 (the tenors' "Hör' auf zu"), which
  puts the "Be-" up-beat on beat 4 of 43 bar 5 and "rei-te" in 43 bar 6.
- The span, from the overview of every page (detail comes with the
  transcription):

| page | figures, tempo words | meter, key | forces |
|---|---|---|---|
| 196 | 43 b5 (beat 4) - b6, Schneller | 4/4, 5 flats | chorus T, B (ff); orchestra silent |
| 197 | 43 b7-b11, Langsamer; 44 Mit Aufschwung, aber nicht eilen (half = the last quarter) | 4/4, then 2/2 and 4 flats at 44 | alto solo, chorus S/A, T, B; then fl, cl, 4 hn, 3 pos, harps, strings (tremolo), alto solo |
| 198 | 44 cont., 45 | 2/2, 4 flats | soprano solo, alto solo, fg, hn, pos, harp, strings (pizz, tremolo) |
| 199 | Vorwärts, Drängend, Nicht schleppen | 2/2, then 3 flats | soloists, fg, hn, pos, harp, strings; chorus basses' "Mit" |
| 200 | 46 Langsam (the quarter = the last half), Halbe taktiren | 3/2, 3 flats | fl, cl, hn, two harps, strings; chorus A, T1, T2, B in canon |
| 201 | Etwas drängend, Langsam steigern | (to read) | ww, hn, timp, harps, strings, chorus S A T1 T2 B |
| 202 | Wieder etwas zurückhaltend, Luftpause | (to read) | full: 4 fl, 4 ob, 4 cl, 4 fg, 10 hn, tpt, pos, tuba, timp, bass drum, harps, strings, chorus S A T1 T2 B1 B2 |
| 203 | 47 Più mosso ("Sterben werd' ich"), Ritenuto | (to read), 3 flats | full brass, cymbals, 2 timp, strings tremolo, chorus SATB |
| 204 | 48 Pesante (the quarter = the earlier half), "Aufersteh'n", Etwas schneller | 4/4, 3 flats | full, organ (volles Werk), soloists with the chorus |
| 205 | 49 Wieder zurückhaltend, Rit. | 4/4 | full, triangle, cymbals, bass drum, organ |
| 206 | Molto rit., Etwas bewegter (langsame Halbe taktiren) | (to read) | full, three deep bells, tam-tam (deep), organ, two harps |
| 207 | (cont.) | | bells, tam-tam, harps, organ (halbes Werk), strings |
| 208 | 50 Più mosso, Noch schneller (Ganze Takte schlagen) | then alla breve | organ pedal alone, bells, timp, harps; then full brass and strings |
| 209 | 51 Noch einmal so langsam (the half = the last whole), Mit höchster Kraftentfaltung, scharf abreissen | alla breve | full orchestra, organ (volles Werk), bells, tam-tam high and deep, two timp; no chorus |

- The score has **no metronome marks** in the span; it gives words and
  equivalences (44: half = the last quarter; 46: quarter = the last
  half; 48: quarter = the earlier half; 51: half = the last whole). The
  tempi are the lane's reading of those, anchored at one choice
  (43 Langsamer, quarter = 48), and every other tempo follows from the
  printed equivalences where there is one; where there is only a word
  (Vorwärts, Drängend, Più mosso, Etwas schneller, Noch schneller) the
  step is a stated choice of about 10-15%.

## 3. Prediction (committed before the first bar is converted)

**The part plan.** Part format: at most 24 parts, chords of up to 6
notes in a part, 32 voices at once (px32 §1, §3, §6). 24 parts:

| part | timbre | carries | dropped / folded |
|---|---|---|---|
| `sop-solo` | voice | soprano solo (45 to 46 bar 1; with the chorus sopranos from 48, then it is silent there and `ch-s` carries the line) | |
| `alt-solo` | voice | alto solo (43 to 46 bar 1) | its doubling of the chorus at 48 (in `ch-a`) |
| `ch-s` | choir | chorus sopranos (S/A unison at 43 as one line) | divisi as a chord of at most 2 |
| `ch-a` | choir | chorus altos | as above |
| `ch-t1`, `ch-t2` | choir | tenors 1 and 2 as two lines where the score writes two staves or two independent lines (46, 202); in unison or chordal writing, the chord in `ch-t1` | |
| `ch-b1`, `ch-b2` | choir | basses likewise | |
| `fl` | flute | flutes and piccolos, the top line (2 notes at most) | the third and fourth flutes when they double |
| `ob` | oboe | oboes, and the clarinets where they double them | |
| `cl` | clarinet | clarinets in B and E-flat | |
| `fg` | woodwind | bassoons and contrabassoon | |
| `hn` | horn | ten horns: the two lines, or the chord (3 notes at most) | doublings |
| `tp` | trumpet | six trumpets, chord of at most 3 | doublings |
| `tb` | trombone | four trombones and tuba, chord of at most 3 | doublings |
| `ti` | timpani | both pairs of timpani, rolls as `*` | |
| `gl` | bells | the bells (Glocken; "3 tiefe Glocken von unbestimmtem Klang") at the written pitches | the indefinite pitch: written pitches are used |
| `tt` | tamtam | tam-tam deep and high (one part: their notes are written separately; the deep one is carried, the high one where it is alone) | |
| `cy` | cymbal | cymbals; the bass drum's roll (Gr. Tr.) folded in at 47-49 | the triangle (not carried, named in the check list) |
| `hp` | harp | the two harps: the chords, and the arpeggios as written runs | the second harp where both play (the busier one kept) |
| `org` | organ | organ manuals, chord of at most 4 | |
| `ped` | pedal | organ pedal | |
| `vn` | strings | first violins, and the second violins as a second note of the chord | |
| `va` | strings | violas (with tremolo) | |
| `vc` | strings | cellos (with tremolo, pizzicato as `'`) | |
| `cb` | strings | double basses | |

So 8 vocal parts and 16 orchestral (12 instrument families once the
organ's pedal, and the percussion's three timbres, are counted with
their instrument). That is above the brief's "about 8-12" orchestra
parts: the format gives one timbre per part, and the climax needs
timpani, bells, tam-tam and cymbals as four different sounds, the
organ needs its pedal, and the strings need four registers to carry
the tremolo chord under the chorus. The arrangement's voice budget is
kept under 32 by chord caps: the densest bars (48, 51) are planned at
26-30 voices; `play -c` says the measured `voices at most` and
`stolen`, which is predicted 0.

**Bars expected doubtful**: 202-203 (the densest pages before 48:
small heads in the wind divisi and the chorus's split staves), the
harps' runs at 46 and 206-207 (ten- and six-note groups printed small),
the bells' pitches (written for bells of no fixed pitch), and 51's
last bar (px29 read the strings there as inconsistent with the E-flat
close; re-read). Expected: under 10 bars with a doubtful pitch in a
carried part, none unreadable.

**The excerpt**: `auferstehung-close` from 47 "Sterben werd' ich, um zu
leben" to the last bar, continuous. "O glaube" (the alto's "O glaube,
mein Herz") comes before "Bereite dich", outside the span this lane
reads, so the choice is "Sterben werd' ich": it begins the last climb
(Più mosso, the chorus ff), runs through 48 "Aufersteh'n", the bells
and tam-tam, and 51 to the end. Predicted length about 190 s at the
tempi below (longer than the brief's "about 2 min"; the score has no
cut point inside it that does not cut a phrase).

**Tempi** (quarter or half per minute, the beat in brackets): 43
Schneller q 60, Langsamer q 48; 44 h 48 (= the last quarter); Vorwärts
h 54, Drängend h 60, Nicht schleppen h 52; 46 q 52 (= the last half),
Halbe taktiren; Etwas drängend q 58; Wieder etwas zurückhaltend q 50;
47 Più mosso q 66 (or h 33 if alla breve, to read); 48 Pesante q 48
(= the half at 44); Etwas schneller q 56; 49 Wieder zurückhaltend, rit
to q 44; Etwas bewegter h 36; 50 Più mosso h 42; Noch schneller whole
40 (ganze Takte); 51 h 40 (= the last whole).

**The full span's length**: about 420 s (7 min), 140 bars ± 10.
`auferstehung-close`: about 190 s. px29's `auferstehung` (228 s) cut
about 50 bars.

## 4. Evidence index

**The close, joined (px33-c).** The readers' pages (px33-r1b p201-202,
r2b p203-204, r3 p205-206, r4b p207-209) are joined in
`notes/px33/transcription/joined-46.11-51.13.txt` (46.11 to 51.13,
bars 49-131, the opening's numbering continued); its head names every
change from the page files. `user/tunes/auferstehung-close` is its
bars 63-131 (47.1 to 51.13, 69 bars, no cut), renumbered from 1, with a
header naming the work, the source, what is not carried and what is
doubtful. It replaces px29's `auferstehung-end`; px29's `auferstehung`
stays until the opening (43.5-46.10, being re-read) is joined.

- **The excerpt starts at 47 ("Sterben werd' ich")**, not "O glaube":
  the readers' pages begin at 46.11, and 47.1 to the end is the
  climb to 48 and the whole close unbroken.
- **Checks**: `notes/px33/tools/check.py` on both files: `errors 0`.
  px32's `play -c` (built from px32 27a8383, with 7b29505's 128 voices,
  on kasumi): the joined file 317940 ms of sound (309939 written), 24
  parts, 95 voices at most, 0 stolen, 0 clamped, 0 notes dropped,
  status 0; the close 254624 ms (246623 written), 95 voices at most, 0
  stolen, 0 clamped, 0 notes dropped, status 0. The same figures from
  px32 c3720b5 (after df224e7: marks on a tie's last event cut only
  that event). Its `play -o` frames for the close equal 27a8383's except
  at 36.3-37.8 s and 171.0-173.8 s (largest sample difference 3339):
  the two ties that end on a marcato, the trumpets into 47.12 and the
  cellos and basses into 49.11, now hold their whole length.
- **Length**: play 246.6 s written; from the bar lines alone (`notes/px33/tools/length.py`: meter,
  tempo, rit, integrated) 248.1 s: 0.6% apart, the difference in the
  ritardandi. The prediction (about 190 s) was short: 48 Pesante at
  q 40 is 6 s a bar.
- **The image** (`pax-mahler-orchestra-6.iso`, sha256 f079d7be...; play from px32 c3720b5)
  under TCG with QEMU's wav backend, `-m 256M`, through pelt:
  `play -m auferstehung-close`: 95 voices at most, 0 stolen, 0
  clamped, 0 notes dropped, 12939 blocks limited; the device 11937
  periods, 0 underruns, 0 dropped. 254.6 s of sound, as play's figure.
- **Levels** (tools/orch-check --env, 5 s windows, dBFS, time from the
  first sound) against the score's marks:

  | s | dB | bars (fig.) | marked |
  |---|---|---|---|
  | 0-20 | -17.5 -17.6 -16.1 -16.4 | 47.1-6 | chorus ff, 47.5 ff brass, cymbal |
  | 20-25 | -20.0 | 47.7-8 | chorus rests; horns ff, trumpets mf |
  | 25-45 | -16.8 -16.1 -15.7 -17.8 | 47.9-14 | ff, 47.13 fff then > f |
  | 45-50 | -21.2 | 47.15-16 | the chorus off at 47.16, < |
  | 50-60 | -12.4 -11.3 | 48.1-2 | fff "Aufersteh'n": 9 dB over 45-50 |
  | 60-105 | -14.7 to -12.1 | 48.2-9 | fff chorus, ff orchestra |
  | 105-125 | -14.0 -16.8 -14.9 -13.9 | 48.9-13 | p, then fff/ff, > p |
  | 125-135 | -21.2 -29.9 | 48.14-49.1 | p/pp: the quietest place |
  | 135-150 | -23.9 -21.9 -19.6 | 49.2-5 | ff chorus, < |
  | 150-160 | -13.6 -12.0 | 49.5-6 | < fff |
  | 160-185 | -14.0 -16.0 -18.5 -19.9 -23.5 | 49.7-14 | fff tutti, tam-tam; dim. to p/mf |
  | 185-200 | -20.8 -20.6 -19.4 | 50.1-4 | pp strings, harp fff, < ff |
  | 200-205 | -24.2 (1 s: -18 at 195 to -37 at 206) | 50.5-12 | ff, > to p |
  | 205-230 | -16.4 -14.1 -16.2 -15.2 -16.7 | 51.1-8 | ff/fff |
  | 230-245 | -11.5 -10.3 -11.6 | 51.9-13 | fff held, one level (1 s: -10.1 to -10.6 from 232 to 242 s) |

- **Seen wrong, then fixed (the tune's)**: in the first image (3) and
  again in image 4 (play with 128 voices, 0 stolen) the held fff chord
  of 51.9-12 stopped at 51.11: the horns' 392 Hz fell 49-59 dB within a
  second, Bb5 and G5 about 15 dB, the whole sound 6.9 dB. It was read
  first as the 64-voice limit; image 4 ruled that out. Bisected with
  `play -o` on kasumi: the held notes tie into 51.13's eighth, which
  p207-209.txt marked staccato for "scharf abreissen", and play sounds
  a tied note as one, so the staccato halved the whole held chord (a
  horn chord tied four bars into `/8'` stops after two). No staccato is
  printed there (check-p207-209.txt); the tie ends lose it
  (`fa13b7b`, `5858bd2`); `notes/px33/tools/tie-stacc.py` finds no
  other tie into a staccato in 46.11-51.13. In image 5 the horns' G4
  holds within 2 dB from 232 to 243 s and ends with the last eighth (images 5 and 6).
  px32 ruled (df224e7): a mark on a tie's last event cuts only that
  event. The tune keeps the fix on its own ground: no staccato is
  printed on those tie ends.

## 5. Done-when

Branch `px33`; PR open, unmerged; CI green at head;
`wolf/tools/lane-audit.sh pax px33 <PR>` from the org directory, exit
status read directly.
