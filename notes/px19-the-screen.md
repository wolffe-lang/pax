# px19 — the screen (a graphical console)

Contract: px19's, `sprints/pax/19-the-screen/px19-the-screen.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-09). Branch `px19` in
pax, cut from pax trunk `ef4c3ca` (px16 merged). §1–§3 are committed
before the first change to the kernel and before the first boot that
could show what Limine hands over.

One deliverable: PAX draws its console on the framebuffer Limine hands
it — a text console with a bitmap font, colours (the common ANSI SGR
set), scrolling and a cursor — mirrored with the serial console, so a
QEMU window shows the boot, pelt's prompt and programs' output as a
machine's screen does; the PS/2 keyboard (px13) types into it.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source is
  read (ruling #22); the refs clone's sparse checkout is never widened.
  Hardware facts come from the Intel and AMD manuals, Limine's
  PROTOCOL.md, QEMU's documented device behaviour and black-box runs.
- No `region` held across a yield, a switch or a return to ring 3
  (wolf-lang#611). Nothing here allocates.
- Test binaries for PAX are built in the `px13-ubuntu` container on
  kasumi or on the CI runner, never with kasumi's CachyOS glibc.
- Nothing in pax names any use of the folders outside it, and no word
  in pax implies one (the contract's list of such words is not repeated
  here).
- px17 (pipes) is open on pax and merges first: this lane touches none
  of its files where avoidable (`kernel/files`, `kernel/paging`,
  `kernel/process`, `kernel/sched`, `kernel/user`, `boot/user.S`,
  `tests/mpx3-shell`, `tests/tour`, `kernel/pax_tour`, `kmain_tour.lu`'s
  one line) and rebases after it. px18 (the speaker) runs in parallel:
  whichever merges second rebases.
- No `rm` outside `~/lanes/px19/` (nomad-1, kasumi, hasu) and this
  lane's clone; no `git add -A`; nothing under `~/.claude`; no merge,
  no tag; no `2>/dev/null` on a checkout; no attribution trailers; no
  "seen red" without a run id, sha, path or digest. File checksums
  carry a trailing `…`. No build on nomad-1 (it boots finished ISOs).
- kasumi's disk is tight (29 GB free at the start): one tree set and
  cache under `~/lanes/px19/`, pruned as the lane goes.
- Font licence: a bitmap font that is public domain or GPL-3.0
  compatible, vendored with its licence file, recorded in
  `docs/SOURCES.md`.
- Strict evidence (wolf-lang#571): suites run with `PAX_REQUIRE_UEFI=1`
  and `WOLF_PAIRING_REQUIRE_SIBLING=1`, full output kept, `SKIP` lines
  counted.

## 2. Inputs, verified (2026-10-09, from origin)

| input | found |
|---|---|
| pax trunk | **`ef4c3ca`** (px16 merged, PR #19), as the contract says. CI green at `ef4c3ca`: run **37999687276**, all 16 jobs (census, proof, mkw, mpx1, mpx2-frames, mpx2-paging, mpx2-interrupts, mpx2-sched, mpx2-heap, mpx3-user, mpx3-loader, mpx3-boreutils, mpx3-console, mpx3-shell, tour, macos-run) |
| px17 | PR **#20**, draft, open, head `df5de90`; it touches `kernel/files`, `kernel/paging` (+66), `kernel/process`, `kernel/sched`, `kernel/user`, `boot/user.S`, `kernel/kmain_tour.lu` (1 line), `kernel/pax_tour`, `tests/mpx3-shell`, `tests/tour`, `README.md`, `kernel/README.md`, `docs/SOURCES.md`, `CHANGELOG.md` (new) — the last four are shared prose this lane also edits (rebase, by hand) |
| px18 | no branch on origin yet |
| Limine's framebuffer request | PROTOCOL.md at limine-protocol `3a0526b7` (the revision `docs/BOOT.md` cites), "Framebuffer Feature": id `{common magic, 0x9d5827dcd881dd75, 0xa3148604f6fab11b}`, revision 0; the response is `{revision, framebuffer_count, framebuffers}` (an array of pointers), each `struct limine_framebuffer` `{address (virtual, the HHDM), width, height, pitch, bpp (u16), memory_model (u8, 1 = RGB), red/green/blue mask size and shift (u8 each), unused[7], edid_size, edid, (rev 1) mode_count, modes}`; no response when there is no framebuffer |
| Limine's caching | PROTOCOL.md "Caching", x86-64: framebuffer regions are mapped by Limine write-combining through **`PAT[5]`** when the CPU has the PAT, and the PAT is laid out PA0 WB, PA1 WT, PA2 UC-, PA3 UC, PA4 WP, PA5 WC (PA6, PA7 unspecified); the memory map's type 7 (framebuffer) entries are "for illustrative purposes only" |
| PAX's paging | `kernel/paging` (px03) leaves memory-map type 7 **out** of PAX's HHDM ("it wants write-combining, a PAT choice for the lane that draws"); `paging.map` takes the leaf's flags as given, so a 4 KiB leaf can carry PWT (bit 3), PCD (bit 4) and PAT (bit 7) without a change to `kernel/paging` |
| PAT encoding | Intel SDM vol. 3A §11.12 (PAT): a 4 KiB PTE selects PAT entry `PAT*4 + PCD*2 + PWT`; IA32_PAT is MSR 0x277, one byte per entry, 0x01 = WC, 0x00 = UC; CPUID.01H:EDX bit 16 = PAT. So WC through Limine's layout is `PWT | PAT` = `0x88` on the leaf, and UC is `PCD | PWT` = `0x18` (entry 3, UC in both Limine's layout and the power-on default) |
| the console layer | `kernel/console` (px13): one line discipline over COM1 and the i8042; every byte the kernel or a program writes reaches the wire through `serial.put` (`kernel/log`, `kernel/console`'s echo, `kernel/user`'s `write`), so one hook there mirrors everything; `TIOCGWINSZ` answers `pax_con_state` word 13, 0 at `start` (0 rows 0 cols, what a Linux serial line and pseudo-terminal answer) |
| who reads TIOCGWINSZ | `ask` (user/elf/ask.S, px13's `ask tty`) prints it (`ask: winsize 0 rows 0 cols 0`, compared with Linux in `tests/mpx3-console`); boreutils' `ls` at `user/boreutils.pin` (`50d8907`) does not ask (`-1` is its default, `COLUMNS` its width); pelt at `dd22a86` has no termios surface |
| QEMU on nomad-1 | Homebrew `qemu-system-x86_64` 11.1.1: display backends `none`, `curses`, `cocoa`, `dbus` (`-display help`) |
| QEMU headless | `tools/qemu-run` boots `-nographic` (no `-vga` given: q35's default VGA device is present, its output shown nowhere); the monitor's `screendump FILE` writes the display surface as PPM |
| the font | **Spleen 2.2.0** (Frederic Cambus), release tarball `spleen-2.2.0.tar.gz` `ec42925c…`; `LICENSE` is the BSD 2-Clause licence (read in full; GPL-3.0 compatible: it asks only that the notice be kept); `spleen-8x16.bdf`: `FONTBOUNDINGBOX 8 16 0 -4`, 978 glyphs, every glyph `BBX 8 16 0 -4`; 192 code points below 256 (printable ASCII and Latin-1); no U+FFFD |
| kasumi | `/home` 97% (29 GB free); `px13-ubuntu` podman image present |

## 3. Prediction (committed before the first change)

- **Q1, the mode.** Limine hands over one framebuffer, the same under
  BIOS and UEFI: **1280×800, 32 bits per pixel, pitch 5120, memory
  model RGB with red 8 at 16, green 8 at 8, blue 8 at 0** (QEMU's
  std-vga EDID preferring 1280×800, which Limine picks when no
  resolution is asked for). Falsified by any other width, height, depth
  or mask on either firmware. (Confidence: about even on UEFI, where
  OVMF's GOP may offer a different set of modes; higher on BIOS.)
- **Q2, the grid.** Spleen 8×16 gives **160 columns × 50 rows**, no
  margin (1280/8, 800/16). Follows from Q1; falsified with it.
- **Q3, the scroll cost per line.** One scroll moves 49 rows of 16
  pixel lines × 5120 bytes = **4,014,080 bytes** and clears 81,920
  (`rep movsq`/`rep stosq` through the WC mapping). Measured in the test
  kernel by the PIT over 400 scrolled lines: **≤ 2 ms per line under
  KVM on hasu; 5–40 ms per line under TCG on kasumi**. Falsified by a
  figure outside either band.
- **Q4, the caching.** QEMU's `-cpu max` reports the PAT; IA32_PAT reads
  back with PA5 = 0x01 (WC), as Limine says, so **the framebuffer is
  mapped write-combining through PAT entry 5** on every leg. Falsified
  by the kernel choosing UC on any leg.
- **Q5, serial unchanged.** Every existing suite holds with trunk's
  PASS counts (CI 37999687276's jobs) with the screen drawn in the
  console, shell and tour kernels; only ISO and ELF digests move. The
  one exception planned for: `ask`'s `winsize` line, which reads the
  screen's grid when the screen is the console — so `tests/mpx3-console`
  boots its ask sessions serial-only (no VGA device), where the answer
  stays px13's `0 rows 0 cols`. Falsified by any other PASS count
  moving.
- **Q6, a boot with no display device.** `-vga none` under SeaBIOS and
  under OVMF: Limine boots the kernel and gives **no framebuffer
  response**; the kernel says so and the console stays serial only.
  Falsified by Limine refusing or hanging without a display.
- **Q7, the comparison.** A headless screendump of each test boot equals
  the host-side reference renderer's image of the same serial bytes,
  pixel for pixel, on both tiers, BIOS and UEFI — once the two
  implementations agree. Predicted: **at least one real disagreement**
  between the kernel's terminal and the reference renderer found during
  the lane (named in §4 when it happens).

## What was built

- **`kernel/screen`** (and `boot/screen.S`): the console drawn on the
  framebuffer. Every byte `serial.put` writes is handed to `screen.put`
  first (`kernel/serial`), so the screen and the serial console carry the
  same bytes; before the screen is attached they go to a 16 KiB early
  buffer and are replayed at attach, so the screen shows the boot from
  the kernel's first line. The terminal: ASCII and UTF-8 in Spleen 8×16
  (`?` for what the font lacks), deferred wrap, LF/CR/BS/TAB, CSI read
  whole with SGR 0 1 7 30–37 39 40–47 49 90–97 honoured, the PC's
  16-colour palette, a steady inverse cursor, scrolling with REP
  MOVSQ/STOSQ. IF clear while drawing; a re-entered `put` does nothing.
- **`kernel/fb`**: Limine's framebuffer (a ninth request in
  `boot/start.S`, its fields in `kernel/boot_info`) mapped at its HHDM
  address in PAX's tables, 4 KiB pages RW NX, **write-combining through
  PAT entry 5** when CPUID has the PAT and IA32_PAT's entry 5 is WC (it is
  on every leg measured: IA32_PAT `0x0000010500070406`), else uncached
  (PCD|PWT, entry 3). `kernel/paging` is untouched (its `map` takes the
  leaf's bits as given).
- **The font**: Spleen 2.2.0's 8×16 BDF, BSD-2-Clause, vendored
  unmodified with its licence (`font/`); `tools/mkfont` makes
  `boot/font.S` from it and `--check`s it.
- **`TIOCGWINSZ`** answers the screen's rows and columns (`50` and `160`
  at 1280×800) when the screen is attached; a boot with no display device
  (`-vga none`) gets no framebuffer and keeps px13's 0 by 0.
- **The kernels**: `kmain_console` (the shell's image) and the tour's two
  attach the screen after paging and print nothing new; `kmain_screen` is
  the screen's own test kernel.
- **The harness**: `tools/qemu-run --no-screen` / `tools/qemu-halt
  --no-screen` (`-vga none`); `tools/screen-ref`, the host-side reference
  renderer (the picture from the serial log, the glyphs read from the BDF,
  the terminal written again from the rules, not from the kernel's code);
  `tests/mpx3-screen` (V0–V6) and its CI job; `tests/mpx3-console`'s ask
  sessions boot with `--no-screen`, where the window size stays 0 by 0.

## 4. Evidence index

| claim | artifact |
|---|---|
| Q1/Q2: 1280×800, 32 bpp, pitch 5120, RGB 8:16 8:8 8:0, 160×50 cells, on BIOS and UEFI, both tiers | V1 lines: `notes/px19/kasumi-mpx3-screen-f0affda.out` (kasumi TCG), `notes/px19/hasu-kvm-mpx3-screen-f0affda.out` (hasu KVM), `notes/px19/ci-38019990181-mpx3-screen-fb845d9.txt` (CI, QEMU 8.2.2) |
| Q4: WC through PAT 5, IA32_PAT `0x0000010500070406` | the same V1 lines, every leg |
| the screendumps equal the reference, pixel for pixel: kmain_screen's pattern (V2), pelt typed through PS/2 (V5), ask (V6); 24 of 24 per host | `notes/px19/kasumi-mpx3-screen-f0affda.out`, `notes/px19/hasu-kvm-mpx3-screen-f0affda.out`; three of them as pictures with their grids: `notes/px19/kasumi-f0affda-native-bios-screen.png`, `…-native-uefi-pelt-ps2.png`, `…-native-bios-ask-ps2.png` (`.grid.txt` beside each) |
| Q3: a scrolled line costs 0.11–0.17 ms under KVM (hasu), 1.0–1.3 ms under TCG (kasumi), 1.2–1.35 ms on CI's TCG; 4,014,080 bytes moved a scroll | V3 lines in the three files above; the byte count in the halt record of the tour's red (`notes/px19/kasumi-red-fb845d9-tour-R5.out`: RDX `0x3d4000` = 49×16×5120 inside `pax_fb_copy`) |
| Q5: every suite's count as trunk's, the screen drawn | kasumi gauntlet at `f0affda`: `notes/px19/kasumi-gauntlet-f0affda.summary` (versions `…f0affda.versions`) — proof 2, census 3, mkw 16, mpx1 26, mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34, mpx2-sched 32, mpx2-heap 56, mpx3-user 38, tour 44, mpx3-boreutils 20, mpx3-console 100, mpx3-shell 128 (the `--images` legs: CI's counts less the build's PASS line), mpx3-screen 24; 0 FAIL, 0 SKIP |
| Q5's one miss: the screen still scrolling after the last serial line | kasumi gauntlet at `fb845d9`: tour R5 native UEFI NOT HALTED, RIP in `pax_fb_copy` (`notes/px19/kasumi-red-fb845d9-tour-R5.out`, `…fb845d9.summary`); fixed by `178ce3e` (the screen drawn before the UART); green at `f0affda` |
| V4 and V6 seen red before they were right (the test's expectations, not the kernel) | CI run **38019990181** at `fb845d9`, job 114118643024 (mpx3-screen; every other job green): V4 ×4 (Limine's CR3 and the full-width rows differ with the display device), V6 ×4 (ask prints `winsize <result> rows <r> cols <c>`) — `notes/px19/ci-38019990181-mpx3-screen-fb845d9.txt`; kasumi the same (`notes/px19/kasumi-red-fb845d9-mpx3-screen.out`); fixed by `f0affda` |
| Q6: no display device, no framebuffer, serial only | V4 lines (`screen: off, no framebuffer`, 413 serial lines byte-identical to the screen run's but the display-dependent ones), every leg, every host |
| the planted break: colour 3 drawn `aaaa00` instead of brown `aa5500` (one palette entry; no serial byte changes) | CI run **38024480797** at `f734ef8` (the plant before the rebase; `9ab30ca` after it), mpx3-screen job 114132277455: **V2 FAIL on all four legs**, 1132 of 1024000 pixels, the first in the pattern's `fg33`; 20 PASS (V5 and V6 hold: no colour 3 on those screens); every other job green — `notes/px19/ci-38024480797-mpx3-screen-plant-f734ef8.txt`; kasumi the same (`notes/px19/kasumi-red-f734ef8-plant.out`); reverted |
| the window on nomad-1 | `-display cocoa` boots of `kmain_screen.iso` and of the shell and tour images (Homebrew QEMU 11.1.1, TCG): each window's monitor `screendump` identical to `tools/screen-ref`'s picture (kept outside pax with the images) |
| the shell and tour images with px17's work merged | a local merge `22bc18d` (px19 `f0affda` + px17 `df5de90`, prose conflicts only): mpx3-console 100, mpx3-shell 152, mpx3-screen 24, tour 44, 0 FAIL (`notes/px19/kasumi-integration-22bc18d.summary`). px17 then merged as trunk `df5de90` and px19 was rebased onto it: every file outside the prose (README, kernel/README, docs/SOURCES.md, CHANGELOG.md, notes) is byte-identical to `22bc18d`'s (`git diff --stat 22bc18d HEAD` on the code: empty), so these runs and the images built there are the rebased head's |
| boot counts | serial logs left by the boots (`find build -name '*.serial.log'`): kasumi `f0affda` 186 (mpx3-screen's 20), the integration tree 76, hasu KVM 20 (mpx3-screen); mpx3-screen boots 20 per run (5 boots × 2 tiers × 2 firmwares) in every CI run |

## The prediction against the measurement

| prediction | result |
|---|---|
| Q1: 1280×800, 32 bpp, pitch 5120, RGB 8@16 8@8 8@0, BIOS and UEFI alike | **right**, on kasumi (QEMU 11.1.1 TCG), hasu (KVM) and CI (QEMU 8.2.2): every V1 line. The framebuffer sits at `0xffff8000fd000000` under SeaBIOS and `0xffff800080000000` under OVMF |
| Q2: 160 × 50 cells, no margin | **right** |
| Q3: 4,014,080 bytes a scroll; ≤ 2 ms a line under KVM; 5–40 ms under TCG | bytes **right** (RDX in the halt record of the tour's red); KVM **right** (0.11–0.17 ms); TCG **wrong**: 1.0–1.3 ms on kasumi, 1.2–1.35 ms on CI — REP MOVSQ is one helper loop in TCG, not an instruction at a time, which I did not count on |
| Q4: WC through PAT entry 5, IA32_PAT entry 5 = 0x01 | **right**, every leg: `0x0000010500070406` |
| Q5: every existing suite's count unchanged with the screen drawn; only ask's winsize moves, so its sessions boot serial-only | **right at `f0affda`**, but **wrong at `fb845d9`** on one leg: tour R5 native UEFI on kasumi caught the kernel inside `pax_fb_copy` after the PANIC line had reached the serial port — `serial.put` wrote the UART first and drew second, so the last line's scroll ran after the harness saw the line. `178ce3e` draws first. CI at `fb845d9` did not catch it (tour green there): a race that kasumi's load exposed |
| Q6: `-vga none` boots, no framebuffer response | **right**, every leg |
| Q7: at least one real disagreement between the kernel's terminal and the reference renderer | **wrong**: none. Every screendump equalled the reference from the first boot (nomad-1, before the test existed). The two reds `mpx3-screen` showed were in the test's expectations (V4's display-dependent lines, V6's reading of ask's line), not in either terminal |

## 5. Done-when

- [x] Branch `px19` on origin, rebased onto trunk `df5de90` (px17
  merged); PR #21 open, unmerged.
- [x] §1–§3 committed before the first change (`55972d9`, rebased to the
  same content).
- [x] The screen, the font with its licence (`font/LICENSE.spleen`,
  `docs/SOURCES.md`), `TIOCGWINSZ`, the tests (`tests/mpx3-screen`, CI
  job `mpx3-screen`), the shell's and the tour's kernels drawing it.
- [x] Planted break red in CI (run 38024480797), reverted.
- [x] Both folders outside pax refreshed from this code (the tour's and
  the shell's images, the source snapshot, a window command in each
  README; their terminal steps unchanged), both preflights GO.
- [ ] CI green at the head (the PR body names the run).
- [x] Worktrees gone; kasumi, hasu and nomad-1 outputs pruned; no
  orphans of this lane's.
- Close nothing. To close: none (no issue was filed or named for this
  lane).
