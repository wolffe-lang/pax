# px104 — push from the console: den to GitHub over https and over ssh, with burrow as /bin/ssh

The goal: at the console of the kernel every image boots, `den push` to a GitHub repository works over https and
over ssh, through burrow, the org's ssh client. px105 gave the console its network. What still stood in the way was
measured first (`notes/px104/probes.txt`): no name resolved (the C library's resolver inside den and burrow was
stopped by two of the kernel's answers before a single DNS question left the machine), the images carried no root
set, no ssh client and no pinned host key, and their den had no https.

Now the kernel answers what the resolver asks (`sendmmsg`, SOL_IP's `IP_RECVERR`, FIONREAD and an empty error
queue on a datagram socket); the images carry burrow as `/bin/ssh` and `/bin/burrow-keygen`, Mozilla's root store
as curl extracts it (`/etc/ssl/certs/ca-roots.der`, named by `/etc/shrc` as `DEN_TLS_ROOTS`), GitHub's published
host key (`/etc/ssh/ssh_known_hosts`) and den at `ac2332bf`; den's two service wrappers are on PATH under git's
names, so over ssh den asks the far side for git's own command. A new suite, `tests/mpx4-console-push`, types the
steps at the console against fixtures that answer as github.com and holds them to git's answers on Linux; its live
way pushes to a GitHub repository named only by its environment.

Footprint: cross-cutting (`.github/workflows/ci.yml` gains the `mpx4-console-push` job; `tests/ci-plan` and
`tools/ci-tiers.map`; `kernel/socket`, `kernel/udp`, `kernel/user`; `tools/distribution-root`, `tools/install-den`;
the pins `user/den.pin`, `user/burrow.pin`, `user/roots.pin`).

## 1. Forbidden, and what was read

- **Clean rooms.** PAX's: no kernel, firmware or driver source; the socket calls come from ip(7), udp(7),
  sendmmsg(2) and socket(7), and what the C library asks of them was read black box, by strace of den and burrow
  on Linux and by strace's fault injection giving PAX's old answers. burrow's: nothing of ssh was implemented here;
  burrow is built unmodified from its pin, and its README and notes were read as the org's own. den's: den is
  built unmodified from its pin; git ran only as a program (the fixtures' services and the Linux side's answers).
  No C library's, resolver's, ssh implementation's or TLS implementation's source was read. `docs/SOURCES.md`
  (px104) lists every source.
- **Secrets.** The live fixture is named nowhere in the tree, the note or a commit; the live way reads its name,
  token and key from three files the environment names, and no live run happened before the canary row was green
  (R-px104-3).
- **Hosts.** Linux host 1 (Intel Core i7-12700KF, 20 threads, 46 GB) for every build and boot, behind its lock
  names (a build heavy: a block's six CPUs; a boot light: two CPUs), in an Ubuntu 24.04 container (QEMU 8.2.2,
  OVMF, clang, lld 18, dnsmasq, OpenSSH 9.6p1's sshd and ssh, OpenSSL 3.0.13, git 2.43.0, e2fsprogs 1.47.0) with
  KVM; the build Mac for git and the root set's own conversion check. The metal target was never touched.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | px105's head `56c360e5` (on trunk `84a1fde3`) | `git log` at the clone |
| den | `ac2332bf` (`user/den.pin`), wolf 0.2.36 / lupin 0.1.58 / wolf-std `d4a4d4ca`; static, 17,696,760 bytes, `cc00cd9a…` | `tools/mkden`: four builds, one digest |
| burrow | `0d98ce92` (`user/burrow.pin`), wolf 0.2.37 / lupin 0.1.59 / wolf-std `5b3a5994`; `burrow` `ae0e800f…` 16,326,632 bytes, `burrow-keygen` `5b21c26c…` 15,480,472 bytes, burrow's own gate's digests | `tools/mkburrow`: two checkouts, one digest each |
| the root set | `cacert-2026-10-20.pem`, sha256 `796f1389…3cbe`, 118 certificates; as DER 127,103 bytes, `7a713f23…c1f1` | `tools/mkroots`: read twice; openssl's per-certificate DER the same bytes |
| GitHub's host key | `github.com ssh-ed25519 AAAAC3…GKJl`, SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU | burrow's `ci/github-known-hosts`, the fingerprint recomputed |

## 3. Prediction, scored

`notes/px104/prediction.txt`, committed first, with its addendum for R-px104-5 before that change.

| predicted | measured | score |
|---|---|---|
| the kernel serves IP_RECVERR (kept, read back), `sendmmsg` for AF_INET datagrams (vlen and iovecs at most 1024, msg_len written, the first message's errno when none went, ancillary data refused by name), FIONREAD, MSG_ERRQUEUE -EAGAIN | N1: `dgramopts`' 39 lines byte-identical to the same binary on Linux; N2: github.com through the DNS fixture, hosts.test from `/etc/hosts`, nosuch.test EAI_NONAME, the literal; the fixture saw A and AAAA for github.com in one millisecond (one `sendmmsg`) and nothing for hosts.test | right |
| under 4 KiB more ELF a tier | native `kmain_console` 3,430,192 to 3,440,864 bytes, +10,672 | wrong: 2.6 times the bound (the sendmmsg loop and its refusals) |
| no existing row moves (mpx4-udp, mpx4-console-net) | (from the records) | |
| burrow at 0d98ce92 built twice, `ae0e800f…` and `5b21c26c…`, installed unmodified | the same digests, burrow's own gate's | right |
| `user/ca-roots.pin`, 118 certificates, 127,103 bytes, `7a713f23…` | the same bytes; the pin is `user/roots.pin`, since the release builder reads every pin's `<STEM>_REV` (`ROOTS_REV`) | right, but the file's name |
| the images grow by about 31.8 MB plus 127 KB | (from the records) | |
| den's config and terminal rows move, every other mpx5-den row holds | the two rows moved, and a third: `status` with an upstream answers Git's words at `ac2332bf` (`not yet implemented: status upstream tracking` at `584b18a3`); `remote-status-limit` became `remote-status-upstream` | wrong by one row |
| the console's witness is `den fetch` into a scratch ref and `den rev-parse` | den at its pin has no `rev-parse` and refuses a refspec named with a remote: the witness is the configured fetch's remote-tracking ref read with `den log -n 1 --pretty=oneline --no-decorate`, and `den fetch --prune` for the deletion | wrong (den's surface) |
| (addendum) S0: `git-receive-pack '<path>'` from a console shell | S0 recorded `git-receive-pack 'wolffe-lang/<name>.git'`, then `git-upload-pack '<path>'` for the fetch | right |
| (addendum) `/etc/nsswitch.conf` with `hosts: files dns` is needed for `/etc/hosts` first | probe 5: without the file the C library reads `/etc/hosts` first; none is shipped | wrong, caught by probe 5 before the change |
| K1 is shown red by a plant of its own, the scrub turned off | the plant `edd78435` (one hunk of `console.py`: the scrub replaces nothing), the names way on the same images: K1 `the canary block lacks <scrubbed:name> <scrubbed:token> <scrubbed:key>`, K3 `name=1 token=1 key=1`, every other row green | right |
| den's https clone and push wall times, the resolve time, the images' sizes | (from the records) | |

## 4. Evidence index

(below, from the records)

## 5. Done-when

### 5.1 Rulings

- **R-px104-1, name resolution: (a), ruled.** The kernel answers what the resolver asks: `IP_RECVERR` on a datagram
  socket (kept, read back), `sendmmsg` for AF_INET datagrams, FIONREAD on one, and a receive with `MSG_ERRQUEUE`
  (-EAGAIN). (b) a DNS stub in shared code would answer differently from what `net_connect` dials; (c)
  wolf-lang#831's `net_resolve` would call the same resolver and meet the same two answers; (d) `/etc/hosts` works
  without a kernel change (measured) and stays documented as the fallback.
- **R-px104-2, the root set: (a), ruled.** curl's extract of Mozilla's store, `cacert-2026-10-20.pem`, by name and
  digest (`user/roots.pin`), converted by `tools/mkroots`' own RFC 7468 decoder and held to openssl's bytes, shipped
  as `/etc/ssl/certs/ca-roots.der`, `/etc/shrc` exporting `DEN_TLS_ROOTS`. (b) Ubuntu's ca-certificates, (c) only
  GitHub's chain roots, (d) none shipped.
- **R-px104-3, the secrets' carrier: (A) with (ii), ruled.** An ephemeral 0600 secrets disk in a 0700
  `/dev/shm/px104-<nonce>/`, read-only to QEMU and mounted by the rows' image at `/run/live`; read in the guest by
  redirection only; the serial output scrubbed in memory before any write, proven by the canary row; the carrier
  removed and checked gone, then the scan. The live session builds its remote with pelt's builtin `printf` and runs
  init, fetch, switch, commit and push, so the URL is on no argument vector; `den clone` is proven hermetically.
- **R-px104-4, how den finds burrow: (a), ruled.** `/bin/ssh` is burrow: den runs `ssh` from PATH and reads no
  `GIT_SSH` or `core.sshCommand` at its pin.
- **R-px104-5, the service variables: (a), ruled, amending px100's R-px100-1.** den's two
  wrappers are installed as `/bin/git-upload-pack` and `/bin/git-receive-pack`, and `/etc/shrc` exports neither
  `DEN_UPLOAD_PACK` nor `DEN_RECEIVE_PACK`: den's ssh transport sends those variables' value as the remote command,
  so a console shell asked GitHub to run `/usr/libexec/den/receive-pack`. An upgrade keeps an edited `/etc/shrc`
  with the new one beside it as `.pax-new`; the README names the two lines to delete.
- **R-px104-6, GitHub's host key: (a), ruled.** `/etc/ssh/ssh_known_hosts` with GitHub's published ed25519 line;
  burrow reads known_hosts files only from `~/.ssh`, so the README's `~/.ssh/config` line names it. (c), burrow
  reading `/etc/ssh/ssh_known_hosts` by default, is the orchestrator's burrow issue.
- **R-px104-7, no ls-remote in den: (a), ruled.** The console's witness is `den fetch` of the pushed ref into a
  scratch ref; this host's `git ls-remote` is the outside witness between steps. den's ls-remote is the
  orchestrator's den issue. Measured on the first green boots: den at its pin has no `rev-parse` (`not yet
  implemented: rev-parse`) and refuses a refspec named with a remote (`configured fetch option/refspec`), so the
  scratch ref is the remote-tracking ref den's configured fetch makes, read with `den log -n 1 --pretty=oneline
  --no-decorate` (the whole id and the subject), and the deletion's witness is `den fetch --prune` and that log
  failing. The first rows of H6 and S6 passed for the wrong reason (the fetch was refused, not the ref gone); the
  rows now demand the prune's exit 0.
- **R-px104-8, den's pin: ruled.** `user/den.pin` to `ac2332bf`, mpx5-den's rows moved first, red at `584b18a3`;
  `tests/mpx4-console-net.d/den-https.pin` retired into it.

### 5.2 Issues

None filed or closed by this lane. Filed by the orchestrator from the rulings: burrow reading
`/etc/ssh/ssh_known_hosts` by default (R-px104-6 (c)), den's `ls-remote` (R-px104-7).

### 5.3 Checklist

(below, from the records)
