"""Hold the job envelope to the measured all-tier runtime distribution."""
from pathlib import Path
import re

here = Path(__file__).resolve().parent
rows = [line.split('\t') for line in (here / 'ci-durations.tsv').read_text().splitlines()[1:]]
assert len(rows) == 20 and len({r[0] for r in rows}) == 20
peak = max(int(seconds) for _, seconds in rows)
workflow = (here.parents[1] / '.github/workflows/ci.yml').read_text()
job = workflow.split('  mpx2-heap:\n', 1)[1].split('\n  mpx3-user:', 1)[0]
bound = int(re.search(r'^    timeout-minutes: (\d+)$', job, re.M)[1]) * 60
assert bound >= peak * 1.5, 'heap CI budget: less than 50% headroom above measured peak'
print('PASS heap CI budget: %d s bound, %d s peak, %d s margin' % (bound, peak, bound - peak))
