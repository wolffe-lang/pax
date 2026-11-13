# T2's mask, held to these pairs (`tests/mpx6-triage.d/selftest.sh`)

`same-NAME.a` and `same-NAME.b` must mask alike; `differ-NAME.a` and `differ-NAME.b` must not. Every `.a` is the
plain UEFI leg's serial log of a hosted run of the full matrix at `c904f800` (mpx6-firmware's F10), and every `.b`
is that log with one change, but for `same-probe-ci`, whose `.b` is the same run's triage leg.

| pair | `.b` | why |
|---|---|---|
| same-probe-ci | the triage leg's log | the two boots differ only by the probe's way: the plain boot's framebuffer read measured 67,007 cycles (4.8 x its write, so `redraw`), the triage boot's 15,141 (1.1 x, so `copy`); T2 went red on it |
| same-calibration | `windows 1 and 2 disagree: … Hz` and `windows 2 and 3 of 6 agree` before the calibrated line | kernel/timer's calibration printing a disagreement and its agreement, as the hosted release run's screen boot did |
| same-set-aside | `window 1 set aside: … Hz, the clock … us against the PM timer's … us`, then an agreement | a window kernel/timer set aside |
| same-no-agreement | five disagreements and `no two windows in a row agreed in 6; took … Hz` | the calibration's last resort |
| differ-second-counter | `no second counter beside the HPET to hold each window to; …` | the machine's shape, not timing: kept |
| differ-undocumented | `windows 1 and 2 disagree` with no rates | not a form kernel/timer prints: kept |
| differ-clock | `calibrated by PM` for `calibrated by HPET` | which clock the tick was calibrated by |
| differ-forced | `by redraw (fbwrite)` and `by copy (fbread)` | a way a command-line word forced |
| differ-probe-or-forced | the probe's way against `by redraw (fbwrite)` | a forced way is never the probe's |
| differ-line | `nothing left to start` | any other line of PAX's |
