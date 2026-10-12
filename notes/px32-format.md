# The part format — `play -m`'s orchestra (px32)

A short spec to write tunes to without reading `user/play`. A file is in
the **part format** when it has a `part` line; any other file is read
and sounds exactly as before (px18's notes, px29's chords). The part
format sounds only through the sound device (`play -m`, or `play` when
`/dev/dsp` opens); `play -s` refuses it by name.

The text: one item a line; `#` that starts a word starts a comment to
the end of the line (inside a word, `F#4`, it is a sharp); blank lines
are skipped; words are separated by spaces or tabs. Every file is read
and checked whole before a sound: the first bad line is `play: <path>:
line <n>: <what>`, status 2, and nothing plays.

## 1. The head (before the first `bar`)

```
title Chorale and tremolo           # optional, words
tempo 72                            # required: beats a minute, 20-400
tempo 60 2                          #   ... the beat a half note (any length: 4. 8 2)
meter 4/4                           # optional (default 4/4): n 1-32 / d 1 2 4 8 16 32
part hn1 horn mf pan -30            # a part: name, timbre, starting level, pan
part vn1 strings p pan -60
part org organ mp gain -3           # gain: the part's balance in dB
part ch choir                       # no level: mf
```

- **`part NAME TIMBRE [LEVEL] [pan P] [gain DB]`** — NAME is 1-16
  letters, digits or `-`, starting with a letter, not a word of this
  format (`r`, a dynamic, `bar`, `part`, `tempo`, `meter`, `title`,
  `cresc`, `dim`, `pan`, `gain`, ...). TIMBRE is from §5. LEVEL, right
  after the timbre, is a dynamic (§3): the part's level until its first
  dynamic mark; **with none the part plays mf** (never louder). `pan` is
  -100 (left) to 100 (right), default 0. `gain` is the part's balance
  against the others in whole decibels, -24 to 12 (`+3`, `-6`), default
  0: it scales every level of the part, so `gain -6` on the brass keeps
  their ff 6 dB under the strings' ff. `pan` and `gain` in either
  order. At most 24 parts. Parts sound in the order declared; the order
  has no other meaning.

## 2. Bars

```
bar 1
hn1  C4/2 E4/4 G4/4
vn1  pp E5/1*                       # a whole note, bowed tremolo
bar 2 tempo 66 meter 3/4
hn1  G4/2.~                         # tied into bar 3
bar 3 rit 50 over 2 fermata 4
hn1  G4/2 r/4
```

- **`bar N [meter n/d] [tempo BPM [UNIT]] [rit|accel BPM [UNIT] over K] [fermata LEN [at POS]]`**
  opens bar N. Bars are numbered **consecutively** from the first bar's
  number (any N ≥ 0, so a pickup can be bar 0); a skipped or repeated
  number is refused. `meter` and `tempo` take effect at this bar and
  stay. `rit` and `accel` (the same thing, two spellings) move the
  tempo smoothly from what it is at this bar's start to BPM by the end
  of K bars (this one and the next K-1); after them the tempo is BPM.
  `fermata LEN` adds LEN (a length at the tempo there) of held time at
  the bar's end, or at POS (a length from the bar's start, `at 2.` = after a
  dotted half): whatever sounds through or ends at that point is held
  through the extra time; what starts there starts after it. Several
  `fermata`s in one bar are allowed (at different POS).
- **A part line**: `NAME` then that bar's events and marks. The events
  of a part in a bar must fill the bar exactly (the meter's length):
  short or long is refused, naming the part, the bar, and by how much.
  A part with no line in a bar rests for the whole bar. A long bar may
  be split: the same NAME on several lines in one bar, joined in order.
- Parts are independent: each has its own rhythms, rests, ties, levels
  and hairpins; they meet only at bar lines.

## 3. Events, levels, hairpins

**An event** is `PITCHES/LENGTH[MARKS]`, one word:

| part | spelling |
|---|---|
| PITCHES | `r` (a rest), one note (`C4`, `F#3`, `Bb5`, `C##4`, `Dbb4`: letter, accidental `#` `b` `##` `bb` or none, octave 0-8; A4 = 440 Hz, equal temperament; sounding range A0 to C8), or up to 6 notes joined by commas, no spaces (`C3,G3,E4`): a chord in one part (divisi, organ) |
| LENGTH | `1 2 4 8 16 32 64` (whole to sixty-fourth); `.` or `..` dots it; then `t` (triplet: two thirds) or `xN` (an N-tuplet: N in the time of the largest power of two below N; `x3` = `t`, `x5` = 4 in 5, `x6` 4 in 6, `x7` 4 in 7, `x9` 8 in 9); `+` joins lengths (`2+8`, `1+4.`) |
| MARKS | any of these, in any order, after the length (none for a rest except `~` is refused): `'` staccato (sounds half its length), `^` marcato (accent and three quarters), `>` accent (the attack a level and a half louder, falling back over 150 ms), `-` tenuto (sounds its full length), `_` slur to the next note of this part (no gap, no new attack: legato), `*` tremolo (strings: unmeasured bowed tremolo; timpani, drums, cymbal, tam-tam: a roll; others: a flutter of repeated attacks), `~` tie (the next event of this part has the same pitches; the two sound as one note, across a bar line too) |

An unmarked note sounds its length less a short gap (an eighth of it,
at most 40 ms) and then releases (§5), so repeated notes part.

**Levels.** A dynamic word in a part line sets that part's level from
that point until the part's next dynamic word or hairpin, across any
number of bars and rests: `ppp pp p mp mf f ff fff`, eight steps **5 dB
apart** (ppp 35 dB under fff, the loudest a part can be). Levels are
absolute: nothing raises a quiet passage (§6). The level is loudness and, for
instruments that do it (§5), brightness: an ff horn is brassier than a
p horn, not only louder. `sfz` (also `sf`, `fz`): the next note's
attack at fff, falling back to the current level over 200 ms. `fp`:
the next note's attack at f, then the level p from there on.

**Hairpins.** `<` (also `cresc`) starts a crescendo, `>` (also `dim`)
a diminuendo, at that point in the part line (between events). It ends
at the next dynamic word of the same part (reaching that level there,
across bars if need be), or at `!` (two steps up for `<`, down for `>`,
from where it began), or at the next `<`/`>` (as `!`). The level moves
smoothly in loudness (and brightness) over the span, also inside a
held note. A `<` with no end by the tune's end is refused.

A word in a part line that is none of these is refused, by name.

## 4. Timing

All in sample frames at 48000 Hz: an event starts at its exact place
(the tempo map: beats, tempo changes, rit/accel, fermatas), not on the
kernel's 10 ms tick. Lengths are counted in units of 1/80640 of a whole
note, so every length above is exact and no error accumulates.

## 5. Timbres

| timbre | what it is (synthesis) | dynamics | tremolo `*` |
|---|---|---|---|
| `strings` | a bowed section: sawtooth-like spectrum, two detuned voices, vibrato ~5.5 Hz | level and brightness | bowed tremolo |
| `brass` = `horn` | horn: round, dark; brightness rises with level; soft attack | level and strong brightness | flutter |
| `trumpet` | bright brass, quick attack | level and strong brightness | flutter |
| `trombone` | bright, broad brass for the low parts | level and strong brightness | flutter |
| `woodwind` = `clarinet` | odd-harmonic reed | level and some brightness | flutter |
| `oboe` | nasal double reed | level and some brightness | flutter |
| `flute` | nearly pure, a breath of noise | level | flutter |
| `organ` | manuals: principal chorus 8' 4' 2' 2-2/3', steady, no vibrato | level only (as a swell box) | repeated |
| `pedal` | organ pedal: 16' and 8' — sounds the written note and the octave below | level only | repeated |
| `choir` | a section singing "ah": vowel formants, two detuned voices, vibrato | level and brightness | repeated |
| `voice` | a solo singer: "ah", wider vibrato | level and brightness | repeated |
| `harp` | plucked, decaying | level and brightness | repeated |
| `timpani` | tuned drum: struck, inharmonic modes and a thump, decays ~2 s | level | roll |
| `bells` | tubular bells: inharmonic partials (hum, prime, tierce, quint, nominal), long decay | level | roll |
| `tamtam` | tam-tam: noise through resonances, slow bloom, decays ~6 s | level | roll |
| `cymbal` | cymbals clashed: bright noise, decays ~3 s | level | roll |
| `drum` | bass drum: low thump and noise | level | roll |

Percussion (timpani, bells, tamtam, cymbal, drum, harp) rings after
the note's length ends, as struck instruments do; a rest does not stop
it. A tamtam/cymbal/drum note's pitch is ignored (write any note).

## 6. Voices, mix, budget

- A **voice** is one sounding pitch of one event, release tail
  included. At most **64** sound at once; past that the quietest
  releasing (or ringing) voice is cut (counted as `stolen` on the
  `played` line). A drum, bell or tam-tam struck again while it rings is
  struck in place (no new voice).
- Each part is placed by its `pan`. The mix has a fixed master gain:
  one part's mf sits near -39 dBFS, a 16-part tutti at pp near
  -38 dBFS, the same tutti at ff near -12 dBFS. A look-ahead **limiter**
  turns the mix down only where its peaks would pass 30000 (about
  -0.8 dBFS), and lets it back up within half a second: it never
  raises anything, so pp stays quiet; no sample is ever clamped
  (counted; `0` is the tests' verdict).
- **The budget**: the synthesis runs in real time, ahead of the device
  by its 8 periods (170 ms); `play -c NAME` says the cost against real
  time. Measured figures are in `notes/px32-the-orchestra.md`.

## 7. What `play` says

```
play -m orchestra
playing Chorale over tremolo, an orchestra study (30.9 s), 17 parts, 48000 Hz
played Chorale over tremolo, an orchestra study: 45 voices at most, 0 stolen, 0 clamped, 60 blocks limited, set up in 60 ms
play -c orchestra
cost Chorale over tremolo, an orchestra study: 1867648 frames (38909 ms of sound, 30908 ms written, 17 parts, 45 voices at most) synthesised in 2360 ms, 6.0% of real time, 0 clamped, 0 stolen, 60 blocks limited; read in 10 ms, set up in 60 ms
play -o orchestra > frames.raw      # S16_LE, two channels, 48000 Hz, to standard output
```

`play` alone lists part-format tunes with their title and length as it
lists the others. (The figures above are TCG on kasumi; the measured
ones are in `notes/px32-the-orchestra.md`.)

## 8. A whole example

```
title Example
tempo 80
meter 3/4
part tpt trumpet mf pan 20
part vc strings p pan -40
part tim timpani p
bar 1
tpt  G4/4 C5/8. D5/16 E5/4>
vc   C3/2.~
tim  C3/4 r/2
bar 2 fermata 2
tpt  < E5/2_ D5/4 f
vc   C3/2 G2/4
tim  G2/2.*
```
