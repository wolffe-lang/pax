#!/bin/bash
# px41: every mpx4-lobo and mpx3-speaker job log of pax CI since px25 (2026-10-12), latest attempt.
cd ~/lanes/px41/ci
awk -F'\t' '$5 >= "2026-10-12T00:00:00Z" {print $1}' runs.tsv | while read -r id; do
  gh api "repos/wolffe-lang/pax/actions/runs/$id/jobs?per_page=100" -q '.jobs[]|select(.name|test("mpx4-lobo|mpx3-speaker"))|select(.conclusion=="success" or .conclusion=="failure")|[.id,.name,.conclusion]|@tsv' 2>/dev/null | while IFS=$'\t' read -r jid name concl; do
    f=harvest/$id-$jid-${name%% *}-$concl.log
    [ -s "$f" ] || gh run view "$id" -R wolffe-lang/pax --job "$jid" --log > "$f" 2>/dev/null
    echo "$id $jid $name $concl $(wc -c < "$f")"
  done
done
echo HARVEST-DONE
