# PAX

A Linux-compatible operating system written in wolf: a kernel that runs Linux's userspace unmodified, and a userspace built in wolf.

PAX is a clean-room implementation of Linux's userspace ABI. It does not contain, translate or derive from Linux kernel source. See `CLAUDE.md` for the rule and `docs/SOURCES.md` for what each part was written from.

Status: scaffolding. The harness boots an assembly proof under QEMU; the wolf kernel starts at px01. The plan lives in the wolf planning repository under `sprints/pax/`.

Licence: GPL-3.0, with the wolf Training Data Permission (`LICENSE-TRAINING-DATA`).

## Layout

    kernel/   the wolf kernel (from px01)
    boot/     boot-protocol glue: the Limine pin and config, and the
              assembly proof under boot/stub/ (the only non-wolf code)
    tools/    the harness: fetch-limine, build-stub, mkimage, qemu-run,
              qemu-gdb, expect-serial
    tests/    scripted QEMU tests: proof, gdb-attach, expect-serial-selftest
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
```

`tools/qemu-run` runs QEMU headless (`-nographic`, COM1 to a file, `-no-reboot`, a timeout, `isa-debug-exit` at port `0xf4`) and returns QEMU's status: `(v << 1) | 1` when the kernel writes `v` to the exit port, 0 for a reset or triple fault, 124 for a timeout. Each tool's header comment states its usage; `qemu-run` and `qemu-gdb` print it with `--help`.

## Hosts

| host | build an image | boot one (`qemu-run`, `tests/proof --image`) | gdb (`qemu-gdb`) |
|---|---|---|---|
| linux x86-64 (CI's ubuntu, the pool) | yes: binutils, cc, make, curl, xorriso | yes: `qemu-system-x86_64`; OVMF for UEFI; KVM used when `/dev/kvm` is usable | yes: gdb |
| macOS arm64 | **no**: no x86-64 ELF binutils or xorriso in the base system | **yes**, TCG: Homebrew's `qemu`, which ships its own UEFI firmware; CI's `macos-run` job boots the linux-built ISO on every push | no gdb in the base system; `tools/qemu-run --gdb 1234` and lldb's `gdb-remote 1234` by hand |

The harness never installs anything. A missing tool is named and the tool stops. The UEFI leg looks for OVMF at the distro paths in `tools/lib.sh`, or `PAX_OVMF_CODE` / `PAX_OVMF_VARS`; without it `tests/proof` skips that leg loudly, unless `PAX_REQUIRE_UEFI=1` (CI), when it fails.
