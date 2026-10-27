# Heap timing

The CI job has a **90-minute bound**. It still builds all six kernels on
each requested compiler tier and boots every requested firmware. Individual
QEMU boots retain their 240-second bound. No assertion or iteration count
is reduced.

`ci-durations.tsv` records 20 completed all-tier jobs: 19 trunk pushes and
schedule run 40326263858. The observations span several commits, so they
are a job-envelope sample, not a controlled compiler benchmark. Times come
from the job's `startedAt` and `completedAt` fields in GitHub's run API.
They include setup, building, boots and artifact upload.

| statistic | elapsed |
|---|---:|
| minimum | 23 min 1 s |
| median | 49 min 47 s |
| maximum | 55 min 36 s |
| old 60-minute bound minus maximum | 4 min 24 s |
| new 90-minute bound minus maximum | 34 min 24 s |

The seven most recent push samples range from 49.27 to 55.60 minutes.
Issue [#212](https://github.com/wolffe-lang/pax/issues/212) separately
records a job cancelled at 60 minutes, with unchanged ELF hashes and
release builds taking 9–11 minutes apiece instead of about 7.5. A cancelled
sample is censored, not a successful 60-minute completion. The new bound
leaves room for that observed compilation slowdown without shortening the
suite or retrying a timed-out job.

`budget.py` checks that the workflow retains at least 50% headroom above
the observed completed-job maximum. These are **before-change CI
measurements**; neither that calculation nor a local warm-image boot loop
is a claim of 20 post-change CI job runs.
