# dw02 — the entropy contract: cryptographically ready bytes, or a refusal by name

Before this lane, `getrandom`, `/dev/random`, `/dev/urandom` and `AT_RANDOM` answered RDRAND words when the processor
had RDRAND and otherwise a fold of the time-stamp counter, and nothing told a program which it got. An encryption tool
(the backup tool, `denward`) needs 32 to 96 unpredictable bytes a backup and must refuse, not guess, when the machine
cannot give them. This lane measured what the kernel did, chose a contract, and built it.

- **Measured** (section 4): with RDRAND masked from CPUID, every getrandom flag set and both devices still answered
  every byte asked, from the fold; of a 1 MiB `/dev/urandom` read's 131,072 words, 131,071 repeated the top half of
  the word before (with RDRAND: none). AT_RANDOM's two halves shared their top half. Nothing failed, so no program
  could tell.
- **The contract** (section 7): getrandom with flags 0, `GRND_RANDOM` or `GRND_NONBLOCK`, and reads of `/dev/random`
  and `/dev/urandom`, answer RDRAND words, each draw's carry flag checked, or fail by name: `EAGAIN` when the machine
  has no qualified source, `EIO` when RDRAND failed. `GRND_INSECURE` (the uapi header's "non-cryptographic random
  bytes"), `AT_RANDOM` and the kernel's own words keep the old answer. `/proc/pax-random` says `ready yes` or
  `ready no` and why.
- **Built** (section 8): `kernel/random`, one RDRAND execution in `boot/fpu.S`, getrandom and the devices on the strict
  path, `/proc/pax-random`, and two test words on the command line that make RDRAND fail. Rows red first at the rows'
  commit, green at the head (section 9).
- **Not built:** an entropy pool or a generator; a pool is planned. Until then a machine without RDRAND has no
  qualified source, and its strict calls refuse.

Footprint: cross-cutting (`boot/fpu.S`, a new `kernel/random`; `kernel/process`, `kernel/user`, `kernel/files`,
`kernel/procfs`; `.github/workflows/ci.yml` gains the `mpx6-entropy` job, `tools/ci-tiers.map` and `tests/ci-plan` its
paths; new `tests/mpx6-entropy`, `tests/mpx6-entropy.d/`, `tools/mkentropy`, `user/elf/entropy.c`,
`user/elf/wolf_entropy.lu`).

The commit shas in this note are those of the branch as first measured, before its rebases (section 13), kept as
`dw02-before-rebase`; `notes/dw02/shamap.txt` sets each beside its commit on each later cut.

## 1. Forbidden, and what was read

- **The clean room.** No kernel's, firmware's or C library's source was read. Sources: the Intel Digital Random Number
  Generator (DRNG) Software Implementation Guide rev. 2.1 (sections 3.2, 5.2, 5.3); the Intel SDM vol. 2 (CPUID,
  RDRAND); AMD's security bulletin AMD-SB-7055 and Intel's advisory INTEL-SA-00320; getrandom(2), random(4) and
  random(7); the uapi header `linux/random.h`; wolf's specification (`spec/11-os.md`, `[os.random]`) and wolf's own
  runtime (`crates/wolf_rt/src/random.rs` at the image's wolf); the image's programs at their pins (section 5).
  `docs/SOURCES.md` (dw02) lists them.
- **Hosts.** A Linux build host (Intel Core i7-12700KF) for every build and boot, in an Ubuntu 24.04 container (QEMU
  8.2.2, the CI runner's version; OVMF; gcc 13.3) under KVM and under TCG; the build Mac for git, for reading and
  for a compile check before each take.
  QEMU only.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk at `4007eaa0` (pax#399 merged), which holds px131's work: getrandom's fill rewritten and `random_fill` added, the functions this lane changes. The lane was written and measured on `px131` at `4b3ab3c0` (now frozen), rebased onto `px131b` at `65902280` (pax#394, since closed; its commits are in trunk) and then onto trunk (section 13, "The base") | the fresh clone's `git rev-parse` |
| wolf | 0.2.35 (`kernel/wolf.pin`) | `tools/fetch-wolf`, by digest |
| Limine | 12.9.1 | `tools/fetch-limine`, by digest |
| the image's programs | `user/*.pin` (boreutils `ff5396ad`, pelt `b80d6570`, yew `3a9983ee`, burrow `7aa182f8`, den `291011dd`, lobo `39788b86`, wolf-std `77cf3210`, wolf-lang v0.2.39 `3fc86f77`) | shallow clones at the pins, read for their draws |

## 3. What the kernel did, from the code (at `4b3ab3c0`)

- `kernel/process`'s `random_word(k)` asked CPUID.1:ECX bit 30; with RDRAND it took `pax_rdrand` (RDRAND up to 16
  times while the carry flag was clear, 0 when none came); without, or when that word was 0, it returned
  `t ^ t>>17 ^ t>>31 + k` of the time-stamp counter. px131's `random_fill` did the same a page at a time.
- `getrandom` read its flags only to refuse bad ones (px24) and filled from `random_fill`, at most 16 KiB a call
  (px131). `/dev/random` and `/dev/urandom` were getrandom with flags 0, their reads whole. `AT_RANDOM` was two
  `random_word`s; the kernel's own TCP sequence numbers and DHCP transaction id were two more.
- So a word of 0 from RDRAND (a legitimate value, or the published fault) became a fold; a stuck RDRAND that reports
  all ones with its carry set was taken as random; and nothing recorded which source answered.

## 4. The measurement (the prediction, `notes/dw02/prediction.txt`, scored)

`tests/mpx6-entropy` at the rows' commit, px131's kernel unchanged; record sha256 in section 12. `hirep` is the count
of a request's 8-byte words whose top 32 bits equal the word before's: independent words do that once in 2^32, the
fold nearly always.

| configuration | CPUID (guest) | flags 0, NONBLOCK, RANDOM, RANDOM\|NONBLOCK, INSECURE, INSECURE\|NONBLOCK, 32 bytes | 4096 bytes (flags 0; /dev/random; /dev/urandom) | 1 MiB `/dev/urandom` read | AT_RANDOM | wolf `os_random(32)` |
|---|---|---|---|---|---|---|
| present, `-cpu max`, KVM (BIOS and UEFI) | GenuineIntel, rdrand 1, rdseed 1 | each 32, hirep 0 of 3 | 4096, hirep 0 of 511 | 1048576, hirep 0 | nonzero, halves differ | 32 |
| present, `-cpu max`, TCG (BIOS) | AuthenticAMD, rdrand 1, rdseed 1 | each 32, hirep 0 | 4096, hirep 0 | 1048576, hirep 0 | nonzero, halves differ | 32 |
| masked, `-cpu max,-rdrand`, KVM and TCG | rdrand 0, rdseed 1 | **each 32, hirep 3 of 3** | **4096, hirep 511 of 511** | **1048576, hirep 131071 of 131071** | nonzero, **halves share their top 32 bits** | **32** |
| `pax.rdrand_fail=9`, `=1000000`, `pax.rdrand_stuck` | as present | as present (the words were unknown to this kernel) | as present | as present | as present | 32 |

In every configuration: `RANDOM|INSECURE` and an unknown bit `EINVAL`; n 0 answers 0; 1, 7, 256 and 16384 bytes
answer in full; 65536 and 1 MiB answer 16384 (px131's cap); the first program's first call and a process two seconds
later answer alike (no readiness state); `/proc/pax-random` absent (`ENOENT`); the static glibc probe runs and
allocates. The prediction held but for one line: TCG's `-cpu max` has RDSEED too (predicted 0). QEMU's default model
(no `-cpu`) was not measured in this take: the suite's wrapper for it ran itself (a bash assignment that read the
variable set beside it), its boots never started and its rows are red for that alone (`E0 … default`); fixed at
`507bb74f` and `a81d861f`, and measured at the head (section 9).

## 5. Who draws, and how (the census)

What each program on the image asks, read at its pin (and, for C libraries, from recorded straces: notes/px10,
notes/px24, notes/px26), and what it does on a machine with no qualified source, before and after.

| who | the call | when | no qualified source, before | after (strict) |
|---|---|---|---|---|
| every static glibc program (every wolf program on the image: pelt, den, burrow, boreutils, yew, scent, trash, aspen, lope, sniff, clef, ligature, lobo; PAX's own login, passwd, su, sudo, the installer; the C probes) | `getrandom(8, GRND_NONBLOCK)`, glibc's allocator's key (straces: notes/px10, notes/px26) | the first allocation | the fold | `-EAGAIN`, as Linux answers before its pool is ready; glibc goes on (row E3: the C probe allocates and runs) |
| Rust's standard library in wolf's runtime threads and in lupin | `getrandom(16, GRND_INSECURE)` (the strace of notes/px24) | a hash map's keys | the fold | unchanged: the insecure path |
| wolf's `os_random(n)` (wolf's runtime: getrandom flags 0, `EINTR` retried, any other failure a trap, exit 134) | pelt: a here-document's and `fc`'s temporary names (12 and 10 bytes); yew: every buffer's identity (7 bytes, so at start-up), and its temporary names; boreutils: `mktemp`, `shuf`, `sort`'s temporary files, `shred`; the installer's seed (32 bytes) and the upgrade's (4); login, passwd, su and sudo: a new password's salt (16); lobo: TLS and ACME keys | on request; yew at start | the fold, silently: lobo's TLS keys from the counter | the trap: each of these stops at that point, with `wolf-trap: assert` on standard error, never with weak bytes |
| burrow (`/dev/urandom` in 4 KiB refills: the key exchange's cookie, the X25519 secret, padding; burrow-keygen's host key at the first boot; mkpw's salt) | `read` | each connection; the first boot | the fold, silently: an ssh key exchange and host key from the counter | refused by burrow's own name, `entropy_unavailable`: no host key is made, so burrowd does not start, and the boot hook says so |
| den's TLS (64 bytes of `/dev/urandom` a handshake) | `read` | each HTTPS fetch | the fold, silently | refused by den's own name, `TLS host entropy unavailable` |
| yew's shell-session nonce (16 bytes of `/dev/urandom`, its own fallback the clock and pid) | `read` | a shell session | the fold | yew's own fallback (its choice, outside PAX's reach) |
| the kernel: TCP's initial sequence numbers, DHCP's transaction id | `random_word` | boot | the fold | unchanged: the insecure path |
| `AT_RANDOM` (glibc's stack guard and pointer guard) | the auxiliary vector | every exec | the fold | unchanged: the insecure path |

**For a user of a machine without RDRAND** (or whose RDRAND fails): `cat /proc/pax-random` says `ready no` and why.
These stop, and how:

| program | when | how it stops |
|---|---|---|
| `burrowd` (the ssh server) | at boot | its hook's `burrow-keygen` cannot make a host key (`entropy_unavailable`), so burrowd is not started; the hook prints `burrowd: no host key could be made at … ; not started` |
| `burrow` (the ssh client), `burrow-keygen`, `mkpw` | at each use | refused by name: `entropy_unavailable` |
| `den` fetching over HTTPS | each fetch | refused by name: `TLS host entropy unavailable` |
| `lobo` serving TLS, its ACME client | at the handshake, at key generation | wolf's trap (`wolf-trap: assert`, exit 134) |
| `yew` | at start (every buffer draws an identity) | wolf's trap |
| `pelt` | at a here-document (`<<`) or `fc` | wolf's trap: the shell itself ends |
| `mktemp`, `shuf`, `sort` (its temporary files), `shred` (boreutils) | at the draw | wolf's trap |
| `passwd`, `su`, `sudo`, `login` setting a password | at the new password's salt | wolf's trap |
| the installer, an upgrade | when it makes its plan's seed (after the disk report; `--check` draws nothing, a scripted run gives `--seed`) | wolf's trap |

Everything else runs: each static program's start-up draw (glibc's, `GRND_NONBLOCK`) gets `EAGAIN` and goes on
(row E3), `AT_RANDOM` and the kernel's own words keep the fold, and Rust's hash maps keep `GRND_INSECURE`.

**The legs.** Every suite that boots PAX passes `-cpu max` (TCG or KVM) or `-cpu host` (KVM) but two:
`tests/mpx6-staged` and `tests/mpx6-bootlog` pass `-cpu host` under KVM and nothing under TCG, so on the CI runner
(which boots everything under TCG but mpx5-burrowd) they run QEMU's own default model. Their programs are small C
inits (`tests/mpx6-staged.d/init.c`, `tests/mpx6-bootlog.d/init.c`) whose only draw is glibc's `GRND_NONBLOCK` one:
row E3's case. Measured in section 4: TCG's `-cpu max` (QEMU 8.2.2, the runner's) has RDRAND and RDSEED; the
default model is measured at the head (section 9), and E3 there shows glibc's start-up draw getting `EAGAIN` and its
program running on.

**Linux, which these programs are written to.** getrandom(2): flags 0 blocks until the pool is initialized and never
fails after; `GRND_NONBLOCK` returns `EAGAIN` instead of blocking; `GRND_INSECURE` (uapi `linux/random.h`) returns
"non-cryptographic random bytes" and never blocks; `/dev/urandom` returns data before initialization, `/dev/random`
blocks until it (random(4), random(7)). A Linux machine always initializes: it has sources besides RDRAND. PAX without
RDRAND has none, so its "not initialized" never ends; a strict call that blocked would block for good, so it says so
instead.

## 6. The hardware

- **The machine PAX is installed on** is an Intel Core i9-11900K (Rocket Lake, 2021; notes/px106). Intel's RDRAND
  came with Ivy Bridge (2012) and RDSEED with Broadwell (2014), so the family has both (the DRNG guide; the
  family's published instruction-set extensions list RDRAND). Every build and test host here has them too (measured:
  CPUID in the guest, section 4). This lane never touched that machine.
- **What the guide promises.** RDRAND returns words of an SP 800-90A generator reseeded from an on-chip entropy
  source; the carry flag is "the sole indicator" of a value, and a zero register is no sign (5.2); ten retries in a
  tight loop are enough, ten failures being "an indication of a larger CPU issue" (5.2.1); built-in self tests run
  before the generator is offered, online health tests while it runs, and a generator that fails "would cease to
  issue random numbers rather than issue poor quality random numbers" (3.2.6, 3.2.7). RDSEED gives seeds and fails
  more often under load (5.3.1).
- **Published faults.** AMD-SB-7055 (CVE-2025-62626): RDSEED's 16- and 32-bit forms on Zen 5 may return 0 with the
  carry set; AMD's workaround includes "treat RDSEED returning 0 equivalent to when CF=0". INTEL-SA-00320
  (CVE-2020-0543, SRBDS): RDRAND and RDSEED values on some processors could be sampled from another core; microcode
  serializes them. Whether the i9-11900K is on SA-00320's list was not established here.
- **So the draw** (kernel/random) is: up to ten executions; one with the carry clear is retried; a value of 0, all
  ones, or the same 64-bit word as the draw before is refused and retried; ten refusals fail the draw. All ones is
  the other constant a stuck output can report as a success: the repeat test would catch it from the second word,
  and refusing it outright costs one word in 2^64. RDSEED is
  reported (`/proc/pax-random`), never executed: nothing here needs seeds, and the faulty forms are never run. A 64-bit
  word repeats by chance once in 2^64 draws, so the repeat test refuses only a stuck source.
- **Early boot and snapshots.** RDRAND answers from the first instruction: there is no pool to fill and nothing to
  wait for. The source's state is decided at the boot's first draw (the kernel's TCP word, before any program), so the
  first program's first call is served or refused as every later one is (row E8). The kernel keeps no random state
  but the last word (for the repeat test), so a virtual machine restored from a snapshot draws fresh words: nothing is
  replayed.

## 7. The contract

One shape of three was chosen after the census above: A, strict, with no boot word that restores the old bytes (section
13 has every choice with its options):

- **A, strict (built, chosen).** getrandom with flags 0, `GRND_RANDOM` or `GRND_NONBLOCK`, and a read of `/dev/random` or
  `/dev/urandom`, are served from RDRAND or refused: `EAGAIN` when the machine has no qualified source (the CPU has no
  RDRAND), `EIO` when RDRAND failed (a draw used its ten tries, or the boot's check refused it); a call or a read that
  may not wait (`GRND_NONBLOCK`, an `O_NONBLOCK` descriptor) gets `EAGAIN` either way, the one errno getrandom(2)
  gives it. A request whose draw fails part way fails whole; a request for no bytes answers 0. `GRND_INSECURE`,
  `AT_RANDOM` and the kernel's own words are the insecure path: RDRAND when it answers, else the fold, as before.
  `/proc/pax-random` says which.
- **B, today's calls unchanged and an opt-in strict call** (a new flag bit, refused as `EINVAL` on Linux, or a
  device), with `/proc/pax-random`. Nothing on the image changes; but wolf's `os_random` makes one call, flags 0, so a
  wolf program could use neither without a change to wolf's runtime, and burrow's key exchange and host key, den's
  and lobo's TLS keep drawing the fold, silently, on a machine without RDRAND.
- **C, A with a boot word that restores the fold for strict calls** (`/proc/pax-random` would still say `ready no`),
  for a machine without RDRAND whose owner accepts that, or a test leg without it. Not chosen, and not built: no leg
  needs it (section 5), and it would make every key on such a machine weak again with one word.

**Why A.** A key exchange whose secret scalar is the time-stamp counter folded on itself is not a weaker key
exchange: anyone who can bound the machine's uptime to a few seconds searches it. On a machine without RDRAND, A stops
ssh, TLS, password changes, the installer and a few utilities' temporary names (section 5), each by name where its
program has a name for it and by wolf's trap elsewhere; B and the old kernel let them run on bytes that only look
random. Every machine PAX runs on has RDRAND, so A changes nothing there but what a failing RDRAND does: before, a
stuck one that reported all ones as a success was taken as random. And wolf's own contract for `os_random` is A's
(`[os.random.trap]`: the platform's failure is a trap, "never a silent fallback").

**What a program sees** (A):

| request | RDRAND ready | no RDRAND | RDRAND failed |
|---|---|---|---|
| `getrandom(buf, n, 0)`, `GRND_RANDOM` | n (at most 16 KiB a call) | -1 `EAGAIN` | -1 `EIO` |
| `GRND_NONBLOCK`, `GRND_RANDOM\|GRND_NONBLOCK` | n | -1 `EAGAIN` | -1 `EAGAIN` |
| `GRND_INSECURE`, `GRND_INSECURE\|GRND_NONBLOCK` | n, RDRAND's | n, the fold's | n, the fold's |
| `read` of `/dev/random` or `/dev/urandom` | n (whole) | -1 `EAGAIN` | -1 `EIO` (`EAGAIN` with `O_NONBLOCK`) |
| `n` = 0 | 0 | 0 | 0 |
| `AT_RANDOM` | RDRAND's | the fold's | the fold's |
| `/proc/pax-random` | `ready yes`, `source rdrand`, `reason ok`, `errno 0` | `ready no`, `source none`, `reason no-rdrand`, `errno 11` | `ready no`, `source rdrand`, `reason failed` or `stuck`, `errno 5` |

The state is decided once a boot and never returns to `ready yes`: a program that reads `ready yes` after its draws
knows every draw between was RDRAND's.

## 8. What was built

- `boot/fpu.S`: `pax_rdrand_step`, one RDRAND, its value into `pax_rand`'s word 0 and its carry flag as the
  return (`MOV` leaves the flag as RDRAND set it); `pax_rand`, sixteen words of kernel/random's state; `pax_rdrand`
  (sixteen tries, 0 for none) goes.
- `kernel/random` (new): the state (`READY`, `NONE`, `STUCK`, `FAILED`, decided at the boot's first draw), the draw
  (ten tries; no carry, 0, all ones and a repeat refused), the boot's check (eight draws), the strict path
  (`strict_errno`, the one place a strict request consults readiness; `strict_word`, `strict_fill`), the insecure
  path (`insecure_word`, `insecure_fill`, `fold`), the counts, and the test words `pax.rdrand_fail=N` (armed after
  the check) and `pax.rdrand_stuck`.
- `kernel/process`: `random_word` and `random_fill` are kernel/random's insecure path (AT_RANDOM, the kernel's words,
  GRND_INSECURE).
- `kernel/user`: getrandom serves flags 0, `GRND_RANDOM` and `GRND_NONBLOCK` from the strict path, refusing with
  `-EAGAIN` or `-EIO` (`-EAGAIN` for `GRND_NONBLOCK`); a request for no bytes answers 0; a page that fails fails the
  call; the staging frame is zeroed before it goes back. A read of `/dev/random` or `/dev/urandom` is getrandom with
  `GRND_NONBLOCK` when the descriptor has `O_NONBLOCK`, else flags 0.
- `kernel/files`: `is_random`'s contract restated (a random device's read takes px23's `nonblocking` for its
  `O_NONBLOCK`).
- `kernel/procfs`: `/proc/pax-random` (entry 59; `ENTRIES` 60): `ready`, `source`, `reason`, `errno`, `rdrand`,
  `rdseed`, `tries`, `draws`, `retried`, `rejected`, `failed`, `folded`, `test`.
- `tests/mpx6-entropy`, `tests/mpx6-entropy.d/` (rows, the default model's wrapper), `tools/mkentropy`,
  `user/elf/entropy.c`, `user/elf/wolf_entropy.lu`; the CI job; `tools/ci-tiers.map` (`mpx6-entropy` in `@user`,
  `kernel/random` to `@user` and `@net`) and `tests/ci-plan`'s rows for them.

## 9. The rows

`tests/mpx6-entropy` (its header lists the rows), in six configurations: `present`, `masked`, `default` (QEMU's own
model), `retry` (`pax.rdrand_fail=9`), `fail` (`pax.rdrand_fail=1000000`), `stuck` (`pax.rdrand_stuck`).

- **Red at the rows' commit** (`437db920`, px131's kernel), native, both firmwares under KVM: `E1` (present, retry:
  no capability), `E2` (masked: every strict call answered 32), `E4` (retry: no counts), `E5` (fail: answered 32),
  `E6` (stuck: answered 32), `E7` (the sizes, not ready: answered in full), `E9` (masked, fail, stuck: wolf's
  `os_random` got 32); `E0 … default` red for the suite's own wrapper fault (section 4). `END entropy-kvm exit=1`.
  Record in section 12.
- **E3 strengthened on review** (`62fa320a`): the probe runs itself under ptrace and holds the C library's own
  start-up draw, a `GRND_NONBLOCK` getrandom of 8 bytes, to its answer (in full when ready, `-EAGAIN` when not) and
  the program's run after it. At the rows' commit that draw answered 8 everywhere (the measured `NONBLOCK` row). The
  first tracer told a stop's entry from its exit by alternation; on PAX execve's syscall-exit stop comes after its
  SIGTRAP, so the count shifted by one and E3 read the entry's `-ENOSYS` as the answer in every configuration (the
  plant's take at `0d89dfc0`, record sha256 `5a82145130559b0cf3f170c00eddea1ceef900b13c074a4d50b0ce1f243d9efb`);
  from `b9e823e7` a stop is an entry when `rax` holds `-ENOSYS`, as ptrace(2) has it.
- **Green at the head**, native (KVM both firmwares, TCG BIOS) and release: the records are cited in the pull request.

## 10. For std and denward

**The call a wolf program makes** is `os_random(n)`, as wolf's spec has it (`[os.random]`): one getrandom(2) with
flags 0, `EINTR` retried, short reads continued, any other failure a trap. On PAX after this change it gives `n`
RDRAND bytes, or the call fails (`EAGAIN` with no RDRAND, `EIO` when RDRAND failed) and the program traps (exit 134,
`wolf-trap: assert`). It never gives weak bytes. **To refuse by name instead of trapping**, a program reads
`/proc/pax-random` first: `ready yes` means draw; `ready no` with `reason no-rdrand` means `entropy_unqualified`;
`ready no` with `reason failed` or `stuck` means `entropy_unavailable`. Reading `ready` again after the draws costs
little and closes the window: the state never returns to `yes` within a boot. Where the file is absent (Linux, macOS),
`os_random`'s own contract stands (Linux blocks until its pool is ready).

**For std (dw03):** nothing is needed for correctness: `os_random` already refuses on PAX. To let a program name the
refusal, std may add one small reader, for example `std.os.entropy_status() -> EntropyStatus` (`ready`,
`unqualified`, `unavailable`, `unknown` where no such file exists), that parses `/proc/pax-random`'s `ready` and
`reason` lines. It must not become an error row on `os_random` (the spec forbids one) and must not fall back to
anything.

**For denward:** before a backup's first draw, read the status: `unqualified` refuses `entropy_unqualified`;
`unavailable`, or a PAX system (`uname` says `PAX`) whose file cannot be read, refuses `entropy_unavailable`. Then
draw the file key (16 bytes), the payload nonce (16) and each recipient's ephemeral secret (32) with `os_random`, and
read the status once more before writing the header; any change refuses `entropy_unavailable` and writes nothing.

## 11. Later work

No entropy pool and no generator were built here. A pool is planned.

## 12. Evidence index

The takes at the rebased head are cited in the pull request.

| what | where | result |
|---|---|---|
| the prediction | `42a9a75c` (`notes/dw02/prediction.txt`) | before the probe; scored in section 4 |
| the probes, the builder, the suite, CI's job and paths | `e01dde26`, `9a6de5b3`, `e52cfb2f`, `c93c69d9`, `d6f2a59a`, `f31ce346`, `f881e580`; the rig `437db920` | |
| **the measurement and red at the rows' commit** | `notes/dw02/rig/red.manifest` at `437db920` (px131's kernel), a block take on the build host, record sha256 `1dd5cdcb4276febc8748d382aef3976726cac95b16614dc80662c6fed60e44c3` | `END ci-plan exit=0 secs=73`, `END entropy-kvm exit=1 secs=670`, `END entropy-tcg exit=1 secs=336`; red by name on BIOS and UEFI under KVM and on BIOS under TCG: `FAIL E1 … present` and `… retry`, `FAIL E2 … masked`, `FAIL E4 … retry`, `FAIL E5 … fail`, `FAIL E6 … stuck`, `FAIL E7 … masked`, `… fail`, `… stuck`, `FAIL E9 … masked`, `… fail`, `… stuck`; `FAIL E0 … default` the suite's wrapper (section 4) |
| the suite's fix for the default model | `507bb74f`, `a81d861f` | |
| the kernel change | `76e0d172`, `23573a2e`, `e6802324`, `d90e60d2`, `f8d4c4fc` (its second `nonblocking` dropped at `3886b705`), `3cc7552c`, `ba3addb2`, `d3a52496`; CI paths `77c74089`, `c59c6c40` | |
| E3's start-up witness | `efb047a9`, `62fa320a`; the tracer's fix `b9e823e7` | |
| the takes at the head (native, release) and the plant | `notes/dw02/rig/{final,release,plant}.manifest` | their records and `END` lines are in the pull request |

## 13. Decisions

Each with its options; the one built is marked.

- **R-dw02-1, the shape.** (A) strict: flags 0, `GRND_RANDOM`, `GRND_NONBLOCK` and both devices served from RDRAND or
  refused by name; `GRND_INSECURE`, `AT_RANDOM` and the kernel's words unchanged; `/proc/pax-random` (built,
  recommended, and chosen: strict, with no boot word that restores the old bytes); (B) today's calls unchanged, an
  opt-in strict flag or device, and `/proc/pax-random`; (C) A with a boot word that restores the fold for strict calls
  on a machine without RDRAND (not chosen). `strict_errno` is the one place a strict request consults readiness.
- **R-dw02-2, the errno.** (A) `EAGAIN` with no qualified source (Linux's errno for "not ready"), `EIO` when RDRAND
  failed, `EAGAIN` for a call that may not wait either way (built, recommended); (B) block for good, as Linux's
  unready pool would, never a named refusal; (C) `EIO` for both: one name, and no program that retries on `EAGAIN`
  can spin. Wolf's runtime traps on either; glibc's start-up goes on (E3).
- **R-dw02-3, `/dev/urandom`.** (A) strict, as `/dev/random` (built, recommended): burrow's key exchange and host key
  and den's TLS read it, and Linux's early-boot leniency would be permanent on PAX; (B) Linux's early-boot reading:
  the fold when not ready.
- **R-dw02-4, RDRAND's handling.** (A) ten tries a word (the DRNG guide's 5.2.1), the carry flag checked each time, 0,
  all ones and a repeat refused, eight draws checked at boot, a failure latched for the boot (built, recommended); (B)
  sixteen tries and a 0 taken as failure, as before (no source for sixteen; a stuck all-ones taken as random); (C) a
  failure per call, not latched (a source that fails and recovers keeps serving).
- **R-dw02-5, the capability.** (A) `/proc/pax-random`, one fact a line (built, recommended); (B) an auxiliary-vector
  entry (no Linux type for it, and it would be read once at exec); (C) `/proc/cpuinfo` flags (a CPU's features, not the
  source's health); (D) `/proc/sys/kernel/random/*` (Linux's names there mean other things).
- **R-dw02-6, the test words.** (A) `pax.rdrand_fail=N` and `pax.rdrand_stuck` on every kernel's command line, since
  they can only take words away (built, recommended); (B) a test kernel of their own, leaving the shipped path
  untested.
- **R-dw02-7, `AT_RANDOM` and the kernel's words.** (A) the insecure path: an exec or a boot never fails for want of
  randomness (built, recommended); (B) refuse exec with no qualified source: nothing would run.
- **R-dw02-8, RDSEED.** (A) reported, never executed: nothing here needs seeds (built, recommended); (B) drawn too.
- **R-dw02-9, the legs.** (A) leave `tests/mpx6-staged` and `tests/mpx6-bootlog` as they are (QEMU's default model
  under TCG; their inits draw only glibc's `GRND_NONBLOCK`, E3's case) (recommended); (B) give them `-cpu max` under
  TCG as every other suite has.
- **The base.** Written and measured on `px131` (`4b3ab3c0`, unmerged, since frozen), which rewrote the getrandom
  fill and added `random_fill`, the functions this lane changes; rebased as a new branch onto `px131b` (`65902280`,
  pax#394, on trunk `bbe91e16`), px131's first part. The lane's own patch came over unchanged but for
  `tools/ci-tiers.map`'s `@user` line, where px131b had added `mpx3-conspeed`; the kernel under it did change (the
  console's batched drawing, px129, in `kernel/screen`, `kernel/serial`, `kernel/console`, `kernel/panic` and
  `kernel/user`'s `write`), so the takes were made again at the rebased head. Rebased again, as a new branch, onto
  trunk at `4007eaa0` (pax#399 merged; pax#394 closed), which adds to px131b's commits the latency close called
  through `pax_lat`'s word 31 from `boot/isr.S`, `boot/sched.S` and `boot/user.S` (`kernel/latency`,
  `kernel/kmain_console`) and drops a weak stub the org's assembler, clef, cannot assemble. The lane's patch came over
  unchanged (the same patch id, no conflict); the kernel under it changed again, so the takes were made again at this
  head, and since `boot/fpu.S` is the lane's assembly, `tests/kernel-as` (every `boot/*.S` through GNU as and clef) is
  a step of the native and release takes.

## 14. Done-when

- [x] the measurement, the prediction first and scored (section 4)
- [x] the census of who draws and what each does with no qualified source (section 5)
- [x] the hardware and its published faults (section 6)
- [x] the contract with its options (sections 7, 13): strict, with no boot word that restores the old bytes
- [x] built, rows red at the rows' commit and green at the head (sections 8, 9)
- [x] the paragraph for std and denward (section 10); a pool is planned (section 11)
- [x] one plant, red by name (the pull request)
