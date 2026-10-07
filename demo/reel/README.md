# pax-demo — the PAX boot reel

Everything needed to film PAX booting on this MacBook. Start with `SHOTLIST.md`.

| file | what |
|---|---|
| `SHOTLIST.md` | the scenes, the exact commands to type (fish), what appears and when, rehearsed and timed |
| `preflight.sh` | run off camera first: QEMU, the ISOs' shas, the source snapshot, the terminal's size, one headless boot; ends `GO` or `NO GO` |
| `pax-reel.iso` | the reel; Limine's menu defaults to finale a (a thread overruns its stack) |
| `pax-reel-b.iso` | the same kernels; the menu defaults to finale b (the kernel writes to its own text) |
| `SHA256SUMS` | `shasum -a 256 -c SHA256SUMS` |
| `src/` | pax's `kernel/`, `boot/` and `user/` at the commit the ISOs were built from, for scene 0 |
| `logs/` | the rehearsal (`rehearsal-*`) and the last preflight's boot |

## Where it came from

- pax PR #11 (branch `px08`, lane px08), source snapshot at commit `1110ad2` (rebased onto pax trunk `a01e2e4`, px09's user mode): `kernel/kmain_reel.lu`, `kernel/kmain_reel_text.lu`, `kernel/reel/`, `boot/limine-reel.conf`, `tools/reel`, `tests/reel`.
- Built on kasumi (Linux) with `tools/reel build` by wolf 0.2.24 (the release archive, sha256 `501d6d3f…`), native tier, Limine 12.9.1:
  - `pax-reel.iso` `25232dbfff8de43cf7cf1b1109c60e3a33e7ecf4bdfc60d086de758c6bbd995d`
  - `pax-reel-b.iso` `87aae34e14ba0a89e3d573664bbf01c124ed4a6be04d71fdd62c43bd21b2c6b0`
  (built from a tree without `.git`, so `SOURCE_DATE_EPOCH` is 0 and a rebuild of the same sources gives the same shas; CI's builds, with history, differ only in the image's dates.)
- QEMU here: Homebrew's `qemu-system-x86_64` 11.1.1, TCG (Apple Silicon has no x86 virtualisation). The film boots BIOS (SeaBIOS); UEFI works too (`edk2-x86_64-code.fd`, see the SHOTLIST's last section).

## Honesty notes

- Every line after Limine's menu is printed by the running kernel over its serial port. Nothing is replayed.
- The kernel pauses between its stages so a viewer can read them; each pause is marked `PAUSE for the viewer` in `src/kernel/reel/reel.lu` and `src/kernel/kmain_reel.lu`. No pause stands in for work.
- Each stage calls the same code the test suites prove (`tests/mpx1`, `mpx2-frames`, `mpx2-paging`, `mpx2-interrupts`, `mpx2-sched`); `tests/reel` asserts the reel itself in CI.
- Nothing here runs in the background or listens on a port. Ctrl-C ends a boot.
