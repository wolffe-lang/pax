#!/usr/bin/env bash
# sh20's exact black-box environment, with /usr read-only. No source
# from dash, coreutils, libc or the kernel is inspected or built.
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/dash-side.pid"
ulimit -c 0
uptime
podman image exists docker.io/library/archlinux:base-devel || { echo 'missing existing sh20 oracle image'; exit 2; }
mkdir -p "$L/pelt-tools" "$L/dash-side/tmp" "$L/dash-side/home"
tar -xf "$L/pelt-tools.tar" -C "$L/pelt-tools"
podman run --rm --network none --userns=keep-id -u "$(id -u):$(id -g)" --init --pids-limit 4096 \
    --cpuset-cpus 8-11 --ulimit core=0:0 -v /usr:/usr:ro -v /var/lib/pacman:/var/lib/pacman:ro \
    -v "$L:$L" -e L="$L" -e TMPDIR="$L/dash-side/tmp" -e HOME="$L/dash-side/home" \
    docker.io/library/archlinux:base-devel bash -c '
set -euo pipefail
O=$L/dash-side
pacman -Q dash bash coreutils > "$O/versions.txt"
cat "$O/versions.txt"
for program in pelt dash; do
  shell=$L/bin/pelt-1/pelt; [ "$program" != dash ] || shell=/usr/bin/dash
  for name in shapes childstate corners notice notice2 notice3 notice4 notice5 trapwait; do
    mkdir -p "$O/$program-$name"
    cd "$O/$program-$name"
    script=$L/pelt-tools/notes/sh20-evidence/probe/$name.sh
    rc=0
    case $name in notice*|trapwait) bash "$script" "$shell" > "$O/$program-$name.out" 2>&1 || rc=$? ;;
      *) "$shell" "$script" > "$O/$program-$name.out" 2>&1 || rc=$? ;; esac
    echo "$program $name status $rc"
  done
done
for name in notice notice2 notice3 notice4 notice5; do
  echo "== $name"
  python3 -I "$L/pelt-tools/notes/sh20-evidence/probe/notice-cmp.py" "$O/pelt-$name.out" "$O/dash-$name.out"
done
only=fork-substitution,fork-subshell,fork-background-group,fork-background-subshell,fork-stage,script-fork-substitution,typed-fork-subshell,fork-redirected-subshell,background-builtin-wait,background-nowait,substitution-pipeline
for program in pelt dash; do
  shell=$L/bin/pelt-1/pelt; [ "$program" != dash ] || shell=/usr/bin/dash
  echo "== original shape-rss defaults $program"
  python3 -I "$L/pelt-tools/tools/shape-rss" --only "$only" "$shell" > "$O/$program-shape-rss.out" 2>&1
  cat "$O/$program-shape-rss.out"
done
'
uptime
echo 'dash-side probes and original RSS rows: PASS'
