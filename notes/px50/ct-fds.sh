#!/bin/bash
# px50 on kasumi: fdtab as 1000:1000 in a throwaway container (tools/linux-tree), the suite's way.
#   ct-fds.sh OUTDIR
L=$HOME/lanes/px50
O=$1; P=$L/pax
mkdir -p $O/froot/bin $O/froot/etc $O/froot/g
cp $L/bin/fdtab $L/bin/as $O/froot/bin/
printf 'root file\n' > $O/froot/g/r644
printf '%s\n' '/g 1777 0 0' '/g/r644 644 0 0' > $O/fds.owners
: > $O/fds.keys
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu PAX_BUILD=$O/build
$P/tools/linux-tree --root $O/froot --keys $O/fds.keys --prompt '$ ' --argv0 /bin/as --size 256m --rdev --nsproc --sys \
    --owners $O/fds.owners $O/fds-user.tty -- /bin/as 1000 1000 /bin/fdtab
echo "rc $?"
