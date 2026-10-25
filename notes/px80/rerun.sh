#!/usr/bin/env bash
# px80: the rerun after the batch: m2-linux (the real zstd/zlib objects), then mkw (lupin fetched).
L=$HOME/lanes/px80
printf '%s\n' $$ > $L/rerun.pid
t0=$(date +%s); flock $HOME/lanes/kasumi-cores-0-3.lock bash $L/pax/notes/px80/m2-linux.sh > $L/logs/m2-linux.log 2>&1; echo "m2-linux rc=$? $(( $(date +%s) - t0 ))s $(date -Is)"
t0=$(date +%s); bash $L/pax/notes/px80/batch.sh b2 mkw; echo "batch b2 rc=$? $(( $(date +%s) - t0 ))s $(date -Is)"; cat $L/runs/b2.out
echo 0 > $L/rerun.exit
