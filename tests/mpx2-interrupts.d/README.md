# Interrupt-suite timing

`timer-tail.py` checks I5's final transcript: the APIC report, only the
calibration diagnostics documented by `kernel/timer`, then a successful
calibration, exactly 20 ticks with zero spurious interrupts, and halt. Unknown
or misplaced diagnostics and missing recovery remain failures. The suite's
separate monitor proof of halt is unchanged.

`python3 -I tests/mpx2-interrupts.d/selftest` replays the saved release BIOS
transcript from nightly run 43898510787 (`498e3e8a`), kept as
`timer-retry.serial` with only CRLF changed to LF. It also replays CRLF and
refusal cases. The fixture's retry lines used to make an otherwise successful
20-tick boot fail the strict four-line tail comparison.

The CI job has a **75-minute bound**. Its largest completed job across 21
runner observations was 2885 s (48 min 5 s), leaving **1615 s** of margin.
Every kernel, assertion and requested compiler/firmware leg remains intact;
individual boot bounds are unchanged.

The observations, censored-job rules, workflow wall times and concurrency
limits are documented in [CI budgets](../ci-budgets.d/README.md).
`tests/ci-budgets.py` checks the workflow envelope against the retained
measurement data. These are runner job timings, not local boot-loop timings;
the final all-tier run validates the new envelope.
