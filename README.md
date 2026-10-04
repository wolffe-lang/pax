# PAX

A Linux-compatible operating system written in wolf: a kernel that runs Linux's userspace unmodified, and a userspace built in wolf.

PAX is a clean-room implementation of Linux's userspace ABI. It does not contain, translate or derive from Linux kernel source. See `CLAUDE.md` for the rule and `docs/SOURCES.md` for what each part was written from.

Status: physical frames (px02, M-PX2's first piece) on first light (M-PX1, px01). The kernel's frame allocator (`kernel/frames`, two bitmaps over Limine's memory map, its state in frames it takes for itself) hands out every usable frame above 1 MiB exactly once and takes them back, and panics by name on a double free or a free of a frame never usable (`tests/mpx2-frames`). wolf is built from source at wolf-lang `eb955c3b` (volatile access and integer-to-pointer casts are in no release yet). The wolf kernel owns the serial console (a 16550 driver in wolf), prints what Limine handed it (bootloader, firmware, memory map, HHDM offset) and halts; a trap reaches its panic path, which prints `PANIC <kind> <file>:<line>` and halts. Both of wolf's compiling tiers, under BIOS and UEFI (`tests/mpx1`). The harness's assembly proof (`tests/proof`) and M-KW's first wolf kernel (`tests/mkw`) still run. The plan lives in the wolf planning repository under `sprints/pax/`.

Licence: GPL-3.0, with the wolf Training Data Permission (`LICENSE-TRAINING-DATA`).

## Layout

    kernel/   the wolf kernel (serial, log, boot_info, frames, panic;
              kernel/README.md), its wolf.pkg and the wolf/lupin pin
    boot/     boot-protocol glue: the Limine pin and config, the kernel's
              entry, requests, port I/O and the requests' addresses
              (start.S, io.S, limine.S, kernel.ld), and the assembly proof under
              boot/stub/
    tools/    the harness: fetch-limine, fetch-wolf, fetch-lupin,
              build-stub, build-kernel, mkimage, qemu-run, qemu-halt,
              qemu-gdb, expect-serial
    tests/    scripted QEMU tests: proof, mkw (with M-KW's frozen kernels
              in mkw.d/), mpx1, mpx2-frames, gdb-attach,
              expect-serial-selftest
    docs/     BOOT.md (the boot protocol, argued), SOURCES.md (the
              consulted-sources log), ABI notes as they come
    notes/    one note per lane: its contract and evidence

## Booting it

PAX boots through the **Limine** protocol from one hybrid ISO that boots under BIOS and UEFI (`docs/BOOT.md` says why). Limine itself is fetched from its release by sha256 digest, never built here.

```sh
tools/fetch-limine                         # Limine 12.9.1, digest-checked, into .pax-cache/
tests/proof                                # build the stub + ISO, boot it under BIOS and UEFI, assert
tools/qemu-run --firmware uefi build/pax-stub.iso; echo $?    # 33 = the stub's success code
tools/expect-serial build/serial.log PAX "firmware: uefi"
tools/qemu-gdb build/pax-stub.iso build/stub/pax-stub.elf     # gdb, frozen at reset
PAX_WOLF=$(tools/fetch-wolf) tests/mpx1    # M-PX1: first light, both tiers, BIOS and UEFI
PAX_WOLF=$(tools/fetch-wolf) tests/mpx2-frames   # px02: the frame allocator, both tiers, BIOS and UEFI
tests/mpx2-frames --images build/mpx2      # boot them elsewhere (hasu under KVM)
tests/mpx1 --images build/mpx1             # boot ISOs built elsewhere (any host with QEMU)
tools/qemu-halt --elf build/mpx1/native/kmain.elf --marker halt build/mpx1/native/kmain.iso   # is it halted?
PAX_WOLF=$(tools/fetch-wolf) PAX_LUPIN=$(tools/fetch-lupin) tests/mkw   # M-KW: the first wolf kernel, both tiers
tests/mkw --images build/mkw               # boot ISOs built elsewhere (any host with QEMU)
```

`tools/qemu-run` runs QEMU headless (`-nographic`, COM1 to a file, `-no-reboot`, a timeout, `isa-debug-exit` at port `0xf4`) and returns QEMU's status: `(v << 1) | 1` when the kernel writes `v` to the exit port, 0 for a reset or triple fault, 124 for a timeout. A kernel that halts never exits QEMU, so `tools/qemu-halt` boots it with QEMU's monitor on a pipe and, after the kernel's last line, holds it to RIP inside `pax_halt`, IF clear and HLT=1 at two probes a second apart, with no further serial output. Each tool's header comment states its usage; `qemu-run` and `qemu-gdb` print it with `--help`.

## Hosts

| host | build an image | boot one (`qemu-run`, `tests/proof --image`) | gdb (`qemu-gdb`) |
|---|---|---|---|
| linux x86-64 (CI's ubuntu, the pool) | yes: binutils, cc, make, curl, xorriso | yes: `qemu-system-x86_64`; OVMF for UEFI; KVM used when `/dev/kvm` is usable | yes: gdb |
| macOS arm64 | **no**: no x86-64 ELF binutils or xorriso in the base system | **yes**, TCG: Homebrew's `qemu`, which ships its own UEFI firmware; CI's `macos-run` job boots the linux-built ISO on every push | no gdb in the base system; `tools/qemu-run --gdb 1234` and lldb's `gdb-remote 1234` by hand |

Where each runs today (2026-10-02, px00):

- **CI**: `ubuntu-latest` with QEMU 8.2.2, OVMF and xorriso from apt (TCG); the `macos-run` job boots the same ISO, checked by digest, with Homebrew's QEMU 11.1.1 (TCG).
- **hasu** (NixOS): nothing system-wide is needed. QEMU and xorriso come from a nix-shell, and the UEFI firmware from nixpkgs' OVMF; use the **combined** `OVMF.fd` with no separate vars file, because split `OVMF_CODE.fd` + `OVMF_VARS.fd` hangs in the firmware under KVM there (5 of 6 boots):

  ```sh
  ovmf=$(nix-build --no-out-link '<nixpkgs>' -A OVMF.fd)/FV
  PAX_OVMF_CODE=$ovmf/OVMF.fd PAX_OVMF_VARS= \
    nix-shell -p qemu xorriso --run 'PAX_QEMU=$(command -v qemu-system-x86_64) tests/proof'
  ```
- **kasumi** (CachyOS): QEMU 11.1.1, xorriso and OVMF since the 2026-10-02 upgrade; the kernel builds (wolf, the objects, the ISOs) and boots here (TCG); px01 booted the same ISOs on hasu under KVM (`tests/mpx1 --images`).
- **macOS** (nomad-1, arm64): `tests/proof --image` on an ISO built elsewhere, as CI's `macos-run` does.

The QEMU binary is `$PAX_QEMU` (default `qemu-system-x86_64` on `PATH`) and the UEFI firmware `$PAX_OVMF_CODE` / `$PAX_OVMF_VARS`, so every host supplies its own. `tools/mkimage` is reproducible: every date in the ISO is `SOURCE_DATE_EPOCH`, default the last commit's time, so one commit builds one digest.

The harness never installs anything. A missing tool is named and the tool stops. The UEFI leg looks for OVMF at the distro paths in `tools/lib.sh`, or `PAX_OVMF_CODE` / `PAX_OVMF_VARS`; without it `tests/proof` skips that leg loudly, unless `PAX_REQUIRE_UEFI=1` (CI), when it fails.
