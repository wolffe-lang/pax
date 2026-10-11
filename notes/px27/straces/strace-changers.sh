#!/bin/bash
# px27: strace of bu21's file changers and pelt's redirections on Linux,
# on a tmpfs, inside a throwaway container. Mounted from the host: /bore
# and /pelt read-only (the binaries), /out (where the straces go).
# Everything the utilities change is under /t, a tmpfs of the container.
set -u
cd /t || exit 2
[ "$(stat -f -c %T /t)" = tmpfs ] || { echo "/t is not a tmpfs"; exit 2; }
export PATH=/bore:/pelt HOME=/ TERM=linux TZ=UTC0
uname -r > /out/uname.txt; /usr/bin/strace -V | /usr/bin/head -n 1 >> /out/uname.txt
/usr/bin/sha256sum /bore/* /pelt/pelt >> /out/uname.txt
n=0
t() { # name, then the command
    n=$((n + 1)); local name=$(printf '%02d-%s' $n "$1"); shift
    /usr/bin/strace -f -s 128 -o "/out/$name.strace" "$@" > "/out/$name.out" 2>&1 < /dev/null
    echo "rc=$?" >> "/out/$name.out"
    echo "\$ $*" >> "/out/$name.out"
}
/usr/bin/printf 'one\n' > f1; /usr/bin/printf 'two\n' > f2
/usr/bin/mkdir -p tree/a/b tree/c; /usr/bin/printf 'x\n' > tree/a/b/x; /usr/bin/printf 'y\n' > tree/c/y; /usr/bin/printf 'z\n' > tree/z
t mkdir-one mkdir d
t mkdir-exists mkdir d
t mkdir-p mkdir -p p/q/r
t mkdir-p-again mkdir -p p/q/r
t mkdir-v mkdir -v v1 v2
t mkdir-m mkdir -m 700 m7
t mkdir-noparent mkdir no/such/dir
t mkdir-under-file mkdir f1/sub
t rmdir-one rmdir d
t rmdir-missing rmdir d
t rmdir-p rmdir -p p/q/r
t rmdir-nonempty rmdir tree
t rmdir-file rmdir f1
t cp-file cp f1 g1
t cp-over cp f2 g1
t cp-into-dir cp f1 tree/c
t cp-r cp -r tree tree2
t cp-r-into cp -r tree tree2
t cp-dir-no-r cp tree tree3
t cp-missing cp nope g2
t cp-same cp f1 f1
/usr/bin/head -c 16777216 /dev/urandom > big
t cp-big cp big big2
/usr/bin/cmp big big2 && echo same >> /out/$(printf '%02d' $n)-cp-big.out
t cp-p cp -p f1 gp
t cp-a cp -a tree tree4
t mv-file mv g1 g3
t mv-over mv f2 g3
t mv-into-dir mv g3 tree/a
t mv-dir mv tree2 tree5
t mv-dir-into-self mv tree5 tree5/sub
t mv-dir-over-nonempty mv tree4 tree5
t mv-missing mv nope g4
t mv-n mv -n f1 big2
t mv-xdev mv big2 /dev/shm/px27-big2
t mv-xdev-dir mv tree5 /dev/shm/px27-tree5
t mv-f-to-dirslash mv f1 nodir/
t rm-file rm big
t rm-missing rm nope
t rm-f-missing rm -f nope
t rm-dir rm tree
t rm-d-empty rm -d m7
t rm-r rm -r tree
t rm-rf-root rm -rf /
t rm-r-root-spelled rm -r //. /..
t rm-rf-dot rm -rf .
/usr/bin/mkdir -p s/a s/b; /usr/bin/printf '1\n' > s/a/1
t ls-l ls -l s s/a
t ls-la ls -la s
t stat stat s/a/1 s
t pelt-redirect pelt -c 'echo hi > r1; echo more >> r1; cat r1; cat < r1 > r2; cat r1 r2 >> r1x; echo n >| r1; : > r2; cat < nope; echo x > s; echo y > s/a/../q; cat s/q'
t pelt-heredoc pelt -c 'cat > h1 <<E
a line
E
cat h1; cat < h1 >> h2; cat h2; exec 3> h3; echo to3 >&3; exec 3>&-; cat h3; echo both > o1 2>&1; cat <> rw1; ls'
t pelt-cd-rm pelt -c 'mkdir w; cd w; rmdir ../w; pwd; ls; echo x > f; cd ..; pwd'
/usr/bin/ls -laR /t > /out/final-tree.txt 2>&1
/usr/bin/ls -la /dev/shm >> /out/final-tree.txt 2>&1
echo done
