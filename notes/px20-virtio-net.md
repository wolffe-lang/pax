# px20 — virtio-net (PAX sends and receives frames)

Contract: px20's, `sprints/pax/20-virtio-net/px20-virtio-net.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-10). Branch `px20` in
pax, cut from pax trunk `bc130e4` (px17, px18 and px19 merged). §1–§3
are committed before the first change to the kernel, the tools or the
tests.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22):
  not Linux, a BSD, lwIP, picoTCP, smoltcp, iPXE, SeaBIOS, OVMF or QEMU,
  and no virtio driver from anywhere, a web search's included; the refs
  clone's sparse checkout is never widened. Read or relied on for this
  lane: the OASIS Virtual I/O Device specification 1.x (the PCI
  transport's capability layout, the split virtqueue, the network
  device), the PCI Local Bus specification's configuration space
  (mechanism #1, the type 0 and type 1 headers, BARs, the capability
  list), Intel's ICH9 data sheet (the PIRQ routing and ELCR registers)
  and 8259A data sheet, RFC 826 and RFC 894, QEMU's documented options
  (`-device virtio-net-pci`, `-netdev user`, `-object filter-dump`) and
  black-box runs (QEMU's monitor, the capture file, the kernel's own
  log). Each is recorded in `docs/SOURCES.md` with how it was used.
- No `region` is held open across a yield, a switch or a return to user
  mode (wolf-lang#611; pax has not adopted s223). The frame path
  allocates nothing from the heap: its memory is frames from
  `kernel/frames` and words in `.bss`.
- Nothing in pax names any use of the image beyond running it (the
  contract's word list). "Capture" here means QEMU's `filter-dump`
  object writing the netdev's frames to a pcap file a test reads.
- No socket system call, no IP, no ICMP, no user-visible network
  interface: the kernel-internal frame interface is the whole surface.
  An IPv4 frame that arrives is counted and dropped by name.
- No test binary is built with kasumi's CachyOS glibc (this lane builds
  no user program at all). No build on nomad-1.
- No `rm` outside `~/lanes/px20/` and this lane's private clones; no
  `git add -A`; nothing under `~/.claude`; no merge; no attribution
  trailers; no "seen red" without a run id, sha, path or digest.

## 2. Inputs, verified (2026-10-10, from origin)

| input | found |
|---|---|
| pax trunk | `bc130e4` (px18 merged, PR #22, after px17 `df5de90` and px19 `1e336af`), as the contract says; trunk CI green at `bc130e4` (run 38041160139) |
| interrupts | `kernel/idt`: 256 gates, vectors 0-47 routed through `boot/isr.S`'s 48 trampolines, the rest not present. `kernel/timer`: the two 8259s remapped to 32 and 40, every line masked but the ones a driver unmasks (0 the PIT; 1 and 4 by `kernel/console`); `unmask` takes a master line only. `kernel/apic`: the local APIC stays enabled with LINT0 as ExtINT (the 8259's INTR passes through); there is no I/O APIC code, no local-APIC EOI and no gate above 47 |
| what a PCI device can use today | **INTx through the 8259 pair**, on the ISA line the firmware wrote into the function's Interrupt Line register (the ICH9's PIRQ routing): a slave line (8-15) needs the slave's mask bit and the master's line 2 cleared, which nothing does yet. **MSI and MSI-X: not usable** without new gates (vector 48 up), their trampolines and a local-APIC EOI |
| the heap | `kernel/heap` (px06): `alloc`/`free` under `sync.heap()`, its books (`pages`, `live_blocks`, `frames_taken`) readable; a block made outside every `region` is never freed, and no `region` may span a switch, so a driver whose thread blocks must not allocate from it |
| threads | `kernel/sched` (px07): 16 slots, `create(body, arg)`, `yield`, `sleep(n)`; a wait state per kind of event (INPUT with `block_input`/`wake_input`, PIPE with `block_pipe`/`wake_pipes`) and `kick` (run a woken thread at once when the CPU was idle); a body is an `export fn` named from another module with `extern "c" let` |
| port I/O and MMIO | `boot/io.S`: `pax_outb`, `pax_inb` only: **no 32-bit port access**, which configuration mechanism #1 needs (0xCF8, 0xCFC). MMIO: `kernel/apic`'s pattern, a page mapped uncached (PCD, PWT) in PML4 slot 352 and read and written volatile, one access per register |
| the harness | `tools/qemu-run`: q35, `-cpu max`, 256 MiB, `-nic none`; QEMU arguments after `--`; `tools/qemu-halt --qemu ARG` passes one through (px18). No kernel has a network device today |
| wolf 0.2.26, freestanding | `read_volatile`/`write_volatile` through `N as *T` for `u8`, `u16`, `u32`, `u64`; `atomic_load`/`atomic_cas`/`atomic_store` on raw pointers; `#[repr(c)]`, `size_of`, `offset_of`; module `const`; `-> never`; checked arithmetic and narrowing casts (a ring index is masked before it is narrowed) |
| QEMU | kasumi 11.1.1, nomad-1 11.1.1 (Homebrew), hasu 11.1.0 (`nix-shell -p qemu`), the CI runner 8.2.2 (ubuntu-24.04, `1:8.2.2+ds-0ubuntu1.18`, from run 38041160139's log) |
| `-device virtio-net-pci` on q35 | **transitional** on kasumi, nomad-1 and hasu, read from QEMU's monitor with the machine stopped at reset (`info pci`, `notes/px20/infopci.*.txt`): bus 0, device 2, function 0, vendor `1af4`, device `1000`, subsystem `1af4:0001`, pin A; BAR0 I/O (the legacy interface), BAR1 32-bit memory (the MSI-X table), BAR4 64-bit prefetchable memory (the 1.x capabilities' registers), an expansion ROM. The CI runner's is read by the test in CI (the census line) |
| SeaBIOS with the device | boots as before (kmain_timer with the device attached: 20 ticks, halt); the ROM's banner line appears on serial before Limine. The firmware may have driven the device, so the driver resets it first |

## 3. Prediction (before the first change)

- **Interface: the 1.x one, through the PCI capabilities (MMIO in
  BAR4), not legacy port I/O.** Why: it is the interface the
  specification defines normatively; the transitional device every
  host presents offers it, and a non-transitional one (`1af4:1041`,
  `disable-legacy=on`, or a device behind a PCIe port) offers nothing
  else, so one driver serves both; with VIRTIO_F_VERSION_1 the header
  is one fixed 12-byte little-endian layout and the three ring parts
  take separate addresses, where the legacy layout is one contiguous
  block whose used ring the device finds by a rounding rule. Cost: a
  capability walk and a mapping in the device slot (352). The legacy
  BAR0 is never touched.
- **Interrupt: INTx, level, through the 8259 pair** on the line the
  firmware left in Interrupt Line (predicted 10 or 11: vector 42 or
  43), acknowledged by reading the ISR status register, then the
  8259 EOI; the handler only records and wakes a kernel thread. MSI-X
  stays off (`msix_config` and the queue vectors untouched). The
  transmit queue's interrupt is suppressed (the avail ring's
  NO_INTERRUPT flag); sent buffers are reclaimed at the next send.
- **Features negotiated: VIRTIO_F_VERSION_1 (bit 32) and
  VIRTIO_NET_F_MAC (bit 5) only**, the word `0x0000000100000020`;
  either missing is a refusal by name. Offered and declined
  (predicted present in the device's word): MRG_RXBUF (15), STATUS
  (16), CTRL_VQ (17), INDIRECT_DESC (28), EVENT_IDX (29), the checksum
  and segmentation bits.
- **Queues:** receive 0 and transmit 1, 64 entries each (the device's
  256 reduced), each queue's three parts in one frame (descriptors at
  0, avail at 1024, used at 1160), one 2048-byte buffer per
  descriptor.
- **Frames per second** (transmit, one notification a frame, measured
  by the PIT's tick):

  | | 64-byte frame (60 + FCS) | 1514-byte frame |
  |---|---|---|
  | TCG (kasumi) | 40,000 | 10,000 |
  | KVM (hasu) | 60,000 | 40,000 |

  and an ARP request answered by the gateway (a round trip through
  the interrupt and the thread): 5,000 a second under TCG, 10,000
  under KVM, so the 10,000-exchange soak takes under 10 s on either.
  The 1514-byte figure is bounded by the kernel's byte copy on the
  native tier.
- **Existing files that change:** `boot/io.S` (32-bit port access),
  `kernel/wolf.pkg` (one more storage file), `kernel/interrupts` (the
  device's vector), `kernel/sched` (a wait state for the network
  thread), `kernel/timer` (unmasking a slave line), `kernel/sync` (a
  lock word), `.github/workflows/ci.yml`, the READMEs, `CHANGELOG.md`,
  `docs/SOURCES.md`. Predicted unchanged: every existing `kmain*.lu`,
  `tools/qemu-run`, `tools/qemu-halt`, every existing test. Every
  kernel's bytes move (`kernel/interrupts` is in each).
- **New:** `boot/net.S` (storage), `kernel/pci`, `kernel/virtio`,
  `kernel/net`, `kernel/arp`, `kernel/netd` (the thread body),
  `kernel/kmain_net.lu`, `boot/limine-net.conf` (the census switch on
  the command line), `tests/mpx4-net`, a pcap checker in `tools/`.
