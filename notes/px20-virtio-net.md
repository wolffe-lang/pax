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

## What was built

1. **PCI** (`kernel/pci`, `boot/io.S`'s `pax_outl`/`pax_inl`): bus 0
   and the bus behind any bridge through configuration mechanism #1;
   each function's ids, class, header type, pin and line recorded in
   `pax_pci_table`; BARs and the capability list read on demand; the
   census printed when the kernel command line holds `pci`
   (`boot/limine-net.conf`).
2. **The virtio transport** (`kernel/virtio`): the four vendor
   capabilities found and mapped uncached in the device slot; reset,
   ACKNOWLEDGE, DRIVER, the features, FEATURES_OK read back, the
   queues, DRIVER_OK; a queue's three parts in one frame from the frame
   allocator, held to the specification's alignment table by a check
   of its own before the device is told; notification at the address
   the capability and `queue_notify_off` give, honouring NO_NOTIFY.
3. **virtio-net** (`kernel/net`): VERSION_1 and MAC taken and required
   (a device lacking either, or the 1.x interface, is refused by name);
   the address from the configuration; 64 receive buffers offered and
   each offered again once its frame is handled; a transmit free list,
   returned buffers taken back at each send; the 12-byte header; the
   interrupt handler reads the cause, acknowledges and wakes
   `kernel/netd`'s thread, which is the only code that looks at a
   frame.
4. **The frame interface**: `net.send` (rows `down`, `size`, `full`),
   `net.rx_take`/`rx_give`, `net.wait`, and counters: frames and bytes
   each way, eight drop causes, interrupts, buffers reclaimed and
   restocked.
5. **ARP** (`kernel/arp`): RFC 826's reception algorithm and a
   request; 10.0.2.15 is `kmain_net`'s constant.
6. **Tests** (`tests/mpx4-net`, `tools/pcap-net`, the `mpx4-net` CI
   job): N0–N11, below.

Filed: wolf-lang#653 (a module `const` initialised from another
module's `pub const` is "an unresolved name at comptime", reported with
a byte offset and no file).

## 3. The prediction against the measurement

| predicted | measured |
|---|---|
| the 1.x interface through the capabilities in BAR4 | so: BAR4 on every host (`0xfe000000` under SeaBIOS; `0x7000000000`, above 4 GiB, under hasu's OVMF), the legacy BAR0 untouched; the same driver brings up a 1.x-only device (`disable-legacy=on`, `1af4:1041`) and refuses a legacy-only one (`disable-modern=on`) by name |
| INTx on line 10 or 11, level, ISR read then EOI; MSI-X off; transmit interrupts suppressed | line 11, vector 43, on every host and both firmwares. **Not predicted:** OVMF leaves the line edge-triggered in ELCR (`0000`; SeaBIOS `0c00`), so the driver sets its line's bit itself. Every interrupt had a cause (0 idle); one interrupt and one wake per received frame |
| features taken `0x0000000100000020`; offered would hold MRG_RXBUF, STATUS, CTRL_VQ, INDIRECT_DESC, EVENT_IDX and the checksum and segmentation bits | taken as predicted. Offered `0x0000010130bf8024` on QEMU 8.2.2 and 11.1.x: bits 2, 5, 15–21, 23, 28, 29, 32, 40. **Wrong about offloads:** no checksum or segmentation bit is offered over the user-mode netdev |
| queues 0 and 1, 64 entries, descriptors at 0, avail at 1024, used at 1160 of one frame | so (`…000`, `…400`, `…488`) |
| transmit, 60-byte frame: 40,000/s under TCG, 60,000/s under KVM | kasumi TCG 122,742–212,444/s; CI TCG 93,933–183,808/s; nomad-1 TCG 84,767–153,011/s; **hasu KVM 1,286,022–1,377,398/s**. Low by 2 to 5 times under TCG and by 20 under KVM |
| transmit, 1514-byte frame: 10,000/s under TCG, 40,000/s under KVM, "bounded by the kernel's byte copy" | kasumi TCG 106,652–151,987/s; CI 80,331–161,352/s; nomad-1 78,979–114,244/s; hasu KVM 769,405–848,680/s. Low by 8 to 20 times, and the stated bound was wrong: the copy is `rep movs` (`pax_fb_copy`), not a byte loop |
| an ARP exchange: 5,000/s under TCG, 10,000/s under KVM; the soak under 10 s | kasumi TCG 28,250–66,916/s; CI 24,882–41,864/s; nomad-1 22,697–36,166/s; hasu KVM 63,508–72,173/s. The 10,000-exchange soak takes 0.13 to 0.43 s |
| existing files changed: `boot/io.S`, `kernel/wolf.pkg`, `kernel/interrupts`, `kernel/sched`, `kernel/timer`, `kernel/sync`, CI, the READMEs, CHANGELOG, SOURCES | those, and one not predicted: `kernel/log` (`hex_n`). No existing `kmain*.lu`, tool or test changed |
| new files as listed | so; the capture checker is `tools/pcap-net` |

Rates are by the time-stamp counter, calibrated against 20 PIT ticks in
the same boot, with QEMU's capture on; ranges are over both tiers, both
firmwares and both device flavours (kasumi: the gauntlet at `9614eb9`;
CI: run 38080568042; hasu: round 1 of three; nomad-1: one run). Why the
transmit rate is so far above one notification's cost is **inferred,
not measured**: the device sets NO_NOTIFY in the used ring while it is
emptying the queue, so most sends write no notification at all (the
driver does not count the ones it skips).

## 4. Evidence index

- **The PCI census** (N1), from the kernel, on every host: 6 functions
  on q35 with the device (5 without); the device at `00:02.0`,
  `1af4:1000` (subsystem `1af4:0001`, rev 00) or, with
  `disable-legacy=on`, `1af4:1041` (subsystem `1af4:1100`, rev 01);
  class 02.00.00; pin A, line 11; capabilities `11@98 09@84 09@70
  09@60 09@50 09@40`; BAR0 I/O (absent on the 1.x-only device), BAR1
  32-bit memory, BAR4 64-bit prefetchable memory. CI's QEMU 8.2.2
  presents the same transitional device (`ci-38080568042-…txt`, N1).
  QEMU's own account with the machine stopped at reset:
  `notes/px20/infopci.{kasumi,hasu,nomad-1}.txt`.
- **The captures** (N5): every run's pcap digests and sizes are in its
  `mpx4-net-runs.txt` lines (kasumi: `kasumi-g2-mpx4-net-runs.txt`; CI:
  the `halt-status` lines of `ci-38080568042-mpx4-net-9614eb9.txt` and
  the run's `pax-mpx4-net-linux` artifact, which holds the eight pcap
  files). A capture is 10.7 MB (45,005 frames), so the repository
  carries one capture's first twelve frames as a pcap of its own,
  `notes/px20/kasumi-g2-native-bios-net.head.pcap` (of the capture
  `cab45d96…`: the gateway's request, PAX's reply, the test's
  datagram, then requests and replies; cut short, so `tools/pcap-net`
  reads it with `--list` and says where it ends), and
  `tools/pcap-net`'s verdicts for all eight of the gauntlet's
  (`kasumi-g2-mpx4-net.checks.txt`). The gateway's request is 60 bytes
  and its replies 64 on QEMU 11.1.x; on CI's 8.2.2 the request is 42,
  unpadded. On UEFI boots OVMF's own driver sends one or two IPv6
  frames before the kernel starts (printed as "before the kernel").
- **A whole transcript**: `notes/px20/kasumi-g2-native-uefi-net.transcript.txt`
  (the census, the device's lines, the exchange, the counters).
- **The soak** (N6): 10,000 requests and 10,000 replies on every leg;
  frames free, heap pages, live blocks and the driver's 66 frames
  unchanged across it (for example kasumi native BIOS: frames free
  64731 -> 64731, heap pages 0 -> 0, live blocks 0 -> 0, net frames
  66 -> 66). The heap's books are flat because nothing on the frame
  path allocates from it (§1); what could leak is frames and ring
  entries, and N8 holds those: every sent buffer reclaimed, every
  received one restocked, 64 of 64 transmit buffers free at the end.
- **Planted breaks, red in CI**:
  - a wrong ring alignment (`8565b1d`: the used ring rounded to 2, not
    4): run **38078662258**, the `mpx4-net` job alone red, N2–N8 on
    all eight legs with a device, the driver's line `net: refused: the
    receive queue could not be laid out, used ring at
    0xffff80000011c486; the network is off`
    (`ci-38078662258-mpx4-net-plant-8565b1d.txt`); reverted in
    `1bb8f9a`. (N9, the halt, and N10, N11 stay green: the kernel
    still ends without a panic.)
  - a dropped used-buffer reclaim (`22ed17a`: `send` takes back no
    returned buffer): run **38080152163**, N5, N6 and N8 red on all
    eight legs — the soak stops at its 64th frame (`soak: 63 requests,
    62 replies in 301 ticks`, `1 full`)
    (`ci-38080152163-mpx4-net-plant-22ed17a.txt`); reverted in
    `ba0e5b4`.
  - not planted, seen: run **38077200062** at `b4f8a27` red on N5 and
    N8, because QEMU 8.2.2's gateway does not pad its request and
    `tools/pcap-net` then demanded 60 bytes
    (`ci-38077200062-mpx4-net-b4f8a27.txt`); fixed in `3d70747`.
- **Boot counts** (`tests/mpx4-net` is 16 boots: 2 tiers × 2
  firmwares × net, modern, absent, legacy):
  - kasumi, QEMU 11.1.1, TCG: 32 in the two gauntlets (`d1ef798` and
    `9614eb9`, each 82 PASS, 0 FAIL, 0 SKIP), 36 in three earlier
    runs while the test was written, 8 in the two plants' local
    runs, and about ten single boots before the test existed;
  - hasu, QEMU 11.1.0, **KVM**: 48 in three rounds at `9614eb9`
    (kasumi-built images, each round 80 PASS, 0 FAIL;
    `hasu-kvm-9614eb9.log`, `hasu-kvm-9614eb9-round1.out`), 16 in one
    earlier round;
  - nomad-1, QEMU 11.1.1, TCG on macOS arm64: 16 (the gauntlet's
    `d1ef798` images, 80 PASS, 0 FAIL;
    `nomad-1-tcg-d1ef798-images.out`);
  - CI, QEMU 8.2.2, TCG: 16 a run.
- **The gauntlet** on kasumi at `9614eb9` (strict env, QEMU 11.1.1
  TCG, wolf 0.2.26, clang 23.1.1; user programs built in
  `px13-ubuntu`): every pax suite exit 0, 0 SKIP
  (`kasumi-g2.summary`, `kasumi-g2.versions`). Every kernel links
  `net`, `virtio` and `pci` now; no other suite's assertions moved.
- **CI green**: run 38080568042 at `9614eb9` (19 jobs; `mpx4-net` 82
  PASS), and at the head (the PR names the run).

## 5. Done-when

Branch `px20`; PR pax#23 open, unmerged, five sections by name, commit
shas as bullets, a test checklist; CI green at the head;
`wolf/tools/lane-audit.sh pax px20 23` run by the lane. Nothing is
closed. To close at merge: nothing (wolf-lang#653 is new and stays
open).

**px21 (IP and ICMP) inherits:**

- `net.send(frame, len)` and the receive path through `kernel/netd`:
  add IPv4 where `netd` now calls `net.drop_type` (type 0x0800 is
  counted as `ipv4` today; `tests/mpx4-net` N8 holds that count to the
  test's own datagrams and will move);
- `kernel/arp`'s four-entry table with no ageing, no retry and no
  queue of frames waiting on a resolution: px21's ARP cache replaces
  it. `arp.lookup`, `arp.request` and the lock order (`sync.arp()`
  before `sync.net()`) are the seams;
- the address is `kmain_net`'s constant (10.0.2.15), the gateway
  10.0.2.2 at 52:55:0a:00:02:02; QEMU's gateway learns the guest's
  address from the guest's first ARP frame, and asks only when it has
  a datagram for a guest it has not heard from (`hostfwd`);
- frames arrive in thread context with interrupts on, one at a time,
  in a 2048-byte buffer that must be given back (`rx_give`) before the
  queue of 64 runs dry; a protocol that keeps a frame must copy it;
- no checksum offload is offered or taken: IP, ICMP, UDP and TCP
  checksums are the kernel's to compute and to check;
- QEMU 8.2.2's gateway sends frames shorter than 60 bytes (42, 45):
  `kernel/net` accepts anything from 14 bytes, so a protocol checks
  its own lengths;
- the interrupt is INTx on the 8259; one interrupt per frame at these
  rates. MSI-X, EVENT_IDX and merged buffers are untaken levers;
- owed by an earlier lane and not this one's: `docs/CENSUS.md` lines
  56 and 640 and `docs/SOURCES.md` line 77 (px19's note); `/dev/tty0`
  (px18's).
