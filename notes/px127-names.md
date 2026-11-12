# px127 — names from an on-box build: recvmsg on a datagram socket

On the installed machine a wolf program built there with `wolf build` failed
`net.connect("github.com:443")` with `io`, while an IP address connected and the image's own den resolved the
same name in the same session, with the same `/etc/resolv.conf`.

## 1. The cause (measured before this file: `notes/px127/probes.txt`)

The two programs carry different C libraries, and so different resolvers. den and burrow are built off the box
and linked static against glibc; their resolver reads its answers with `recvfrom`, which PAX has served since
px104. A program `wolf build` makes on the box is linked static against the dev image's musl
(`/usr/lib/wolf-musl/libc.a`; the default `ld.lld` link and `WOLF_LD=cc` take the same archive). Its resolver
sends the A and AAAA questions with `sendto` and reads the answers with `recvmsg` (47), and PAX answered
`recvmsg` -ENOSYS. So the questions left, the DNS server answered both, and nothing read the answers: the resolver
asked once more after 2.5 s, gave up after 5 s, and std.net's `connect` answered `io`. The link line, the link
inputs and `nsswitch.conf` play no part.

**What a person can do today, with no new image:** put the name in `/etc/hosts` (as root). Both resolvers read
that file before they ask DNS, and for a name it holds neither makes a socket (measured on Linux and on PAX:
probes 1 and 2). It pins one address, so the line needs updating if that address stops answering; den and ssh
then use the same address. A program can also dial an address instead of a name.

## 2. Prediction

Written before the first change (the probes above ran first; they are the measurement this prediction rests on).

- **The fix.** kernel/socket serves `recvmsg(fd, msg, flags)` on an AF_INET datagram socket (recvmsg(2), udp(7)):
  the oldest datagram scattered over `msg_iov`, the sender written to `msg_name` (cut to `msg_namelen`, which is
  set to 16), `msg_controllen` set to 0, `msg_flags` MSG_TRUNC when the datagram was longer than the iovecs; the
  flags `recvfrom` takes (MSG_DONTWAIT, MSG_PEEK, MSG_TRUNC, MSG_ERRQUEUE's -EAGAIN), and its waits (O_NONBLOCK's
  -EAGAIN, a wait, SO_RCVTIMEO). A stream socket's `recvmsg` is refused by name; `sendmsg` stays unserved
  (nothing measured calls it). kernel/user dispatches 47.
- **N1** (tests/mpx4-console-push, the names way): `dgramopts` gains recvmsg's cases. At the base it is red by name:
  every recvmsg line reads `ENOSYS` on PAX and answers on Linux. Green after the fix, byte-identical to Linux.
- **N3** (new, the same way): `gai` built against musl (Ubuntu's musl-gcc, static). At the base github.com and
  nosuch.test both answer `EAI_AGAIN` after about 5 s each, while hosts.test (from `/etc/hosts`) and the literal
  hold; after the fix github.com is the fixture's 10.0.2.2, nosuch.test `EAI_NONAME`, as glibc's `gai` (N2)
  answers.
- **The on-box rows** (tests/distribution-net, the dev image, with the router as the nameserver and a DNS fixture
  behind it): a program built on the box with `wolf build`:
  - **N2** builds;
  - **N3** dials a name the fixture serves and connects, a name nobody has answers `io`, and an address connects.
    Red with the image 65d972ac's kernel (the name answers `io`), green with the fix's kernel and the same root
    archive;
  - **N4** dials a name only `/etc/hosts` holds and connects, the fixture asked nothing for it. Green at the base
    too: it is the workaround's guard, not a red-first row.
- **Size.** kmain_console grows by under 8 KiB of ELF on each tier.
- **No existing row moves**: mpx4-udp, mpx4-tcp, mpx4-dhcp, mpx4-console-net, mpx4-console-push's N1 cases from
  px104 and N2, its https and ssh ways, mpx5-den.
- **Wall time.** The on-box probe's two names answer in well under a second each after the fix (5 s each before).

Footprint: cross-cutting (`kernel/socket`, `kernel/udp`, `kernel/user`; `.github/workflows/ci.yml` installs
musl-tools for mpx4-console-push; `tools/ci-tiers.map`).

## 3. Forbidden, and what was read

- **Clean room.** No kernel's, C library's or resolver's source. recvmsg(2), udp(7), socket(7) and hosts(5) as
  the man-pages project publishes them; what Linux answers measured black box with `user/net/dgramopts.c`'s new
  rows; what musl's resolver asks measured black box by strace of programs on Linux (`notes/px127/probes.txt`).
  The org's own wolf-std (`net/net.lu`'s header on names) and PAX's own kernel were read. `docs/SOURCES.md`
  (px127) lists them.
- **Hosts.** One Linux host with KVM (Intel Core i7-12700KF), every build and boot in an Ubuntu 24.04 container
  (QEMU 8.2.2, OVMF, clang, lld 18, musl-tools 1.2.4, strace), rootless, with no network for every boot; the
  native kernel builds, the images and the boots as light jobs (two CPUs), the release kernel on a block of six.
  A Mac for git only. The installed machine was not touched.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 4. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `48ea81ba` (px120's hot-plug merge); developed on `309036ec` and rebased before the first kernel commit | `git rebase`, nothing in conflict |
| the image | 65d972ac's dev root archive (`dev.cpio`, 639,621,564 bytes, sha256 `5a8cc4d4…6090c`) and its kernel (`kmain_console.elf`, 2,835,296 bytes, `dce9a270…4ec1`), copied from the image's build, each read twice; `tools/mkimage` with `boot/limine-initramfs-quiet.conf` gives `ac0dfe60…2376`, the digest the image's build recorded for its dev ISO | sha256, twice |
| the dev compiler | the image's `/usr/bin/wolf`: `wolf 0.2.39 (wolfgang, pin 3fc86f7)`, its `ld.lld` 18.1.8 and `/usr/lib/wolf-musl/{crt1.o,crti.o,crtn.o,libc.a,libunwind.a}` | `wolf --version` on the box and on Linux |
| the kernel's compiler | `kernel/wolf.pin`'s wolf 0.2.35, archive `4cc4045b…ad1a` | `tools/fetch-wolf` by digest |
| musl for N3 | Ubuntu 24.04's musl-tools 1.2.4-2 (`musl-gcc`) | `dpkg -l` |

## 5. Prediction, scored

| predicted | measured | score |
|---|---|---|
| the fix as written in §2 | as written; an iovec array or header the caller cannot reach -EFAULT, more than 1024 iovecs -EMSGSIZE, a negative `msg_namelen` -EINVAL with the datagram kept, a null `msg_name` leaving `msg_namelen` as it was, all as Linux answered the witness | right |
| N1 red at the base by name, green after | red at the rows tip: every recvmsg line `-ENOSYS` (`FAIL N1 … recvmsg -ENOSYS`); green at the head: 77 lines byte-identical to Linux | right |
| N3: EAI_AGAIN for github.com and nosuch.test at the base; hosts.test and the literal hold; glibc's answers after | exactly that at the rows tip; at the head the four answers of N2 | right |
| on-box N2 builds, N3 red at the base, N4 green at the base | at the rows tip with the image 65d972ac's own kernel and with the rows tip's native kernel: N2 PASS, N3 `github.com:PORT: io`, N4 PASS, both firmwares; at the head all three PASS, both firmwares | right |
| under 8 KiB more ELF a tier | native 3,745,584 → 3,751,648 bytes, +6,064; the release tier in the PR's records | right (native) |
| no existing row moves | measured here: the names way's N2 and its px104 N1 cases, distribution-net's N1 on both firmwares; mpx4-udp, mpx4-tcp, mpx4-dhcp, mpx4-console-net, the push suite's https and ssh ways and mpx5-den are the full records' | held where measured |
| names in well under a second each after the fix | nosuch.test fails at once; github.com's connection reached the listener 0.99 s after the fixture's answer (both firmwares), and musl's `gai` asked its next name 0.47 s after the answer; before the fix each name took 5.0 s | wrong in part: about one second, not well under; the half-second steps were not chased |
| (not predicted) a longer answer | probe 3: an answer too long for one datagram sends musl over TCP, with TCP_FASTOPEN_CONNECT, `sendmsg` and `recvmsg` on a stream socket, none served | R-px127-3 |

## 6. Evidence index

Every take ran on the Linux host above; each record's path and sha256 is in the PR's body with its `END` lines.

| take | what | at |
|---|---|---|
| probes 1-3 | `notes/px127/probes.txt`: the image's compiler on Linux under strace; the image under QEMU (its own ISO and the same files without `quiet`, the same answers but for the kernel's `syscall 47: -ENOSYS` line); a truncated answer | `309036ec`'s kernel, the image's |
| red | the rows tip: kernel-native, quick-images, names-native (`FAIL N1`, `FAIL N3`), dist-image, distribution-net-dev (`FAIL N3` on both firmwares) | `5aaebf51` |
| green | ci-plan, census, the head's native kernel, the names way, the dev ISO with the head's kernel and 65d972ac's root, distribution-net-dev: every row PASS | the final head |
| release | the head's release kernel, its dev ISO, distribution-net-dev and the names way | the head |
| plant | `px127-plant-trunc-flag`: one hunk, recvmsg never reports MSG_TRUNC; `FAIL N1` by name, N3 green | the final head |

The quick checks build the names way's image from the tree's own `user/net` and copy the console's shell and
utilities from the 65d972ac image (`tests/mpx4-console-push`'s own build makes them from their pins, and the names
way's rows read none of them); the suite's full run at the head is the full records'.

## 7. Done-when

### 7.1 Rulings

- **R-px127-1, where the fix belongs: (a), recommended and done.** (a) The kernel serves `recvmsg` on a datagram
  socket. (b) On-box builds link glibc instead: the image has no glibc archive, its compiler and runtime are musl
  programs, and a second C library would ship beside the first. (c) wolf resolves names itself: std's own header
  rules it out (std neither resolves nor answers differently from `connect`), and a DNS client in std would
  answer differently from the C library's. (d) Ship `/etc/hosts` entries: only names known in advance. The
  contract expected an image or link-line fix; the measurement put it in the kernel, so the footprint is
  cross-cutting.
- **R-px127-2, recvmsg's reach: (a), recommended and done.** (a) AF_INET datagram sockets, what the resolver
  asks; a stream socket's refused by name (-EOPNOTSUPP), an AF_UNIX socket's by the existing name. (b) Stream
  sockets too, through `tcp.recv` per iovec: no caller measured but probe 3's. (c) `sendmsg` with it. pax#356
  asks for `sendmsg` and `recvmsg` with SCM_RIGHTS on Unix sockets (a terminal multiplexer's readiness probe):
  this lane serves its AF_INET datagram half of `recvmsg` only; the Unix-socket half and `sendmsg` stay open there.
- **R-px127-3, a truncated answer: a lane of its own, recommended.** Probe 3: musl asks again over TCP with
  TCP_FASTOPEN_CONNECT, `sendmsg` with and without a destination, and `recvmsg` on a stream socket. github.com's
  answer never needs it; a name whose answer passes 512 bytes would fail with `io`. To file on pax.
- **R-px127-4, the rows' places: both, recommended and done.** The kernel's rows in mpx4-console-push's names way
  (N1's recvmsg cases, N3 through musl's resolver), which CI runs; the on-box rows in tests/distribution-net on
  the dev ISO, which no CI job runs (owed since px92: a CI job for the distribution suites, or a link-stack leg).
- **R-px127-5, the on-box fixture.** The console names the router (10.0.2.2) as its only nameserver, as an
  installed system's `/etc/resolv.conf` names its router; tools/dns-fixture on this host's port 53 (root or
  `sudo -n`; SKIPPED LOUDLY without, a failure under `PAX_REQUIRE_NAMES_FIXTURE=1`) and a listener on an
  ephemeral port. distribution-net takes VARIANT arguments, so the dev rows run on an image directory with the
  dev ISO alone (the red take's).
- **R-px127-6, the workaround.** `/etc/hosts`, as root, measured on Linux and under QEMU; not tried on the
  installed machine by the lane.
- **R-px127-7, N3 needs musl-gcc.** Without it the suite names `/bin/gai-musl` at P0 and leaves it out, as it
  does every piece the tree cannot build, so N3 fails by name; CI installs musl-tools.

### 7.2 Issues

None filed or closed by this lane. To file: R-px127-3 (pax: musl's TCP fallback, TCP_FASTOPEN_CONNECT, `sendmsg`
and `recvmsg` on a stream socket); the distribution suites' CI job (pax, owed since px92). pax#356 stays open for
its Unix-socket half.

### 7.3 Checklist

- [x] probes 1-3 (Linux black box, the image under QEMU)
- [x] N1 (dgramopts' recvmsg cases) red at the rows tip, green at the head
- [x] N3 (musl's resolver) red at the rows tip, green at the head
- [x] distribution-net N2-N4 on the dev ISO: N3 red with the image's kernel and the rows tip's, green with the head's; N4 green throughout
- [x] tests/ci-plan, tests/census
- [x] the plant red by name
- [ ] the release tier's rows (in the PR's records when the block frees)
- [ ] the full records: mpx4-console-push (every way), mpx4-udp, mpx4-tcp, mpx4-dhcp, mpx4-console-net, mpx5-den, on the orchestrator's word
