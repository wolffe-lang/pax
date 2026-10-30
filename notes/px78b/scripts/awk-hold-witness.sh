#!/usr/bin/env bash
# px78b (pax#254): does awk act on a matching record at once, or hold it until more input? A writer prints the match,
# waits 2 s, prints one more line; the reader prints and exits at the match. Under pipefail the pipeline's status is
# the writer's: 141 when its second line meets a closed pipe.
set -o pipefail
for a in mawk "$1"; do
  t0=$(date +%s%N)
  out=$( (printf 'a b match\n'; sleep 2; printf 'tail\n') | $a '$3 == "match" { print "hit"; exit }'); st=$?
  t1=$(date +%s%N)
  echo "$($a --version 2>/dev/null | head -1 | cut -c1-14 || true)$($a -W version 2>/dev/null | head -1 | cut -c1-16): status=$st out=$out ms=$(( (t1 - t0) / 1000000 ))"
done
