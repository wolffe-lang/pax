#!/usr/bin/env bash
# px87 (on the Mac): copy the lane's kasumi scripts into kasumi's bin/ by rename, never in place
# (a running bash reads its script as it goes: an in-place overwrite changes what a waiting job runs).
set -euo pipefail
cd "$(dirname "$0")"
ssh kasumi mkdir -p /home/mfwolffe/lanes/px87/bin/.in
scp -q ./*.sh kasumi:/home/mfwolffe/lanes/px87/bin/.in/
ssh kasumi bash -s <<'EOF'
cd /home/mfwolffe/lanes/px87/bin
for f in .in/*.sh; do chmod +x "$f"; mv -f "$f" "${f#.in/}"; done
ls
EOF
