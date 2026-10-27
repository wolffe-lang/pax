# Interrupt-suite timing

The CI job has a **75-minute bound**. Its largest completed job across 21
runner observations was 2885 s (48 min 5 s), leaving **1615 s** of margin.
Every kernel, assertion and requested compiler/firmware leg remains intact;
individual boot bounds are unchanged.

The observations, censored-job rules, workflow wall times and concurrency
limits are documented in [CI budgets](../ci-budgets.d/README.md).
`tests/ci-budgets.py` checks the workflow envelope against the retained
measurement data. These are runner job timings, not local boot-loop timings;
the final all-tier run validates the new envelope.
