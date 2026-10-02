# PAX — agent guidance

## The clean-room rule (read before writing a line)

**Never read, copy or translate Linux kernel source** (`.c`, `.S`, `.h` outside the uapi trees, Kconfig, Makefiles). PAX implements Linux's userspace ABI; it is not a port.

Allowed sources:
- the uapi headers (`include/uapi/`, `arch/*/include/uapi/`), GPL-2.0 WITH Linux-syscall-note;
- the syscall tables (`arch/x86/entry/syscalls/*.tbl`);
- `Documentation/`, the man-pages project, POSIX.1-2024, the x86-64 psABI;
- the Intel and AMD manuals, the UEFI, ACPI and virtio specifications;
- black-box behaviour of a real Linux under QEMU.

Permissively licensed kernels (the BSDs, seL4, Redox, Asterinas, Maestro, Kerla) are design references only, never copied. Record in `docs/SOURCES.md` what each change consulted.

The planning repo's refs clone (`wolf/refs/repos/linux`) is a sparse checkout of the allowed paths only.

## Where the plan is

`sprints/pax/index.md` in the planning repo (`wolffe-lang/wolf`). Contracts there are binding. When this file and the wolf spec disagree, the spec wins.
