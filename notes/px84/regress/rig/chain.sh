#!/usr/bin/env bash
L=/mnt/steamlib/lanes/px84
echo $$ > $L/runs/chain.pid
echo "chain start $(date -Is) head $(git -C $L/pax rev-parse HEAD)"
for j in "$@"; do
  bash $L/px84-job.sh $j bash $L/scripts/$j.sh || true
  echo "$j exit=$(cat $L/runs/$j.exit 2>/dev/null) $(date -Is)"
done
echo "CHAIN-DONE $(date -Is)"
