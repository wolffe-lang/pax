#!/usr/bin/env bash
# px78b (pax#254): for each kernel ELF, where qemu-halt's two lookups fall in nm's output (4096-byte writes), and
# the status of qemu-halt's unguarded line under pipefail, 100 runs with mawk and with gawk.
set -uo pipefail
GAWK=$1; shift
for elf in "$@"; do
  total=$(nm "$elf" | wc -c)
  for s in pax_serial_log pax_serial_log_count; do
    end=$(nm "$elf" | awk -v s="$s" '{ n += length($0) + 1 } $3 == s { print n; exit }' 2>/dev/null || true)
    echo "$(basename $(dirname $elf))/$(basename $elf) $s: line ends at byte $end of $total; nm write $(( (end - 1) / 4096 + 1 )) of $(( (total - 1) / 4096 + 1 ))"
  done
  for a in mawk "$GAWK"; do
    ok=0 bad=0
    for i in $(seq 1 100); do cnt_addr=$(nm "$elf" | $a '$3 == "pax_serial_log_count" { print "0x" $1; exit }'); st=$?; [ $st = 0 ] && ok=$((ok+1)) || bad=$((bad+1)); done
    echo "   $(basename $a): status 0 x$ok, status 141 or other x$bad"
  done
done
