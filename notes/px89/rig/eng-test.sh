#!/usr/bin/env bash
# px89: the container engine inside a lane container (ctr2.sh ENGINE=1),
# once: the remote client answers, and one throwaway container runs.
#   eng-test.sh BLOCK   (launch.sh runs it)
set -uo pipefail
S=/home/mfwolffe/lanes/px89/scripts
CTR_WD=/home/mfwolffe/lanes/px89 bash "$S/ctr2.sh" "$1" eng localhost/px89-dhcp:1 ENGINE=1 -- \
    bash -c '"$PAX_ENGINE" version --format "{{.Client.Version}} {{.Server.Version}}" && "$PAX_ENGINE" run --rm localhost/px75-ubuntu:2 sh -c "echo inside; nproc" && echo ENGINE-OK'
