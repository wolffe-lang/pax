# tests/mkw.d — M-KW's kernels, frozen

M-KW (kw05) proved a wolf kernel boots: `kernel/kmain.lu` printed `KWC`
and exited 33, `kernel/kmain_trap.lu` printed `TRAP 1` through an
assembly `wolf_trap`. px01 grew `kernel/` into first light (M-PX1),
whose trap hook is wolf's own, so M-KW's kernels and the `io.S` they
link against are kept here, byte-identical to pax `7840d79`, laid out
like the repository so `wolf.pkg`'s `../boot/io.S` holds. `tests/mkw`
builds and boots them; `boot/start.S`, `boot/kernel.ld` and the tools
are the repository's own, so M-KW keeps proving the boot path the
kernel uses.
