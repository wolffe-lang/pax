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
