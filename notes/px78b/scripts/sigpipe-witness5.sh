#!/usr/bin/env bash
# px78b (pax#254): qemu-halt's cnt_addr line as on trunk (awk exits at the match) and as fixed (awk reads to the end,
# the first match kept), under `set -euo pipefail` in a subshell each, N runs, with the given awk first on PATH.
elf=$1 n=$2
for form in trunk fixed; do
  ok=0 dead=0 last=
  for i in $(seq 1 "$n"); do
    if [ $form = trunk ]; then
      ( set -euo pipefail; cnt_addr=$(nm "$elf" | awk '$3 == "pax_serial_log_count" { print "0x" $1; exit }'); [ -n "$cnt_addr" ] ); st=$?
    else
      ( set -euo pipefail; cnt_addr=$(nm "$elf" | awk '$3 == "pax_serial_log_count" && !f { print "0x" $1; f = 1 }'); [ -n "$cnt_addr" ] ); st=$?
    fi
    [ $st = 0 ] && ok=$((ok+1)) || { dead=$((dead+1)); last=$st; }
  done
  echo "$(awk --version 2>/dev/null | head -1 | cut -c1-14)${last:+} form=$form runs=$n survived=$ok died=$dead${last:+ (status $last)}"
done
