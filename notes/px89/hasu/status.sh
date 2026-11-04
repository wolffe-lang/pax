#!/usr/bin/env bash
# px89: each job's exit marker, or run.
for j in "$@"; do printf '%s=%s ' "$j" "$(cat /home/mfwolffe/lanes/px89/logs/$j.exit 2>/dev/null || echo run)"; done; echo
