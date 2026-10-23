#!/bin/bash
# px64, kasumi: the Linux-side prerequisite (contract item 5): scent's own
# full byte suite (tools/pax-posture: plain ubuntu:24.04, no LANG, no
# locale data) against the binary pax's tools/mkscent built, with the
# GNU 3.12 oracle built from its signature-verified tarball by scent's
# own tools/fetch-oracle (black box: built, never read). CPUs 12-15.
set -u
L=$HOME/lanes/px64
S=$L/scent
printf '%s\n' $$ > "$L/posture.pid"
uptime
if [ ! -d "$S/.git" ]; then
    git clone -q https://github.com/wolffe-lang/scent "$S" && git -C "$S" checkout -q --detach b6f63a4892cca631475cd0b87a0b648ce9b532a9
fi
echo "scent HEAD $(git -C "$S" rev-parse HEAD)"
export SCENT_IMAGE=localhost/px64-scent-oracle SCENT_CONTAINER_ARGS="--cpuset-cpus 12-15 --ulimit core=0:0"
cd "$S"
tools/fetch-oracle > "$L/fetch-oracle.log" 2>&1; echo "fetch-oracle rc=$?"; tail -3 "$L/fetch-oracle.log"
mkdir -p target/mkscent
cp "$L/scent-out/scent" target/mkscent/scent
sha256sum target/mkscent/scent
tools/pax-posture > "$L/posture.log" 2>&1; echo "pax-posture rc=$?"
grep -v '^agree ' "$L/posture.log" | tail -25
echo "posture.sh done $(date -Is)"
