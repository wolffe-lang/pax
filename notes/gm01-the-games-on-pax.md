# gm01 — the games on PAX: the font row, the three games in the installer, the equal-experience proof

Contract: `sprints/lair/pax/gm01-the-games-on-pax.md` in wolffe-lang/wolf
(M-PK4, M-CB5, M-TR2; read 2026-10-25). Branch `gm01` from pax trunk
`77d7b00c` (px80 merged). Model: Claude Opus 5.5. Kasumi CPUs 12–15
under `kasumi-cores-12-15.lock`, everything in the lane's `px80-ubuntu`
containers; the Mac held the worktree and git only. Evidence under
`notes/gm01/`.

Footprint: cross-cutting

## Prediction

Committed first, `e3cea2e2` (`notes/gm01/prediction.txt`), before any
change. Scored:

| prediction | measured | score |
|---|---|---|
| (read, not predicted) the union of the three GLYPHS.md lists is 161 code points; Spleen 2.2.0 already draws 159 of them; it lacks U+2024 and U+25AA | 161 (pack 18, cub 152, trail 8); 159 in Spleen; G0 holds `font/games-glyphs.txt` to the lists inside the pinned archives | as read |
| P1 the loader does not take merged rows without a format change: a code-point map and a wider glyph field are needed | right: `boot/font.S` gained `pax_font_ranges` and `pax_font_glyphs` (551 glyphs, 8 ranges); the cell keeps the glyph number's high byte in bits 20–27; the BDF format itself unchanged | right |
| P2 a 2×2-dot braille generator and plain rectangles reproduce Spleen's braille (256) and non-shade block elements (29) bit for bit; the shades are 25/50/75 % dithers but not one nested ordered matrix | right on all three (`tools/mkfont --test`) | right |
| P3 every key the games bind arrives through PAX's PS/2 driver, Shift+arrows as `ESC [ 1 ; 2 X` | right: the `--record` files name `left right parry` (pack), `up left sneak-right` (cub), `start up left down` (trail); Space, Enter and `q` reached each game; Ctrl-D reached `cat` | right |
| P4 static binaries: pack ~15.5 MB, cub ~17 MB (the largest), trail ~13 MB, each within 20 % | pack 15,413,192, cub 15,579,480, trail 15,317,552: each inside its 20 % band and in the predicted order, but within 2 % of each other, not 30 % apart (the linked runtime and glibc dominate; the games' own code is small) | right in band and order; the spread wrong |
| P5 the games start on PAX unmodified, the first gap (if any) in a clock or signal call | no gap at all: -ENOSYS only for set_robust_list (273) and rseq (334), glibc's, as every static program here; no `refused:` line | right that they start; no gap to place |
| P6 a bare start picks the plain tier on PAX (TERM=linux), so R-gm01-3 A cannot hold as written | right (G6, with and without the font row): ruling R-gm01-4 asked | right |
| P7 with the row, every cell of each title and scene is the golden's glyph, colours through the VT's 256-to-16 mapping; without it, `?` exactly above U+00FF | right: 8000 of 8000 cells pixel for pixel on every frame, both firmwares, both kernel tiers (native and release); withheld, trail's title is the golden with its 253 cells above U+00FF drawn `?` and nothing else different | right |

## Forbidden

No kernel, libc, shell, grep, file-system tool, bootloader or font-engine
source was read. Spleen stayed vendored unmodified (its BDF read as data,
as px19 read it); the two glyphs added are drawn for PAX
(`font/pax-extra.bdf`). The braille and block functions are written from
Unicode's chart definitions. The games and their engine are the
maintainer's (RULES §1): read and run, never changed; a game-side need is
listed under Follow-ons for its track. No signal was sent by any script:
`q`, Ctrl-D and every key went in as pty bytes or PS/2 keys. Nothing
installed on kasumi (px71's recipe unpacks the installer gate's oracle
debs into the lane with `dpkg-deb -x`); `~/pax-playground` untouched; as02b's
branch and worktree untouched; no merge, label, tag, release, issue, or
attribution trailer.

## Inputs verified

- pax trunk `77d7b00c91d4…` (px80 merged), read at the branch point.
- The pins, each source archive fetched twice from codeload and read
  twice (identical): pack `e10835f2818ada427bc2d74f1171653af3ffdce1`
  `b997002b4176436ab4c7c14a3a78905f7014616118af379ece415d6d27863fe5`; cub
  `6153d97555b3e1ae7406b9405df0e2cd10033af9`
  `ba390445c2ab7b709a90eb334a2f52cdfbcc673b316bb6fe893e4ba8e3f02ab2`;
  trail `6dbe253fad3c73225c547a036aa8ec786abd91dc`
  `bac96fe52e2cb2f7ef24ea7a082d20fb804ce92aaedb829a6df16cd5ad51a9bf`; their
  engines lair `aa6c4dc0bc5071d3c07121451d913a8837cd2a6a` (pack, cub)
  `7507a4cb1f6fdb8313350600dd2f4fdf9b89d42c40953c2f68aa5da7ac4f8074` and
  `57870143ebbb4806b8bee40379e8c6e781f50842` (trail)
  `191dc62672d13610b65e77fd7d743119f620365af9087c037da1f256d26b22d2`. Each
  game's `lair.pin` names its row's engine; the tree `fetch-lair` stages
  is the engine archive file for file (`tools/mkgames`).
- The toolchain, as both engines' `wolf-toolchain.toml` pin it: wolf
  0.2.35 `cf0c13d`, x86_64 Linux archive
  `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a` (the
  same archive pax's `kernel/wolf.pin` names), lupin 0.1.56, wolf-std
  `2386522e`; Ubuntu 24.04's gcc 13.3.0 and `libc.a` for the static link.
- The binaries, built three times in the lane (games-01, g-01, g-02) to
  the same bytes, each sha read twice by `tools/mkgames` and once more by
  G0 against `games.sha256`: pack 15,413,192 bytes
  `19c63c04a4486a0727e543b4824e1e219f60ac2f467925986cbbcc25e7340cd7`; cub
  15,579,480 `8eb5bf7d665e3dd84bffe19b24303e6e1979f6e45abc982959290aedac68a632`;
  trail 15,317,552
  `391e4083f88698bbc0934ff491845c58f309890144ab92cebbab7fcbfc565ff3`. Every
  committed rich golden of the 80-column cases reproduces from them
  headless: 63 of 63 surveyed (`notes/gm01/runs/kasumi-goldens-survey.txt`,
  which also names the 10 whose frame holds still for 150 ticks after
  the case's last; G0 keeps three).
- Spleen 2.2.0's BDF unchanged (`4a3d97ee…`); 978 glyphs, of which the
  table now draws 192 below U+0100 and 293 above.

## Evidence index

| claim | artifact |
|---|---|
| the font row: 285 generated glyphs equal Spleen's, braille distinct and read back, blocks rectangles, shades 25/50/75 % | `notes/gm01/mkfont-test.txt` (`tools/mkfont --test`), G0 in every suite log |
| `boot/font.S` is the fonts' table: 551 glyphs, 8 ranges | `tools/mkfont --check` (G0; mpx3-screen V0) |
| the 161 code points: each in the table, its own glyph, none blank, none `?`'s, no two alike; one cell each on PAX's screen | G0 table, G1 glyphs; `notes/gm01/screens/native-bios-glyphs.png` and `…-glyphs-withheld.png` |
| each game's `--probe-glyphs` on PAX's console: every width 1 | G2; `notes/gm01/probe-{pack,cub,trail}.txt` (the "PAX's console" column) |
| the frames equal the Linux side's, cell for cell, pixel for pixel | G3; `notes/gm01/screens/native-bios-*.png`; logs below |
| the keys through the PS/2 driver; the terminal restored | G4 |
| the font row withheld: `?` exactly above U+00FF; the plain tier untouched | G6 |
| the games' system calls; nothing new needed on PAX | `notes/gm01/census/*.calls`, `docs/CENSUS.md` "The wolf games (gm01)", G5 |
| the installer lands all three with their sources | `tests/mpx6-install` logs below |
| suite logs, kasumi CPUs 12–15, all PASS | `notes/gm01/runs/`: `kasumi-mpx6-games-native-both-g02.log` and `…-release-both-g03.log` (with their `.runs`), `kasumi-mpx6-install-smoke-native-bios.log` (48 PASS), `kasumi-mpx6-install-full-native-bios.log` (62 PASS, I-session-uefi among them), `kasumi-mpx3-screen-native-bios.log`, `kasumi-mpx5-screen-native-bios.log`, `kasumi-mpx3-speaker-native-bios.log`, `kasumi-ci-plan.log`, `kasumi-mkgames.log`, `kasumi-mkinstall-payload.log` (a changed cub refused by name), `kasumi-census-strace.log`, `kasumi-goldens-survey.txt` |

### The frames

Each row: PAX's screendump against the Linux side's frame of the same
run (`tests/mpx6-games.d/compare.py`), 8000 cells of 160 × 50, pixel for
pixel and glyph for glyph. Native: g-02 (`kasumi-mpx6-games-native-both-g02.log`);
release: g-03 (`kasumi-mpx6-games-release-both-g03.log`); 54 PASS rows and
`mpx6-games: PASS` each.

| game | frame | the Linux side's golden | native BIOS | native UEFI | release BIOS | release UEFI |
|---|---|---|---|---|---|---|
| trail | title (`--replay title-80.pk`) | headless frame 1 = trail's committed `title-80-rich` | 8000/8000 | 8000/8000 | 8000/8000 | 8000/8000 |
| trail | its natural run, paused at tick 560 | headless frame 600 of `trail-natural-paused.pk` | 8000/8000 | 8000/8000 | 8000/8000 | 8000/8000 |
| cub | the opening (`--replay opening.pk`), which animates every 6 ticks | one of the headless frames 1–89, pixel for pixel | frames 6–11, 60–65 | 6–11, 60–65 | 12–17, 66–71 | 12–17, 66–71 |
| cub | the walk to the water (`--replay walk-north.pk`) | headless frame 120 = cub's committed `walk-north-rich` | 8000/8000 | 8000/8000 | 8000/8000 | 8000/8000 |
| pack | title (`pack --tier rich`) | the same command live on a 50 × 160 pty, through `pack --apply` | 8000/8000 | 8000/8000 | 8000/8000 | 8000/8000 |
| pack | the death card (`--replay death-card.pk`) | the same replay live on the pty (Follow-on 3) | 8000/8000 | 8000/8000 | 8000/8000 | 8000/8000 |

The keys (G4), every firmware and tier: pack records `left right parry
quit` (Shift+arrow the parry), cub `up left sneak-right` among its
journey events, trail `start up left down quit`; after each game the
main screen is back, the cursor shown, and a typed line echoes through
`cat`. A bare start is the plain tier with the row and without it (G6);
withheld, trail's title is the golden with its 253 cells above U+00FF as
`?`, 8000 of 8000.

### The plants

Three draft PRs, one planted break each on a `gm01-plant-*` branch cut
from the lane's head at the time (`de0dbf9c` later changed only a
failing row's wording), each run red by name in its own CI run:

| plant | PR | head | run | red rows |
|---|---|---|---|---|
| `boot/font.S` draws U+2802 as U+2801 (two braille patterns alike) | #205 | `86679899` | 40253361683 | mpx6-games G0 (`mkfont: … boot/font.S is not what the font gives`), G1 (`glyphs: at byte 4133, not screen-ref's picture`), G3 (`ref: 10 dumps, 9 screen-ref's picture`); mpx3-screen V0 (the same mkfont check) |
| `tools/mkgames` changes a game after recording its sha256 | #206 | `e5e85636` | 40253363949 | mpx6-games G0 (`pack's sha256 405b1283… is not games.sha256's 19c63c04…`); mpx6-install I-install (`pax-install: stopped: corrupt_asset`) |
| `kernel/console` drops Shift from the arrows | #207 | `6ebcde02` | 40253365140 | mpx6-games G4 native bios pack (`4 events recorded (left right down quit); not left right parry in order`) and cub (not `up left sneak-right in order`); mpx5-yew Y3 (its probe's Shift+arrow bytes) |

mpx3-speaker was also red in #205's and #207's runs, at K0: `tools/mkbeep`
could not fetch beep's source from launchpad.net (`curl: (22) … 503`,
then broken pipes), so every later K row had no `beep`. Not a plant's
(#206's plan skipped the suite): the lane's own `tests/mpx3-speaker
--tier native --firmware bios` on kasumi at this head passed K0 (the
fetch) and every K row after it
(`notes/gm01/runs/kasumi-mpx3-speaker-native-bios.log`).

## Rulings

- **R-gm01-1 A** (implemented): braille is one function, `braille(cp)` in
  `tools/mkfont`, tested (`--test`: 256 distinct, read back as the
  bits, four pixels a dot). Measured: Spleen 2.2.0 already draws the
  whole block, and the function's output equals it for 256 of 256, so
  the generated rows and Spleen's unmodified rows are the same bytes; the
  build refuses by name if they ever differ.
- **R-gm01-2 A** (implemented): the shades are ordered dithers at 25/50/75
  % — Spleen's own (two-row patterns, 32/64/96 of 128 pixels), held so by
  `--test`. A Bayer matrix would have drawn different patterns from the
  font PAX vendors; Spleen's are not one nested matrix (P2), and its
  author's choice is kept.
- **R-gm01-3 A as written does not hold at these pins** (P6): the engine's
  `tier.detect` (lair `src/tier/tier.lu`, both pins) answers plain for
  `TERM=linux` whatever the locale, and PAX's console is `TERM=linux`.
- **R-gm01-4 (new) — the tier on PAX's console.** (A) PAX keeps
  `TERM=linux` (what its console is, held by the VT comparisons and the
  Linux differentials' environment); the rich tier is the games' own
  `--tier rich` flag; the engine is asked (its track) for a way a console
  whose font draws the rows can say so. (B) PAX's framebuffer console
  names itself something other than `linux` when the row is present: the
  games pick rich unchanged today, but every program and row that names
  the terminal moves, and no terminfo entry exists for the new name.
  **Recommended and implemented: A.** G6 records the plain bare start
  with and without the row; docs/BOOT.md and the README say `--tier rich`.
- **R-gm01-5 (new) — the engine's source.** Each game's binary links its
  engine (lair, GPL-3.0), whose source is not in the game's archive.
  (A) `games.txt` gains the engine's commit and archive digest, the
  payload carries `<game>.engine.source.tar.gz`, the installer verifies
  and lands it as `~/Games/<game>/engine.source.tar.gz` (0644,
  1000:1000); (B) a combined archive made by pax. **Recommended and
  implemented: A** (the pinned archives byte for byte).
- **R-gm01-6 (new) — the table's extent.** (A) the code points the games
  draw, widened to the whole braille and block-element blocks the
  functions draw (295 above U+00FF); (B) all of Spleen's 978. **A
  recommended and implemented**: every drawn code point is named and
  tested; B is `font/extent.txt` alone when a program needs it.

## Follow-ons

1. **lair** (the engine's track): `tier.detect` demotes every `TERM=linux`
   terminal to plain; PAX's console draws the rich tier (R-gm01-4). Ask
   for a way to say so (an explicit environment word, say `LAIR_TIER`,
   or the locale on a console that measured its font). lair#13 (CSI-u)
   unchanged.
2. **pack, cub, trail** (each track): paste the "PAX's console" column
   of `docs/GLYPHS.md` from `notes/gm01/probe-<game>.txt` (every width 1,
   2026-10-25, BIOS and UEFI); trail's GLYPHS.md says PAX's widths are
   unmeasured.
3. **pack** (its track to judge; same bytes on Linux, so not PAX's): the
   live `pack --replay tests/cases/death-card.pk` card reads `replay:
   score 600, the file carries no` above its own `score 773`. Two things:
   the line (`replay: score 600, the file carries none; q leaves`) is
   clipped at the card's width, and the verdict's headless re-run
   (`verdict_of` → `rerun_score`, `src/pack.lu`) stops at the replay's
   last recorded tick while the live run goes on to the bite, so the two
   scores differ for a replay that ends without a key. The headless card
   offers `s` instead, so the committed `death-card-rich` golden is not
   this frame (G0 holds it as `pack-death`; G3 compares the live one).
4. **The next ISO respin** (px-side; this lane does not respin): the dev
   ISO (`notes/px80/dev-iso/assemble.sh`) needs (a) the kernel at this
   head (the font row: `kernel/screen` and `boot/font.S`; every byte of
   `kmain_console` moves); (b) the three games from `tools/mkgames`
   **unstripped**, at `/home/pax/Games/<game>/<game>` 0755 1000:1000 with
   `source.tar.gz` and `engine.source.tar.gz` beside them 0644 1000:1000
   (the bytes `games.sha256` names, so the ISO's games are the
   installer's; about 46 MB more initramfs); (c) for `pax-install --games
   yes` from the ISO, the payload staged by `tools/mkinstall-payload BOOT
   build/games OUT` copied to `/usr/share/pax-install`; (d) a motd line,
   e.g. `Games: ~/Games/pack/pack --tier rich (cub, trail the same; q
   quits)`. A machine with 1 GiB holds it (the suites boot with `-m 1024M`).
   Until then, the playground recipe: the release-tier games ISO from
   g-03 is staged on kasumi at `~/lanes/gm01/out/gm01-games-release.iso`
   (99,276,800 bytes,
   `7d036b42ad24b4b23ec0f8f1c75349e3ab308afa6eb6762767d05d9fddfb8f61`,
   read twice; `tests/mpx6-games --tier release` rebuilds it as
   `build/mpx6-games/release/games.iso`). Copy it to the Mac and run
   `qemu-system-x86_64 -machine q35 -cpu max -m 1G -display cocoa -serial
   file:serial.log -nic none -no-reboot -cdrom gm01-games-release.iso`; it
   boots to pelt as `pax`: `cd /home/pax`, then `Games/cub/cub --tier
   rich` (pack and trail the same; `q` quits; `exit` halts). Its
   `cases/` holds the replays the suite uses.
5. **fugue** (wolffe-lang/fugue), a fourth game opened 2026-10-25, is not
   in this lane's scope: gm01 ships pack, cub and trail as briefed. A
   later lane adds it as one more `user/install/games.txt` row (built by
   `tools/mkgames` unchanged if it pins lair), its `docs/GLYPHS.md` to
   `font/games-glyphs.txt` (and any code point Spleen lacks to
   `font/pax-extra.bdf` and `font/extent.txt`), and its frames to
   `tests/mpx6-games`.
6. Static glibc and wolf's runtime/std are linked into each binary as
   into px71's pack; the corresponding-source question for those (LGPL
   relinking objects, the std's licence) is unchanged by this lane.

## Done-when

- [x] Prediction first (`e3cea2e2`).
- [x] Item 1, the font row: `font/pax-extra.bdf`, `font/games-glyphs.txt`,
      `font/extent.txt`, `tools/mkfont`, `boot/font.S`, `kernel/screen`,
      `tools/screen-ref`, `tests/mpx5-screen.d/compare.py`.
- [x] Item 2, the games in the payload: `tools/mkgames` (mkpack retired),
      `user/install/games.txt`, `tools/mkinstall-payload`,
      `user/install/prepare.lu`, `tests/mpx6-install{,.d/*}`.
- [x] Item 3, the proof: `tests/mpx6-games{,.d/}`, `user/console/games*.keys`,
      the CI job, `tools/ci-tiers.map`, `tests/ci-plan`.
- [x] Item 4: docs (BOOT, CENSUS, SOURCES), README (read and refreshed),
      this note.
- [x] Plants: #205, #206, #207, each red by name in its own run (above).
- [x] Release tier, both firmwares (g-03): `mpx6-games: PASS`, 54 rows.
- [ ] The PR's run, the labelled `tier full` and the audit's last line:
      the PR body and the hand-back (they name this note's head).
