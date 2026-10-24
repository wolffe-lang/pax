#!/bin/bash
# px65, kasumi: the kernel's cost of the pin. Every kernel (kernel/kmain*.lu)
# built from trunk (PX65_BASE: 68807993 before the rebase, f0617320 after
# it; wolf 0.2.34) and from the branch (0.2.35),
# the same kernel source but the tour's one line, in the lane's container
# on CPUs 12-15, four builds at a time; `size -A`'s .text, .rodata, .data
# and .bss, and the ELF's digest.
#   cost.sh TIERS [KERNEL...]   (TIERS: native, release or both)
# The container is named px65-cost, so it is stopped by that name only.
L=$HOME/lanes/px65; X=${PX65_TREE:-$L/pax}
tiers=$1; shift
case $tiers in both) tiers="native release" ;; esac
ks=${*:-$(cd "$X/kernel" && ls kmain*.lu | sed 's/\.lu$//')}
B=${PX65_BASE:-f0617320}; T=$L/trunk-$B
[ -d "$T/kernel" ] || { mkdir -p "$T" && git -C "$X" archive "$B" | tar -x -C "$T"; }
mkdir -p "$L/build/cost" "$L/cache" "$L/tmp"
podman run --rm --name px65-cost --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp \
    -e L="$L" -e X="$X" -e T="$T" -e KS="$ks" -e TIERS="$tiers" localhost/px65-ubuntu bash -c '
one() { # side kernel tier
  t=$1 k=$2 tier=$3
  d=$T; [ $t = branch ] && d=$X
  cd $d && export PAX_WOLF=$(tools/fetch-wolf 2>/dev/null | tail -n 1)
  flag=; [ $tier = release ] && flag=--release
  o=$L/build/cost/$t-$k-$tier; rm -rf $o; mkdir -p $o
  s=$(date +%s)
  if tools/build-kernel $flag --src kernel/$k.lu $o > $o.log 2>&1; then
    e=$o/$k.elf
    printf "COST %s %s %s %s %ss" $t $k $tier $(sha256sum < $e | cut -c1-16) $(( $(date +%s) - s ))
    size -A $e | awk "/^\\.(text|rodata|data|bss) / { printf \" %s=%s\", \$1, \$2 }"; echo
  else
    echo "COST $t $k $tier BUILD-FAILED $(tail -n 3 $o.log | tr "\n" " ")"
  fi
}
export -f one
for t in trunk branch; do
  d=$T; [ $t = branch ] && d=$X
  (cd $d && w=$(tools/fetch-wolf | tail -n 1) && echo "$t: $($w --version | head -n 1)")
done
for t in trunk branch; do for k in $KS; do for tier in $TIERS; do echo "$t $k $tier"; done; done; done |
  xargs -P 4 -L 1 bash -c "one \$0 \$1 \$2"
'
