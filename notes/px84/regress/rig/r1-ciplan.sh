set -euo pipefail
git log -1 --format='head %H' 2>/dev/null || true
tests/ci-plan
