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
- No word implying filming, recording, viewers or a demo anywhere in
  pax; nothing in pax names any use of the folders outside it.
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
