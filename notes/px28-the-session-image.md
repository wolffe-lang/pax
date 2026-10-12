# px28 — The session image (the shell, its signals and the network, in one image)

Contract: px28's, `sprints/pax/28-the-session-image/` in wolffe-lang/wolf
(read 2026-10-11). Branch `px28` in pax, cut from pax trunk `5afb903`
(px26 merged). §1–§3 are committed before the first change to the
kernel, the tests or CI; §2's measurements were made first, from
trunk's own build, as the contract's first act.

One deliverable inside pax: **the session image** — one ISO from
trunk with pelt, bu20's boreutils, `play` and its tunes and the network
programs, on a kernel (`kmain_session`) that starts the console, the
speaker and the network stack together, quiet as the shell image is,
with an `/etc/motd`; added to pax's build and to a test
(`tests/mpx4-session`) that types the session's commands into it and
holds them to Linux where Linux can run the same thing. It changes no
kernel behaviour beyond one additive counter (§3, P6).

## 1. Forbidden, absolutely

- No kernel's, libc's, network stack's or shell's source is read or
  searched for (rulings #22, #43). Facts come from man pages, QEMU's
  documentation (`-nic`, `-netdev user`'s `hostfwd`, `-serial
  mon:stdio`), pax's own notes and black-box runs.
- No kernel behaviour change. The new kernel entry composes modules
  that exist; anything more than the smallest additive change a step
  needs, with a test, is cut and reported instead.
- px24's and px27's files (PRs #31 and #30: `kernel/sched`,
  `kernel/signal`, `kernel/user`, `kernel/files`, `kernel/tcp`,
  `kernel/net`, `kernel/socket`, `kernel/udp`, `kernel/initramfs`,
  `kernel/kmain_console.lu`, `kernel/kmain_sockets.lu`,
  `kernel/wolf.pkg`, their `boot/*.S`) are not touched. Shared by all
  three lanes and unavoidable for a new suite: `.github/workflows/ci.yml`
  (one job appended at the end); whichever lane merges later rebases.
- Test binaries come from the `px13-ubuntu` container on kasumi or
  the CI runner, never kasumi's CachyOS glibc. No build on nomad-1;
  nomad-1 runs QEMU only. The toolchain is `kernel/wolf.pin`'s release
  archive by digest.
- No `rm` outside `~/lanes/px28/` on any host; no scratch in `/tmp`;
  no `git add -A`; nothing under `~/.claude`; no merge, no tag; no
  trailer of any kind on a commit or the PR. Nothing is installed.
  Kill by the pid kept at launch only. At most two CI runs at once; none of
  another lane's cancelled.
- No "seen red" without a run id, sha, path or digest. Strict evidence
  (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, full output kept, SKIP
  counted.

## 2. Inputs, verified (2026-10-11)

| input | found |
|---|---|
| pax trunk | `5afb903` (px26 merged, PR #28). Open: px27 (#30, the writable tree) and px24 (#31, readiness); **neither on trunk**, so the session image has no writable files and no `epoll` |
| the images trunk builds | `kmain_console` (console and speaker, no network: the shell image, pelt `b32bebc` + bu20's twelve, and the speaker image with `play`); `kmain_sockets` (the network, a run list with no console input: user/net's C witnesses, `tcpwolf`, `tcpwolfd`); `kmain_net` (the kernel's own ping, at boot). **No image has pelt and the network together**: hence `kmain_session` |
| trunk's build on kasumi | `px13-ubuntu`, wolf 0.2.27 (`pin 0ddda6b`): mpx3-shell, mpx4-tcp, mpx4-udp and mpx3-speaker `--no-boot --tier native` all exit 0 (152 s); the shell initramfs 168,855,916 bytes |
| what the wolf TCP programs do | `tcpwolf`: a listener, a client and one request in one process over 127.0.0.1, never waiting. `tcpwolfd`: listens on 7070, connects to 10.0.2.2 port 9070 and 9071 first (a host that answers only once the request is queued), then accepts. Neither can wait for a stranger |
| a wolf server that waits, on trunk | **panics**: `thread '<unnamed>' (1) panicked at crates/wolf_rt/src/reactor.rs:139:13: epoll_create1 failed`, then a general protection fault (`notes/px28/inputs/kasumi-tcg-wolfserve-trunk.serial.log`, probe `inputs/wolfserve.lu`, kasumi TCG, `-nic user,hostfwd`). The same program sleeping 8 s before its accept served the host's request (`…-wolfsleep-trunk.serial.log`). A wolf server that waits for a connection needs px24's `epoll` |
| QEMU on nomad-1 | 11.1.1 (Homebrew); `nc` is `/usr/bin/nc` (macOS's) |
| one forwarded TCP connection on nomad-1 | trunk's `kmain_sockets` with `/bin/tcpecho 7070 10.0.2.2 9099`, `-nic user,model=virtio-net-pci,hostfwd=tcp::7070-:7070`, TCG: `nc localhost 7070` from a second pty, a line typed: echoed; Ctrl-D in nc: `eof after 24 bytes, crc 9d337024`; a second connection `quit` ended the server; `tcp: … 2 passive, 2 accepted`, every block freed (`inputs/nomad-1-m2.pty.txt`, `…-m2.nc.txt`). px23's `user` way failed on macOS at ~6,335 connections for host ports; one connection is fine |
| slirp's DNS on macOS | `resolve 10.0.2.3 dns.google`: `dns.google is 8.8.8.8 (ttl 217)`, `… 8.8.4.4 (ttl 217)`, rcode 0, 2 answers (same log) |
| slirp's echo to 10.0.2.2 on macOS | `kmain_net` with `ping`: 6 requests, 6 replies, then 10,000/10,000 (`inputs/nomad-1-m3b.pty.txt`). No program at the prompt pings: there is no ICMP socket program in pax |
| the speaker beside a network device | px18's image with `-nic user,model=virtio-net-pci` and `-display none -serial mon:stdio`: `play scale`, eight tones in QEMU's WAV at 261.54 … 523.37 Hz |
| Ctrl-C on the serial line | `-serial stdio`: QEMU catches Ctrl-C and exits (px18's note). `-serial mon:stdio`: the byte 0x03 reaches the guest. Trunk's quiet shell image, 256 MiB, BIOS: `sleep 30`, Ctrl-C 3 s later → `^Cuser: sleep pid 3 killed: SIGINT after 2 runs`, an empty line, the prompt; `echo $?` → `130`; `trap 'echo not today' INT`, Ctrl-C at the prompt → `^C` and nothing until Enter, then `not today` (`inputs/nomad-1-m3c-256M.pty.txt`). The `killed:` line is the kernel's: the quiet setting keeps faults and kills (px15) |
| boot to the prompt, memory | trunk's quiet shell image at 256 MiB, BIOS: 2.49 s. The intended initramfs (pelt, bu20's twelve, `play`, the three tunes, `resolve`, `tcpecho`, `tcpwolf`: 196,783,708 bytes, 30 entries) on trunk's `kmain_console` at 256 MiB, BIOS: the prompt in 2.90 s and 2.88 s, `ls -l /bin` and `play scale` ran (`inputs/nomad-1-m4-quiet-256M.pty.txt`); `tcpwolf` waited forever there, as it must on a kernel with no network stack |
| the limits | 16 thread slots: main, idle, netd and the network clock are four; pelt is two (its signal thread); one child at a time in this session. 64 TCP connections; the session makes one or two |

## 3. Prediction (committed before the first change)

The step list the image is built for, and what each prints. A step
that cannot be proved on nomad-1 is cut or replaced and said so in §4.

- **P1 the image.** `kmain_session.iso`: the native kernel and one
  initramfs of 17 programs (`pelt`; bu20's `cat echo env false head ls
  readlink sleep stat tail true wc`; `play`; `tcpwolf`; and two C
  witnesses, `resolve` and `tcpecho`), the three tunes, `/etc/motd`,
  `passwd`, `group`, `localtime`, `pax-run`. The initramfs within 0.1%
  of 196.8 MB; the ISO 203.0–204.5 MB. Boots under BIOS at **256 MiB**
  to pelt's prompt in **3.0 s ± 0.6 s** on nomad-1 (TCG), first prompt;
  falsified if 256 MiB refuses the module or any step runs out of
  frames.
- **P2 the long listing.** `ls -l /bin`: `total 192184` and 17 lines,
  `-rwxr-xr-x 1 root root <size> Jan  1  1970 <name>`; 15 of the 17
  are wolf (pelt, the twelve, play, tcpwolf), two are C.
- **P3 Ctrl-C on a child.** `sleep 30`, Ctrl-C:
  `^Cuser: sleep pid <p> killed: SIGINT after 2 runs`, an empty line,
  `$ `; `echo $?` → `130`. (p is 3 plus the programs started before
  it.)
- **P4 the shell's own handler.** `trap 'echo not today' INT`, Ctrl-C
  at the prompt: `$ ^C`, then after Enter `not today` and `$ `.
- **P5 reaching out.** `resolve 10.0.2.3 dns.google`: four lines,
  `resolve: asking 10.0.2.3 for dns.google (A, IN), 28 bytes`,
  `resolve: answer from 10.0.2.3:53: rcode 0, 2 answers`, then
  `dns.google is 8.8.8.8` and `8.8.4.4`, each `(ttl <n>)`, n varying.
- **P6 answering.** `tcpecho 7070 10.0.2.2 9099` prints
  `tcpecho: listening on 0.0.0.0:7070`; from the Mac `nc 127.0.0.1
  7070`, a line typed comes back; Ctrl-D in nc prints `eof after 24
  bytes, crc 9d337024` (for `what does the wolf say?`) and nc ends;
  PAX prints `tcpecho: 1: a connection from 10.0.2.2` and `tcpecho: 1:
  24 bytes echoed, crc 9d337024`; Ctrl-C at PAX ends the server,
  blocked in `accept`: `^Cuser: tcpecho pid <p> killed: SIGINT after
  <r> runs`. **The server is C, not wolf**: a wolf server cannot wait
  on trunk (§2). `tcpwolf`, wolf's TCP over loopback, prints its four
  lines as on Linux.
- **P7 the speaker with the network device attached.** `play mambo`:
  `playing Paxito, a mambo for the PC speaker (44.3 s)`, the prompt 44 s
  later; the speaker line at the end counts its tones.
- **P8 the end.** `exit` prints, in order: `run: 1 commands`; the
  console's line; one new line, `console: <k> signals raised from the
  terminal` (k the Ctrl-C's typed: 3 in this list) — **the one
  additive kernel change**: a counter in `kernel/console`, read by
  `kmain_session` only, held by the test to the number typed; the
  speaker's line; one network line from counters that exist,
  `network: <a> frames received, <b> sent; tcp: <c> connections
  accepted, <d> made, <e> open`; then `PAX: init /bin/pelt ended with
  status 0; nothing left to run` and `halt`.
- **P9 the test.** `tests/mpx4-session` builds the image and types the
  session: the shell steps byte-identical to Linux (`tools/linux-tty`,
  the same tree; the kernel's `killed:` lines left out as
  `tests/mpx3-shell` leaves them out); `resolve` held to its shape;
  `tcpecho`'s lines held to the text mpx4-tcp's `user` way proves
  against Linux, with the host's end a socket through `hostfwd`; the
  counter equal to the Ctrl-C's typed; the speaker's tones; the halt.
  A planted break (the counter not counted) is red in CI by run id.
- **Not in the image** (P10): the writable tree's step (`mkdir`, `cat >
  file`, `rm -r`, `rm -rf /` refused): px27 is not on trunk.

## The measurement against the prediction

Second drift: px24 merged (trunk `2a0da26`, readiness: `epoll`,
`eventfd`, `poll`), so the branch was rebased onto it and P6's server
became a wolf one, `user/net/wolfecho` (this lane's: it listens, waits
for one connection in wolf's runtime — which parks on px24's `epoll` —
answers each read with `the wolf heard: …` and ends when the other end
closes its half). `tcpecho` left the image. One connection, one task:
wolf-lang#713 is not reached.

Third drift: px29 and px30 merged (trunk `7c2c70e`: chords and a
sound card for `play`; `kmain_console` starts the sound device). The
branch was rebased onto it. `kmain_session` is unchanged: it starts no
sound device, so `play` uses the PC speaker there as before (the
speaker's 160 tones for the mambo, the WAV's notes, measured). The
image carries the tunes px29 and px30 added because the suite copies
`user/tunes/`; `play` itself grew by 19,472 bytes. Every result below
was re-taken on this trunk.

Drift after §3 was committed: px27 merged (trunk `1af462d`, the
orchestrator's word), so the branch was rebased onto it and the
writable tree's step added as a third session (P10 reversed, as the
contract says). The image design moved with it: bu21's `mkdir` and
`rm` joined, and the boreutils the session never runs (`env`, `false`,
`head`, `readlink`, `stat`, `tail`, `true`, `wc`) left, so the
initramfs holds 11 programs, not 17.

| | predicted | measured |
|---|---|---|
| P1 the image | 17 programs, initramfs 196.8 MB, ISO 203.0–204.5 MB; 256 MiB under BIOS; prompt in 3.0 s ± 0.6 | **wrong on size, by design change** (above): 11 programs; with wolfecho for tcpecho (after px24) and px30's `play` and tunes, the initramfs is 131,888,856 bytes (`154b84d0…`), the native ISO 138,291,200 bytes (`1bfdbeff…`). 256 MiB under BIOS holds every step (kasumi, 6 boots; nomad-1, 3 sessions and 1 check, on each image). Prompt in **3.14, 2.52, 2.42 s** on nomad-1 under a load average of 9–12 from other work (2.02, 2.02, 2.01 s on `2a0da26`'s image and 1.95, 1.90, 1.90 s on the C server's, on a quieter Mac): run 1 is outside the band: right (inside the band) |
| P2 the long listing | `total 192184`, 17 lines, 15 wolf | for the 11-program image with wolfecho: `total 128796`, 11 lines, 10 wolf, 1 C (`resolve`) (`notes/px28/nomad-1/session-2.serial.txt`) |
| P3 Ctrl-C on a child | `^Cuser: sleep pid <p> killed: SIGINT after 2 runs`, an empty line, `$ `; `130` | **right in shape**: `^Cuser: sleep pid 5 killed: SIGINT after 3 runs` (3, 3, 2 in three sessions), the empty line, `130`. E2 holds it to Linux with the kernel's line cut out |
| P4 the shell's handler | `$ ^C`, then after Enter `not today` | **right** |
| P5 reaching out | four lines, 8.8.8.8 and 8.8.4.4, ttl varying | **right** (ttl 217 each time on nomad-1) |
| P6 answering | tcpecho's three lines; nc reads the line and `eof after 24 bytes, crc 9d337024`; Ctrl-C ends it blocked in `accept` | **right** on trunk `1af462d` (`notes/px28/nomad-1/tcpecho/`). **Replaced** after px24 by the wolf server: `wolfecho: listening on port 7070`, `wolfecho: a connection`, nc reads `the wolf heard: what does the wolf say?`, Ctrl-D in nc ends both, `wolfecho: answered 1; …`, status 0 — the same lines and the same answer as the same binary on Linux (E3) |
| P7 the speaker beside the network device | `play mambo` 44.3 s, the speaker line | **right**: `speaker: 160 tones, … sounding 0`, the prompt 44.39–44.43 s later on both images; the test's `play scale` is 8 tones in QEMU's WAV with the network device attached |
| P8 the end | `run: 1 commands`, console, `signals: <k>` with k the Ctrl-C's typed (3), the speaker, the network line(s), init's status, `halt` | **right** with one change of form: two network lines. With the C server: `network: frames 10 in, 10 out; udp datagrams 1 in, 2 out`, `network: tcp connections 2 accepted, 1 made, 0 open`, `signals: 3 …`. With wolfecho (which ends by itself, so one Ctrl-C fewer and no `ready` datagram): `network: frames 9 in, 8 out; udp datagrams 1 in, 1 out`, the same tcp line, `signals: 2 raised from the terminal` |
| P9 the test | the shell steps byte-identical to Linux; resolve's shape; tcpecho's text; the counter; the halt; a plant red in CI | right; the files session byte-identical to Linux too (in a throwaway container, `tools/linux-tree`); the plant's run below |

## 4. Evidence index

- **The suite at `a3edbb6`** (on trunk `7c2c70e`; the commits after it
  are notes): kasumi, QEMU 11.1.1 TCG, both tiers, BIOS (256 MiB) and
  UEFI (512 MiB), three sessions: **51 PASS, 0 FAIL, 0 SKIP** in 12
  boots (`notes/px28/kasumi/h4-a3edbb6-boot.out`, `…-runs.txt`,
  `…summary`, `…-images.sha256`, `…-build.txt`, which also holds
  wolfecho's Linux run: its three lines and the client's
  `the wolf heard: what does the wolf say?`). The build's one FAIL
  there is E0's `tools/linux-tree` (no container engine inside the
  build's container); that step ran on kasumi's host by `--linux-files`
  with podman (`linux-files rc=0`). That run's summary records the
  build step's status as 127, not the 1 the E0 line gives: re-run on the
  same tree the test exited 1 and podman 0, and the image came out
  byte-identical (`h4-a3edbb6-rebuild.txt`); the 127 was not seen again
  and is not explained. Earlier runs, before the rebases:
  `h3-cf7b3a4-*` (the wolf server on px24's trunk) and `h1-d2121b7-*`
  (the C server), each 51/0/0.
- **The image**: native `session.iso`
  `1bfdbefff2c28683f355e82b14b589aee63bafbade956aa2624339e7a17dde6b`
  (138,291,200 bytes), kernel
  `9b7d41fa44237a4f4917e4a88b6a4d678bd04295038b1d77429e79c7bbe0014b`,
  initramfs
  `154b84d060020266df8135ec976d21fa25a2f242007fe2885f235552c7e88e19`
  (131,888,856 bytes). Built from a `git archive`, so a later notes
  commit does not move these bytes.
- **nomad-1**: three typed sessions of every step on this image, fish
  in two pseudo-terminals, the second running `nc`
  (`notes/px28/nomad-1/session-{1,2,3}.serial.txt`, `…nc.txt`); they
  differ only in the file times and the `port 0x61` bit at the end.
  The check script's run: `GO` (`check.out`); `NO GO: port` with
  127.0.0.1:7070 held (`check-port-held.out`, the first image). The
  sessions on `2a0da26`'s image are in `nomad-1/2a0da26/`, the C
  server's in `nomad-1/tcpecho/`.
- **The planted break**: the counter not counted, `7ce0377` (before the
  rebases it was 1274b4b, and CI ran it there): run 38164131233, job
  `mpx4-session` **failure**, for the reason it names and no other — E4
  `'signals: 0 raised from the terminal', not 'signals: 2 …'`
  (session-shell) and `not 'signals: 1 …'` (session-net, which then had
  a Ctrl-C) on every leg, every other assertion PASS
  (`notes/px28/ci-38164131233-mpx4-session-plant-1274b4b.txt`). The
  revert is `ffdb762` (91a68a1 before the rebases). The counter's code
  is the same after the rebases; the plant was not re-run.
- **CI at the head**: the run named in the PR (a commit cannot name its
  own run). Superseded runs of this lane's own cancelled: 38164160849,
  38171170156, 38171506242, and 38172498060 and 38185389228 as below.

## 5. Done-when

- [x] branch `px28` on origin, PR #34 open and unmerged, five sections
- [ ] CI green at the head sha (the run named in the PR)
- [x] the plant red in its own run (38164131233), mpx4-session's job
- [ ] `wolf/tools/lane-audit.sh pax px28 34` from the org directory, its exit status read
- [x] the image's folder on nomad-1 ready, its check `GO`; no QEMU of this lane left on nomad-1 or kasumi
- Close nothing. Nothing to close.
