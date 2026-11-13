# V4's strip, held to these pairs (`tests/mpx3-screen.d/v4-selftest.sh`)

`same-NAME.a` and `same-NAME.b` must strip alike; `differ-NAME.a` and `differ-NAME.b` must not. The logs are the
release BIOS legs of a hosted release-tier run at `c904f800` (mpx3-screen's V4), normalised as the suite reads
them: the screen boot's (`same-calibration-ci.a`) and the boot with no display device (every other `.a`, and each
`.b` with one change).

| pair | `.b` | why |
|---|---|---|
| same-calibration-ci | the screen boot's log, against the no-display boot's | the screen boot's calibration printed `windows 1 and 2 disagree: 62437425 and 62500543 Hz` and `windows 2 and 3 of 6 agree`, the other boot none; V4 went red on it |
| same-set-aside | `window 1 set aside: … Hz, the clock … us against the PM timer's … us`, then an agreement | a window kernel/timer set aside |
| same-no-agreement | five disagreements and `no two windows in a row agreed in 6; took … Hz` | the calibration's last resort |
| differ-second-counter | `no second counter beside the HPET to hold each window to; …` | the machine's shape, not timing: kept |
| differ-undocumented | `windows 1 and 2 disagree` with no rates | not a form kernel/timer prints: kept |
| differ-clock | `calibrated by PM` for `calibrated by HPET` | which clock the tick was calibrated by |
| differ-line | `utf-8: cafe …` for `utf-8: café …` | any other line of PAX's |
