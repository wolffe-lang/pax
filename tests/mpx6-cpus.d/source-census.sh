#!/usr/bin/env bash
# Gate data must cover the current source sites, not a stale inventory.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
cd "$root"
: "${PAX_BUILD:?}"
export TMPDIR=${TMPDIR:-$PAX_BUILD/cpu-tmp}
mkdir -p "$PAX_BUILD" "$TMPDIR"
python3 -I tests/mpx6-cpus.d/census-selftest.py
python3 -I tests/mpx6-cpus.d/census.py . --check tests/mpx6-cpus.d/inventory.json
python3 -I tests/mpx6-cpus.d/protections.py tests/mpx6-cpus.d/inventory.json > "$PAX_BUILD/cpu-protections.json"
cmp tests/mpx6-cpus.d/protections.json "$PAX_BUILD/cpu-protections.json"
printf 'PASS CPU-PROTECTIONS every explicit exclusion site classified\n'
