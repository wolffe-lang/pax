# User-soak deadlines

Only `soak-user` and **`chk-soak` with `PAX_ROOTDISK=1`** use **1200 s**.
Every other session retains 900 s, including memory-root `chk-soak` and
`chk-soak-user`. All four ident/chk soak commands still request **100000
rounds**. `deadline.py` executes the actual selection for ten session classes
with both kinds of root, and checks those counts.

Twenty unchanged rootdisk `chk-soak` sessions under four host CPUs completed
in **456–472 s**, with **0/20 failures**. Each take recorded exactly one real
disk boot and retained the ordinary assertions. U3's memory-tree census
prints its existing named rootdisk skip: a disk cache retains frames.

`ci-durations.tsv` adds eleven completed CI rootdisk observations from run
logs. Each is the interval from the preceding `chk-user` U5 completion to
the `chk-soak` U5 completion, with the rootdisk U3 skip identifying the disk
leg. These approximate session wall times include intervening harness work
and log delivery; they are not guest CPU times. They span several heads.

| sample | minimum | median | maximum |
|---|---:|---:|---:|
| 11 CI disk sessions | 423.142 s | 622.884 s | 860.145 s |
| 20 local disk sessions | 456 s | 460.5 s | 472 s |

The old 900 s bound left **39.855 s** above the observed CI maximum. The new
1200 s bound leaves **339.855 s** (locally, at least 728 s). Issue
[#197](https://github.com/wolffe-lang/pax/issues/197) also records a failed
900 s run; that censored observation is not counted as a successful timing.
The larger bound does not retry a failed permission assertion or shorten
the soak. Post-change local sessions are recorded separately from this
before distribution.
