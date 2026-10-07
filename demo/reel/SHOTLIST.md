# PAX — the shot list

A short film in four scenes: a kernel written in wolf boots on this MacBook, inside QEMU, and walks through what it can do today, ending in a panic it causes on purpose.

How to read a scene: **SHOW** means put this on screen and hold it; **RUN** means type this command and let the output land; the time is how long the shot holds. Times are targets for the edit, not limits. The times inside the boot (scene 2) are measured, not targets: the kernel paces itself.

Every command on camera is typed by you, in full, in fish: no scene scripts. Every line the boot prints is printed by the running kernel; the pauses between its stages are pauses for the viewer, written into the kernel as such (`src/kernel/reel/reel.lu`, every `PAUSE` comment). Only `preflight.sh` stays a script, and it runs off camera. Rehearsed end to end on this MacBook on 2026-10-06 (the timings below are from that rehearsal).

---

## Before you press record

| step | command | what you should see |
|---|---|---|
| terminal | a dark theme, a font size that fits **125 columns** across the screen (145 if you film finale b: its PANIC line is 145 wide), 30 rows or more | the longest line of finale a (the `apic:` line) on one row |
| go to the demo | `cd /Users/mfwolffe/scratch/wolf/pax-demo` | `pax-reel.iso`, `pax-reel-b.iso`, `SHA256SUMS`, `src/`, this file |
| preflight | `bash /Users/mfwolffe/scratch/wolf/pax-demo/preflight.sh` | five `ok` lines, then `GO` on the last line (it boots the reel once, headless, about 30 s) |

Do not film until the preflight prints **GO**. If it prints `NO GO`, it names the failing step; the usual one is the terminal's width.

Nothing runs in the background. Each boot is one QEMU in the foreground of your terminal; **Ctrl-C** ends it (QEMU prints `terminating on signal 2`).

---

## Scene 0 — "A kernel written in wolf" (about 20 s)

| # | action | command | hold |
|---|---|---|---|
| 0.1 | SHOW the size of the thing | `find src/kernel -name '*.lu' \| xargs cat \| wc -l` | 3 s: `4890` (lines of wolf in the kernel; `src/` is a copy of pax's `kernel/` and `boot/` at px08's head) |
| 0.2 | SHOW the reel's kernel | `mat src/kernel/kmain_reel.lu` | 10 s, scroll slowly: 79 lines, none wider than 75 columns. It calls the stages one by one, with a `// PAUSE for the viewer` after each, then starts the thread that will overrun its stack |
| 0.3 | *(optional)* SHOW the rest | `cat src/boot/*.S \| wc -l` | 3 s: `796`. The assembly ring: the Limine entry, port I/O, control registers, the interrupt trampolines, the context switch. Everything else is wolf |

**Caption idea:** "4,890 lines of wolf. One ISO." *(True: the wolf is in `src/kernel`; say "plus 796 lines of assembly" if a viewer will ask.)*

---

## Scene 1 — "Built on Linux, booted on a Mac" (about 10 s)

| # | action | command | hold |
|---|---|---|---|
| 1.1 | SHOW the images are the ones built | `shasum -a 256 -c SHA256SUMS` | 3 s: `pax-reel.iso: OK`, `pax-reel-b.iso: OK` |
| 1.2 | SHOW the machine that will run it | `qemu-system-x86_64 --version \| head -n 1` | 3 s: `QEMU emulator version 11.1.1`: an x86-64 PC, emulated on Apple Silicon (no hardware virtualisation) |

The ISOs were built on kasumi (Linux) by the pinned wolf 0.2.24 release, by `tools/reel build` in the pax repo. Their shas are in `README.md` too.

---

## Scene 2 — "The boot" (about 35 s, one take)

**RUN** (type it in full; it is one line):

```
qemu-system-x86_64 -machine q35 -cpu max -m 256M -display none -serial stdio -monitor none -nic none -no-reboot -cdrom pax-reel.iso
```

What the flags say, if a caption wants it: a q35 PC, 256 MiB, no screen (`-display none`), its serial port is this terminal (`-serial stdio`), no network, stop instead of rebooting.

Then **do not touch the keyboard** until the PANIC line. What lands, measured from Enter (rehearsal on this MacBook, BIOS):

| time | what appears | hold for the edit |
|---|---|---|
| 0.1 s | Limine's menu: **PAX, the boot reel**, two entries, the first highlighted: *finale a: a thread overruns its stack*, *finale b: the kernel writes to its own text*; `Booting automatically in 5...` counting down | 5 s (it boots the first entry by itself) |
| 5.1 s | the screen clears; `PAX: a kernel written in wolf` / `wolf 0.2.24, target x86_64-unknown-none; every line below is printed by this kernel`; **[1/5] boot**: Limine 12.9.1, firmware bios, `20 map entries, 254 MiB usable`, the HHDM, the kernel image's addresses | 3 s |
| 8.1 s | **[2/5] frames**: `65107 usable` frames, one taken (`free 65058 -> 65057`), the word `0x50415820776f6c66` ("PAX wolf") written through the direct map and read back `same`, the frame freed (`-> 65058`) | 3 s |
| 11.1 s | **[3/5] paging**: the kernel's own page tables, CR3 switched (`limine cr3 … pax cr3 0x…105000`: the PML4 is the very frame stage 2 handed back); `text … r-x`, `rodata … r--`, `data … rw-`, each "every page alike", read back from the live tables; `lower half 0 of 256 top-level entries present` | 3 s |
| 14.1 s | **[4/5] interrupts**: the GDT, the IDT (`256 gates, 48 routed`), the local APIC, the PIT at 99.998 Hz; then `tick: 50 ticks handled, 0.5 s` … `tick: 300 ticks handled, 3.0 s`, one line every half second, **live** | 5 s (the ticks run 3 s, then a 2 s pause) |
| 19.1 s | **[5/5] threads**: four kernel threads, `wolf`, `lupin`, `lobo`, `pax`, spawned; none yields; the timer switches between them every 2 ticks. 24 lines interleave over 2.3 s (`wolf t2 run 5 at tick 532`, `lupin t3 run 5 at tick 534`, …), then `join: 4 of 4 exited; frames free 65040 before, 65040 after: every stack given back` | 5 s |
| 24.5 s | the closing lines: `PAX today: Limine boot on BIOS and UEFI, frames, paging, interrupts, / a timer and preemptive threads, all in wolf. Next: user mode, then / Linux binaries, unmodified.` | 1 s |
| 25.5 s | `finale in 3...` then ` 2...`, ` 1...`, one a second | 3 s |
| 28.5 s | `finale: a thread recurses until it runs off its stack` / `overflow: t6 stack 0xffffd0000002c000 to 0xffffd00000030000, guard 0xffffd00000020000 to 0xffffd0000002c000` / **`PANIC stack overflow thread 6 cr2 0xffffd0000002bfe8 guard 0xffffd00000020000 to 0xffffd0000002c000`** | 4 s or more: the machine has halted, nothing more will print |
| after | press **Ctrl-C** | `qemu-system-x86_64: terminating on signal 2` |

The addresses and counts above are the rehearsal's; they do not move between boots of the same ISO on this MacBook (BIOS). The thread lines' ticks depend on when the timer started and may differ by a tick or two.

**What the finale is:** thread 6 recurses forever; its stack is 16 KiB with an unmapped 48 KiB guard below it. The write into the guard is a page fault; the CPU cannot push the fault's frame on that same stack, so it raises a double fault onto a separate stack (IST1), and the kernel finds the faulting address (`cr2`) inside thread 6's guard and names it. `cr2 …bfe8` is 24 bytes below the stack's bottom (`…c000`).

**Caption idea:** "It boots. It schedules. It knows exactly how it died."

---

## Scene 3 — "The other ending" (optional, about 35 s)

Finale b: the kernel writes to its own code, which stage 3 showed is mapped read-execute.

Either choose it in the menu on camera:

| # | action | command / key | hold |
|---|---|---|---|
| 3.1 | RUN the same boot | `qemu-system-x86_64 -machine q35 -cpu max -m 256M -display none -serial stdio -monitor none -nic none -no-reboot -cdrom pax-reel.iso` | the menu |
| 3.2 | in the menu, within 5 s | **Down arrow**, then **Enter** | the second entry highlights, then `limine: Loading executable 'boot():/boot/pax-text'...` |
| 3.3 | the same stages | (hands off) | as scene 2 (times count from the Enter) |
| 3.4 | the ending | | `finale: the kernel writes to its own text, which paging mapped r-x` / `write: text at 0xffffffff80000040` / **`PANIC page fault vector 14 error 0x0000000000000003 rip 0xffffffff8000a9ab rsp … frame … cr2 0xffffffff80000040`**: `cr2` is the address it wrote; error `0x3` is present + write |
| 3.5 | | **Ctrl-C** | QEMU ends |

or boot the image whose menu defaults to finale b (no keys): `-cdrom pax-reel-b.iso` in the same command.

The PANIC line of finale b is 145 columns; under that width it wraps once.

---

## Timings (rehearsal, 2026-10-06, this MacBook)

The rehearsal typed every command above, as written, into an interactive fish in a 146 x 40 terminal (a pty driven by a script, so the keys land at known times), and stamped each line of output on arrival. Its logs are in `logs/`.

| scene | measured | log |
|---|---|---|
| preflight | five `ok`, `GO`; its headless boot reached the PANIC line in about 29 s, the whole preflight about 30 s | `logs/rehearsal-preflight.out` |
| 0 | `4890`; `kmain_reel.lu` shown whole (rehearsed as `mat … \| cat`: the script cannot scroll a pager; by hand, `mat` alone); `796` | `logs/rehearsal-scene0-1.times` |
| 1 | `pax-reel.iso: OK`, `pax-reel-b.iso: OK`; `QEMU emulator version 11.1.1` | `logs/rehearsal-scene0-1.times` |
| 2 | from Enter: menu at once; `PAX: a kernel written in wolf` 5.13 s; headings [1/5] 5.13, [2/5] 8.13, [3/5] 11.14, [4/5] 14.14, [5/5] 19.15 s; the threads' 24 lines 19.47 to 21.46 s; `join` 21.47 s; `PAX today` 24.47 s; the PANIC line 28.47 s; Ctrl-C at 31.5 s ended QEMU at once (`terminating on signal 2`) | `logs/rehearsal-scene2.times` |
| 3 | Down at 2.00 s, Enter at 2.73 s: `Loading executable 'boot():/boot/pax-text'` at 2.74 s; headings 2.77, 5.77, 8.78, 11.78, 16.78 s; the PANIC line (page fault, cr2 = the address written) 26.10 s, 23.4 s after Enter; Ctrl-C ended QEMU | `logs/rehearsal-scene3.times` |

## If something goes wrong

- **The menu does not answer the arrow keys:** the terminal must have focus; the menu reads the keyboard through the same serial line. Or film finale b from `pax-reel-b.iso` (no keys).
- **Nothing after `limine: Loading executable`:** Ctrl-C and run the preflight again.
- **A stage's lines wrap:** widen the window to 125 columns (finale b: 145) or shrink the font.
- **UEFI instead of BIOS** (slower firmware, about 1.4 s more before the menu; the firmware line then says `uefi64`): add `-drive if=pflash,format=raw,readonly=on,file=/opt/homebrew/share/qemu/edk2-x86_64-code.fd` to the command. The film uses BIOS.
