# SigIgn ordering

J4's `masks` child is started while its parent ignores SIGSEGV. POSIX
`exec` preserves ignored dispositions, but the new runtime may install a
handler with `sigaction`. A read inside a wolf program is not a read at
exec entry. The previous requirement that PAX always show `0400` therefore
selected one runtime-initialization interleaving.

The probe joins a runtime task, emits `~X: runtime task joined`, then reads
its status. `sigign.py` requires that event before exactly one zero-mask
row, on PAX and the fresh Linux reference. No delay is used as a substitute
for the join. Missing, duplicate, reversed or nonzero rows fail.

The existing stack-overflow witness remains checked. Its PC must be inside
the current executable's `_Wdeep$…` function. Only that address is normalized
for comparison with the historical recording, since rebuilding the probe
moves code. An arbitrary PC, absent symbol or duplicate PC fails.

| release BIOS, four host CPUs, both identities per boot | failed / runs | whole-take elapsed |
|---|---:|---:|
| unchanged probe | 0 / 20 | 7–8 s |
| ordered probe, before correcting old absolute-PC comparison | 20 / 20 | 7–8 s |
| ordered probe and current-ELF PC check | 0 / 20 | 7–8 s |

The middle row failed the address comparison, **not** the ordering assertion.
The local baseline did not reproduce #174; CI runs 40258323326 attempt 1
and 40394044200 did. The boot bound remains **900 s**; the observed whole-take
maximum leaves at least **892 s**. These are targeted `sigs` boots, not
claims about the duration of the complete jobs suite.

References: POSIX.1-2024 [exec, DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html)
and [sigaction, DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/functions/sigaction.html).
