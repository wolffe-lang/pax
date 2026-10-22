# px59 — The console for an editor

Contract: px59's, `sprints/pax/59-the-console-for-an-editor/px59-the-console-for-an-editor.md`
in wolffe-lang/wolf (read 2026-10-21), under `sprints/RULES.md` and Track
13's rules (`sprints/pax/index.md`). Branch `px59` in pax, cut from pax
trunk `0681c57` (px57) by two Codex agents whose connection kept
dropping, stacked on px58's `d13d6f9` by the third agent and, px58
fast-forwarded to trunk, on trunk `d13d6f9`. The first two agents'
committed steps were verified against the branch and kasumi before
being built on (§2); one of them had never compiled (§2). The two
predictions (`notes/px59/prediction.txt`, its addendum) were committed
before the first change and before the second measurement.

px58 (pax#111) put yew on PAX byte-identical over COM1 and measured
what the framebuffer console dropped. This lane makes the screen draw
what the console receives as a Linux VT draws it, and the keyboard give
what the VT's gives, so yew at PAX's screen and keyboard is the editor
it is on a VT.

## 1. Forbidden, absolutely

- No kernel's source was read or searched for, Linux's above all, nor
  any libc's, terminal driver's or terminal emulator's, nor any editor's
  but the maintainer's (yew `77c1083`: `src/term/tty.lu`,
  `runtime/init.fl`; pelt `90d7c64`: `src/sh/edit.lu`,
  `src/sh/interact.lu`; read and cited, never changed). Facts about the
  VT come from `console_codes(4)`, `vcs(4)`, `console_ioctl(4)`,
  `termios(3)`, ECMA-48 for the names, and black-box runs: kasumi's own
  kernel image (7.2.8-1-cachyos, `f4c00d5d…`) under QEMU 11.1.1 with
  its VGA display and PS/2 keyboard, a probe as pid 1 sending bytes to
  `/dev/tty1` and reading `/dev/vcsa1` and the input back
  (`notes/px59/vtprobe.c`, `vtprobe2.c`). `wolf/refs/repos/linux` not
  opened. No filming words. Sources in `docs/SOURCES.md` (px59).
- Builds in `px13-ubuntu` on kasumi (`ulimit -c 0`); QEMU under
  `taskset -c 0-3`; jobs `setsid -f` with pid files, none killed (one
  stuck boot ended through the lane's own monitor socket's `quit`); no
  build on nomad-1; nothing installed. No line of yew changed. No issue
  filed or closed (§J). No attribution trailer.

## 2. Inputs, verified (2026-10-21)

- pax trunk `0681c57` (px57) at the cut; px58's branch `d13d6f9`, then
  trunk at `d13d6f9` (pax#111 fast-forwarded); `kernel/wolf.pin` wolf
  0.2.34 (`88a9dd3d…`, staged by `tools/fetch-wolf`, its digest checked
  by the tool); yew `77c1083` by its own 0.2.33 (`tools/mkyew`), pelt
  `90d7c64` (`user/pelt.pin`).
- The previous agents' steps, checked: the prediction (`126a2c0`, was
  `83502c5`), the VT measured twice (`98eedf7`, was `012dfa9`: kasumi's
  `out/vt.rows` `4ada93fb…` the same bytes as the branch's, the two runs
  compared by `vt-run.py`), the indexed palette (`e50d81d`/`077ddf8`,
  was `71b72df`/`4fd977c`), the cursor and erase classes, OSC, DECSC/
  DECRC, the alternate screen's layout (`d658978`). The "first kernel
  compiled" was compiled at 21:14, before the erase, colour, OSC, save
  and alternate-screen commits; at their head the kernel did **not
  build** (`put_cell`'s pointer casts outside `unsafe`, E1301): fixed in
  `9724540`. The pre-stack shas are on `px59-prerebase`.
- kasumi `~/lanes/px59` held the measure and build trees and a copied
  (not cloned) pax tree, kept aside as `pax.copy-codex`; nothing running.

## 3. Prediction

`notes/px59/prediction.txt`: P1–P5 (the first agent's, `126a2c0`), P6–P10
(the addendum, `d1d896a`, before `vtprobe2.c` ran and before any change
to the queries or the keyboard).

## 3a. The prediction, scored

| | predicted | measured | verdict |
|---|---|---|---|
| P1 | screen-ref knows text, UTF-8, the wrap, CR LF BS TAB, the basic SGR, a cursor always shown; none of the editor's classes | so (trunk's `tools/screen-ref`) | right |
| P2 | a second buffer costs 8 frames at 160×50, 32 at 256×128; the VT ignores `?1049` and DECSCUSR | the VT **serves** `?1049` (cleared on entry, the cursor kept, main screen and cursor and rendition restored on leave, a second h or l nothing); DECSCUSR consumed (vcsa shows no shape); the layout chosen costs **0** frames (§C) | wrong on `?1049`; the cost moot |
| P3 | DA1 `ESC[?6c`, 6n the 1-based position, kitty and DECRQM 2026 unanswered; the last input device must gate the answers | all so; gated (R-px59-4) | right |
| P4 | F1–F5 `ESC[[A`–`E`, F6–F12 `ESC[17~`…`24~`; modified arrows not all `CSI 1;m X`; left Alt ESC; right Alt AltGr | the F-keys so; **every** arrow takes `CSI 1;m X` (Alt alone on Left/Right: nothing); right Alt is AltGr (hex entry: AltGr+a gives 0x0a on release) | right but the arrows |
| P5 | the smear gone with CUP and SGR 22/27; cell-for-cell agreement needs the reference changed alongside and the keyboard's 50×160 | yew's first frame typed at the keyboard: 8,000 of 8,000 cells screen-ref's (S2 `yew-opened`) | right |
| P6 | arrows `CSI 1;m X`, m = 1+Shift+2Alt+4Ctrl; Alt+Left/Right maybe nothing; the editing block unmodified; Shift+PgUp/PgDn nothing | all so | right |
| P7 | Shift+F1–F8 F11–F20's codes, Shift+F9–F12 `33~ 34~` or nothing; Ctrl+Fn plain; Alt+F1 nothing | so; Shift+F9/F10 `33~`/`34~`, Shift+F11/F12 themselves; Shift+Ctrl+Fn nothing (not predicted) | right |
| P8 | left Alt: ESC then the key (Alt+Shift+a ESC A, Ctrl+Alt+a ESC 01, Alt+Backspace ESC 7f, Alt+Enter ESC 0d) | so but **Alt+Shift+a and Alt+Shift+1 give nothing**; Alt with a keypad key no ESC (Alt+kp_1 decimal entry) | wrong on Shift |
| P9 | ESC Z and `CSI 0 c` as DA1, DSR 5 `ESC[0n`, the wrap's column itself, the alternate screen's own position; DA2, DECXCPR, OSC 11 unanswered; yew's probe DA1 alone; echoed in canonical mode | all so but **DECXCPR (`CSI ? 6 n`) is answered as `CSI 6 n`** | right but DECXCPR |
| P10 | SGR 2 3 4 as colours, 5 the blink bit; 38;2 nearest of 16; a 9th parameter does not end CUP on the VT; ICH DCH ECH IL DL DECSTBM served; `?1049h` clears in the current background; a scroll on one screen leaves the other | all so | right |

## A. The VT, measured

Two probes, each run twice on kasumi's kernel's VT, the two runs'
rows compared byte for byte by their drivers (`notes/px59/vt-run.py`,
`vt-run2.py`, `vt2.sh`; `notes/px59/kasumi-vt2.out`):

- `vtprobe.c` → `notes/px59/vt.rows` (51 rows, `4ada93fb…`): 25 screen
  cases (CUP HVP, relative moves, HPA VPA, clamps, ED and EL 0 1 2,
  DECSC/DECRC, five `?1049` cases, SGR 22 27, 100–107, `38;5`/`48;5`,
  OSC to BEL and ST, DECTCEM, DECSCUSR, erase in a colour), the 256
  indexed colours as foreground and background, 4 queries, 20 keys.
- `vtprobe2.c` → `notes/px59/vt2.rows` (188 rows, `97fa8e11…`): 48
  screen cases (SGR 2 3 4 5 8 9 21, with colours, truecolour, lists, the
  colon form, empty parameters; CUP private, nine and seventeen
  parameters, huge, with an intermediate; the wrap with CUP BS CR; CNL
  CPL; ICH DCH ECH IL DL DECSTBM; a scroll and ED in a background; six
  more `?1049` cases among them one that scrolls on both screens and
  switches back; `?1047` and `?47` ignored; DECTCEM; every DECSCUSR;
  the VT's own `CSI ? n c`; OSC ended by ESC, with a C0 byte inside,
  `OSC P`, OSC 11; the private modes yew writes; kitty's; DECRQM), 16
  queries, 2 echo rows (a query in canonical mode), 121 keys (every
  modifier on the arrows, the editing block, F1–F12 with Shift, Ctrl
  and both, Alt with letters, digits, Enter, Backspace, Tab, Esc, Space,
  punctuation and the keypad, right Alt, the keypad, the console
  switches; `VT_GETSTATE` after each: no switch happened).

## B. The gap table, re-measured

Every class held twice: `tools/screen-ref` against the VT's rows case
by case (`tests/mpx5-screen.d/vtcheck.py`: **80 cases the VT's, 17
named**, every cell of 80×25 and the cursor, each answer), and PAX's
screen against the VT's rows directly on the VT's own 80×25 grid
(`tests/mpx5-screen` S1, BIOS: **60 the VT's, 17 named, 20 of 20
answers**) and against screen-ref pixel for pixel on every leg (77 of
77 screens).

**Served** (PAX's screen is the VT's, cell for cell): CUP, HVP, CUU,
CUD, CUF, CUB, CNL, CPL, CHA, HPA, VPA, defaults and clamps, a private
or intermediate CUP ignored; ED 0 1 2 and EL 0 1 2 (the cursor's cell
included, blank in the current rendition); DECSC/DECRC (one slot for
both screens); `?1049h/l` (entered: cursor and rendition kept, the
alternate screen cleared in the current background, the cursor where
it was; left: main screen, cursor and rendition as left; nested h and
repeated l nothing; a scroll on either screen leaves the other); `?1047`
and `?47` ignored, as the VT; `?25l/h`; DECSCUSR consumed; the VT's
`CSI ? n c` consumed; SGR 0 1 7 22 27 30–37 39 40–47 49 90–97, empty and
listed parameters, `38;5`/`48;5` (all 256 each way, R-px59-3); SGR 8 9
ignored as the VT; OSC to BEL, to ST, to any ESC (the next byte read as
an escape's), a C0 byte inside consumed, `OSC P` with seven digits,
`OSC R`, OSC 11; the private modes yew writes (paste, mouse 1002/1006,
focus, sync), kitty's push/pop/query, DECRQM: consumed; the deferred
wrap, BS at the margin (R-px59-5), CR; a scrolled-in row blank in the
current rendition. **Answered** (typed into the input once the
keyboard is typed at): DA1 `CSI c` and `CSI 0 c` and DECID `ESC Z` →
`ESC [ ? 6 c`; DSR 5 → `ESC [ 0 n`; DSR 6 and `CSI ? 6 n` → `ESC [ r ; c
R` (the wrap's column itself, the alternate screen's own position); DA2,
OSC 11, kitty's `CSI ? u`, DECRQM 2026 unanswered; yew's probe string
DA1's answer alone; two queries both answers; in canonical mode with
ECHO the answer echoed `^[[?6c` (the VT's echo rows, cell for cell).
**The keyboard** (§E): every key of `vt2.rows` but the named ones.

**Divergent, named**: SGR 100–107 drawn bright (R-px59-1); a CSI of 9
to 16 parameters (the VT acts, PAX ignores more than 8); DECSCUSR drawn
as a block whatever the shape (recorded; the VT's own shape is not in
vcsa: not measured); the answers withheld before any input and after
COM1 input (R-px59-4); right Alt adds nothing (R-px59-2: the VT's AltGr
enters a character by its hex code on release).

**Dropped, measured** (the VT draws them, PAX does not; none is yew's
or pelt's, px58's census): SGR 2 (the VGA VT's colour 8), 3 (green), 4
and 21 (cyan), 5 (the blink bit); `38;2`/`48;2` (the VT's nearest of
16; PAX skips them); the colon form `38:5:n`; ICH, DCH, ECH, IL, DL,
DECSTBM; `OSC P`'s palette (consumed, not applied); the keypad's digits
and point (the VT, NumLock off: the editing keys; `kp_1` measured as End);
Alt with a keypad key (the VT's decimal entry). Kept as px58 found them
(small, not this lane's: pax#116): OCRNL and OLCUC, cflag CS6, CS7,
CREAD, PARENB.

A resize is not a VT's: a VT's grid is its font's and mode's, which no
program here asks for; PAX's screen is the framebuffer's (160×50, or
80×25 at 640×400). What PAX answers a resize under yew is px58's Y1
(TIOCSWINSZ read back, SIGWINCH sent and not resent; served). No row
resizes the screen.

## C. The screen (`kernel/screen`, `tools/screen-ref`)

`kernel/screen/screen.lu`'s header states the rules; screen-ref's
header the same, from the rules and not the code. The alternate
screen lives in the upper 16 bits of each 32-bit cell of
`pax_screen_cells` (the main screen in bits 0–15, as px19 laid it out),
allowed as an engineering choice:

- **layout**: a cell is `glyph | fg << 8 | bg << 12`; `put_cell` and
  `cell` read and write the active half (`S_ALT`); the inactive half is
  never touched while the other is shown;
- **the scroll rule**: the framebuffer's pixel rows move by REP MOVSQ as
  before; the cells move one by one, the active half only (`put_cell(i,
  cell(i + cols))`), so the other screen never moves; the new row is a
  blank in the current rendition;
- **the frame cost**: none. The kernel's data and bss segment is
  0x437078 bytes on trunk `d13d6f9` and on px59 (`readelf -lW`,
  kmain_console native, kasumi); `pax_screen_cells` is 128 KiB (32
  frames) in both. A second grid would have been 32 frames more at the
  largest grid (8 at 160×50). The code grew 13,120 bytes (the classes,
  the answers, the keyboard). The time: a scrolled line, mpx3-screen V3
  under TCG on kasumi, 1.83 ms on trunk, 2.92 and 3.57 ms on px59 (the
  per-cell copy; kasumi's load 9.9–13 across the runs: a measurement, no
  bound); leaving the alternate screen redraws the 8,000 cells;
- **the row** that scrolls on both screens and switches back: the VT's
  case `1049-scroll-both` (28 lines on the main screen, `?1049h`, 27 on
  the alternate one, `?1049l`, one more line), PAX's screen the VT's
  cell for cell on 80×25 (S1) and screen-ref's pixel for pixel; plant C
  (§H) moves both halves and that row alone goes red.

The answers: DA1, DECID, DSR 5, DSR 6 and `? 6` queue their bytes in a
32-byte ring in four of the state's words (the save slot packed into
two words made room; `pax_screen_state` stays 64 words). `pub fn answer`
hands them out one at a time.

## D. The queries (`kernel/console`, `kernel/user`)

`console.answered()` takes the screen's answers after every console
write (`kernel/user`'s `write`, `put_kernel`) and at every `read` and
`readable`, and types them into the input through the line discipline
(so canonical mode echoes them, as the VT's do) — when the keyboard is
the device input last came from (`C_SRC` 2, px48's `typed_at`). Before
any input, and after COM1's, they are dropped and counted (`C_ANSWERS`,
`C_UNANSWERED`): R-px59-4. A reader already waiting is woken
(`sched.wake_input`). What the answers do, measured: yew's probe
reaches its DA1 fence (Y7: its bytes unchanged from Linux's, where no
answer comes); a pelt started from the keyboard is answered and asks
before every prompt (S3: two `ESC [ 6 n` from the typed `sh -i` on, its
first prompt's and the one after `printf abc`, where an unanswered pelt
asks once: plant B); the 20 answers of the VT's probes the VT's (S1).

## E. The keyboard (`kernel/console`)

Left and right Alt tracked (`K_LALT`, `K_RALT`). The arrows `ESC [ 1 ;
m X` with m = 1 + Shift + 2 Alt + 4 Ctrl (left Alt alone on Left or
Right: nothing, the VT's console switch); the editing block unmodified,
Shift+PgUp/PgDn nothing; F1–F12 (`ESC [ [ A`–`E`, `ESC [ 17 ~`–`21 ~`,
`23 ~`, `24 ~`), Shift+F1–F10 F11–F20's codes, Shift+F11/F12 themselves,
Ctrl+Fn plain, Alt or Shift+Ctrl with Fn nothing; left Alt sends ESC
before a character key's byte (Ctrl applied: Ctrl+Alt+a ESC 01), Alt
with Shift nothing, the keypad's keys no prefix; right Alt adds nothing.
mpx5-yew Y3 sends 51 keys through the monitor and reads 188 bytes, each
key's the VT's.

## F. The rows

`tests/mpx5-screen` (new; tests/mpx3-screen's shape):

| row | what |
|---|---|
| S0 | the build; screen-ref against the VT's rows case by case (vtcheck.py: 80 the VT's, 17 named) and its 29 unit rows (term.py) |
| S1 | the VT's two probes played on PAX by `user/elf/vtcases.c` (`tools/mkvtcases`), the image booted by `boot/limine-vt.conf` (640×400: 80×25 under the BIOS); each of 77 screens taken after the case's name (an OSC string) reaches the serial log: screen-ref's pixel for pixel; on 80×25, the VT's cells and cursor (the named classes still different); the 20 answers the VT's; on 160×50 (OVMF ignores the resolution) said so loudly and counted, the answers' one grid-dependent row (CPR at the 80th column) by name |
| S2 | yew typed at the PS/2 keyboard (`user/console/yew-screen.keys`, `tools/ps2-session`): opened, edited, saved, the message expired, C-z, `fg`, quit, the shell, `cat`: 9 screens, each screen-ref's at the moment taken, pixel for pixel and cell for cell; notes.txt alpha beta gamma delta |
| S3 | `sh -i` typed at the keyboard: the inner pelt answered (it asks `ESC[6n` before every prompt only once answered: 2 from the typed line on; kasumi's `s4` and `r1` counted from the run line, `/bin/sh -i -m`, so 3 with the outer pelt's boot query, fixed in `8fc2c0c3`), its prompt after `printf abc` screen-ref's |
| S4 | per boot: nothing refused, init's end, halted |

`tests/mpx5-yew` (px58's) extended:

| row | what |
|---|---|
| Y2 | the halted screen of the probe image is screen-ref's picture of the boot's bytes (px58's per-class reading of dropped classes retired: they are served) |
| Y3 | 51 keys, 188 bytes, each the VT's (px58's ten and the F-keys, the modifiers, Alt, right Alt, five keys that give nothing) |
| Y6 | yew suspended and continued over COM1 (`user/console/yew-tstp.keys`: `G`, C-z, `jobs`, `fg`, `:q`): 5,519 bytes byte-identical to the container's, `Stopped` on both |
| Y7 | yew typed at the PS/2 keyboard (px58's `yew.keys`, the same file, through `tools/ps2-session`), the window the screen's 50×160 and DA1 answered: 10,580 bytes byte-identical to the container's on a 50×160 pseudo-terminal (`tools/linux-tty --winsize`) |

`tests/mpx3-screen`'s pattern (kmain_screen) keeps its "ignored:" line
to sequences the screen still ignores (px19's `ESC[2J`, `?25l`, `CSI 5
A` are served now) and gains a "served:" line (save, move, restore, the
alternate screen, OSC, SGR 22 27 101, the 256 colours, EL in a
background): V2 pixel for pixel.

Wired: `.github/workflows/ci.yml`'s `mpx5-screen` job; `tools/ci-tiers.map`
(mpx5-screen in @user, @console, @asuser; the new paths); `tests/ci-plan`.

## G. The screen-compare counts

On kasumi, native BIOS (`notes/px59/kasumi-*.txt`):

- S1: 77 screens of 77 screen-ref's (640×400: 2,000 cells each, 154,000
  cells); against the VT 60 cases the VT's and 17 named, 0 failed; 20
  answers of 20.
- S2: 9 screens of 9, 72,000 of 72,000 cells; S3's `pelt-6n` 8,000 of
  8,000.
- mpx3-screen V2, V5, V6: 8,000 of 8,000 cells each; mpx5-yew Y2 8,000
  of 8,000.

## H. The plants

Each a branch never merged, one commit, dispatched `-f tier=pr -f
suites=<suite>` (a `tier partial` run of the one suite on native BIOS),
each red at its predicted rows only (extracts `notes/px59/ci-*.txt`):

| plant | the break | run, job | red at | green at | verdict |
|---|---|---|---|---|---|
| A, `px59-plant-a` `d8e13f16` (on `0143a8f9`) | the function keys give nothing; the keyboard's window 0 by 0 (`kernel/console`) | **39714120050**, mpx5-yew 119612218195 | Y3 (the F-keys' bytes missing), Y7 (yew lays out 24 by 80: the bytes part at 212) | Y0, Y1 (root, pax, screen), Y2, Y4, Y5, Y6 | as predicted |
| B, `px59-plant-b2` `a5075e17` (on `8fc2c0c3`) | no DA1 answer, no cursor report (`kernel/screen`) | **39715558112**, mpx5-screen 119616889244 | S1: 13 of 20 answers (DA1, `CSI 0 c`, DECID, every CPR, DECXCPR, yew's probe, the pair) and the two echo cases; S3 (the inner pelt asked once) | S0, S1's 58 other cases and 7 other answers, S2, S4 | as predicted |
| C, `px59-plant-c2` `19547851` (on `8fc2c0c3`) | a scroll moves both screens' halves (`kernel/screen`) | **39715560492**, mpx5-screen 119616894200 | S1: `2:1049-scroll-both` alone, 27 of 2,000 cells, against screen-ref and the VT | S0, S1's 76 other screens and 20 answers, S2, S3, S4 | as predicted |

The control: the head `8fc2c0c3` unplanted, the same dispatch (run
**39715530933**, job 119616809830; and 39715533528): every row green on
CI's runner (S1 60 the VT's, 17 named, 20 answers; S2 72,000 of 72,000
cells; S3 two reports). Plants B and C were first cut on `0143a8f9`
(`px59-plant-b` `8fea130e`, run 39714122253; `px59-plant-c` `97dd7443`,
run 39714124627), before three harness fixes (`vtcases`' BG palette by
its name and the echo cases' flush, the answers read past the clear):
red where predicted but also where those bugs were, so cut again; B's
first run also showed S3 counting from the kernel's run line (the
outer pelt's query counted): fixed in `8fc2c0c3` and red in B2.

## I. Rulings

- **R-px59-1** (answered): PAX keeps its bright backgrounds for SGR
  100–107 (a documented divergence; the VGA VT draws them without
  brightness). Named in vtcheck and S1.
- **R-px59-2** (answered): ESC prefix on left Alt only; right Alt
  unserved (the VT's AltGr hex entry).
- **R-px59-3** (answered): the measured VT 256-colour mapping into the
  16, as implemented: all 512 entries the VT's (S0, S1).
- **R-px59-4** (asked; taken meanwhile as implemented): the screen's
  answers are typed only when the keyboard was the device last typed at;
  before any input and after COM1 input they are dropped. A VT answers
  always, but PAX's console is a serial line and a screen at once: an
  answer before anyone types would reach a serial terminal that answers
  for itself (two answers), and pelt, once answered, asks before every
  prompt and waits 300 ms each time it is not, so every session typed
  over COM1 would change (px58's Y4, byte-identical to Linux, among
  them). **Recommendation: keep.** The cost: a pelt started at boot by
  a person at the screen asks once, unanswered, and assumes column 0
  (right after its motd); a pelt started from the keyboard is answered.
- **R-px59-5** (asked; the VT's behaviour taken meanwhile): BS with a
  wrap pending clears it and moves one column left, as the measured VT
  (`wrap-BS`); px19 only cleared the wrap, so the line discipline's `\b
  \b` erased the last column's character, where the VT's erases the one
  before it. **Recommendation: keep the VT's** (the editor's and the
  line discipline's echo then look as on a VT).

## J. Issues

To close at merge (by hand: no `closes` phrasing closes them): **pax#114**
(px58's gap table: served or named here) and **pax#115** (suspend and
continue, the keyboard instead of COM1: Y6, Y7; the resize: §B).

To file (pax, none filed):

1. The screen drops SGR 2, 3, 4, 5, 21 (the VGA VT draws them as colours
   8, 2, cyan and the blink bit), `38;2`/`48;2` (the VT's nearest of 16)
   and the colon form (`notes/px59/vt2.rows`; named in vtcheck).
2. ICH, DCH, ECH, IL, DL and DECSTBM are dropped (the VT serves them;
   not yew's or pelt's, but a pager's or vi's).
3. A CSI with 9 to 16 parameters is ignored (the VT takes 16).
4. `OSC P`'s palette is consumed, not applied; `OSC R` likewise.
5. The keypad without NumLock gives nothing (the VT: the editing keys);
   Alt with a keypad digit (the VT's decimal entry) and AltGr's hex entry
   unserved (R-px59-2).
6. DECSCUSR's shape is recorded, not drawn (PAX's cursor is a block).
7. A scrolled line costs about 1.6–2× trunk's under TCG (the per-cell
   copy of the active half; §C): a back buffer would serve both.

Carried from px58's §I: pax#116 (OCRNL, OLCUC, the cflag bits; filed);
yew: `G` then `o` on the phantom last line (not checked against C yew
here either).

## K. The legs on kasumi

Under `taskset -c 0-3`, TCG, the builds in `px13-ubuntu`:

- native BIOS (the merge gate's leg): mpx5-screen S0–S4 PASS (`s4`),
  mpx5-yew Y0–Y7 PASS (`y1`), mpx3-screen V0–V6 PASS (`s3`, the
  extended pattern); trunk `d13d6f9`'s mpx3-screen beside it (`t1`);
- release UEFI: mpx5-screen S0–S4 PASS (`r1`; S1's direct comparison
  with the VT skipped loudly and counted, 77 screens not 80×25: OVMF
  gives 1280×800 whatever Limine asks; every screen screen-ref's, the 20
  answers the VT's with CPR at column 80 the 160-column grid's), mpx5-yew
  Y0–Y7 PASS (`r2`: Y4 3,732 bytes, Y6 5,519, Y7 10,580, each the
  container's).

The other legs (native UEFI, release BIOS) are the trunk push's.
Logs: `notes/px59/kasumi-mpx5-screen-native-bios.txt`,
`kasumi-mpx5-yew-native-bios.txt`, `kasumi-mpx3-screen-native-bios.txt`,
`kasumi-release-uefi.txt`.

## L. The playground (item 4)

The orchestrator's `~/lanes/orch-paxplay/build.sh` and `assemble.sh` on
kasumi, changed by `notes/px59/playground.sh` as px57's script changed
them (the pre-edit copies kept at kasumi `~/lanes/px59/ev/`,
`orch-build.sh.before` `e8c6ca5f…`, `orch-assemble.sh.before`
`d41b1a76…`; after: `48a874e9…`, `512cb1b8…`): its pax clone moved to
this branch's `e187317` (the kernel's code as at the head), and, so the
maintainer's `yew notes.txt` has a yew to run, build.sh gains
`tools/mkyew` (yew `c2daa653…`, px58's bytes) and assemble.sh a
stripped `/bin/yew` and a motd line naming it. Every builder rc 0
(`notes/px59/kasumi-playground.txt`). **`pax-playground.iso`
`a45e2bf49e54dde091b14fa227ed8991614c381539aa8f76f97948e7a23994e7`**
(82,534,400 bytes; px57's `242ecec2…`), read twice on kasumi, copied to
nomad-1 as `~/pax-playground/pax-playground.iso` with px57's kept as
`pax-playground.iso.px57`, read twice there: the same digest.

The maintainer's session, typed at the PS/2 keyboard
(`notes/px59/playground.keys` through `tools/ps2-session`, BIOS, TCG,
`notes/px59/playground-boot.sh`): `cd /tmp`, `yew notes.txt`, `i`, a line
typed, Esc, `:w`, `:q`, `cat notes.txt`, `exit`. Four screens taken
(yew opened, the line typed, saved, the shell after), **4 of 4 screen-ref's
pictures of the serial bytes at the moment taken, 32,000 of 32,000
cells**; `cat` reads the typed line back (yew wrote it with no final
newline, its own behaviour: the next prompt follows it on the line);
halted; `console: 0 bytes from com1, 87 keys (184 scancodes) from the
keyboard` (`notes/px59/kasumi-playground-session.txt`).

## M. What was not done

- Nothing of §B's dropped list is implemented (§J 1–6).
- The VT's cursor shape and visibility are not in `/dev/vcsa1`: PAX's
  DECTCEM is console_codes(4)'s and yew's, not measured on the VT.
