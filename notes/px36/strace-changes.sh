#!/bin/bash
# px36: strace of bu22's chmod, touch, ln, mkdir -m and cp -p (and ls -l,
# readlink, cat, rm, mv meeting links) on Linux, on a tmpfs, inside a
# throwaway container. Mounted: /bore and /pelt read-only (the binaries),
# /out (where the straces go). Everything the utilities change is under
# /t, a tmpfs of the container.
set -u
cd /t || exit 2
[ "$(stat -f -c %T /t)" = tmpfs ] || { echo "/t is not a tmpfs"; exit 2; }
export PATH=/bore:/pelt HOME=/ TERM=linux TZ=UTC0
/usr/bin/uname -r > /out/uname.txt; /usr/bin/strace -V | /usr/bin/head -n 1 >> /out/uname.txt
/usr/bin/sha256sum /bore/* /pelt/pelt >> /out/uname.txt
/usr/bin/id >> /out/uname.txt
n=0
t() { # name, then the command
    n=$((n + 1)); local name=$(printf '%02d-%s' $n "$1"); shift
    /usr/bin/strace -f -s 128 -o "/out/$name.strace" "$@" > "/out/$name.out" 2>&1 < /dev/null
    echo "rc=$?" >> "/out/$name.out"
    echo "\$ $*" >> "/out/$name.out"
}
/usr/bin/printf 'one\n' > f1; /usr/bin/printf 'two\n' > f2; /usr/bin/printf '#!/x\n' > ex
/usr/bin/mkdir -p tree/a/b tree/c; /usr/bin/printf 'x\n' > tree/a/b/x
t chmod-octal chmod 600 f1
t chmod-sym chmod u+x,g-r f1
t chmod-v chmod -v 644 f1
t chmod-c chmod -c 644 f1
t chmod-R chmod -R 700 tree
t chmod-missing chmod 600 nope
t chmod-suid chmod 4755 ex
t chmod-ref chmod --reference=f2 f1
t touch-new touch new1
t touch-exists touch f1
t touch-t touch -t 202001020304.05 f1
t touch-d touch -d '2020-01-02 03:04:05' f2
t touch-a touch -a -t 199901010000 f1
t touch-m touch -m -t 199901010000 f2
t touch-r touch -r f1 f2
t touch-c touch -c nope
t touch-dir touch tree
t ln-hard ln f1 h1
t ln-hard-exists ln f1 h1
t ln-f ln -f f2 h1
t ln-s ln -s f1 s1
t ln-s-dangling ln -s nowhere s2
t ln-sf ln -sf f2 s2
t ln-s-dir ln -s tree st
t ln-into-dir ln f1 tree
t ln-dir ln tree tl
t ln-v ln -sv f1 s3
t ln-n ln -sfn tree st
t ln-T ln -T f1 h3
t ln-r ln -sr tree/a/b/x xr
t ln-L ln -L s1 h4
t ln-P ln -P s1 h5
t readlink readlink s1 s2 st xr
t readlink-f readlink -f xr
t cat-through cat s1 st/a/b/x xr
t cat-dangling cat s2x
t ls-l ls -l s1 s2 h1 f1 st
t ls-L ls -lL s1
t stat-link stat s1
t stat-L stat -L s1
t mkdir-m mkdir -m 700 m7
t mkdir-m-sym mkdir -m u=rwx,g=rx m8
t mkdir-pm mkdir -p -m 711 p/q/r
t mkdir-m-sticky mkdir -m 1777 m9
t cp-p cp -p f1 g1
t cp-p-dir cp -rp tree tree2
t cp-link cp s1 g2
t cp-P cp -P s1 g3
t cp-rP cp -r st st2
t mv-link mv s1 s1m
t rm-link rm s1m
t rm-hard rm h1
t chmod-h chmod -h 600 s3
t chmod-link chmod 640 s3
t touch-link touch s3
t touch-h touch -h -t 200001010000 s3
t ls-final ls -l
