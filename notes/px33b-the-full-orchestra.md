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
