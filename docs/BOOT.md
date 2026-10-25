# BOOT — how PAX is loaded, and why Limine

**Ruled by px00 (2026-10-02): PAX boots through the Limine boot protocol,
base revision 6, from one hybrid ISO that boots under BIOS and UEFI alike.**
The bootloader is Limine's own release binary, fetched by digest
(`boot/limine.pin`, `tools/fetch-limine`); it is not PAX code and nothing of
it is copied into this repository.

## The three candidates

The question for each: how much C or assembly does the kernel itself have to
carry before wolf code can run, under what licence, and what does the kernel
get handed?

| | Limine protocol | multiboot2 | direct UEFI stub |
|---|---|---|---|
| CPU mode at entry | **64-bit long mode**, paging on | 32-bit protected mode, paging **off** | 64-bit long mode, firmware's identity map |
| higher half | **yes**: the ELF's `PT_LOAD` segments mapped at their addresses (≥ `0xffffffff80000000`), plus an HHDM of usable memory | no: the kernel builds its own page tables and jumps up | no: the kernel builds its own page tables |
| kernel-side glue before wolf runs | **none**: entry is a SysV-ABI function on a 64 KiB stack | page tables, PAE, `EFER.LME`, a 64-bit GDT, a far jump: 32-bit assembly (wolf's backend emits none) | PE32+ output, Microsoft x64 calls into boot services, `GetMemoryMap` / `ExitBootServices`, page tables |
| what it hands over | memory map, HHDM offset, framebuffer, RSDP, SMBIOS, EFI system table, modules (initramfs), command line, firmware type, MP start-up of every CPU, paging-mode choice — each a static request in the kernel image | memory map, framebuffer, modules, command line, ACPI and EFI tags (as tags in a 32-bit-addressed blob) | whatever the kernel asks boot services for, before it exits them |
| BIOS and UEFI | **both, one kernel binary, one ISO** | both through GRUB (or Limine), with the same 32-bit entry | UEFI only |
| licence of what we depend on | bootloader BSD-2-Clause, protocol text 0BSD; fetched, never vendored | GRUB GPL-3.0 (compatible, but a GPL-3 binary on every image); spec GNU FDL | UEFI spec (no third-party code) |
| QEMU test path | ISO on a cdrom, SeaBIOS or OVMF | QEMU's `-kernel` speaks multiboot **1** only, so tests need a GRUB image anyway (`grub-mkrescue`: xorriso plus GRUB's BIOS and EFI module trees) | OVMF plus a FAT image |

Limine is the only candidate under which the first instruction of PAX can be
wolf. multiboot2 forces a 32-bit trampoline that wolf cannot write and this
project would carry as assembly forever. A UEFI stub needs nothing third-party
but asks the most of the compiler (a PE32+ target and the Microsoft calling
convention beside SysV) and gives up BIOS machines. It stays a possible second
entry for P6, not the first.

The cost of Limine, named: a third-party binary on every image (BSD-2,
fetched by digest); a protocol that is Limine's own rather than a multi-vendor
standard (its text is 0BSD, so a second loader could implement it); and the
P6 installer must run Limine's `bios-install` step or copy
`BOOTX64.EFI`, as it would GRUB's.

## What the kernel must do under it (the clauses for kw00)

From PROTOCOL.md (limine-protocol `3a0526b7`), base revision 6, x86-64. Each
is a requirement on wolf's freestanding output, so each is a clause for the
KWC design note to rule on:

1. **An ELF64 executable linked in the top 2 GiB** (or relocatable; Limine
   slides a lower-half PIE up), entry at `e_entry`, one `PT_LOAD` per
   permission (Limine honours `PF_W` and `PF_X`; NX is on).
2. **The entry is a SysV-ABI function that never returns**, called on a
   bootloader stack of at least 64 KiB with a 0 return address pushed.
3. **No FP/SIMD before the kernel enables it.** Base revision 5 and later
   clear every `cr0`/`cr4` bit beyond PE, ET, WP, PG and PAE, so
   `CR4.OSFXSR` is off and the first SSE instruction faults (#UD). wolf's
   kernel code must either be compiled without SSE (as soft-float kernels
   are) or enable it in its first lines — and the protocol's own
   boundary is "System V ABI without FP/SIMD" either way.
4. **Requests are static, 8-byte-aligned data** with exact layout (four
   64-bit id words, a revision, a response pointer), between the start and
   end markers, and must survive the linker (no section GC drops them).
5. **The response pointers are written by the bootloader after the image is
   built**: the compiler must treat them as volatile (a zero-initialised
   static the optimiser folds to null reads as "no response" forever).
6. **The base revision tag is read back**: Limine zeroes its third word when
   it honours the revision; the kernel checks it (the stub does: status 35
   and a message when it is not).
7. Interrupts are off, the IDT is empty, the PICs and I/O APIC entries are
   masked, the local APIC is in a defined state: the kernel loads its own IDT
   before enabling anything. Kernel code that takes interrupts must not use
   the SysV red zone (a P2 clause, named here so kw00 sees it).

The stub `boot/stub/pax-stub.s` exercises 1, 2, 4, 6 and the firmware-type
request, in assembly, so the harness has something to boot. px01 replaces it
with wolf.

**The wolf kernel's boot path (kw05, M-KW).** `boot/start.S` holds the
request markers and the base-revision tag, checks the tag's third word and
calls wolf's `kmain` (an `export fn`) with the stack aligned to 16 bytes:
clauses 1, 2, 4 and 6. Clause 3 is the compiler's: `wolf build --target
x86_64-unknown-none` emits no SSE and no red zone on either tier, and
`tools/build-kernel` checks every object for it. Clause 5 is met by not
needing it yet: the one bootloader-written word M-KW reads (the base
revision) is read in assembly, so no wolf code reads a response pointer
before wolf has volatile access (KWC kw07). `boot/io.S` holds the port I/O,
the exit and the trap hook (`wolf_trap`), listed under `asm` in
`kernel/wolf.pkg` so wolf assembles it for the kernel's target.
`boot/kernel.ld` is the stub's layout plus what a compiled object brings
(`.rodata.*`, `.data.rel.ro`, the small-PIC GOT, `.bss`).

**First light (px01, M-PX1).** `boot/start.S` carries four more requests
between the markers — bootloader info, firmware type, memory map and
HHDM — each with its PROTOCOL.md id words, revision 0 and a null response
pointer. Clause 5 is still met by not needing it in wolf: `boot/limine.S`
(listed under `asm`, so on wolf's roster) loads each response pointer
afresh on every call, follows it, and returns plain integers (a string
byte by byte; a memory-map field by entry and index), so wolf code never
holds a pointer the bootloader wrote. When wolf has volatile access (kw07)
and integer-to-pointer lowering (kw06) the readers can move into wolf;
the requests stay in `start.S`. Measured on QEMU (q35, 256 MiB, Limine
12.9.1): SeaBIOS gives 18 memory-map entries and ~254.5 MiB usable, OVMF
30–33 entries and ~210–214 MiB usable (boot-services memory is reported
bootloader-reclaimable), and the HHDM offset was `0xffff800000000000` on
every boot (4-level paging) — which the test asserts only by shape, since
the protocol lets it vary. The kernel ends in `cli; hlt` (`boot/io.S`'s
`pax_halt`), not `isa-debug-exit`; `tools/qemu-halt` proves the halt
through QEMU's monitor.

**Physical frames (px02).** `boot/start.S` carries a sixth request,
the executable address (id `0x71ba76863cc55f63, 0xb2644a48c516a487`):
Limine answers with the image's physical and virtual base, which the
frame allocator's test needs, because executable-and-modules entries in
the memory map are "illustrative only" (PROTOCOL.md). With wolf-lang
`eb955c3b` (kw06's `N as *T`, kw07's `read_volatile`) the readers moved
into wolf: `kernel/boot_info` follows each response pointer with one
volatile load per word, afresh per call, which is clause 5 met in wolf
itself. `boot/limine.S` keeps only what wolf cannot spell: a symbol's
address (each request's, and `boot/kernel.ld`'s `__pax_image_start` /
`__pax_image_end`; wolf-lang#529) — until kw10, which retired it:
with wolf-lang kw09's `extern "c" let`, `kernel/boot_info` and
`kernel/paging` name those symbols themselves. Measured on QEMU (q35, 256 MiB,
Limine 12.9.1): SeaBIOS 65147–65157 usable frames, 44 of them below
1 MiB, the highest usable byte below `0x10000000`; OVMF 53784–54863
usable frames (the count moves by about a thousand between the OVMF
builds of kasumi, CI and hasu), 159 below 1 MiB; the image near the top
of RAM (`0xff7f000` under SeaBIOS; `0xbfb1000` or `0xe72b000` under
OVMF, by build). Usable memory is mapped in the
HHDM at this base revision, so the allocator reaches every frame it
hands out through it.

## The image

`tools/mkimage KERNEL.elf OUT.iso` lays out:

    /boot/pax                         the kernel ELF
    /boot/limine/limine.conf          boot/limine.conf: timeout 0, quiet, one entry
    /boot/limine/limine-bios.sys      Limine's BIOS stage 2
    /boot/limine/limine-bios-cd.bin   El Torito BIOS boot image
    /boot/limine/limine-uefi-cd.bin   El Torito EFI system partition image
    /EFI/BOOT/BOOTX64.EFI             Limine for UEFI

then runs `xorriso -as mkisofs` with Limine's documented hybrid flags and
`limine bios-install` on the result, so the same file boots from a cdrom
under SeaBIOS, from a cdrom under OVMF, and (later) written raw to a USB
stick.

## The disk beside the image (px63)

The ISO is read-only and its initramfs lives in memory, so nothing
written survives a boot. A second file, a raw disk image, does: QEMU
gives it to PAX as a virtio block device,

    -drive file=pax-home.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0

and the boot goes on as before up to the first program, with three
steps added in `kernel/kmain_console`:

1. `kernel/block` finds the disks: `kernel/vblk` brings up each virtio
   block device on the PCI transport (`blk: virtio-blk 1af4:1042 at …`),
   one queue, polled requests, and the block layer names it `vda`
   (device 254:0, as Linux numbers it).
2. `kernel/fstab` reads the initramfs's `/etc/fstab` (the repository's
   `user/fstab`: `/dev/vda /home ext2 defaults 0 2`, R-px63-1) and
   mounts each line through `kernel/ext2` onto a directory of the
   in-memory tree, the tree's second store (`fstab: /dev/vda on /home:
   ext2, read-write, write-back`). A disk that is not there leaves the
   directory the tree's, said once. Root stays the in-memory tree
   (R-px63-2 reports what a disk at `/` would take).
3. When a volume is write-back (the default, R-px63-3), a kernel thread
   writes its changed blocks every 5 seconds.

At the end (init's last program ends, or root's `reboot(2)`), every
volume is written, flushed and marked clean before the halt or the
reset. The disk is ext2 as `mkfs.ext2` makes it (`tools/mkdisk`; the
playground's by `tools/mkdisk --home`), so the host reads and checks
it with e2fsprogs (`e2fsck -fn`, `debugfs`) and Linux mounts it as
it is. An image booted with no disk boots as before: no `blk:` line,
and `/home` the tree's.

## A disk that boots (px66)

The ISO is read-only and needs a disk beside it for anything to last.
`tools/mkdisk --gpt` makes one disk that is both: QEMU boots it with no
`-cdrom` at all,

    -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0

under SeaBIOS (the default) or a UEFI firmware (an edk2 or OVMF code
file as a read-only pflash, `-drive if=pflash,format=raw,unit=0,readonly=on,file=…`;
Homebrew's `edk2-x86_64-code.fd` as `-bios` is refused by QEMU, measured). Its GUID partition table (the UEFI
specification 2.10, chapter 5: a protective MBR, the primary header at
LBA 1, the backup at the last LBA, 128 entries; every GUID derived from
the label and SOURCE_DATE_EPOCH) has three entries, numbered as Linux
numbers them, by slot:

| partition | LBAs | type | holds |
|---|---|---|---|
| 3, `vda3` | 2048-4095 (1 MiB), first on the disk | BIOS boot (`21686148-6449-6e6f-744e-656564454649`) | Limine's BIOS stage 2, written by `limine bios-install DISK 3` |
| 1, `vda1` | from 4096 (2 MiB), `--esp` (default 64 MiB) | EFI system partition (`c12a7328-f81f-11d2-ba4b-00a0c93ec93b`) | FAT32 (pinned dosfstools' `mkfs.fat`, mtools' `mcopy`): `/EFI/BOOT/BOOTX64.EFI`, `/boot/limine/limine.conf`, `/boot/limine/limine-bios.sys`, `/boot/pax` (the kernel), `/boot/initramfs.cpio` |
| 2, `vda2` | the rest, 1 MiB aligned | Linux file system data (`0fc63daf-8483-4772-8e79-3d69d8477de4`) | ext2, `tools/mkdisk --home`'s: `/home`, `/home/pax` pax's |

**UEFI** finds the ESP by its type and runs `\EFI\BOOT\BOOTX64.EFI`, the
removable-media path (Limine's USAGE.md "UEFI"; OVMF says `BdsDxe:
loading Boot0002 "UEFI Misc Device"`). **BIOS** runs the MBR's boot code,
which `limine bios-install` wrote over the protective MBR's first 440
bytes (bytes 1-422 measured; the partition records and the 0x55aa are
left alone), which loads stage 2 from partition 3 (SeaBIOS says
`Booting from Hard Disk...`). Either way Limine then finds `limine.conf`
on the boot drive's partitions (CONFIG.md: `/boot/limine/limine.conf` is
one of the names it tries) and the entry's `boot():` paths resolve to
the partition the configuration was found on, the ESP. The
configuration is the ISO's (`boot/limine-initramfs.conf`, or the quiet
one for the playground): nothing in it knows it is on a disk.

The kernel is entered as from the ISO. kmain_console says where its
initramfs came from when it was not an optical disc (Limine's
`struct limine_file`: its media type, partition index and GPT GUIDs):

    boot: /boot/initramfs.cpio from a disk: partition 1, GPT disk <guid>, partition <vda1's PARTUUID>

kernel/block reads the same table (the next section's), the image's
`/etc/fstab` (`user/fstab-disk`: `/dev/vda2 /home ext2 defaults 0 2`)
mounts partition 2 at `/home`, and `/` is the initramfs in memory, as
it is from the ISO (px67 moves `/` onto partition 2: the next section). The disk is
written in place: `reboot` restarts the machine on it, and `exit` writes
`/home` and marks it clean.

**R-px66-2 (recommended, implemented, not decided): the BIOS layout on
GPT.** Limine documents one (USAGE.md "BIOS/GPT": a partition "usually of
BIOS boot type", at least 32 KiB, its number given to `bios-install`),
and its installer allows no other: measured, on a GPT image with no such
partition it refuses ("no BIOS boot partition specified or detected")
and changes nothing, and given none by number it finds one by its type.
So there is no choice of layout, only of place and size:
recommendation, partition 3 at 1 MiB, 1 MiB long, first on the disk
(stage 2 measured at 22.5 KiB, in the 1 MiB before the ESP that
alignment leaves anyway), numbered after the ESP and `/home` so that
`/home` is `vda2`.

**R-px66-3 (a report): where the ESP is mounted.** Nowhere, now: PAX
reads no FAT (FAQ.md argues for the ESP as `/boot`, which is what an
installer that updates the kernel would want). Reading FAT is a lane of
its own (a FAT32 reader in kernel/, the ESP at `/boot` by fstab with
`vfat`); until then a new kernel or initramfs is put on the disk by the
host (`tools/mkdisk --gpt` again, or mtools on the image). Recommended:
`/boot`, when P6's installer needs to write it.

**A partition table, in kernel/block.** At `start`, before any mount:
LBA 0's 0x55aa or no table (a bare file system, the ISO's
`pax-home.img`: nothing is said); a 0xEE record from LBA 1 for GPT, the
primary header and its array checked (signature, revision, size, CRC32,
MyLBA, the usable range, the entry size, the array's place and CRC32),
the backup at the last LBA checked the same way; else the MBR's four
primary records (R-px66-1). Each partition is a device whose requests
are offset by its first sector and refused past its last: the
specification's rules, the Linux guest's answers on eleven fixture disks
(`tests/mpx6-part`; `notes/px66-the-partition-table.md`).

## `/` on the disk (px67)

`tools/mkdisk --gpt --root ARCHIVE` makes the disk whose partition 2 is
`/`: the archive an ISO would carry as its initramfs (tools/mkinitramfs'
newc) is unpacked and installed onto the ext2 partition at build time by
`mkdisk --from` (px63's sorted, reproducible debugfs path), with an
`--attrs` file generated from the archive's own headers (every entry's
mode, owner and modification time; kept beside the image as
`OUT.root-attrs`), and the kernel's mount points added as empty
directories (`/dev` 755, `/proc` and `/sys` 555, `/tmp` 1777). The ESP
holds Limine and the kernel and no initramfs (R-px67-2), and every
entry's `cmdline` gains `root=PARTUUID=<partition 2's GUID> rw`.

The kernel reads `root=` from Limine's command line (kernel/boot_info)
in Linux's spellings (bootparam(7), each measured on Linux 7.2.8 under
QEMU): `/dev/vda2` or `vda2`, the device's numbers (`0xfe02`, `fe02`,
`254:2`), `PARTUUID=` in either case, `UUID=` (a named drift: Linux's
kernel alone refuses it), `rootfstype=ext2` (px68: or `ext3`), and `ro` or `rw`, read-only
when neither is given (Linux's answer, where bootparam(7) says `rw`).
Before the first program, kernel/fstab mounts that partition as `/`:

    root: PARTUUID=… (vda2) on /: ext2, read-write, write-back

every lookup, `..` at the root (the root mount's root is its own
parent), getcwd, chroot's root check and every absolute path then
resolve on the volume, and programs are exec'd from it. The kernel's
own trees are mounted over the disk's directories: /dev (devtmpfs, the
kernel's), /proc and /sys, as Linux's tables show them, and the
image's `/etc/fstab` (`user/fstab-root`) names `/` on its first line
and mounts a tmpfs at /tmp, the memory's (R-px67-1). `/home` is a
directory of `/` (R-px67-3); `/etc/mtab` is a link to
`../proc/self/mounts`. A `root=` that names no partition panics by
name, unless the entry also loads the initramfs (`mkdisk --initramfs`,
R-px67-2's other way), which stays `/`. Without `root=` the ISO boots
as before, `/` the initramfs in memory (`rootfs` in the table).

**The end.** When init's last program ends (after up to a second for
what it left to end of itself: a shell's stopped jobs, hung up when it
exits), or root calls `reboot(2)`, every process left is sent SIGTERM;
those still there after a grace of 2 s (R-px67-4) are sent SIGKILL; then each volume is written and unmounted
in the reverse of its mount order, `/` last: flushed, its clean flag
written; the disk's books, then init's line, then `halt`:

    PAX: the end: SIGTERM to 2 processes, 1 ended within 10 ms; SIGKILL to 1 after the 2000 ms grace

On an ext2 root (px67's; since px68 `--no-journal`, the journal's
section below says what a journalled root does) a power cut (QEMU
closed without `exit` or `reboot`) leaves `/` not clean; the next boot
mounts it read-write, says `not cleanly unmounted` once, and leaves it
not clean through its own clean end, as Linux's ext2 does (R-px67-5).
Repair it offline with `fsck.ext2 -y /dev/vda2` from the rescue archive described below, or with the host's `e2fsck -fy`. Never repair the mounted root.

## The journal (px68)

The root is ext3 since px68: `tools/mkdisk --gpt --root` makes partition
2 with the pinned `mke2fs -t ext3` (has_journal beside ext2's features,
the journal inode 8, mke2fs's default size: 1024 blocks of 4 KiB for a
root under 128 MiB, 4096 for 448 MiB; `--no-journal` keeps px67's ext2,
R-px68-3). kernel/ext2 finds the journal's blocks through inode 8 and
hands them to kernel/journal, which checks the journal's superblock
(jbd2's v2 layout, big-endian; no journal feature but revocation is
served, anything else refused by name) and, when its log holds
transactions, replays them before anything else of the volume is read,
in e2fsck's rules (measured on journals tools/mkjournal writes): a
transaction with no commit block, or a torn one, is dropped whole; a
revocation in the tag's own transaction or a later one suppresses it;
an escaped block's magic is restored. One line says what it did:

    ext2: vda2: recovering the journal: 2 transactions (sequence 1 to 2), 116 blocks written home, 0 revoked; recovery complete

The log is emptied (s_start 0, s_sequence one past the last commit's, as
e2fsck leaves it) only after every replayed block is home and a FLUSH
has returned. A replay that cannot finish (a read or a write the disk
fails, a tag past the volume's end, a revocation block whose count is
wrong) says where it stopped, leaves the log as it was and refuses the
volume (-EIO), so the next boot replays it whole
(`tests/mpx6-journal` J10 fails one block's write with QEMU's blkdebug):

    ext2: vda2: recovering the journal stopped at sequence 2: an I/O error; the volume is refused, -EIO

A read-write mount sets needs_recovery and leaves the state `clean`
(Linux 7.3.0 keeps a journalled root clean while it is mounted and after
a power cut, measured), and the root's line says how it writes:

    root: PARTUUID=… (vda2) on /: ext3, read-write, data=ordered

From then on every change to metadata (the superblock, the group
descriptors, both bitmaps, the inode tables, indirect blocks, directory
blocks, a slow link's block) goes into the running transaction and
never reaches its home before that transaction's commit block is on the
disk; a file's data is not journalled (data=ordered, R-px68-1: written
before the commit that names it). A commit (at the flusher's 5 s turn,
at `sync`, `fsync`, `fdatasync`, `syncfs`, `msync`, a remount read-only,
the unmount and the halt, and at a call's start when the transaction
holds 128 blocks: R-px68-2) writes the data, the descriptors, the logged
blocks and any revocation blocks, a FLUSH, the commit block, a FLUSH.
The log wraps; a checkpoint writes the committed blocks home when the
log could not hold the largest transaction the cache can, and at the
unmount, which then empties the log and clears needs_recovery. A block
logged since the last checkpoint and freed is revoked, and a block
freed by the running transaction is not allocated again before it
commits. The halt's line is the journal's books:

    journal: vda2: 7 commits (0 with nothing to log), 191 blocks logged in 7 descriptors, the most 50; 0 revoked, 0 escaped, 1 checkpoints, 16 flushes; next sequence 8

So a power cut (QEMU closed without `exit` or `reboot`) leaves `/` clean
with needs_recovery, and the next boot replays the journal to the last
commit: nothing a commit wrote is lost, and what the last 5 seconds
wrote before it is (`sync` first keeps it). `init=PATH` on Limine's
command line runs PATH alone as init (bootparam(7)'s), which the crash
row uses to boot a killed disk once for its replay. An ext2 root
(`--no-journal`) behaves as px67 measured: not clean after a cut, said
once by the next boot, left for an offline check, from the rescue archive or the host.

## The disks' nodes and a second disk (px79)

kernel/vblk brings up every virtio block device on the bus, up to four,
in kernel/pci's order (bus, device, function: QEMU's slot order, the
order of its `-device` options), and kernel/block names them `vda`,
`vdb`, `vdc`, `vdd` as the Linux guest does (254:0, 254:16, 254:32,
254:48; each disk's partitions 254:N to 15 and the extended major 259
past it, the lowest free minor across every disk: R-px79-1). Each disk
says its lines in turn at boot, and its partition table's:

    block: vda: 131072 sectors (67108864 bytes), 254:0, read-write, flush
    block: vdb: 32768 sectors (16777216 bytes), 254:16, read-write, flush

`/dev` holds a node for every disk and partition the block layer knows,
made at boot and as a table is read again (BLKRRPART) or changed (BLKPG),
in memory, as devtmpfs makes them (R-px79-2: never written into an
image); `brw-------` and root's, as the guest's with no udev:

    /dev/vda  /dev/vda1  /dev/vda2  /dev/vdb  /dev/vdc

and `/sys/block/<disk>/…`, `/sys/class/block/<name>/dev` and
`/proc/partitions` say what lsblk and blkid read. A tool writes a disk
through its node (a GPT, a file system, Limine's BIOS stage), asks for
its size and geometry by ioctl, and has the kernel read the table again;
`mount` and `/etc/fstab` name a partition by its node (`/dev/vdb2`).
The boot disk stays `vda` whatever else is given:
`tools/qemu-run --boot-disk DISK --drive SECOND [--drive THIRD]` (and
`tools/qemu-halt` the same) gives each further image a virtio device of
its own after it, in order (`--drive FILE,ro` read-only, `--drive
'FILE;cyls=…,heads=…,secs=…'` with the device's own properties), so a
second, blank disk is `vdb`:

    qemu-system-x86_64 … -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0 \
        -drive file=blank.img,if=none,id=d1,format=raw -device virtio-blk-pci,drive=d1

## Measured

The proof's runs, both firmwares, the same ISO on linux and macOS: see
`notes/px00-the-harness.md` §4. Exit status 33 is the stub's `0x10` through
`isa-debug-exit` (QEMU reports `(value << 1) | 1`).

## Writing a disk on PAX (px69)

`tools/mkdisktools OUTDIR` builds three static Linux programs from
`user/disktools`, using the pinned Wolf compiler and standard library.
`tools/mklimine-static OUTDIR` builds the pinned Limine installer with
`-static -no-pie`, without changing its source. These same executables run
on Linux and PAX. Block nodes and the second disk are provided by px79.

**These are offline formatters, not a guided installer. Formatting destroys
the selected disk's partition table or filesystem. Never use a mounted
volume or the disk containing the running root.** The test selects a new,
blank second virtio disk, `/dev/vdb`, and boots it alone afterward as `vda`.

The interfaces are:

```text
paxgpt [--seed TEXT] [--size SIZE] IMAGE SLOT:TYPE:FIRST:LAST[:NAME]...
paxgpt --dump IMAGE
paxfat [--offset BYTES] [--seed TEXT] mkfs IMAGE SIZE [LABEL]
paxfat [--offset BYTES] mkdir IMAGE /PATH
paxfat [--offset BYTES] copy IMAGE SOURCE /PATH
paxfat [--offset BYTES] ls IMAGE [/PATH]
paxfat [--offset BYTES] cat IMAGE /PATH
paxext2 [--from DIR] [--attrs FILE] [--label LABEL] [--seed TEXT]
        [--inodes N] [--offset BYTES] [--exclude /DIR]... SIZE IMAGE
limine bios-install IMAGE 3
```

`IMAGE` can be a regular image file or an existing block node. Without
`--size`, paxgpt uses the existing device's capacity. Partition starts are
1 MiB aligned. `--offset` is **bytes**, not sectors: the formatters work on
the whole disk's windows without needing a partition-table rescan. For the
512 MiB test disk the BIOS partition is sectors 2048–4095, the ESP is
4096–135167 (64 MiB at 2 MiB), and root is 135168–1048535
(467644416 bytes at 66 MiB). The last usable GPT sector is 1048542.

The running system supplies `/boot/pax`, `/boot/EFI/BOOT/BOOTX64.EFI`,
`/boot/limine/limine-bios.sys` and `/boot/limine/limine.conf`; these are copied
to the ESP. The root-only boot has no initramfs module, as in px67. A rescue
initramfs, if wanted, must be supplied separately and the ESP sized for it.
The root configuration must name the **new** root partition. Tests fix the
seed for reproducibility; a real installation should use a fresh seed and
write the resulting PARTUUID into its configuration.

`paxext2 --from /` needs an explicit metadata manifest and exclusions for
`/dev`, `/proc`, `/sys` and `/tmp`. Exclusions preserve the named directory
but omit its contents. `--attrs` is the host builder's format:
`PATH MODE UID GID [MTIME [ATIME [CTIME]]]`, with quoted paths allowed.
A non-empty source `lost+found` is refused unless explicitly excluded;
it is not silently discarded. `SOURCE_DATE_EPOCH` controls generated
timestamps and seeds. FAT timestamps are UTC, with two-second resolution,
and must fit 1980–2107.

Current bounds: GPT has 128 entries of 128 bytes and 512-byte sectors;
FAT32 uses 512-byte clusters on 33 MiB–2 GiB volumes and supports CP850
short aliases plus UTF-16 long names; ext2 uses 4 KiB blocks, 256-byte
inodes and 8 MiB–4 GiB volumes. Files, directories and links are supported,
not device-node creation. The tools do not resize or repair filesystems,
provide power-failure transactions, or overwrite existing FAT files.

The ext2 writer leaves `has_journal` clear. The host's `mkdisk --gpt --root`
still creates ext3 by default; `--no-journal` selects ext2.
`PAX_EXT2_WRITER=/path/to/paxext2` is an explicit host-builder override for
ext2 only and rejects journalled requests. The root suite's `--fstype ext2`
leg uses it without changing the default ext3 leg or its journal tests.

`tests/mpx6-disktools` runs Linux differentials, compares static Limine on
Linux with the same binary on PAX `/dev/vda`, then runs the three tools and
Limine on `/dev/vdb`. It compares the resulting root tree, boots the target
alone, and checks the playground's reboot persistence under each requested
firmware. CI uses a compact installed tree with pelt, lope and the commands
that session needs; the lane also tested the complete installed playground
(239 final tree rows). Every missing prerequisite is a failure; the suite
has no skip mode (its raw-node prerequisite, pax#144, is px79's, served).

## Checking a volume from rescue

`tools/mkfsck OUTDIR` builds `OUTDIR/fsck.ext2` from `user/fsck`, using
this repository's compiler and standard-library pins. It is a static Linux
executable; the same binary runs on Linux and PAX.

```text
fsck.ext2 [-n|-p|-y] [-f] DEVICE
```

The default is report-only (`-n`). `-p` plans automatic count/bitmap and
reference repairs; an operation needing a choice remains uncorrected.
`-y` also clones duplicate data blocks and reconnects disconnected files
and directories, creating `lost+found` when needed. All five passes run;
`-f` is accepted. Exit status is 0 for no remaining error, 1 for completed
repairs, 4 for uncorrected or unsupported damage, 8 for an operational
failure, and 16 for bad arguments. As observed with e2fsck 1.47.0, `-n`
reports a primary superblock count disagreement without setting status 4
when no other inconsistency is found. Report-only mode never replays a
journal or writes the image.

**Use an unmounted volume.** Repair opens a block device with `O_EXCL`
without `O_CREAT`, retains that descriptor for the whole check, and takes
an advisory lock. A mounted PAX root is refused. A regular image file must
also be offline; an advisory lock does not exclude an unrelated program
that ignores it. There is no force-mounted option.

The checker reads 1, 2 and 4 KiB legacy block maps, including indirect
blocks. Supported ext3 journals are v1/v2 headers with 32-bit tags and
optional revocations, without checksums. Committed transactions are
validated before replay; revoked blocks, escapes, wrapped logs and torn
commits follow the existing journal corpus. Home blocks are flushed before
the log is emptied, then `needs_recovery` is cleared. Other repairs are
staged until every pass finishes, the superblock made dirty first, and
`clean` written only after metadata is flushed. This is not a transaction
for an arbitrary power cut during repair; keep a copy of important images.

Bounds and refusals are explicit: at most 512 groups, 4,194,304 blocks and
1,048,576 inodes; external journals, journal checksum/64-bit features,
external attribute blocks, indexed-directory validation, a nonempty
orphan chain, cyclic/shared indirect blocks, and ambiguous malformed
directory records are not repaired. A refusal is not a clean verdict.
Lost writes absent from both the filesystem and journal cannot be restored.

The normal disk still boots without an initramfs. The rescue fixture in
`tests/mpx6-fsck` explicitly supplies a separate archive containing
`/bin/fsck.ext2` and `/etc/pax-run` with:

```text
/bin/fsck.ext2 -fy /dev/vda2
```

Its Limine entry loads that archive and uses `root=/dev/vda9`, a missing
root, so PAX stays on the in-memory archive and leaves `/dev/vda2`
unmounted. The unattended test selects this entry after a real power cut,
checks the repaired superblock before mounting it, then selects the normal
root entry and verifies persistence across reboot. Both BIOS and UEFI are
covered. This does not add a rescue menu to existing disks or alter any
installed playground image; distributing that entry remains separate work.
