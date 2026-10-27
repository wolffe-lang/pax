# Linux replay timing

F0's Linux reference has a **30 s per-prompt bound**, followed by a separate
30 s process-exit bound in `tools/linux-tty`. The entire replay contains
multiple commands and deliberate 20 ms byte spacing, so its elapsed time
must not be compared directly with one prompt's deadline.

The #196 timeout says "prompt 24" because the driver waits **before** typing
step 24. The command actually running is the preceding eight-background-
`true` loop followed by `wait`. It produces neither its completion marker
nor another prompt. Timeout snapshots show the shell's remaining task in
`futex_do_wait` with one unreaped zombie child; the pty reader is active.
The shell/runtime problem is tracked in [pelt#98](https://github.com/wolffe-lang/pelt/issues/98).
The row is unchanged and [pax#196](https://github.com/wolffe-lang/pax/issues/196)
stays open.

| four-CPU Linux shapes replay, root and pax per take | terminal failures / takes | elapsed |
|---|---:|---:|
| original baseline | 9 / 20 | green 62–65 s; red 88–121 s |
| separate timeout-instrumented replication | 3 / 20 | green 63–65 s; red 89–121 s |
| issue-scoped one-retry bridge | 0 / 20 | 63–65 s first-pass; recoveries 154 and 184 s |

Bridge takes 6 and 13 recovered on the second attempt. This is **not** a
claim that the shell race is fixed, or that every future retry will recover.
A second failure remains red. There is no completion-time margin for a
hung command; raising the prompt deadline would only delay that failure.

CI builds once, runs the Linux leg through `tools/ci-retry`, then boots PAX
once. Only exit 1 with both the known prompt-24 diagnostic and F0 failure
signature is eligible. Build/tool failures and unrelated failures are not
retried. The warning names `pax#196`. `build/ci-attempts/mpx5-pelt-linux/`
retains attempt 1's log, exit status and raw transcript snapshot, with hashes;
removing or changing them during attempt 2 is itself a failure. The workflow
uploads them even when both attempts fail. Remove the #196 entry when the
upstream fix is pinned and this row is verified without retry.
