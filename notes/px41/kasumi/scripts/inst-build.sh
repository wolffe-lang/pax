#!/bin/bash
# px41 on kasumi: a scratch kernel (trunk's tree with st/inst/files.lu: the open-file table printed at
# every open of a /proc file), release and native, and lobo images from t-trunk's initramfs. Never committed.
set -u
L=~/lanes/px41; T=$L/t-inst
rm -rf $T; mkdir -p $T && cd $L/pax && git archive 7d2e9ba | tar -x -C $T || exit 2
cp $L/st/inst/files.lu $T/kernel/files/files.lu
cd $T; export PAX_CACHE=$L/cache TMPDIR=$L/tmp CARGO_INCREMENTAL=0
export PAX_WOLF=$(tools/fetch-wolf) || exit 2
tools/fetch-limine || exit 2
for tier in release native; do
  fl=(); [ $tier = release ] && fl=(--release)
  mkdir -p build/mpx4-lobo/$tier
  elf=$(taskset -c 0-7 tools/build-kernel ${fl[@]+"${fl[@]}"} --src kernel/kmain_session.lu build/mpx4-lobo/$tier 2> build/mpx4-lobo/$tier/build.log) || { echo "$tier build failed"; tail -20 build/mpx4-lobo/$tier/build.log; continue; }
  tools/mkimage --conf boot/limine-initramfs-quiet.conf --add $L/t-trunk/build/mpx4-lobo/lobo-trunk.cpio initramfs.cpio "$elf" build/mpx4-lobo/$tier/lobo-trunk.iso > /dev/null && echo "$tier ok $(sha256sum < build/mpx4-lobo/$tier/lobo-trunk.iso | cut -c1-12)"
done
ln -s $L/t-trunk/build/mpx4-lobo/data build/mpx4-lobo/data
echo done
