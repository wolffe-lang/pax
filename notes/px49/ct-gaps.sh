#!/bin/bash
# px49 on kasumi: gaps as 1000:1000 in a throwaway container (tools/linux-tree), the suite's way.
#   ct-gaps.sh OUTDIR
L=$HOME/lanes/px49
O=$1; P=$L/pax
mkdir -p $O/groot/bin $O/groot/etc $O/groot/g
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cd $P && tools/mkjobs $L/bin && tools/mkas $L/bin" || exit 1
cp $L/bin/gaps $L/bin/as $O/groot/bin/
printf 'B: the sendfile reached the terminal\n' > $O/sf
for f in r644 r600 sf; do cp $O/sf $O/groot/g/$f; done
printf '%s\n' '/g 1777 0 0' '/g/r644 644 0 0' '/g/r600 600 0 0' '/g/sf 644 0 0' > $O/gaps.owners
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
$P/tools/linux-tree --root $O/groot --keys $P/user/console/gaps.keys --prompt '$ ' --argv0 /bin/as --size 256m --rdev --nsproc \
    --owners $O/gaps.owners $O/gaps-user.tty -- /bin/as 1000 1000 /bin/gaps
echo "rc $?"; tr -d '\r' < $O/gaps-user.tty
