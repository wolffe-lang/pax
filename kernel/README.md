# kernel/

The wolf kernel. Today it is M-KW's (kw05, `sprints/compiler/91-freestanding/`
in the planning repo): `kmain.lu` writes `KWC` to COM1 and leaves QEMU with
status 33; `kmain_trap.lu` overflows an addition and its trap reaches
`boot/io.S`'s `wolf_trap`, which writes `TRAP 1` and leaves with status 3.
px01 (first light) grows `kmain` from here.

- `wolf.pkg` lists `../boot/io.S` under `asm`: wolf assembles it for the
  kernel's target and refuses a call into anything off its roster
  (`[abi.asm.roster]`, E1306). The target is passed by
  `tools/build-kernel` (`--target x86_64-unknown-none`), not set here, so
  M-KW's seen-red variant (the flag removed) is a hosted build that fails.
- Each kernel file is a standalone entry (`//! member: false`): a
  directory is one wolf module, and two `kmain`s would collide.
- `wolf.pin` names the wolf-lang commit wolf is built from
  (`tools/fetch-wolf`) and lupin's release and digest (`tools/fetch-lupin`);
  moving the wolf pin is one line.

`tests/mkw` builds both kernels on both tiers, boots them under SeaBIOS and
OVMF, and checks the machines' refusals; `docs/BOOT.md` says what the boot
protocol asks of the object.
