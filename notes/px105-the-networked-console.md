# px105 — the networked console: network on the console kernel every image boots

`kmain_console`, the kernel every shipped console image boots, linked px89's network modules (`kernel/dhcp`,
`kernel/gbe`, `kernel/net`) but never started the stack. No image gave the metal target network: no DHCP, no den
over `git://` or `https`, and px100's `git://` clone stalled at the console at prompt 73. Only `kmain_sockets` and
`kmain_session` read `/etc/pax-net`. Now the console starts the stack as kmain_session does, with bounds of its own,
takes its address as `/etc/pax-net` says (a lease, or, new, a static address), ships `dhcp wait=10` in the release
and dev roots, and never lets a missing device, a cable with no link or a server that never answers stop the boot.

Footprint: cross-cutting (`.github/workflows/ci.yml` gains the `mpx4-console-net` job; `tests/ci-plan` and
`tools/ci-tiers.map`; the kernel's three network kmains, `kernel/dhcp`, `kernel/net`, `kernel/gbe`; `tools/mkden`,
`tools/distribution-root`).

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware, driver, emulator, DHCP, HTTP or TLS implementation's source, and no Git
  source. The sources are in `docs/SOURCES.md` (px105): RFC 2131 and resolv.conf(5) as px89 read them, Intel's
  public 82576 and I210 datasheets for STATUS.LU alone, QEMU's documentation for its monitor and netdevs (its igb
  model measured black box), and the org's own den (its smart-HTTP fixture and URL rules) and wolf-std (the TLS
  client's name check). git and OpenSSL ran as black boxes.
- **Hosts.** Two x86-64 Linux hosts with KVM, each behind its lock names; the build Mac for git and the planner's
  rows behind its build lock. The metal target was never touched.

  | host | CPU | memory | here |
  |---|---|---|---|
  | Linux host 1 | Intel Core i7-12700KF, 20 threads | 46 GB | the probes, the red and green runs, the records |
  | Linux host 2 | Intel Core i7-10870H, 8 cores / 16 threads | 31 GB | probe 1's second take |

- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `84a1fde3` (px100's head) | `git log` at the clone |
| wolf | 0.2.35, `kernel/wolf.pin`'s archive `4cc4045b…` (`tools/fetch-wolf` by digest) | every build |
| Limine | 12.9.1, `boot/limine.pin`'s `5cdebc51…` | `tools/fetch-limine` by digest |
| den at the image's pin | `584b18a3` (`user/den.pin`), static `ac1ec526…`, 17,251,992 bytes | `tools/mkden`, four builds, one digest |
| den at the https pin | `ac2332bf` (`tests/mpx4-console-net.d/den-https.pin`, den's merge of its smart-HTTP transport) | `tools/mkden` with `PAX_DEN_PIN` |
| the lane container | Ubuntu 24.04 with QEMU 8.2.2, OVMF, clang, lld 18, dnsmasq-base, iproute2, tcpdump, openssl, git | the image's package list |

## 3. Prediction, scored

`notes/px105/prediction.txt`, committed first (`ffa4b239`). Measured on Linux host 1 under KVM, a light slot
(two CPUs), native BIOS, each pair from the same pipeline at the rows tip (the base's kernel) and at the head.

| | predicted | measured | |
|---|---|---|---|
| R-px105-1 size | A: under 4 KiB more ELF a tier, under 0.5 % | native 3,410,880 → 3,430,168 bytes, +19,288 (0.57 %); release in the record | **wrong**: the bring-up, the static parser and the lines are five times the guess; still under 1 % |
| boot, no device | under 10 ms more | `boot:` 201 and 203 ms at the base, 199 and 198 at the head (none, nofile) | held |
| boot, virtio-net + QEMU's DHCP | under 0.2 s more | 264 ms (base 200): +64 ms; the console waited 64 ms | held |
| boot, igb + QEMU's DHCP | about 1.5 s more (the 82576's PHY restart) | 1,792 ms (base 200): +1.6 s; waited 1,593 ms | held |
| every console row | five more lines before `run 1:` with no device; one more kernel thread; 333 frames fewer | six: the five and R-px105-5's waited line (`notes/px105/probe1.txt`'s base log against the head's, numbers aside); no other line moved | held, with the sixth line the prediction's own R-px105-5 asks for |
| no existing row's assertion moves | | the gauntlet's suites (the record) and the labelled full tier | see the record |
| C1-C9, H1-H5 red at the base by name | | red at the rows tip (the base's kernel): C1-C7 and C9 by name; C8 (the halt) held there, as a base kernel halts; H1-H5 red, den's clone never returning and the fixture seeing no request (§4.2) | held |
| mpx5-den R4 red at the base at prompt 73 | | (§4.2) | |
| C1-C9, H1-H5 green at the head | | green on BIOS and UEFI (§4.2) | held |
| igb with no link, the way to make it | (not predicted) | a listening socket netdev, a hub port alone, a NIC with no peer and a link set down before `cont` all show igb a link at 1.5 s; set down 0.3 s after `cont`, none for the driver's 10 s (`probe2.txt`) | measured |
| https: the leaf's name, SNI, the clock | risks named | a leaf naming `DNS:10.0.2.2` matched; den's SNI for an address and OpenSSL's answer to it raised nothing; the clock (QEMU's RTC, UTC) inside the leaf's day; den at that pin decorates `log` at a terminal (`--no-decorate`) | held, with one row fix |
| `triage nonet` | the escape hatch beside the `no*` words, under `triage` | a plain `nonet`, honoured with or without `triage`: under `triage` the kernel halts in triage's own unsized `t_halt`, which qemu-halt cannot hold, and a plain word is the simpler hatch on metal | changed |
| the waited line's device part | the device's start | the first take counted the `nonet` line's printing (1 ms over a 0 bound); now `net.start` alone is timed | fixed |

## 4. Evidence index

### 4.1 The change

- **kmain_console** brings the network up after the PCI scan (the device, none with `nonet`; the protocols; the
  network clock thread always and the receiving thread with a device, both counted among the threads a run does not
  wait for), takes the address after the disk is mounted (an installed system's own `/etc/pax-net`), and waits,
  bounded, before the identity line: the first lease at most the file's `wait=`, none when the device has no link,
  3 s for the router's or the gateway's echo, then the loopback line and `net: the console waited <w> ms for the
  network (bound <b> ms: device <d>, lease <l>, echo <e>)` (d: 10 ms with no device, 1,000 for virtio-net, 12,000
  for an Intel controller, 0 with `nonet`). Each run waits up to 30 s for a closing connection's FIN, as
  kmain_session's runs do, and the session's `network:` books and the client's counters close the log when there
  is something to count. With no device and no file the console's other lines are what they were
  (`kernel/README.md`, "The console's network").
- **kernel/dhcp**: the static line (`static_asked`, `take_static`, `echo_gateway`; a malformed line is one
  `net: /etc/pax-net: <why>` line and the fixed address), quiet's routine lines (R-px105-3), and `echo_of`, one
  echo loop for the router and the gateway.
- **kernel/net, kernel/gbe**: `link()` (STATUS.LU read at the call; virtio-net always) and `intel()`.
- **kmain_session, kmain_sockets**: the static line and the gateway's echo; with no file, every line as it was.
- **The shipped roots**: `/etc/pax-net` from `user/pax-net` (`dhcp wait=10`, its grammar in comments), in both
  roots (`tools/distribution-root`), held by `tests/distribution`. A fresh install copies it from the live tree;
  an upgrade writes it, as a path the new image ships and the target lacks (px93's plan).
- **The https row's den** (R-px105-2 B): `tools/mkden` takes `PAX_DEN_PIN`; the row's own pin is den's merge of its
  smart-HTTP transport. `user/den.pin` does not move.
- **The metal leg**: `tests/distribution-net` and `user/console/distribution-net.keys`, run by the stick lane;
  `notes/px105/stick-leg.txt`, what a person reads at the metal target's console and what each other answer means.

### 4.2 The rows

`tests/mpx4-console-net` (C0-C9, H1-H5), `tests/mpx5-den`'s remote image on kmain_console (R0-R4),
`tests/distribution`'s `/etc/pax-net`, `tests/ci-plan`'s px105 rows, and `tests/distribution-net`, the stick's leg.
Every row is committed before the first kernel commit; the rows tip is the red commit.

The dev runs (Linux host 1, native, two CPUs and KVM through the light helper; the builds under a block's two lock
names):

| way | red at the rows tip (the base's kernel) | green at the head |
|---|---|---|
| lease (igb) | FAIL C1: no `dhcp: started`, no bound line, the capture empty | PASS C1: `bound 10.0.2.15 …` at +0.04 s, a lease after 0.05 s; C7 waited 1,596 ms of 45,000 |
| virtio | FAIL C1, as lease | PASS C1; C7 waited 56 ms of 34,000 |
| static | FAIL C2: no static line | PASS C2: `net: static 10.0.2.20/24 gateway 10.0.2.2; /etc/resolv.conf: nameserver 10.0.2.3`, the gateway answers; C7 14 ms of 4,000 |
| none, nofile | FAIL C3: no `net:` line at all | PASS C3; C7 0 ms of 0 |
| nolink | FAIL C4 | PASS C4: `net: NO link after 10000 ms (STATUS 80080481)`, no lease wait; C7 10,095 ms of 12,000 |
| nonet | FAIL C9 | (the record) |
| silent | FAIL C5 | PASS C5: `dhcp: no lease after 5 s`; C7 4,994 ms of 6,000 |
| quiet | FAIL C6: no lease | PASS C6: one `bound` line, no routine line, two renewing REQUESTs on the wire |
| https | FAIL H1-H5: the clone never returns, the fixture sees no request | PASS H1-H5: den clones over https at the console, its log is git's, `fsck --full` clean, protocol v2's discovery and fetch, three requests; C7 1,620 ms |

Each green way passed on BIOS and UEFI (https on BIOS in these runs; both in the record). The stick's leg, run against a copy of the last stick (its kernel the
base's console), is red by name: `net-row: no line ^dhcp: started on …`.

### 4.3 Probes

`notes/px105/probe1.txt` (the base's sizes and boot line; QEMU's netdevs as PAX sees them) and `probe2.txt` (igb's
link and `set_link`).

## 5. Done-when

### 5.1 Rulings (recommended and implemented, not decided)

- **R-px105-1, where the stack starts: A.** (A) kmain_console starts kernel/net, the protocols, kernel/dhcp and
  kernel/gbe as kmain_session does, with the console's own bounds; (B) the console images boot kmain_session. A:
  every module was linked into kmain_console already, so A costs the bring-up calls alone (§3's sizes and boot
  times); B would lose, or move into kmain_session, everything the console grew since px28 (triage and the early
  tables, the identity and boot lines, the sound device, `init=`, the `no*` words, the boot medium line,
  /etc/pax-banner, the upgrade entry's mount, the Unix sockets' report), and move every builder and about 50
  suites to another kernel and banner.
- **R-px105-2, the https row's den: B.** (A) move `user/den.pin` to den's merge of its smart-HTTP transport here,
  with mpx5-den's rows moved first for den's new behaviour; (B) the https row builds den at that merge for its own
  image (`tests/mpx4-console-net.d/den-https.pin`, `tools/mkden`'s `PAX_DEN_PIN`), and the pin moves in the lane
  that carries den's push to PAX, which then points the row at the pin; (C) the row skips by name until then. B
  holds the kernel's part, the console's network carrying den's TLS and smart HTTP, without a 100-commit den move
  in a kernel lane.
- **R-px105-3, kernel/dhcp's routine lines under `quiet`: A.** (A) under `quiet` the retransmissions, OFFER, ACK,
  RENEW, REBIND and a renewal's `bound` are not printed; `started`, a lease's first `bound` and its `ip:` line,
  NAK, `expired`, `unbound`, `gave up`, the lease wait's line and the router's still are; (B) every line, as
  before. Every shipped console boots `quiet`, and a renewal at T1 would print into an editor's screen.
- **R-px105-4, a static address: A.** (A) one line, `static <a.b.c.d>/<prefix> [gateway <a.b.c.d>] [dns
  <a.b.c.d>]…`, read by the same reader as `dhcp`; (B) key=value words. A reads as `ip addr` and a route do, and
  a malformed line names what is wrong.
- **R-px105-5, the bound on the console's wait: A.** (A) the first lease at most the file's `wait=` (the shipped
  file: 10 s), none when the device has no link, 3 s for the echo, and one line saying what was waited and the
  bound; (B) kmain_session's waits (30 s, link or not). With no cable, A's prompt comes after the driver's own
  10 s link wait and no more.

### 5.2 Issues

None filed or closed by this lane. For the orchestrator to consider:
- The I225's own interrupt (it is polled, px89), DHCPRELEASE at the halt, and a resolver (wolf-lang#831): the
  console takes a lease but names no host.
- `user/den.pin` to den's smart-HTTP merge, with mpx5-den's rows moved first (px97's note), and then
  `tests/mpx4-console-net.d/den-https.pin` retired for the pin: the lane that carries den's push to PAX.
- The triage sticks' configurations could offer a `nonet` entry for the metal target.

### 5.3 Checklist

- [x] The prediction, committed first (`ffa4b239`), scored above.
- [x] R-px105-1 A: kmain_console starts the stack; its cost measured against the session kernel's at the base.
- [x] A failing or absent NIC never stops the boot, within a stated bound: no device (C3), no link (C4), a server
  that never answers (C5), `nonet` (C9), every way's C7.
- [x] The lease on QEMU's igb at the console, its address on the console (C1), and over virtio-net.
- [ ] px100's git:// row R4 on kmain_console (mpx5-den's remote image): red at the rows tip; green in the record.
- [x] den clones over https from den's own TLS fixture at the console (H1-H5, R-px105-2 B).
- [x] `/etc/pax-net` honoured at the console, a static address (C2), and on the session kernels.
- [x] Quiet's routine lines off the console (C6, R-px105-3).
- [x] The metal check as the stick's leg (`tests/distribution-net`, `notes/px105/stick-leg.txt`), red by name on
  the last stick; green on the next stick, the stick lane's.
- [x] Every row red first at the rows tip, before the first kernel commit.
- [x] README, kernel/README.md, docs/SOURCES.md and CHANGELOG (README-only commits for README).
- [ ] The gauntlet green at the final head, every END line in the PR body (after the rebase onto the named trunk).
- [ ] The plant red by name in its own record.
- [ ] The audit, once.
