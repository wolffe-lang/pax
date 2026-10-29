# PAX

A Linux-compatible operating system written in wolf: a kernel that runs Linux's x86-64 userspace unmodified, and a
userspace built in wolf.

PAX is a clean-room implementation of Linux's userspace ABI. It contains, translates and derives from no Linux kernel
source; `CLAUDE.md` states the rule and `docs/SOURCES.md` lists what each part was written from. Every behaviour claim
below is a scripted QEMU test that CI runs, and where the behaviour is Linux's, the test holds PAX byte for byte to a
real Linux booted the same way.

Licence: GPL-3.0, with the wolf Training Data Permission (`LICENSE-TRAINING-DATA`).

## At a glance

| Area | What PAX does today | Held to |
|---|---|---|
| Boot | Limine 12.9.1 from one hybrid ISO (BIOS and UEFI), from a GPT disk, or from a live USB stick; a guided installer onto a disk | both firmwares under QEMU, every push |
| Programs | Static x86-64 ELF run in ring 3 with Linux's syscall numbers; `fork`, `execve`, `#!` lines, threads (`clone3`, `futex`), signals with the full frame restored, job control and sessions; a fixed 1 MiB initial stack | the same binaries on Linux, byte for byte |
| Users | `root`, `pax` and the service account `lobo`; real, effective, saved and file-system ids; every path walk, mode, owner and signal checked by Linux's rules; `su` in wolf; no passwords yet | Linux as root and as a user |
| Files | A writable in-memory tree seeded from the initramfs: links, modes, times, holes, `rename`; `mmap` private and shared, `mremap`, FIFOs, `flock`; `/dev`, `/proc`, `/sys`, `/tmp` | Linux's tmpfs in a throwaway container |
| Disks | Up to four disks: virtio, NVMe (`nvme0n1`, major 259), or SATA AHCI (`sda`, major 8, LBA48), with GPT or MBR tables and `/dev` nodes; ext2 read and written, file data past 2 TiB on virtio and NVMe; ext3's journal written and replayed; `/` on the disk, `mount(2)`, `/etc/fstab`; an offline `fsck.ext2` in wolf | Linux 7.3.0 under QEMU (NVMe and AHCI: 7.2.4) and e2fsprogs |
| Network | virtio-net, ARP, IPv4, ICMP, UDP, TCP (RFC 9293, 6298, 5681), Unix sockets, `poll`, `epoll`, `eventfd`; 256 TCP connections | Linux in a namespace, and captures rebuilt byte by byte |
| Console | A 16550 serial console, the PS/2 keyboard and USB keyboards over xHCI, one line discipline; a framebuffer console of 160×50 cells with the Linux VT's colours and 560 glyphs | typed sessions on a Linux pseudo-terminal; screendumps against a reference renderer |
| Sound | The PC speaker through Linux's console ioctls; virtio sound behind OSS `/dev/dsp`; `/bin/play`, an orchestra of 17 timbres | QEMU's capture, every pitch within 1% |
| Shipped programs | pelt (the shell, PID 1), boreutils (107 utilities), scent as `grep`, yew, lope, aspen, lupin, lobo, clef, three wolf games | the same binaries in a Linux container |

What PAX is not: a security boundary. The permission checks hold for honest programs; the kernel has never been fuzzed
or audited, it loads programs at fixed addresses, and the live USB entry accepts `root` with no password.

## Quick start

On a Linux x86-64 host with binutils, cc, make, curl, xorriso and `qemu-system-x86_64` (the Hosts table below says what
each machine can do):

```sh
tools/fetch-limine                          # Limine 12.9.1 by digest, into .pax-cache/
tests/proof                                 # the harness's own proof: build the stub, boot it under BIOS and UEFI
PAX_WOLF=$(tools/fetch-wolf) tests/mpx1     # first light: the wolf kernel on both compiler tiers, both firmwares
PAX_WOLF=$(tools/fetch-wolf) tests/mpx3-shell   # pelt at a prompt, typed sessions held to Linux
PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-nvme    # NVMe disks held to Linux on QEMU: names, bytes, errors, / on NVMe
PAX_WOLF=$(tools/fetch-wolf) tests/mpx6-ahci    # SATA identity, DMA, large LBAs, no-write live boot, / on AHCI
tools/qemu-halt --elf K.elf --drive a.img --nvme n.img --marker halt K.iso   # vda and nvme0n1 beside the ISO; --boot-nvme boots from NVMe
PAX_ROOTDISK_BUS=nvme tools/rootdisk-leg mpx5-users --tier native --firmware bios   # a suite again with / on nvme0n1p2
tools/qemu-run --ahci disk.img,serial=MY-SATA-DISK,model=Test-SSD K.iso  # a SATA disk beside the ISO; --boot-ahci boots from SATA
```

Then, to use it rather than test it:

1. Build the disk that boots: `tools/mkdisk --gpt --kernel K.elf --root I.cpio 512M pax-disk.img`.
2. Boot it in a terminal with the SeaBIOS line under [A disk that boots](#a-disk-that-boots).
3. Type at pelt's prompt; `reboot` restarts on the same disk, `exit` (or Ctrl-D) writes `/` and halts.

The harness never installs anything: a missing tool is named and the tool stops. `tools/qemu-run` boots an image
headless and returns QEMU's status, `(v << 1) | 1` when the kernel writes `v` to the exit port, 0 for a reset or
triple fault, 124 for a timeout; `tools/qemu-halt` holds a kernel that halts to RIP inside `pax_halt` through QEMU's
monitor. Each tool's header comment states its usage; `qemu-run` and `qemu-gdb` print it with `--help`.

## What is in the image

The release and dev images carry the programs below. `/etc/pax-release` prints their exact input identities (the pin
files' digests, the games' source archives, the kernel's own ELF digest and `SOURCE_DATE_EPOCH`), and the boot banner
shows the kernel commit and the first eight digits of that file's SHA256.

| Program | What it is | Pin |
|---|---|---|
| wolf | the build compiler, and the dev image's compiler | 0.2.35 |
| lupin | the reference interpreter for wolf, `/bin/lupin` | 0.1.58, `6240efe5` |
| wolf-std | the standard library beside lupin, `/usr/share/wolf/std` | `78b9d3cb` |
| pelt | the POSIX shell, PID 1 at the console | `4683b3f5` |
| boreutils | coreutils in wolf, 107 command binaries in `/bin` (`df` not yet) | `0f7a57b6` |
| scent | grep in wolf: `/bin/scent`, with `grep` a link to it and `egrep` and `fgrep` its wrappers | `81d761d6` |
| yew | the editor | `0ccb2c67` |
| lope, aspen, lobo | the directory jumper, tree(1), the web server | `e6f623c7`, `3692cf5d`, `49ed870e` |
| clef | the assembler in wolf, opt-in at `/usr/bin/clef` of the dev image | `user/clef.pin` |
| pack, cub, trail | three wolf games, installed by the installer into `~/Games/` with their source | `27848095`, `6a1db765`, `24099a81` (engines `aa6c4dc0`, `74b89744`, `57870143`) |

Every program is built from its own tree, static, and pinned by commit or by digest (`user/*.pin`); `tools/mk*` builds
each. `tools/mkdistribution VERIFIED_BASE.cpio BUILT_INPUTS NEW_OUT` assembles both image variants at one clean
commit: it rebuilds the kernel and the installer, verifies the supplied program outputs, and keeps only the unchanged
compiler and linker bundle from the digest-pinned prior dev payload. Every packed file has a build-time digest
inventory. trail is held at its pin until the [glyph-probe mismatch](https://github.com/wolffe-lang/trail/issues/8)
is resolved. Every ELF process starts with a fixed 1 MiB initial stack, which `RLIMIT_STACK` reports.

Two things the shipped `grep` says that GNU's would not: `--help` and `--version` are scent's own prose, and a
diagnostic names the program as `grep:` whatever path ran it. `-r` and colour are refused by name until scent's next
milestone. Everything else on its first-milestone options is byte-identical to GNU grep 3.12 in the C locale.

## Booting PAX

PAX boots through the Limine protocol (`docs/BOOT.md` says why). Limine is fetched from its release by digest, never
built here. There are four ways to boot, from least to most durable.

### From the ISO

The default: everything the image holds is in memory and gone at the next boot.

```sh
tools/qemu-run --firmware uefi build/mpx1/native/kmain.iso; echo $?
tools/expect-serial build/serial.log PAX "firmware: uefi"
tools/qemu-gdb build/pax-stub.iso build/stub/pax-stub.elf     # gdb, frozen at reset
```

### A disk beside the image

Give QEMU an ext2 image as a virtio block device and the kernel mounts it where the image's `/etc/fstab` says, the
playground's at `/home`:

```sh
tools/mkdisk --home 128M pax-home.img
qemu-system-x86_64 -machine q35 -cpu max -m 512M -display cocoa \
    -serial file:serial.log -nic none -cdrom IMAGE.iso \
    -drive file=pax-home.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0
```

Without `-no-reboot`, root's `reboot` restarts the machine and the same disk boots again. Between boots, `e2fsck -fn
pax-home.img` and `debugfs` read it on the host: the file is the file system, with no partition table.

### A disk that boots

One file, no ISO. `tools/mkdisk --gpt` writes a GPT disk with an EFI system partition (Limine, the kernel, the
initramfs), a BIOS boot partition for Limine's stage 2 and an ext2 partition 2; with `--root` the whole system is
installed onto partition 2 at build time, every mode, owner and time from the archive's own headers, and the kernel
mounts it as `/` from `root=` on Limine's command line (`/dev/vda2`, `PARTUUID=`, `UUID=`, `ro`, `rw`, in Linux's
spellings) with no initramfs. The root is ext3 by default since the journal was added; `--no-journal` makes an ext2 one.

```sh
tools/mkdisk --gpt --kernel K.elf --root I.cpio 512M pax-disk.img
```

Under BIOS (SeaBIOS):

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 512M -nographic -nic none \
    -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0
```

Under UEFI, with the edk2 firmware Homebrew's QEMU ships as a read-only flash (`-bios` with this file is refused):

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 512M -nographic -nic none \
    -drive if=pflash,format=raw,unit=0,readonly=on,file=/opt/homebrew/share/qemu/edk2-x86_64-code.fd \
    -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0
```

What to know at the prompt:

- `-nographic` puts COM1 and QEMU's monitor on the terminal: Ctrl-A x quits QEMU, Ctrl-A c switches to the monitor
  and back, and Ctrl-C reaches PAX.
- `/` is the disk, so what you change anywhere lasts (`/etc`, `/root`, `/home/pax`, `/bin`), but for `/tmp`, which is
  memory. Try `echo hello > /etc/motd`, `lope add /usr/share/tunes`, `cat > notes.txt`, then `reboot`: all three are
  there on the next boot. `cat /proc/self/mounts` shows `/dev/root` at `/`; `cat /proc/partitions` shows the table
  PAX read.
- `exit` (or Ctrl-D at the prompt) sends every process SIGTERM, then SIGKILL after two seconds, writes every volume and
  unmounts it, `/` last, marked clean. On the host, `dumpe2fs -h` of partition 2 then says `clean`.
- **Closing QEMU without `exit` (Ctrl-A x, the window, the terminal) is a power cut.** What the last five seconds wrote
  may be lost. A journalled root is replayed at the next boot before anything reads it; an ext2 root stays `not cleanly
  unmounted` until an offline check repairs it: `fsck.ext2 -y /dev/vda2` from the rescue archive, or `e2fsck -fy` of
  partition 2 on the host (it starts at `--esp` + 2 MiB).
- A second and third disk: `tools/qemu-run --drive a.img --drive b.img` (repeatable; `FILE,ro` for read-only). PAX
  names them `vdb` and `vdc` in PCI slot order, and `/dev` holds a node for every disk and partition.

### The live USB stick

`tools/mkdisk --usb` writes a reproducible raw GPT image with one FAT32 EFI system partition and a reserved Limine BIOS
partition; the supplied initramfs is preserved byte for byte, so the whole live system and any installer or games
payload stay in memory. The live entry accepts `root` with no password and starts pelt; it changes no installed
account and provides no authentication.

```sh
tools/mkdisk --usb --kernel K.elf --initramfs I.cpio --conf boot/limine-usb.conf pax-stick.img
tools/qemu-run --firmware uefi --usb-stick pax-stick.img       # xHCI mass storage, no CD-ROM, no virtio disk
tools/usb-write --dry-run pax-stick.img /dev/sdX               # inspect a removable target; the write is yours to do
PAX_WOLF=$(tools/fetch-wolf) tests/usb-stick --tier native     # BIOS and UEFI, the live login, Linux mounting the ESP
```

Physical writes and real-machine boots are not tested here. See
[The live USB stick](docs/BOOT.md#the-live-usb-stick).

### The guided installer

`pax-install` inventories the real block nodes, shows a read-only plan and requires an exact confirmation of the target
before writing. It is an explicit ext2 developer preview, not a journalled installation:

- whole-disk fresh installs only, 512-byte sectors, root volumes up to 16 TiB less one 4 KiB block;
  larger targets keep that root size and name the remaining space as unused in the plan;
- the running root's disk, mounted disks, read-only targets and disks of 4096-byte logical sectors are refused by name;
- it asks for a user name and whether to install the three games, staged offline with their source and their engine's;
  neither answer fetches anything; the games answer alone decides the install from the verified payload (the live
  demo's marked Games directory is never copied implicitly), and a custom source tree with a Games directory already
  present is still refused;
- it writes with `paxgpt`, `paxfat` and `paxext2`, PAX's own disk tools (below), not embedded formatters.

The installer and the installed tree are tested on separate QEMU virtio disks under BIOS and UEFI, including reboot
persistence. The merge gate (`tier full`) also installs onto a sparse 500 GB disk and `tier all` onto 4 TB, each
target then booted alone under both firmwares. Nothing here is a claim about real-machine drivers. See
[Guided installation](docs/BOOT.md#guided-installation).

## Seeing the screen

The harness boots headless. To see PAX's screen, give QEMU a window; on macOS (Homebrew's QEMU, TCG):

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 256M -display cocoa \
    -serial file:serial.log -nic none -no-reboot -cdrom IMAGE.iso
```

(`-display gtk` or `-display sdl` on Linux, where `-accel kvm` makes it fast.) Limine hands PAX its framebuffer, PAX
draws the console there from its first line, and the window's keyboard is the PS/2 keyboard the console reads, so a
shell image is typed into from the window while COM1 still gets every byte. With `-display none` the screen is drawn
where nobody sees it; `-vga none` (`tools/qemu-run --no-screen`) boots a machine with no display at all.

The framebuffer console is a 160×50 grid in Spleen 8×16 at QEMU's 1280×800 and supports:

- the Linux VT's colour renditions (dim, italic, underline, RGB mapped to its small palette), `OSC P` and `OSC R` for
  the palette, sixteen CSI parameters, scroll margins, character and line insertion and deletion;
- 560 glyphs: every braille pattern, the block elements and the other code points the wolf games use
  (`font/extent.txt`); anything else above U+00FF is `?`;
- the keypad's navigation with NumLock off and digits with it on, decimal entry with Alt and hexadecimal with AltGr;
- USB keyboards over xHCI, directly or behind hubs, sharing the PS/2 keyboard's mapping; unplugging one releases its
  held keys, and a replacement can be attached while the system runs; repeat at 250 ms then 33 ms, as measured on Linux.

Blink attributes are recorded but drawn steadily, and `DECSCUSR` is consumed without changing the cursor's shape, as
on the measured Linux VT.

## Friendly shell editing

Pelt adds opt-in suggestions, syntax colours, abbreviations, history events and extra editing keys. At the prompt:

```sh
set -o friendly -o suggest -o histsearch
```

1. Type `echo prefix_suffix`, then `echo prefix`: the history suffix appears. Enter runs only what you typed; Right
   accepts the suggestion.
2. `abbr add hi 'echo hello'`, then type `hi` and Space.
3. `!!` repeats the previous command, `!$` recalls its last word, and Alt-. inserts the last argument while editing.

Scripts keep POSIX behaviour, and `set +o friendly` turns the additions off. Suggestions default to bright black
(SGR 90); `PELT_COLORS='command=green:shadow=brblack+dim'` dims them and colours resolving commands green. The
framebuffer console reports its 160×50 grid; a serial-only console starts with an unknown (0×0) size.

## The dev image

The dev variant adds to the base image, which it leaves unchanged:

| Addition | Where | Notes |
|---|---|---|
| a musl-static `wolf` | `/usr/bin/wolf` | the v0.2.35 tag built unpatched, so it says the release's own line |
| the compiler's paired standard library | `/usr/share/wolf/compiler-std` | lupin's own stays at `/usr/share/wolf/std`; the shell selects it through `WOLF_STD` |
| a static `ld.lld` 18.1.8 and a link-only `cc` | `/usr/bin` | built from LLVM's release tarball with zlib and zstd (`notes/px80/build-lld.sh`); not a C or assembly compiler |
| musl's binary CRT and libc inputs | | recorded in `user/wolf-link.sums` |
| scent as `grep`, with its fixture | `/usr/share/scent` | `cd /usr/share/scent; grep -n -C1 cat words.txt` |
| clef, the assembler in wolf (opt-in, `tools/mkdev --clef DIR`) | `/usr/bin/clef` | `clef --64 -o x.o x.S`, `clef --expand x.S` |

At the dev console, write a program in your home directory and use:

```sh
wolf fmt hello.lu
wolf fmt --check hello.lu
wolf conform-run --json --phase=typecheck hello.lu
wolf conform-run --json --checked hello.lu
wolf build hello.lu
./hello
```

Three things to know at 0.2.35: there is no `wolf check` command; `wolf run --checked` is a native build, not the
checked machine, and needs the native link step; and `--release` still needs an external clang, which the image does
not carry. `wolf build --no-cache --emit=obj hello.lu -o hello.o` emits a native object with no linker. The dev ISO is
tested with 2 GiB of RAM. `tests/mpx5-wolf` holds root and `pax` sessions byte for byte to the same binaries on Linux
and checks independent command and verdict witnesses, so agreement on a broken compiler cannot pass; its fast CI root
omits the link bundle on purpose and checks the missing-tool errors.

## Disks and rescue

AHCI uses one polled command slot per disk, with reads and writes up to 128 KiB and explicit cache flushes.
Logical sectors must be 512 bytes; 512e disks report their physical sector size through the block ioctls.
Disk names follow controller and port order, not identity: adding a disk on a lower port can rename later disks.
AHCI and NVMe expose hardware model and serial strings under `/sys/block/<disk>/device/`; internal spaces in serials
are preserved. A SATA disk's `model` is its whole ATA model, where Linux shows the first 16 characters (its SCSI
product field). The boot log prints each SATA controller and each disk's port, model, serial, capacity and sector sizes.
AHCI's waits run on the 8254 PIT until the shared clock lands; on a machine whose PIT does not count, each AHCI
controller is refused by name and the boot goes on without its disks.
No SATA hotplug, NCQ or interrupt-driven completion is implemented.

Three programs in wolf write disks, built as static Linux executables and run unchanged on PAX:

| Tool | Writes | Compared with |
|---|---|---|
| `paxgpt` | a GPT | sgdisk, sfdisk |
| `paxfat` | FAT32 and VFAT | dosfstools, mtools |
| `paxext2` | an ext2 tree with modes, owners, times, symbolic and hard links (no journal) | e2fsprogs |

`paxext2` formats volumes through 16 TiB less one 4 KiB block, with fully initialized inode tables and sparse
superblock backups. Its large-volume inode density follows Linux's defaults. File data beyond 2 TiB is written and
read back through both virtio and NVMe, with the same bytes read by a Linux guest.

The tests compare each tool's output with the host's, then build a second disk entirely on PAX through its `/dev/vdb`
node and boot it alone under SeaBIOS and OVMF. Limine's pinned installer is linked statically with no source change,
and its Linux and PAX runs write identical bytes. See `docs/BOOT.md`, "Writing a disk on PAX".

`tools/mkfsck` builds `fsck.ext2` in wolf for Linux and PAX. It checks inodes, blocks, directories, connectivity,
references and allocation summaries; repairs counts, bitmaps, links, orphans and duplicate data blocks; and replays
supported ext3 journals. A separate rescue archive repairs an unmounted `/dev/vda2` without Linux. Unsupported formats
and ambiguous damage are refused, never marked clean, and a mounted volume is never repaired. The current checker
also refuses more than 4,194,304 blocks, 1,048,576 inodes or 512 groups by name; large installed volumes need Linux's
`e2fsck` until the checker is extended. See `docs/BOOT.md`, "Checking a volume from rescue".

## Tests

Every suite is a script under `tests/` that builds images, boots them under QEMU and asserts the serial log, the exit
status and, where the behaviour is Linux's, the same session on a real Linux. Each runs as
`PAX_WOLF=$(tools/fetch-wolf) tests/NAME`; `--images DIR` boots images built elsewhere (a KVM host, a Mac under TCG),
and `--tier native --firmware bios` picks one leg.

| Group | Suites | What they hold |
|---|---|---|
| The harness's own proofs | `proof`, `expect-serial-selftest`, `paxtcp-selftest`, `lobo-session-selftest`, `gdb-attach`, `ci-plan`, `census`, `kernel-as`, `mkw` | that the harness can fail, that CI's plan covers the change, every syscall by name, both assemblers' identical kernels, the first wolf kernel |
| The kernel's core | `mpx1`, `mpx2-frames`, `mpx2-paging`, `mpx2-interrupts`, `mpx2-sched`, `mpx2-heap` | first light, the frame allocator, paging, named panics and the timer, threads, the heap: read back through QEMU's monitor |
| Programs and the console | `mpx3-user`, `mpx3-loader`, `mpx3-boreutils`, `mpx3-console`, `mpx3-shell`, `mpx3-screen`, `mpx3-threads`, `mpx3-tree`, `mpx3-maps`, `mpx3-speaker`, `mpx3-sound`, `mpx3-orchestra` | ring 3, the ELF loader, boreutils and pelt against the same binaries on Linux, screendumps against the reference renderer, threads and signals, the writable tree, mappings, sound captures |
| The network | `mpx4-net`, `mpx4-udp`, `mpx4-tcp`, `mpx4-ready`, `mpx4-unix`, `mpx4-session`, `mpx4-lobo` | captures rebuilt byte by byte, the witnesses against `tools/net-peer` and QEMU's user network (root for the Linux side), `poll` and `epoll`, Unix sockets, lobo serving |
| Users and the shipped programs | `mpx5-users`, `mpx5-accounts`, `mpx5-jobs`, `mpx5-pelt`, `mpx5-bore`, `mpx5-scent`, `mpx5-lope`, `mpx5-aspen`, `mpx5-lupin`, `mpx5-yew`, `mpx5-wolf`, `mpx5-clef`, `mpx5-screen` | every rule as root and as `pax`, job control typed byte for byte, each program's typed session against the same binary in a container |
| Disks | `mpx6-blk`, `mpx6-ext2`, `mpx6-part`, `mpx6-root`, `mpx6-journal`, `mpx6-nodes`, `mpx6-nvme`, `mpx6-ahci`, `mpx6-disktools`, `mpx6-fsck`, `mpx6-install`, `mpx6-games` | Linux 7.3.0 on QEMU with the same disks, e2fsprogs, the formatters' differentials, a power cut repaired, the installer, the games' frames cell for cell |
| USB | `mpx6-usb`, `mpx6-usbcheck`, `usb-tools`, `usb-stick`, `usb-linux-fetch` | xHCI, hubs, keyboard bytes and hotplug; the stick's boot files, both firmwares, Linux mounting the ESP; the oracle's two pinned Ubuntu packages |

Suites that need something of the host say so and stop: root for the Linux network side (`tools/linux-net`), docker or
podman for the throwaway containers (`tools/linux-tree`, e2fsprogs), KVM for speed. `tools/mkimage` is reproducible:
every date in an ISO is `SOURCE_DATE_EPOCH`, default the last commit's time, so one commit builds one digest.

## Continuous integration

- A pull request's push runs the suites its change can affect (`tools/ci-plan`, `tools/ci-tiers.map`) on one leg,
  native BIOS; a change to the kernel's core or to CI itself runs every suite on that leg.
- The `full-matrix` label runs every suite on the merge leg (`tier full`); a push to trunk, the nightly and a dispatch
  run every suite on every compiler and firmware leg (`tier all`). Merging needs a green `tier full` or `tier all` run
  at the head.
- Long jobs have budgets: 75 minutes for interrupts, 90 for the heap, 210 each for pelt and users, 90 for users again
  with `/` on AHCI (`mpx5-users-ahci`, a job of its own), and for the installer 110 in `tier full` and 175 in `tier all`
  (its 500 GB and 4 TB installs); the measured stage timings and their headroom are in
  [CI budgets](tests/ci-budgets.d/README.md). The root-disk `chk-soak` has 1200 seconds for its 100,000 rounds.
- A test is seen red before it is trusted: the break is planted in a commit and run of its own, then fixed.
- One known stall of the Linux reference shell ([#196](https://github.com/wolffe-lang/pax/issues/196),
  [pelt#98](https://github.com/wolffe-lang/pelt/issues/98)) gets one retry of its Linux leg only, with a warning that
  names the issue and the first log uploaded beside the retry; a second failure stays red, and nothing else is ever
  retried. The exception lives in `tools/ci-retry` and goes when the upstream fix is pinned.

## Hosts

| host | build an image | boot one (`qemu-run`, `tests/proof --image`) | gdb (`qemu-gdb`) |
|---|---|---|---|
| linux x86-64 (CI's ubuntu, the pool) | yes: binutils, cc, make, curl, xorriso | yes: `qemu-system-x86_64`; OVMF for UEFI; KVM used when `/dev/kvm` is usable | yes: gdb |
| macOS arm64 | **no**: no x86-64 ELF binutils or xorriso in the base system | **yes**, TCG: Homebrew's `qemu`, which ships its own UEFI firmware; CI's `macos-run` job boots the linux-built ISO on every push | no gdb in the base system; `tools/qemu-run --gdb 1234` and lldb's `gdb-remote 1234` by hand |

- **CI**: `ubuntu-latest` with QEMU 8.2.2, OVMF and xorriso from apt (TCG); the `macos-run` job boots the same ISO,
  checked by digest, with Homebrew's QEMU 11.1.1 (TCG).
- **NixOS**: nothing system-wide is needed. QEMU and xorriso come from a nix-shell and the UEFI firmware from nixpkgs'
  OVMF; use the **combined** `OVMF.fd` with no separate vars file, because the split `OVMF_CODE.fd` + `OVMF_VARS.fd`
  pair hangs in the firmware under KVM there:

  ```sh
  ovmf=$(nix-build --no-out-link '<nixpkgs>' -A OVMF.fd)/FV
  PAX_OVMF_CODE=$ovmf/OVMF.fd PAX_OVMF_VARS= \
    nix-shell -p qemu xorriso --run 'PAX_QEMU=$(command -v qemu-system-x86_64) tests/proof'
  ```
- **Arch-family Linux**: QEMU 11.1.1, xorriso and OVMF from the repositories build and boot everything (TCG or KVM).
- **macOS** (arm64): `tests/proof --image` on an ISO built elsewhere, as CI's `macos-run` does.

The QEMU binary is `$PAX_QEMU` (default `qemu-system-x86_64` on `PATH`) and the UEFI firmware `$PAX_OVMF_CODE` /
`$PAX_OVMF_VARS`, so every host supplies its own. The UEFI leg looks for OVMF at the distro paths in `tools/lib.sh`;
without it `tests/proof` skips that leg loudly, unless `PAX_REQUIRE_UEFI=1` (CI), when it fails.

## Layout

| Directory | Holds |
|---|---|
| `kernel/` | the wolf kernel, one module per subsystem (`kernel/README.md`), its `wolf.pkg` and the wolf and lupin pins |
| `boot/` | the Limine pin and configs, the kernel's entry and requests, port I/O, the control registers, the interrupt trampolines and the descriptor tables' storage (`start.S`, `io.S`, `cpu.S`, `isr.S`, `kernel.ld`), and the harness's assembly proof under `boot/stub/` |
| `user/` | what the images carry: the pins of every shipped program (`*.pin`), the typed sessions (`console/`), `su`, the probes (`elf/`, `net/`), `play/` and `tunes/`, `disktools/` (paxgpt, paxfat, paxext2), `install/` (the guided installer), the fstabs and the shell's `$ENV` file |
| `tools/` | the harness: the fetchers by digest (`fetch-limine`, `fetch-wolf`, `fetch-lupin`, `fetch-usb-linux`), the builders (`build-kernel`, `mkimage`, `mkdisk`, `mkdistribution`, `mkinstall`, `mkgames`, `mkfsck`, `mk*` for each program), the QEMU drivers (`qemu-run`, `qemu-halt`, `qemu-fault`, `qemu-gdb`, `expect-serial`), the Linux sides (`linux-run`, `linux-net`, `linux-tree`, `linux-blk`, `linux-part`), the network tools (`net-peer`, `pcap-net`, `gateway-probe`, `paxnet.py`, `paxtcp.py`), the font tools (`mkfont`, `screen-ref`), the USB tools (`check-usb`, `usb-write`, `usb-typing`) and CI's planner (`ci-plan`, `ci-tiers.map`, `ci-retry`) |
| `font/` | the screen's font: Spleen 8×16 (BSD-2-Clause, with its licence), `extent.txt` (the code points drawn above U+00FF), `pax-extra.bdf` (PAX's own rows for the glyphs Spleen lacks) and `games-glyphs.txt` |
| `tests/` | the suites above, each with its fixtures in `NAME.d/`; `ci-budgets.d/` |
| `docs/` | `BOOT.md` (the boot protocol, the disks, the installer and rescue, argued), `SOURCES.md` (the consulted-sources log), `CENSUS.md` (every system call PAX serves, by name), `HISTORY.md` (how PAX got here, lane by lane) |
| `notes/` | one note per lane: its contract and evidence |

The plan lives in the wolf planning repository under `sprints/pax/`. How PAX came to be, in the order it was built, is
[docs/HISTORY.md](docs/HISTORY.md).
