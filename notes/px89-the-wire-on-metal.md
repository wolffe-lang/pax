# px89 — the wire on metal: a DHCP client, then the I225-V

Contract: `wolf/sprints/pax/89-the-wire-on-metal/px89-the-wire-on-metal.md` (planning `e8db61a`), under
`sprints/the-lane-rules-1031.md` (every "Added" item). Base pax trunk `b38643a5`, rebased onto `37217ba0` (px98's merge and pax#297's), then onto `411fc9f5` (px93's); branch `px89`. Footprint:
cross-cutting (two new CI jobs, `mpx4-dhcp` and `mpx4-igb`; `tools/ci-tiers.map`; `tests/ci-plan`; kernel/net,
kernel/netd, kernel/ip, kernel/arp, kernel/udp and both network kmains).

PAX had one network device (virtio-net) and one address (10.0.2.15, fixed). px89 gives it a DHCP client in the
kernel (`kernel/dhcp`, RFC 2131: the whole client state machine, renewal, rebinding, expiry, NAK) that a boot uses
when its image's `/etc/pax-net` says `dhcp`, and a driver for Intel's gigabit controllers (`kernel/gbe`) on the
programming model QEMU's 82576 (`-device igb`) and the I225 share, so the DHCP, UDP and TCP rows run over a
second device; and it stages a stick for kasumi whose script takes a lease on the I225-V, records the router's
answer and one TCP connection, and writes the record to the stick.

## Forbidden

No kernel, firmware, driver, hypervisor, DHCP client or server source was read: no Linux `igc`/`igb`/`e1000e`, no
FreeBSD `em`/`igc`, no QEMU device model, no dnsmasq, ISC, busybox or systemd-networkd source. Written from RFC 2131,
2132, 951, 1542 and 950, resolv.conf(5), Intel's public 82576EB (rev 2.63), I210 (333016 rev 3.7) and I225/I226
(596659 rev 2.6) datasheets, PCI Local Bus 3.0 (§6.8, MSI and MSI-X), and black-box runs of QEMU 8.2.2's user-mode
DHCP server, of QEMU's `-device igb` (what its registers read back after PAX's writes), of dnsmasq 2.91, and of
kasumi's CachyOS (read-only `lspci`, `ip`, `/sys/class/net`). Each is in `docs/SOURCES.md` (px89's section); the
measurements are in `notes/px89/blackbox.txt`; the datasheets' digests in `notes/px89/datasheets.sha256`. QEMU's igb
documentation page (not its source) was read once and says nothing about interrupts. No DNS resolver: writing
`/etc/resolv.conf` is the limit (wolf-lang#831).

Hosts: hasu block B only, both lock names, every take under 2 h; nothing in `/tmp` or `/var/folders`, TMPDIR under
`~/lanes/px89/`; no commit signed or made on hasu (every git there passes `-c commit.gpgsign=false`). kasumi was read
once, read-only, under CachyOS (no disk touched, `/mnt/steamlib` not mounted, the rpc-server not touched); the metal
leg is staged, not run. No label, merge, tag or close; no attribution trailers. A lane-only branch, `px89-probe`,
holds three probe commits (register read-backs) that are not part of this PR.

## Inputs, verified

- **Base** `b38643a520eefcd89203c9e1e4188017a23e97bc`, pax trunk at clone time, rebased onto
  `37217ba0832ea36304c0eb517ff2662801b26a46` (px98's merge, then pax#297's), then onto
  `411fc9f524595c4fc1a174487879839259aef317` (px93's merge). The lane's own diff did not move: each file's added and removed lines are the same
  before and after, each commit's patch-id the same. The first rebase's only conflicts were README.md (trunk's
  Programs row kept, px89's network rows taken), CHANGELOG.md (px89's entry above px98's) and docs/SOURCES.md (px87's
  and px96's sections, then px89's); none of px98's other files is one px89 touches. The second had none: no file
  px93 changes is one px89 changes. The two meet in `boot/limine-usb.conf`, the configuration tools/mkwire's stick
  takes: px93 adds an upgrade entry, and mkwire's netpoll twin put a `cmdline: netpoll` line after every
  `module_path` line, that entry's too (`2785deaa` keeps the word to the first entry). The stick at that commit (w4,
  `notes/px89/logs/w4.rows`) showed the twin had not been polled since the first rebase: px87's `cmdline: quiet`
  (pax#246) gave the first entry a command line of its own, and a second `cmdline:` line in an entry does not reach
  the kernel, so Q0 was red on both netpoll boots (`MSI-X vector 83`) and every other row green. `d8a51e49` puts the
  word on the entry's own line (`cmdline: quiet netpoll`), or makes the line when there is none, and refuses a first
  entry with more than one; the stick at that commit qualified again (w5, `notes/px89/logs/w5.rows`). The staged
  stick (`f68505c6`, the MSI-X one the metal leg uses) predates both: its first entry had no command line, and w3's
  twin was polled. A stick built at the head carries px93's entry, which mounts nothing: the stick's
  `/pax/install-targets` names no disk as shipped. `notes/px89/rebase-map.txt` pairs each commit with its twins:
  this note cites the last, and every run in its tables ran at the map's first column (the commit before the
  rebases) but w4's, w5's and the CI mirror's, which name their own. Branch `px89` in `~/lanes/px89/pax`; on hasu a clone at
  `/home/mfwolffe/lanes/px89/pax`, a worktree per tested commit (`wt-<sha8>`), git behind a lane-local lock.
- **Toolchain** wolf 0.2.35 by `kernel/wolf.pin` (`tools/fetch-wolf`'s digest check every build), Limine 12.9.1.
- **Image** `localhost/px89-dhcp:1`: px88's `localhost/px88-ubuntu:1` (px75's QEMU 8.2.2, OVMF, clang, lld 18,
  gcc; musl-tools, strace) plus Ubuntu 24.04's `dnsmasq-base` 2.91, `iproute2` and `tcpdump`
  (`notes/px89/hasu/Containerfile`); the suites' Linux sides that run throwaway containers reach hasu's podman
  through a lane-owned rootless service (`notes/px89/hasu/podman-service.sh`, `podman-remote`). CI's two jobs get dnsmasq-base and
  iproute2 from the runner's apt and `modprobe tun`.
- **Hosts** hasu block B (CPUs 6-11, `/dev/kvm`), `notes/px89/hasu/launch.sh` (both lock names, one `flock -w
  21600` each, detached, pid, log and exit marker). dnsmasq runs on a tap in the container's own network namespace
  (`/dev/net/tun`, CAP_NET_ADMIN: nothing of hasu's network is touched).
- **kasumi** (read once, 2026-11-03 23:05Z): the cabled port is the I225-V, PCI `70:00.0`, `8086:15f3` rev 03,
  BAR0 1 MiB at 0xa4900000 (32-bit), BAR3 16 KiB, `enp112s0`, MAC `7c:10:c9:3f:cb:9c`, 1000 Mb/s, DHCP from
  `192.168.0.1` on `192.168.0.0/24`. The other port is an Aquantia AQC113CS (`6f:00.0`, `1d6a:94c0`), no cable.
- **The datasheets**: the I225/I226 public datasheet has no register map, no descriptor layout, no reset, PHY or
  interrupt programming (Intel's I225 software manual is not public and was not read). The 82576 and I210
  datasheets agree on every register, bit and descriptor the ring driver uses. This decided R-px89-1.

Commits (the prediction first; each phase's rows red before its code):

- `fddfa54d` notes/px89/prediction.txt, before any change; `a64b1b99` the black boxes and the datasheets' digests;
  `eb4d4f70` notes/px89/hasu: the container, the launcher, the probes
- Phase A rows: `a69926e7` user/net/netstate.c; `4dd9ee41` tools/pcap-dhcp; `c0127021` tools/dhcp-wire;
  `388ed38a` tests/mpx4-dhcp (D0-D10); `95b85ff4` CI's mpx4-dhcp job; `08e7c2db` notes/px89/red: D1-D9 red at base
- Phase A code: `60059340` boot/net.S; `704e8314` kernel/udp; `f78e4682` kernel/ip; `2ab17c2a` kernel/arp;
  `86c86f7f` kernel/dhcp; `508154c8` kernel/netd; `aee0aee0` kmain_sockets; `40730537` kmain_session; `b23c9144`,
  `0d7caee5`, `7f061f48` kernel/dhcp: two reserved words, a trapping shift; `30442f5a` kernel/dhcp: the lease file
- Phase B rows: `0d832222` tools/pcap-net --dhcp; `d72e245f` tests/mpx4-dhcp per NIC; `242b4897`, `12d04376`
  tests/mpx4-udp and tests/mpx4-tcp `--nic igb`; `c5d5806a` tests/mpx4-igb (G1-G4); `bc119edd` CI's mpx4-igb job;
  `6c7fc4e3` notes/px89/red: G1-G4 red before kernel/gbe
- Phase B code: `cbd40129` boot/net.S; `7240dd9c` kernel/gbe; `a2f77968` kernel/net; `65f7a006` kernel/netd;
  `4d2c9af1` kernel/net: the registers read back; `a141470c` kernel/gbe: the 82576's PHY restart; `ee327936`,
  `49103a6e`, `386a3228` kernel/gbe, kernel/net: the interrupt (IVAR/EIMS, then MSI, then MSI-X); `0ebe35bf`,
  `e71a5afa` the kmains' loopback line counts its own frames; `3ba2a213` kmain_session attaches the USB disks
- The metal leg: `0ac9a661` user/net/tcpprobe.c; `d6245d8a`, `75c85ddc` user/wire.sh; `5c218350`, `b8585bee`,
  `1fde2d17` tools/mkwire (the stick, its netpoll twin, mkdir); `8a528bd0` tools/ci-tiers.map
- Docs: `7ca67e6b`, `90fa7e45` docs/SOURCES.md; `75bf3c36`, `9132f88b`, `e201f025` kernel/README.md; `5498d651`, `acb6c6ca`
  CHANGELOG; `fba06cb7`, `e2f4ab70` README (README-only commits)
- Harness fixes on the way: `b8fc225b`, `abef5f7c`, `033f430a`, `3ed74f49`, `6f46dab4`, `026438ff`, `c3547e5c`,
  `d21c9218`, `0512ae48`; notes: `841da07c`, `836acd04`, `ad1d562e`, `9fc430ee`, `d7780088`, `514a60c4`,
  `2f35dd75`, `83cca6c8`, and this note

## Prediction, scored

`notes/px89/prediction.txt` (`fddfa54d`, 2026-11-03 23:25Z, pushed before the first change):

| predicted | measured |
|---|---|
| D0-D9 red by name at the base | **right**: D1-D9 red by name (`no 'dhcp: started on …' line`, `RENEW at 'none'`, …) at `95b85ff4` (`notes/px89/red/mpx4-dhcp-at-ba7fc305.log`); D0 (the build) and D10 (the halt) were green there, not red as predicted: the base kernel builds and halts, it only ignores `/etc/pax-net` |
| G rows red at base: `net: no virtio network device …` | **right**: G1-G4 red by name at `bc119edd` (`notes/px89/red/mpx4-igb-at-9cb8e014.log`) |
| DISCOVER→ACK against QEMU's server in under 0.1 s of guest time | **right**: bound at +0.03 s (virtio), +0.04 s (igb) |
| retransmission at 4, 8, 16, 32 s ±1 s, the xid kept, secs counting up | **right**: 4.99, 8.27, 16.52 s apart, one xid (D4; dnsmasq started 20 s late) |
| renew at T1 unicast, rebind at T2 broadcast, expiry, NAK back to INIT | **right**: RENEW at lease+10.00 s; REBIND +20.00 after an unanswered RENEW; expiry at lease+120 s then a new lease; NAK → new xid, a new address and its server's DNS (D5-D8) |
| no existing row moves | **right** for the rows run (the gauntlet, below) — and one row needed a kernel change to stay so: the loopback line counted every frame sent since boot, which a lease's frames made non-zero; it now counts its own pings' frames (`0ebe35bf`, `e71a5afa`: the same bytes on every fixed-address boot) |
| igb: INTx on the firmware's line (10 or 11) | **wrong**: QEMU's igb raises no INTx and sends no MSI for an unmasked cause (PCI status bit 3 never set; EICR bit 0 set and EIMS bit 0 set; IMS reads 0 whatever is written). MSI-X vector 0 works; the 82576 now interrupts by MSI-X (R-px89-6) |
| no PHY register access | **wrong for the 82576**: QEMU's igb leaves its PHY's auto-negotiation idle after CTRL.RST (no link for 10 s); PCTRL's restart through MDIC brings it up in 0.5 s. The I225 still touches no PHY register |
| igb throughput within a factor of 2 of virtio-net's (U8, ~20,000 a second) | **right**: 22,886 datagrams a second in, 22,773 out (peer way); polled, 100 a second (one a tick) |
| the dnsmasq rows: 30, 40, 150, 40, 60 s | about right in guest time: the lease at +3 s (dnsmasq's ICMP probe first), RENEW at +13, REBIND at +23, the lease run out at +123 and a new one at +130.6, the NAK's new lease at +16.1, the backoff's lease at +32.8 (dnsmasq started 20 s late) |
| kernel/dhcp ~900 lines, kernel/gbe ~650 | kernel/dhcp 1,274 lines, kernel/gbe 840 |
| the I225 polled (its line the firmware's 255) | **changed by design**: every I225 is polled now, whatever its line (R-px89-6); the stick's `net:` line will name its line |

## Evidence index

### Rulings (recommended and implemented, not decided)

- **R-px89-1, the shared ring model.** (A) one driver on the 82576/I210 model for QEMU's 82576 and the I225, the
  I225-only paths named in the module (the ids, the reset's wait, the link with no PHY register touched, the
  speed's raw bits, the polled path), confirmed on metal by its own read-back (`net: regs …`); (B) wait for the
  I225's register manual. **A**: the public I225 datasheet names the same registers (RAL0/RAH0 from the NVM, CTRL,
  RCTL, the legacy and advanced transmit descriptors) and the 82576 and I210 agree word for word; what cannot be
  proven here is the stick's to show.
- **R-px89-2, where the client runs.** (A) in the kernel, a thread of its own, configured by `/etc/pax-net`; (B) a
  program. **A**: PAX has no interface-configuration ABI (no SIOCSIFADDR, no netlink) a program could use, and the
  lease must be held before init's list runs.
- **R-px89-3, the TCP target.** The contract says "a host the maintainer names". The stick connects to every
  `<ip> <port>` line of its ESP's `/pax/wire-target` (any OS can write it before the boot) and, with none, to the
  router's port 80. **Recommendation:** the maintainer names a host on the LAN with an open port (a machine's
  sshd on 22, say) and writes the line, or accepts the router's 80.
- **R-px89-4, how a boot asks for DHCP.** (A) `/etc/pax-net` in the image (`dhcp`, `dhcp wait=N`); (B) the kernel
  command line. **A**: an image's file is the image's configuration, as `/etc/fstab` is; every existing image has
  no such file and keeps the fixed address.
- **R-px89-5, resolv.conf on a lost lease.** (A) emptied (no `nameserver` line) at NAK or expiry, rewritten at the
  next ACK; (B) left. **A**: a server the network no longer gives should not be asked.
- **R-px89-7, the record's rig (ruled B).** mpx4-lobo's Linux side runs its container on the engine's `--network
  host`, hasu's own namespace, and connects to it at 127.0.0.1; the gauntlet's step had a namespace of its own, so
  every Linux leg was refused (red at base `b38643a5` as at the head, green with the step in hasu's namespace:
  `ctr2.sh HOSTNET=1`, mpx4-lobo's step alone, no tap). The scripts' copies are committed before the record.
- **R-px89-8, kernel-as (ruled A).** CI-only for this PR, a named SKIP line in the local record; the full-matrix
  run must show it green before the merge.
- **R-px89-9, the record's legs (ruled A).** `mpx4-dhcp` and `mpx4-igb` run on native BIOS and release UEFI in the
  local record, through the committed gauntlet's own arguments; earlier records ran all four legs green (at the
  commits before the rebase: g3 and g4, `notes/px89/rebase-map.txt`).
- **R-px89-10, mpx4-ready's stall guard (for a later lane).** The user way's guard stops a boot whose serial log has
  not grown for 4 x 240 s; its epoll server prints nothing until its 10,000-connection soak ends. On a loaded host the
  soak runs at 3 connections a second (g3: 34,842 frames over 968.6 s, still flowing when stopped) against 45 when it
  is quiet, so the guard cannot tell a slow host from a hang. Recommendation: count the capture's growth as life too,
  or have the server print a line every 1,000 connections.
- **R-px89-11, mpx4-ready's capped reference (ruled A, its own PR: pax#297, merged).** g4's mpx4-ready red was the
  Linux reference, not PAX: the reference's pipe held 8192 bytes because the host user's pipe pages were past
  `pipe-user-pages-soft` (pipe(7)), witnessed in the lane container as a private uid; PAX's 65536 was right. pax#297
  makes such a reference refuse itself by name (T0r, T0) instead of reporting a PAX difference.
- **R-px89-6, the 82576's interrupt.** (A) MSI-X vector 0 (GPIE.Multiple_MSIX, IVAR0, the table in BAR3) to
  kernel/net's vector 83, the last of kernel/idt's four MSI gates; (B) poll it as the I225 is polled. **A**: it is
  the only interrupt QEMU's igb sends; polled costs a tick a round trip (100 a second). The I225 stays polled (one
  interrupt path fewer to confirm on metal); its MSI-X is a later lane's once the stick has spoken.

### CI's red at D5 (pax#298's full-matrix run 41967637438)

D5 failed on native BIOS in `mpx4-dhcp` (virtio) and in `mpx4-igb` (G1's igb boots) with
`dnsmasq logged  requests;`, an empty count, while every other row of the same boots passed (D1's capture of the
renew boot: `REQUEST (renewing)=2 server ACK=3`). CI's dnsmasq is the lane's, `dnsmasq-base 2.91-0ubuntu0.24.04.2` (Ubuntu
24.04), so the version was not the difference; the user was. CI runs the suite as its runner, not root, and
tools/dhcp-wire starts dnsmasq through `sudo -n`. dnsmasq run as root makes its `--log-facility` file mode 640,
root:root, which the runner cannot read, and the row's `grep -c … 2>/dev/null` printed nothing. The same file
stopped the jobs' artifact uploads (`EACCES … dnsmasq-1.log`). The lane's containers run every suite as root, so
no local record met it. Witnessed on hasu block B (`notes/px89/logs/dnslog1.log`, `dnslog2.log`): the log dnsmasq
makes as root is 640 root:root and uid 1001's read is `Permission denied`; a log the caller makes first keeps its
owner and its mode 644, and dnsmasq appends to it.

- `1b9b40d5`, the row, first: D5 finds each renewing REQUEST of the capture in dnsmasq's log by its xid (dnsmasq
  writes it in decimal: `273854788` is the capture's `0x1052b144`), requested and ACKed, beside the row's earlier
  counts; a log the suite cannot read fails by its mode and owner. A lifted copy of the clause on g6's renew files
  passed, and failed on two altered copies of the log, one renewal's lines gone and its ACK made a NAK
  (`notes/px89/logs/d5-lifted.txt`).
- `a8ab4ae1`, the fix: dhcp-wire makes each log, mode 644, as the caller before dnsmasq opens it, and says in
  `account.txt` whether the caller can read it.
- The CI mirror (`notes/px89/hasu/Containerfile.ci`, `ci-mirror-run.sh`, `probes/ci-mirror.sh`;
  `notes/px89/logs/cimirror1.log`): the lane image with sudo and a user `runner`, uid 1001, with password-less sudo,
  as GitHub's runner has; the renew way's native BIOS boot run as runner, as CI runs it, one image for the three
  commits (only tests/ and tools/ differ). At the rebased head before the row (`0b5cb6b0`) D5 red in CI's own
  words; at the row (`1b9b40d5`) red by name, `cannot be read by uid 1001: 640 root:root`; at the fix (`a8ab4ae1`)
  green, `dnsmasq's log holds the capture's 2 renewing REQUESTs by xid, each ACKed`, every file of the wire
  directory readable by runner.

### The client (kernel/dhcp)

The states INIT, SELECTING, REQUESTING, BOUND, RENEWING, REBINDING; 300-byte BOOTP messages with 53, 61 (`01` +
the MAC), 50 and 54 in SELECTING's REQUEST, 55 asking for 1, 3, 6, 51, 58, 59, and 255; the BROADCAST flag until
bound; retransmission 4 s doubled to 64 s ±1 s with the xid kept and `secs` counting; T1 (default 0.5 of the lease)
RENEW unicast to the server, T2 (0.875) REBIND broadcast, the retransmission there half the time left, never under
60 s; NAK or the lease's end back to INIT with the address, the route and the servers withdrawn (kernel/ip's
`configure` to 0.0.0.0). Options 3 and 51 honoured, 6 written to `/etc/resolv.conf` (three servers at most), 58
and 59 when given. Every change is a `dhcp:` line stamped from the client's start. `/var/lib/dhcp/pax.lease` holds
the lease as a program reads it, and whether the router answered the kernel's echo.

### The rows (hasu block B; each run's verdict lines in `notes/px89/logs/<run>.rows`, the igb boots' `net:` and probe lines in `notes/px89/logs/igb-boots.txt`)

| run | commit | what it showed |
|---|---|---|
| red1 | `95b85ff4` | D1-D9 red by name on the base kernel |
| red2 | `bc119edd` | G1-G4 red by name before kernel/gbe |
| d2 | `fba06cb7` | **mpx4-dhcp green on virtio**, native BIOS: 7 boots, D0-D10 |
| i1 | `6f46dab4` | igb: DISCOVERs out, no OFFER in: no link (STATUS.LU 0 for 10 s) |
| i2 | `a141470c` | the PHY restart: link in 1.5 s; still no frame taken (0 interrupts) |
| i3 | `a141470c` | igb **polled**: every U0-U9 row of mpx4-udp's user way, 100 datagrams a second |
| p3, p4 | `f4eef2ca`, `daa2643b` (px89-probe) | the ring receives (RDH 4), EICR bit 0 set and unmasked, PCI Interrupt Status never set; IMS never holds a bit |
| i4, i5 | `ee327936`, `9fc430ee` (`49103a6e`'s code) | IVAR/EIMS by INTx, then MSI: 0 interrupts |
| p5 | `9fbd3ccf` (px89-probe) | six GPIE/EIMS/EIAC/EIAM/ICS/EICS variants, read back; run with IF clear, so silent on delivery (`notes/px89/blackbox.txt`) |
| i6 | `0512ae48` | **MSI-X: D1-D3, D10 green over igb** |
| i8 | `0512ae48` | mpx4-igb: G1, G2, G4 green (U8 over igb 22,886 datagrams a second); G3 red only at T1 of the user way (`4 frames on the wire`: the lease's) |
| i9 | `e71a5afa` | **mpx4-tcp over igb green**, both ways, after the loopback line's fix (T8: 16 MiB out of PAX at 9.3 MB/s, in at 15.1 MB/s) |
| w2 | `e71a5afa` | the stick: Q0 green (MSI-X), Q1-Q4 red: the root archive has no `/tmp` (the record could not be made) and kmain_session attached no USB disk (no `/dev/sd?` for the stick) |
| w3 | `1fde2d17` | **the stick qualified**: Q0-Q5 PASS on all four boots (BIOS, UEFI, each MSI-X and netpoll), after `3ba2a213` (kmain_session attaches USB disks), `75c85ddc` and `1fde2d17` (`mkdir -p /tmp`) |
| w4 | `b6200d20` | the stick after the second rebase: the MSI-X stick's Q0-Q5 green on BIOS and UEFI, the netpoll twin red at Q0 alone (`MSI-X vector 83`: its word on a second `cmdline:` line after px87's `quiet`) |
| w5 | `d8a51e49` | **the stick qualified again**: Q0-Q5 PASS on all four boots, the twin's word on the entry's own command line |
| eng | — | the container engine inside a lane container (`notes/px89/hasu/eng-test.sh`): podman 5.8.9 client and server, one throwaway container: the gauntlet's Linux sides |

### The metal leg (staged, not run)

`tools/mkwire root` and `tools/mkwire stick` at `1fde2d17` on hasu (`notes/px89/hasu/wire-build.sh`), qualified by
`notes/px89/hasu/wire-qualify.sh` (`notes/px89/logs/w3.rows`): a copy of the image as USB storage on qemu-xhci,
QEMU's 82576 on its user network, a server on the host for the TCP row, a SATA disk and an NVMe disk of 64 MiB of
random bytes beside it; four boots (BIOS and UEFI; the stick, and its twin `pax-wire-netpoll.img` with `netpoll`
on its command line so the controller is polled as the I225 will be). Every boot: Q0 the controller's line, Q1 the lease and
resolv.conf in the record, Q2 the router's answer to the kernel's echo, Q3 tcpprobe's connection and the server's
line, Q4 the record on the image afterwards (`/pax/logs/wire-1.txt`, 19 lines), Q5 the other two disks
byte-identical. The stick: `~/pax-smoke/pax-wire-f68505c6.img` on nomad, 241,172,480 bytes, sha256
`ba06df59…358c7` (read twice on hasu, twice on nomad), with `~/pax-smoke/README-wire-f68505c6.txt` (a copy in
`notes/px89/stick-README.txt`).

The I225-V on kasumi: PCI `70:00.0`, `8086:15f3` rev 03, `enp112s0`, MAC `7c:10:c9:3f:cb:9c`, the port cabled
today (CachyOS's `lspci -nn` and `/sys/class/net`, read once; `notes/px89/blackbox.txt` §3). The stick's own
`net: Intel I225/I226 8086:15f3 at 70:00.0` line will confirm it from PAX's side.

### The plant and the gauntlet

Both records are in the PR body (each at the head they name: this note is part of the gauntlet's head, so it cannot
hold them). The gauntlet (`notes/px89/hasu/gauntlet.sh` under planning's `gauntlet-record.sh`, hasu block B, each
step its own lock take): the plan job's self-tests; `mpx4-dhcp` and `mpx4-igb` on native BIOS and release UEFI
(R-px89-9: BIOS and UEFI as item 5 asks; the full-matrix label and tier all cover the other legs); `mpx4-unix`,
`mpx4-session`, `mpx4-net`, `mpx4-udp`, `mpx4-tcp`, `mpx4-ready`, `mpx4-lobo` (its step in hasu's own network
namespace, where its Linux side's container listens: R-px89-7), `mpx5-jobs` and `mpx3-shell` on the merge leg
(native BIOS). The gauntlet's containers run the suites as root; CI's runner is not root, and
`notes/px89/hasu/probes/ci-mirror-suites.sh` runs `mpx4-dhcp` and `mpx4-igb` whole as runner on the leg CI ran red
(its take is in the PR body). `kernel-as` is CI-only, a named `SKIP` line in the record (R-px89-8): it builds a second wolf from
source with cargo, which the lane image does not have; the full-matrix run holds it. Those are the readers of every kernel path changed but 20 of kmain_sockets'
(mpx3-boreutils, -console, -screen, -threads, -tree, -maps; mpx5-forks, -accounts, -lope, -pelt, -aspen, -den,
-scent, -bore, -lupin, -wolf, -clef, -yew, -screen; mpx6-games: their kernel is the same but for px89's `dhcp`
branch, never taken without `/etc/pax-net`, and the loopback line's count), which the cross-cutting `full-matrix`
run covers with the rest of ci-plan's 64 (`tools/ci-tiers.map` and `tests/ci-plan` changed, so the plan picks
every suite). The plant, `px89-plant-t1`: one hunk in kernel/dhcp, BOUND renews at the lease's end instead of at
T1; the rows it names: D5, D6, D7, D8.

## The maintainer's session

The steps are `~/pax-smoke/README-wire-f68505c6.txt` (`notes/px89/stick-README.txt`): write the stick
(balenaEtcher; its digest checked first), optionally name the TCP host in its ESP's `pax/wire-target` (R-px89-3),
the cable in the I225-V's port, F8, the stick's UEFI entry, the default Limine entry; a video from the menu, photos
of the `net:` and `dhcp:` lines and of the record; the line `== written to /pax/logs/wire-1.txt on /dev/sd?`; then
the power button (the stick has no reboot program); the record copied from the stick's ESP on nomad. What can go
wrong and what to photograph for each is in the README. The stick writes only itself.

## Done-when

- [x] Item 1: the DHCP client in the kernel (DISCOVER/OFFER/REQUEST/ACK, retransmission with backoff, T1 renew,
  T2 rebind, expiry, NAK; address, mask and default route from the lease; option 6 to `/etc/resolv.conf`; 3 and 51
  honoured), over virtio-net and QEMU's slirp first (D1-D3, D10).
- [x] Item 2: dnsmasq on a tap, a 2-minute lease with T1 10 s and T2 20 s: backoff, renew, rebind, expiry and NAK
  (D4-D8), each row reading PAX's own state (its `dhcp:` lines, `ip:` line, and `/etc/resolv.conf` read back by a
  program, `netstate`), every client frame rebuilt byte for byte (`tools/pcap-dhcp`).
- [x] Item 3: kmain_sockets and kmain_session bring the interface up by DHCP when the image's `/etc/pax-net` says so
  (D9: init's list runs over the lease); the fixed address stays the default; no existing row changes (the
  gauntlet, in the PR body).
- [x] Item 4 (R-px89-1): kernel/gbe from the datasheets, one ring/RX/TX path for QEMU's 82576 and the I225, the
  I225-only paths named; the 82576 and I210 share the ring layout, the I225's public datasheet has no register map.
- [x] Item 5: PAX on `-device igb` takes its lease by DHCP and passes the existing UDP and TCP rows (mpx4-igb
  G1-G4, BIOS and UEFI: the gauntlet's `mpx4-igb` and `mpx4-igb:release-uefi`).
- [x] Item 6: the stick for kasumi built, qualified under QEMU (BIOS and UEFI, MSI-X and polled, no other disk
  written) and staged with the session's exact steps (below); the I225-V identified (PCI `70:00.0`, `8086:15f3`
  rev 03, the cabled port, `enp112s0`). Not run: the maintainer's session.
- [x] Item 7: each phase's rows red by name before its code (`notes/px89/red/`).
- [x] Item 8: the plant (the PR body).
- [x] Item 9: this note; the PR and the audit are the hand-back's.
- README read against the change: the Network row and the network suites' row moved (`fba06cb7`, `e2f4ab70`,
  README-only commits).

**Issues** (none filed or closed by this lane). Owed, for the orchestrator to file: the I225's interrupt (MSI-X,
once the stick has shown the ring works on metal); DHCPDECLINE after an ARP probe, DHCPRELEASE and INIT-REBOOT; a
resolver (wolf-lang#831, exists); polled throughput (one round trip a tick: kernel/netd could poll faster while
frames flow).
