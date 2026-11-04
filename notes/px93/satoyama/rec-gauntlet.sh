#!/usr/bin/env bash
# px93: the final head's take as tools/gauntlet-record.sh records it, run from a clean checkout at the head
# (green) or on the plant branch (plant), under both satoyama locks the caller holds for the whole take:
#   flock -w 21600 satoyama-A.lock flock -w 21600 satoyama-B.lock \
#     bash gauntlet-record.sh --output REC -- bash notes/px93/satoyama/rec-gauntlet.sh green
#   ... --output PREC --base HEAD_SHA --plant U3d-upgrade: -- bash notes/px93/satoyama/rec-gauntlet.sh plant
# Each step is one of job.sh's chunks (PX93_HELD=1: no lock of its own). Its output reaches the record
# two spaces in, the serial masked, but for `FAIL ` lines, at column 0 (the plant's evidence); only
# gauntlet_step's START and END lines are the record's own. The take stops at the first red step.
set -uo pipefail
L=/home/mfwolffe/lanes/px93
. "$L/gauntlet-record.sh"
SHA=$(git rev-parse HEAD)
export PX93_HELD=1
SERIAL=$(sed -n 's/^model=Samsung SSD 860 serial=//p' "$L/allow-line")
[ -n "$SERIAL" ] || exit 3
col0() { "$@" 2>&1 | sed -u -e "s/$SERIAL/<kasumi-serial>/g" -e '/^FAIL /!s/^/  /'; return "${PIPESTATUS[0]}"; }
case ${1:-} in
  green)
    for c in stick gauntlet-1 gauntlet-2 gauntlet-3; do
      gauntlet_step "$c" col0 bash notes/px93/satoyama/job.sh "$c" "$SHA" || exit $?
    done
    ;;
  plant)
    # The plant's stick and section d to the upgrade: FAIL U3d-upgrade by name.
    export ROWS=U1d,U2d,U3d
    gauntlet_step plant col0 bash notes/px93/satoyama/job.sh stick "$SHA" || exit $?
    ;;
  *) exit 2 ;;
esac
