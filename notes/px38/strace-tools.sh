#!/bin/bash
# px38: strace of the distribution's own identity tools on Linux, inside
# a throwaway container (item 2(e)): id, whoami, groups, ls -l, stat,
# chown, chgrp, su, login, passwd, sg. Black box: the binaries are
# Ubuntu 24.04's (GNU coreutils, util-linux's su, shadow's login and
# passwd, PAM), run and traced, never read. The accounts made here
# (alice 1000, bob 1001, group pack 2000) exist only in this container
# and go with it. /out gets NN-name.strace and NN-name.out.
set -u
cd /t || exit 2
export PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root TERM=linux TZ=UTC0 LC_ALL=C
{
    uname -srm; strace -V | head -n 1
    dpkg-query -W -f '${Package} ${Version}\n' coreutils util-linux login passwd libpam-modules libpam-runtime libc6 2>/dev/null
    id
    echo "CapEff $(sed -n 's/^CapEff:\t//p' /proc/self/status)"
    tr -s ' ' < /proc/self/uid_map
} > /out/uname.txt 2>&1
userdel -r ubuntu 2>/dev/null # the image's own uid 1000
groupadd -g 2000 pack
useradd -m -u 1000 -s /bin/bash alice
useradd -m -u 1001 -s /bin/bash bob
usermod -aG pack alice
echo 'alice:wolf-pw-1' | chpasswd
echo 'root:root-pw-1' | chpasswd
{
    echo "== /etc/passwd (the lines used)"; grep -E '^(root|alice|bob):' /etc/passwd
    echo "== /etc/group (the lines used)"; grep -E '^(root|alice|bob|pack):' /etc/group
    echo "== /etc/shadow (the hash cut to its method and parameters)"
    grep -E '^(root|alice|bob):' /etc/shadow | sed -E 's/^([^:]*):(\$[^$]*\$[^$]*\$)[^:]*:/\1:\2<salt and hash cut>:/'
    echo "== modes"; stat -c '%a %U:%G %n' /etc/passwd /etc/group /etc/shadow /etc/gshadow /usr/bin/su /usr/bin/passwd /usr/bin/newgrp /usr/bin/login /usr/sbin/unix_chkpwd /usr/bin/chsh /usr/bin/chfn /usr/bin/gpasswd /usr/bin/mount 2>&1
    echo "== ENCRYPT_METHOD"; grep -E '^(ENCRYPT_METHOD|YESCRYPT_COST_FACTOR|SHA_CRYPT|UMASK|UID_MIN|GID_MIN|SYS_UID)' /etc/login.defs
    echo "== pam.d"; ls /etc/pam.d
} > /out/accounts.txt 2>&1
n=0
t() { # name, then the command; standard input is the function's
    n=$((n + 1)); local name; name=$(printf '%02d-%s' $n "$1"); shift
    strace -f -s 160 -o "/out/$name.strace" "$@" > "/out/$name.out" 2>&1
    echo "rc=$?" >> "/out/$name.out"
    echo "\$ $*" >> "/out/$name.out"
}
ta() { # the same, the command run as alice (strace -u: set-ID programs keep their meaning)
    n=$((n + 1)); local name; name=$(printf '%02d-%s' $n "$1"); shift
    strace -f -s 160 -u alice -o "/out/$name.strace" "$@" > "/out/$name.out" 2>&1
    echo "rc=$?" >> "/out/$name.out"
    echo "\$ (as alice) $*" >> "/out/$name.out"
}
mkdir d; printf 'a\n' > d/a; printf 'b\n' > d/b; printf 'c\n' > d/c; printf 'f\n' > f
chown alice:alice d/a; chown bob:pack d/b; chown 4242:4343 d/c; chmod 1777 /t
t id id < /dev/null
t id-alice id alice < /dev/null
t id-u id -u < /dev/null
t id-Gn id -Gn alice < /dev/null
t id-nosuch id nosuch < /dev/null
t whoami whoami < /dev/null
t groups groups alice < /dev/null
t ls-l ls -l d < /dev/null
t ls-ln ls -ln d < /dev/null
t stat stat -c '%U %G %u %g %A' d/a d/c < /dev/null
t chown-name chown alice f < /dev/null
t chown-name-group chown bob:pack f < /dev/null
t chown-numbers chown 1001:2000 f < /dev/null
t chown-nosuch chown nosuch f < /dev/null
t chgrp chgrp pack f < /dev/null
t chown-R chown -R alice:pack d < /dev/null
ta alice-id id < /dev/null
ta alice-whoami whoami < /dev/null
printf 'mine\n' > am; chown alice:alice am
ta alice-chown-away chown bob am < /dev/null
ta alice-chgrp-own-group chgrp pack am < /dev/null
ta alice-chgrp-other-group chgrp bob am < /dev/null
ta alice-chmod-others chmod 600 f < /dev/null
t su-to-alice su alice -c id < /dev/null
t su-login-alice su - alice -c 'id; pwd; echo $HOME $USER $LOGNAME $SHELL $PATH' < /dev/null
t su-nosuch su nosuch -c id < /dev/null
ta alice-su-root su root -c id <<< 'root-pw-1'
ta alice-su-root-wrong su root -c id <<< 'not-it'
ta alice-su-bob-nopw su bob -c id <<< ''
ta alice-sg-pack sg pack -c id < /dev/null
t passwd-S passwd -S alice < /dev/null
t passwd-root-sets passwd alice <<< $'wolf-pw-2\nwolf-pw-2'
ta alice-passwd passwd <<< $'wolf-pw-2\nwolf-Pw-3x9\nwolf-Pw-3x9'
ta alice-passwd-wrong passwd <<< $'not-it\nwolf-Pw-4x9\nwolf-Pw-4x9'
# login wants a terminal. `login -f` through script(1)'s pseudo-terminal;
# the password logins through pty-type.py, which waits for each prompt
# (login flushes what was typed ahead).
t login-f script -qec 'login -f alice' /dev/null <<< $'id\ntty\nexit'
tp() { # name, the prompts and answers, --, the command: traced on a pseudo-terminal
    n=$((n + 1)); local name; name=$(printf '%02d-%s' $n "$1"); shift
    local steps=(); while [ "$1" != -- ]; do steps+=("$1"); shift; done; shift
    python3 /pty-type.py "/out/$name.out" "${steps[@]}" -- strace -f -s 160 -o "/out/$name.strace" "$@" < /dev/null > /dev/null 2>&1
    echo "rc=$?" >> "/out/$name.out"
    echo "\$ (on a pseudo-terminal) $*" >> "/out/$name.out"
}
tp login-password 'login: =alice' 'assword: =wolf-Pw-3x9' '$ =id; tty; exit' -- login
tp login-wrong 'login: =alice' 'assword: =not-it' 'login: =' -- login
tp login-nosuch 'login: =nosuch' 'assword: =x' 'login: =' -- login
{
    echo "== /etc/shadow after the changes (cut as before)"
    grep -E '^(root|alice|bob):' /etc/shadow | sed -E 's/^([^:]*):(\$[^$]*\$[^$]*\$)[^:]*:/\1:\2<salt and hash cut>:/'
    ls -la /etc/passwd /etc/shadow /etc/.pwd.lock /etc/nshadow 2>&1
} >> /out/accounts.txt 2>&1
chmod -R a+rX /out
echo done > /out/done
