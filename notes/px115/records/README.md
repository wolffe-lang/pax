# px115 phase 2: the takes' records

Each `take-*.log` is a take's index on the lane host: its START and END lines and every PASS, FAIL and SKIP line
(the full logs stay there). Commits before the rebase onto 483bfabf are named as they were when the take ran.

| record | what | at | verdict |
|---|---|---|---|
| take-u1.log | pax-upgrade's rows P1-P28: red against the stub, then green | 20498a98, then 8050e613 | red by name (P1-P27), then 28 of 28 |
| take-s3.log | tests/mpx6-staged, native, BIOS and UEFI: T3-T5 red before the kernel's letter, then T1-T6 green | f60379e6, then 2b159fa7 | red by name, then green |
| take-l2.log | the leg, S1-S4, BIOS | ffa47874 | 4 of 4 |
| take-l3.log | the leg, S1-S4, UEFI | ffa47874 | 4 of 4 |
| take-plant2.log | the plant (the age refusal taken out): P10 red alone; the head green | 70a3a00e, then 853b15d0 | 27 of 28, then 28 of 28 |
| take-c1.log | after the rebase: ci-plan, ci-budgets, P1-P28, mpx6-staged (both tiers, both firmwares), the leg on BIOS | 48ad82cb | every step 0 |

The leg's serial logs (`*-sN-FW.serial.txt`, and `sNb` for the boot after a power cut or a changed archive) and its
results (`result-FW.json`) are each take's, under the take's name. The final gauntlet at the PR's head, recorded by
the organization's recorder (the distribution build and both firmwares' legs among its steps), is named in the PR.
