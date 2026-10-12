# px33b — the full orchestra: Auferstehung in 36 of 48 parts

Lane px33b re-arranges px33's close of Mahler's Second (`auferstehung`,
43.5-51.13, and `auferstehung-close`, 47.1-51.13) with the lines px33's
readers read but could not carry in 24 parts, now that px32's part
format allows 48 parts and 128 voices (`notes/px32-format.md`).

## 1. Sources and rights

As px33 (`notes/px33-auferstehung.md` §1): the 1897 Hofmeister first
edition of the full score (Internet Archive `symphonieno200mahl`, page
images 0198-0211, sha256 in `notes/px33/source-jp2.sha256`), public
domain. No modern edition, encoding or recording; nothing from memory.
Behn (UE 2937) and Walter (UE 949) only to find errors; not used here.

The added lines come from px33's check lists (`notes/px33/check-*.txt`).
Where a line was "read but not carried" without its notes written out,
it was read here from the same scans, to the same standard: each staff's
five lines measured in the bar's own column band, every head read
against a guide drawn at every line and space of that staff
(`notes/px33b/tools/guide.py`, crops at 3-8x), cross-checked against the
carried parts it doubles. Those readings are in
`notes/px33b/check-px33b.txt` with the bar, the staff and what was seen.

## 2. Inputs, verified

- px33's joined transcription `notes/px33/transcription/joined-43.5-51.13.txt`
  (bars 0-131) is the base; nothing in it is re-read except where an
  added line shares a staff with a carried one.
- px32's format: at most 48 parts, 6 notes a chord, 128 voices; `play -c`
  reports voices, stolen, dropped, clamped.
- px33's figures: 24 parts, 95 voices at most, 0 stolen, 463.8 s
  written (`auferstehung`), 246.6 s (`auferstehung-close`).

## 3. Prediction (committed before the first tune change)

**The head: 36 parts** (12 new). The tempo map, bars and every carried
note stay; lines are split out of shared parts or added.

| part | timbre | carries | was |
|---|---|---|---|
| sop-solo, alt-solo, ch-s, ch-a, ch-t1, ch-t2, ch-b1, ch-b2 | voice/choir | unchanged | |
| fl | flute | flutes, piccolos | |
| **ob** | oboe | the oboes: 46.15-24, 47.13-16, 48.1, 49.1-6, 49.13-14, 51.9-13 | folded in `cl` or not carried |
| cl | clarinet | clarinets in B (and A), E-flat; at 49.13 the B clarinets' own halves | |
| fg | woodwind | bassoons, contrabassoon | |
| hn | horn | horns 1.3 (the upper staff, 1.3.5.7.9 from 47) | all horns |
| **hn2** | horn | horns 2.4 (44.9-16, 45.3-9, 45.13-15), 5.6 and 7-10 at 46.13-24, the lower staff (2.4.6.8.10) from 47 | in `hn` |
| tp | trumpet | trumpets 1.2 (and the chords where the pairs are not separated) | |
| **tp2** | trumpet | trumpets 3.4: the tie at 47.11-12, 48.5-9, 49.1-6 | not carried |
| **tp3** | trumpet | trumpets 5.6: 48.7-9, 49.1-6 | not carried |
| tb | trombone | trombones 1-3 (and 4 where it is with them) | with the tuba |
| **tu** | trombone | tuba (with Pos. 4 where they share a staff) | in `tb` |
| ti, gl | timpani, bells | unchanged | |
| tt | tamtam | the deep tam-tam | both |
| **tt2** | tamtam | the high tam-tam 51.2-8 (play ignores a tam-tam's pitch: the same sound, placed apart) | in `tt`, 51.4-5 not carried |
| cy | cymbal | the cymbals (Becken) | with the bass drum |
| **bd** | drum | the bass drum (Gr. Tr.): 46.21-24, 48.10, 48.13, 49.5-7 | in `cy` |
| **tri** | bells | the triangle, 48.10-11 and 48.13-14, as a roll on a nominal C7 (no triangle timbre; a stated stand-in) | not carried |
| hp | harp | harp I | both harps |
| **hp2** | harp | harp II: 45.3, 45.9, 45.11-13 (zu 2), the runs 46.9-18, 49.7-9 | in `hp` or not carried |
| **hp3** | harp | harp I's notes past six (44.1, 44.10, 44.13, 46.1, 46.9, 46.11-14, 46.16) | dropped |
| org, ped | organ, pedal | unchanged | |
| vn | strings | first violins (and both sections where px33's check list does not separate them) | both |
| **vn2** | strings | second violins wherever the check list or this lane's reading names their notes | in `vn`, in `va` (46.1-4), or not carried |
| va | strings | violas (rest 46.1-4 as printed) | |
| **vc** | strings | cellos | `lo` |
| **cb** | strings | double basses | `lo` |

Rules: where px33 carried the cellos and basses as an octave pair, the
lower note is the basses' (written at the cellos' pitch, sounding an
octave down) and the upper the cellos'; where the check list names
their notes apart, those are used. Where it carries `vn` as one chord
for both sections and names the halves, the named halves are split;
where it does not name them, the chord stays in `vn` and is listed.

**New readings (from the scan, this lane)**: harp I's chords 46.11-16
(to separate them from harp II's runs, which px33 carried in one part);
the oboes 46.15-16; trumpets 3-6 and trombones 1-3 48.5-9; triangle and
Becken/Gr. Tr. 48.10-14; harp I and harp II 49.7-9; second violins
44.1-8; horns 2.4 45.4-8. Predicted: no carried note changes, except
where a reading here contradicts one; any such is a correction, named.

**Expected not carried (stays listed)**: harp II 49.10-50.4 (px33 read
it only at 1x; not re-read here); the woodwinds' grace notes into 48.1;
the organ 48.10-12 (not readable); the clarinets' upper note at 46.24
(not readable); vn2 at 44.10; the trumpets' inner pairs at 47.1-10 and
the trombones' 47.7-13 where the check list gives one chord.

**Figures predicted**: `notes/px33/tools/check.py` errors 0 on every
file. `play -c`: 36 parts; voices at most rise from 95 to 105-125
(harp II's runs ring, the oboes double the clarinets at 51.9-12), 0
stolen, 0 notes dropped, 0 clamped; lengths unchanged (463.8 s and
246.6 s written: no tempo or bar changes), so the `play` listing in
`user/console/speaker.expect` is unchanged. Levels per 5 s within 1.5
dB of px33's image 7 except at 46.11-24 (harp II and oboes), 48.5-14
(trumpets, trombones, triangle), and 51.9-12 (oboes): louder there by at
most 2 dB, the limiter holding peaks.

## 4. Evidence index

- **The join**: `notes/px33b/transcription/joined-36-43.5-51.13.txt`,
  made from px33's join by `notes/px33b/edits.txt` through
  `notes/px33b/tools/rearrange.py` (every op names its source: a px33
  check-list row or a reading in `notes/px33b/check-px33b.txt`). The
  tunes come from it with `notes/px33b/tools/tunes.py` and the two
  headers. `notes/px33/tools/check.py`: errors 0 on the join and both
  tunes; `notes/px33b/tools/pins.py` (hairpin ends, open hairpins, ties
  into notes the next event does not sound): errors 0 on all three, and
  0 on px33's join.
- **Seen wrong, then fixed**: the first `play -c` refused the join at
  44.13 (`'!' ends a hairpin, and none is open in part 'cb'`): the
  cellos and basses' octave split had copied the `!` that closes a
  hairpin only the cellos carried (fixed in `3635748`). `pins.py` was written then and finds that one place only.
- **Levels entering the close** (px33-c's `levels.py` at bar 63 of the
  join and bar 1 of the close): every part's first sound after 47.1
  follows a dynamic word, after bar 69's second violins were given the
  ff of 47.1.
- **`play -c`** (play built on kasumi from this branch at `0e53345`,
  wolf 0.2.27, the binary trunk's play is: sha256 `ba9f2e68…`):
  - the join and `auferstehung`: 463769 ms written (471770 ms of
    sound), 36 parts, **125 voices at most, 0 stolen, 0 clamped, 0
    notes dropped**, 22282 blocks limited, status 0;
  - `auferstehung-close`: 246623 ms written, 36 parts, 125 voices at
    most, 0 stolen, 0 clamped, 0 dropped, status 0.
  - The listing over the image's tunes equals `user/console/speaker.expect`
    (463.8 s and 246.6 s, unchanged).
- **The image** `pax-mahler-orchestra-36.iso` (sha256 `0083e5b8…`),
  played on nomad-1 under TCG with QEMU's wav backend, `-m 256M`,
  through pelt: `play -m auferstehung` 125 voices at most, 0 stolen, 0
  clamped, 0 dropped; the device 22116 periods, 0 underruns, 0 dropped;
  `auferstehung-36.wav` 471.8 s (sha256 `1f880aad…`). `play -m
  auferstehung-close`: the same counts, 11937 periods, 0 underruns;
  `auferstehung-close-36.wav` (sha256 `092e4687…`). QEMU stopped by its
  recorded pid after "halt" both times.
- **Levels per 5 s** (`tools/orch-check --env`, dBFS, the 36-part
  render against image 7's `auferstehung-full.wav`): equal within 1 dB
  through 43.5-46.8 except 25-30 s (44.1's ff chord, +1.0 and +1.6: the
  harp's notes past six and the second violins), 85 s (+1.3) and 100 s
  (46.1, pp: -46.5 to -43.4, +3.1: harp I's two notes past six and the
  second violins' chord, now its own part); the build 46.11-24 moves
  -1.0 to +3.1 dB from 145 s to 215 s, louder from 190 s (+1.9 to +3.1:
  harp II apart, the oboes, the cellos' own fff line at 46.21-24);
  47-48.4 within 0.4 dB;
  48.5-14 within 0.4 dB (the added trumpets and trombones double lines
  already sounding); 49.5-7 +0.8 to +2.1 dB (360-380 s: trumpets 3-6,
  harp II); 50-51.8 within 0.5 dB; 51.9-12 **-1.0 dB** (450-460 s: the
  limiter, with the oboes and the split parts, takes the held fff a
  little lower); the last chord's ring after 465 s +2 to +3.6 dB. The marks still read in the curve: "Bereite dich" -27
  falling to -48; 46.1-10 pp about -44; the build -42 to -13; 48 fff
  -10; 49.1 p -30; 49.6 fff -11.7; 51.9-12 fff -10.8.
- **Prediction against measure**: 36 parts, right. Voices 125 at most,
  inside the predicted 105-125 but at its edge (3 voices from px32's
  128; 0 stolen). Lengths and the listing unchanged, right. Levels
  "within 1.5 dB except three places, louder there by at most 2 dB":
  **wrong in degree** — the build at 46.11-24 is up to 3.1 dB louder,
  46.1 3.1 dB, 49.5-7 2.1 dB, and 51.9-12 is 1.0 dB quieter, not
  louder. "No carried note changes except corrections": right; the two
  corrections are horns 1.3 at 45.5-6 (rhythm) and harp I at 49.8
  (pitches), both read in the score (`check-px33b.txt`).

## 5. Not carried, and not done

- Listed in the tune headers: harp II 49.10-50.4 (not re-read); the
  second violins where px33 gives one chord for both sections and at
  44.10; the trumpets' and trombones' pairs given as one chord (47.1-12,
  49.3-4 Pos 4 and tuba, 49.11) and trumpets 3.4's A4 at 49.1; the
  woodwinds' grace notes into 48.1; the oboes 3.4's p < at 46.17; the
  cellos' pizz A at 44.9 (in the basses' chord); the organ at
  48.10-12; one clarinet note at 46.24.
- The triangle sounds on the bells' timbre at a nominal C7 and the high
  tam-tam as the deep one (play ignores a tam-tam's pitch): stated
  stand-ins, not readings.
- Not run: KVM (hasu); listening by a person; a spectral check that
  each added line is heard apart (the counts and levels are the
  evidence here).

## 6. The tempo passes and the harp fix (after the maintainer listened)

- **t** ("plodding … more natural, but not blistering"): every tempo
  word on pp. 196-209 was read again. There is **no metronome mark**,
  and the four printed equivalences are kept exactly. Two words were
  misplaced in px33's join and are corrected: Nicht schleppen is at
  45.13 (not 45.12) and Wieder etwas zurückhaltend at 46.22 (not
  46.21). Rit., zurückhaltend and Langsam steigern now move over their
  bars. 463.8 → 398.1 s; the close 246.6 → 218.6 s.
  - 49.7 had to stay at h 36. The harps' runs there overran 128 voices
    at h 38 or faster (3 to 23 stolen, measured).
  - Image `pax-mahler-orchestra-36t.iso` (sha256 `74315611…`). The full
    render had 121 device underruns at a nomad-1 load of 17-21 (another
    lane's soak); the file is whole (406.1 s, play's sound length). The
    close render had 0 underruns.
- **t2** ("another 15% across the board"): every value ×1.15, 49.7
  included, the equivalences exact. 346.7 s; the close 190.6 s.
  - The overrun's cause, fixed in play (`user/play/orch.lu`): a harp
    string plucked again while it rings took a new voice and left the
    earlier pluck ringing about 11 s, a sound one string cannot make.
    It is now plucked in place, as a bell struck again already was,
    with its phase and level carried (no click). `notes/px32-format.md`
    §6 says so.
  - Test `user/play/parts-test/replay` in mpx3-orchestra O4: red at the
    test's own commit (`17 voices at most`); green with the fix. The
    other O4 checks are unchanged (host-only on kasumi, play sha256
    `035554da…`).
  - `play -c`: 84 voices at most (was 125), 0 stolen, 0 dropped.
  - Image `pax-mahler-orchestra-36t2.iso` (sha256 `e2579f3a…`): both
    renders 0 underruns at load 2-6. `auferstehung-36-t2.wav` (sha256
    `fbdbd146…`) and the close (`d3d0db76…`).
  - The 5 s levels still follow the marks: the build -45 to -12; 48 fff
    -11.6; 49.1 p -29.6; the last fff -11.3.
- The tempo table (old, t, t2) is in `notes/px33-auferstehung.md`,
  "Tempo pass".
