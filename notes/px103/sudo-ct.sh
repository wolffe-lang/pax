#!/bin/bash
# px103: Linux's sudo(8), black-box, inside a THROWAWAY container
# (localhost/px103-sudo:1: Ubuntu 24.04, sudo 1.9.15p5-3ubuntu5.24.04.4) as
# the container's root, with the accounts made in that container only.
# Nothing of sudo is read but what it shows: its messages, its exit
# status, and what the command it runs is given (px46's /show probe:
# argv, the working directory, the ids, the groups, the environment).
#
#   sudo-ct.sh SHOWBIN [SUDO]      (run inside the container, as its root)
#
# With SUDO, that program (PAX's sudo, user/sudo) is put in place of
# /usr/bin/sudo, mode 4755 and owned by root, and the same rows run.
#
# The rows are grouped by configuration: the subset (the sudoers file
# PAX ships, plus /etc/sudoers.d files for the other rules), then each
# hostile variation, then the log file. Every row prints its command, its
# stdout, its stderr and its exit status.
set -u
cp "$1" /show; chmod 755 /show
if [ -n "${2:-}" ]; then
    cp "$2" /usr/bin/sudo; chown 0:0 /usr/bin/sudo; chmod 4755 /usr/bin/sudo
    echo "== sudo replaced by $2 ($(sha256sum /usr/bin/sudo | cut -d' ' -f1))"
fi
# the image's own account at 1000 (Ubuntu 24.04's `ubuntu`) is removed first
for u in $(awk -F: '$3 == 1000 || $3 == 990 || $3 == 1001 { print $1 }' /etc/passwd); do userdel -r "$u" 2>&1 | sed 's/^/userdel: /'; done
for g in $(awk -F: '$3 == 1000 || $3 == 990 || $3 == 1001 || $3 == 2000 { print $1 }' /etc/group); do groupdel "$g" 2>&1 | sed 's/^/groupdel: /'; done
groupadd -g 1000 pax; groupadd -g 990 lobo; groupadd -g 2000 pack; groupadd -g 1001 bob
useradd -u 1000 -g 1000 -G pack -d /home/pax -m -s /show pax
useradd -u 990 -g 990 -d /srv/lobo -s /bin/false lobo
useradd -u 1001 -g 1001 -d /home/bob -m -s /show bob
usermod -s /show root
mkdir -p /srv/lobo /home/pax/evil /work; chown 990:990 /srv/lobo; chmod 777 /work
printf '#!/bin/sh\necho EVIL "$@"\n' > /home/pax/evil/id; chmod 755 /home/pax/evil/id; cp /home/pax/evil/id /home/pax/evil/show
ln -s /usr/bin/id /usr/local/bin/idlink
echo "== accounts"; grep -E '^(root|pax|lobo|bob):' /etc/passwd; grep -E '^(root|pax|lobo|pack|bob):' /etc/group
echo "== sudo: $(sudo -V 2>&1 | head -n 1); mode $(stat -c '%a %U:%G' /usr/bin/sudo); hostname $(hostname)"
echo "== /etc/pam.d/sudo"; grep -v '^#' /etc/pam.d/sudo | grep -v '^$'
echo "== /etc/environment: $(cat /etc/environment 2>/dev/null)"

# The caller's environment: what a login on PAX gives (HOME, USER, LOGNAME,
# SHELL, TERM, PATH) plus what an attacker or a habit adds.
CALLER_ENV='TERM=linux PATH=/home/pax/evil:/usr/bin:/bin FOO=bar DISPLAY=:0 LANG=C.UTF-8 LC_ALL=C TZ=UTC PS1=caller$ EDITOR=vi MAIL=/var/mail/caller SUDO_USER=fake SUDO_COMMAND=fake XAUTHORITY=/x COLORS=/c LS_COLORS=x HISTSIZE=5 PWD=/work'
row() { # name, who (root|pax|lobo|bob), then the command line (run by bash -c)
    local name=$1 who=$2; shift 2
    local ids home
    case $who in
        root) ids=; home=/root ;;
        pax) ids="setpriv --reuid=1000 --regid=1000 --init-groups --"; home=/home/pax ;;
        lobo) ids="setpriv --reuid=990 --regid=990 --init-groups --"; home=/srv/lobo ;;
        bob) ids="setpriv --reuid=1001 --regid=1001 --init-groups --"; home=/home/bob ;;
    esac
    echo "=== ROW $name ($who)"
    echo "\$ $*"
    # shellcheck disable=SC2086
    (cd /work && env -i HOME=$home USER=$who LOGNAME=$who SHELL=/bin/bash $CALLER_ENV $ids /bin/bash -c "$*" </dev/null >/work/o 2>/work/e); rc=$?
    echo "--- stdout"; cat /work/o
    echo "--- stderr"; cat /work/e
    echo "--- rc $rc"
}
sudoers_subset() {
    cat > /etc/sudoers <<'EOF'
# PAX's /etc/sudoers (px103): a subset of sudoers(5). No passwords exist
# yet (R1), so only NOPASSWD rules are honoured for anyone but root.
Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
root ALL=(ALL:ALL) ALL
#1000 ALL=(ALL:ALL) NOPASSWD: ALL
#includedir /etc/sudoers.d
EOF
    chown 0:0 /etc/sudoers; chmod 0440 /etc/sudoers
    rm -rf /etc/sudoers.d; mkdir -m 0755 /etc/sudoers.d
    cat > /etc/sudoers.d/bob <<'EOF'
bob ALL=(root) NOPASSWD: /show, /usr/bin/id, /usr/local/bin/idlink
bob ALL=(pax) /show
%pack ALL=(lobo : pack) NOPASSWD: /show
EOF
    chmod 0440 /etc/sudoers.d/bob
}

runall_basic() {
    for who in root pax; do
        row "$who-show" $who 'sudo /show a "b c"'
        row "$who-bare-name" $who 'sudo show one'
        row "$who-u-pax" $who 'sudo -u pax /show'
        row "$who-u-uid" $who "sudo -u '#1000' /show"
        row "$who-u-lobo" $who 'sudo -u lobo /show'
        row "$who-g-pack" $who 'sudo -g pack /show'
        row "$who-u-g" $who 'sudo -u pax -g pack /show'
        row "$who-u-lobo-g-pax" $who 'sudo -u lobo -g pax /show'
        row "$who-g-gid" $who "sudo -g '#2000' /show"
        row "$who-i" $who 'sudo -i'
        row "$who-i-cmd" $who 'sudo -i /show "a b" "c\$d" "e;f"'
        row "$who-i-u-pax" $who 'sudo -i -u pax /show x'
        row "$who-s" $who 'sudo -s'
        row "$who-s-cmd" $who 'sudo -s /show "a b" "c\$d"'
        row "$who-E" $who 'sudo -E /show'
        row "$who-l" $who 'sudo -l'
        row "$who-l-cmd" $who 'sudo -l /show x'
        row "$who-l-cmd-no" $who 'sudo -l /nonexistent'
        row "$who-ll" $who 'sudo -ll'
        row "$who-l-U" $who 'sudo -l -U bob'
        row "$who-n" $who 'sudo -n /show'
        row "$who-v" $who 'sudo -v'
        row "$who-k" $who 'sudo -k'
        row "$who-k-cmd" $who 'sudo -k /show'
        row "$who-K" $who 'sudo -K'
        row "$who-dashdash" $who 'sudo -- /show -x'
        row "$who-h" $who 'sudo -h'
        row "$who-V" $who 'sudo -V'
        row "$who-noargs" $who 'sudo'
        row "$who-u-nosuch" $who 'sudo -u nosuch /show'
        row "$who-g-nosuch" $who 'sudo -g nosuch /show'
        row "$who-nosuch-cmd" $who 'sudo nosuchcmd'
        row "$who-missing-path" $who 'sudo /nonexistent'
        row "$who-dir" $who 'sudo /etc'
        row "$who-badopt" $who 'sudo -x /show'
        row "$who-badlong" $who 'sudo --bogus /show'
        row "$who-u-noarg" $who 'sudo -u'
        row "$who-evil-path" $who 'sudo id -u'
        row "$who-env-path" $who 'sudo /usr/bin/env'
        row "$who-status" $who 'sudo /bin/sh -c "exit 7"'
        row "$who-signal" $who 'sudo /bin/sh -c "kill -TERM \$\$"'
        row "$who-cwd" $who 'cd /srv && sudo /show'
        row "$who-umask" $who 'umask 077; sudo /show'
    done
    row lobo-show lobo 'sudo /show'
    row lobo-n lobo 'sudo -n /show'
    row lobo-l lobo 'sudo -l'
    row lobo-n-l lobo 'sudo -n -l'
    row lobo-v lobo 'sudo -v'
    row lobo-n-v lobo 'sudo -n -v'
    row lobo-k lobo 'sudo -k'
    row lobo-h lobo 'sudo -h'
    row lobo-V lobo 'sudo -V'
    row lobo-u-nosuch lobo 'sudo -u nosuch /show'
    row bob-show bob 'sudo /show'
    row bob-id bob 'sudo /usr/bin/id'
    row bob-id-bare bob 'sudo id'
    row bob-id-bin bob 'sudo /bin/id'
    row bob-idlink bob 'sudo /usr/local/bin/idlink'
    row bob-cat bob 'sudo /usr/bin/cat /etc/hostname'
    row bob-n-cat bob 'sudo -n /usr/bin/cat /etc/hostname'
    row bob-u-pax bob 'sudo -u pax /show'
    row bob-n-u-pax bob 'sudo -n -u pax /show'
    row bob-u-lobo bob 'sudo -u lobo /show'
    row bob-l bob 'sudo -l'
    row bob-l-cmd bob 'sudo -l /show'
    row bob-l-cmd-no bob 'sudo -l /usr/bin/cat'
    row bob-E bob 'sudo -E /show'
    row bob-i bob 'sudo -i /show'
    row bob-s bob 'sudo -s /show'
    row pax-pack pax 'sudo -u lobo -g pack /show'
    row pax-pack-n pax 'sudo -n -u lobo -g pack /show'
}

echo "##### configuration subset (pam as installed)"
sudoers_subset
echo "== /etc/sudoers"; cat /etc/sudoers; echo "== /etc/sudoers.d/bob"; cat /etc/sudoers.d/bob
runall_basic

# PAX has no PAM: the rest runs with what PAM adds taken away (px46's
# "bare" configuration: the lines naming pam_env, pam_umask, pam_limits
# and pam_mail removed from /etc/pam.d, /etc/environment emptied, a
# configuration change measured by its effect; no module is read).
for f in /etc/pam.d/*; do sed -i -E '/pam_(env|umask|limits|mail)\.so/d' "$f"; done
: > /etc/environment
echo "##### configuration subset (bare)"
echo "== /etc/pam.d/sudo"; grep -v '^#' /etc/pam.d/sudo | grep -v '^$'
runall_basic


echo "##### configuration details"
sudoers_subset
ln -sf /show /usr/local/bin/showlink
cat > /etc/sudoers.d/detail <<'EOF'
bob ALL=(root) NOPASSWD: /usr/local/bin/showlink
%#2000 ALL=(root, lobo) NOPASSWD: /usr/bin/env, PASSWD: /usr/bin/id, (pax : pack) /usr/bin/printenv
EOF
chmod 0440 /etc/sudoers.d/detail
cat /etc/sudoers.d/detail
row pax-s-show pax 'SHELL=/show sudo -s'
row pax-s-show-cmd pax "SHELL=/show sudo -s /show 'a b' 'c\\d' \"e'f\" 'g\"h' 'tab	x' 'a/b.c=d:e,f@g~h*i?j[k]l{m}n(o)p<q>r|s&t!u#v%w^x+y'"
row pax-i-chars pax "sudo -i /show 'a b' 'c\\d' \"e'f\" 'g\"h' 'tab	x' 'a/b.c=d:e,f@g~h*i?j[k]l{m}n(o)p<q>r|s&t!u#v%w^x+y' '' 'z'"
row pax-i-empty pax "sudo -i ''"
row pax-u-i pax 'sudo -u bob -i'
row pax-u-s pax 'SHELL=/show sudo -u bob -s'
row pax-noterm pax 'env -u TERM sudo /usr/bin/env'
row pax-env-order pax 'env -i ZZ=1 TERM=t DISPLAY=d PATH=/bin HOME=/h USER=u LOGNAME=u SHELL=/s LANG=l AA=2 COLORS=c MAIL=m TZ=UTC /usr/bin/sudo /usr/bin/env'
row pax-env-order-u pax 'env -i ZZ=1 TERM=t DISPLAY=d PATH=/bin HOME=/h LANG=l /usr/bin/sudo -u lobo /usr/bin/env'
row pax-env-order-i pax 'env -i ZZ=1 TERM=t DISPLAY=d PATH=/bin HOME=/h LANG=l /usr/bin/sudo -i /usr/bin/env'
row pax-env-order-E pax 'env -i ZZ=1 TERM=t DISPLAY=d PATH=/bin HOME=/h LANG=l LD_X=1 BASH_FUNC_f%%="() { :; }" IFS=x /usr/bin/sudo -E /usr/bin/env'
row pax-env-unsafe pax "env -i TERM=x/y TZ=/etc/x LANG='a%b' LC_CTYPE=C LANGUAGE=en COLORTERM=truecolor LINGUAS=x PATH=/bin /usr/bin/sudo /usr/bin/env"
row pax-env-tz1 pax "env -i TZ=:UTC PATH=/bin /usr/bin/sudo /usr/bin/env"
row pax-env-tz2 pax "env -i TZ=/usr/share/zoneinfo/UTC PATH=/bin /usr/bin/sudo /usr/bin/env"
row pax-env-tz3 pax "env -i TZ=../x PATH=/bin /usr/bin/sudo /usr/bin/env"
row pax-env-tz4 pax "env -i 'TZ=a b' PATH=/bin /usr/bin/sudo /usr/bin/env"
row pax-env-func pax "env -i 'X=() { :; }' DISPLAY='() x' PATH=/bin /usr/bin/sudo /usr/bin/env"
row pax-env-empty pax "env -i /usr/bin/sudo /usr/bin/env"
row pax-var-arg pax 'sudo FOO=1 /usr/bin/env'
row bob-var-arg bob 'sudo FOO=1 /show'
row bob-showlink bob 'sudo /usr/local/bin/showlink x'
row bob-show-via-link bob 'sudo -n /show y'
row pax-detail-l pax 'sudo -l'
row pax-detail-ll pax 'sudo -ll'
row pax-detail-env pax 'sudo -u lobo /usr/bin/env'
row pax-detail-id pax 'sudo -n -u lobo /usr/bin/id'
row pax-detail-printenv pax 'sudo -n -u pax -g pack /usr/bin/printenv HOME'
row pax-l-U-self pax 'sudo -l -U pax'
row bob-l-U-pax bob 'sudo -l -U pax'
row pax-double-dash-opt pax 'sudo -u lobo -- -x'
row pax-shell-noarg pax 'sudo -s -u'
row pax-i-s pax 'sudo -i -s'
row pax-l-n pax 'sudo -l -n'
row pax-v-cmd pax 'sudo -v /show'
row pax-k-l pax 'sudo -k -l'
row pax-h-cmd pax 'sudo -h /show'
row pax-V-cmd pax 'sudo -V /show'
row root-u-g-only root 'sudo -g lobo -u root /show'
row pax-u-numeric-nosuch pax "sudo -u '#4242' /show"
row pax-g-numeric-nosuch pax "sudo -g '#4242' /show"
row pax-u-g-bad pax "sudo -u lobo -g nosuch /show"
row root-cwd-gone root 'mkdir /work/gone && cd /work/gone && rmdir /work/gone && sudo /show'

echo "##### configuration env_keep"
sudoers_subset
sed -i 's|^Defaults secure_path=.*|&\nDefaults env_keep += "FOO EDITOR"\nDefaults env_keep += "LD_PRELOAD"|' /etc/sudoers
cat /etc/sudoers
row pax-keep pax 'sudo /show'
row pax-keep-i pax 'sudo -i /show'
row root-keep root 'sudo -u pax /show'
sed -i 's|^Defaults env_keep += "FOO EDITOR"|Defaults env_keep = "FOO"|' /etc/sudoers
cat /etc/sudoers
row pax-keep-eq pax 'sudo /show'

echo "##### configuration log"
sudoers_subset
sed -i 's|^Defaults secure_path=.*|&\nDefaults logfile=/var/log/sudo.log|' /etc/sudoers
rm -f /var/log/sudo.log
row root-log root 'sudo /show'
row pax-log pax 'sudo -u lobo -g pack /show a b'
row pax-log-i pax 'sudo -i /show'
row lobo-log lobo 'sudo -n /show'
row bob-log bob 'sudo /usr/bin/cat /etc/hostname'
row bob-log-n bob 'sudo -n -u pax /show'
row pax-log-l pax 'sudo -l'
row pax-log-nosuch pax 'sudo /nonexistent'
row pax-log-long pax "sudo /show $(printf 'word%02d ' $(seq 1 30))"
echo "== /var/log/sudo.log, $(stat -c '%a %U:%G' /var/log/sudo.log)"; cat /var/log/sudo.log
sed -i 's|^Defaults logfile=.*|&\nDefaults !loglinelen|' /etc/sudoers
rm -f /var/log/sudo.log
row pax-log2 pax 'sudo -u lobo -g pack /show a b'
row pax-log2-long pax "sudo /show $(printf 'word%02d ' $(seq 1 30))"
row bob-log2 bob 'sudo /usr/bin/cat /etc/hostname'
echo "== /var/log/sudo.log, $(stat -c '%a %U:%G' /var/log/sudo.log)"; cat /var/log/sudo.log

echo "##### configuration hostile"
hostile() { # name, setup command run as root, then the rows' commands
    local name=$1 setup=$2; shift 2
    sudoers_subset
    echo "--- setup $name: $setup"
    bash -c "$setup"
    row "$name-pax" pax 'sudo /show'
    row "$name-root" root 'sudo /show'
    row "$name-pax-l" pax 'sudo -l'
}
hostile world-writable 'chmod 0666 /etc/sudoers'
hostile group-writable-root 'chmod 0460 /etc/sudoers'
hostile group-writable-other 'chgrp 1000 /etc/sudoers; chmod 0460 /etc/sudoers'
hostile owned-by-user 'chown 1000 /etc/sudoers'
hostile readable-0644 'chmod 0644 /etc/sudoers'
hostile symlink 'mv /etc/sudoers /etc/sudoers.real; ln -s sudoers.real /etc/sudoers'
hostile missing 'rm /etc/sudoers'
hostile d-user-owned 'chown 1000 /etc/sudoers.d/bob'
hostile d-world-writable 'chmod 0666 /etc/sudoers.d/bob'
hostile d-dir-world-writable 'chmod 0777 /etc/sudoers.d'
hostile d-symlink 'mv /etc/sudoers.d/bob /etc/bob.real; ln -s ../bob.real /etc/sudoers.d/bob'
hostile d-dotfile 'cp /etc/sudoers.d/bob /etc/sudoers.d/.hidden; echo "lobo ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/.hidden; echo "lobo ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/x~; echo "lobo ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/y.bak; chmod 0440 /etc/sudoers.d/*'
row d-dotfile-lobo lobo 'sudo -n /show'
hostile relative-cmd 'echo "bob ALL=(root) NOPASSWD: show" > /etc/sudoers.d/rel; chmod 0440 /etc/sudoers.d/rel'
hostile cmnd-alias 'echo "Cmnd_Alias X = /show" > /etc/sudoers.d/alias; echo "bob ALL=(root) NOPASSWD: X" >> /etc/sudoers.d/alias; chmod 0440 /etc/sudoers.d/alias'
row cmnd-alias-bob bob 'sudo -n /show'
hostile syntax-error 'printf "bob ALL=(root NOPASSWD: /show\n" > /etc/sudoers.d/bad; chmod 0440 /etc/sudoers.d/bad'
hostile syntax-error-main 'sed -i "s|^root ALL=(ALL:ALL) ALL|root ALL=(ALL:ALL ALL|" /etc/sudoers'
hostile cmd-args 'echo "bob ALL=(root) NOPASSWD: /usr/bin/id -u" > /etc/sudoers.d/args; chmod 0440 /etc/sudoers.d/args'
row cmd-args-bob bob 'sudo -n /usr/bin/id -u'
row cmd-args-bob2 bob 'sudo -n /usr/bin/id -g'
hostile host-name 'echo "bob pax=(root) NOPASSWD: /usr/bin/cat" > /etc/sudoers.d/host; chmod 0440 /etc/sudoers.d/host'
row host-name-bob bob 'sudo -n /usr/bin/cat /etc/hostname'
hostile long-line '{ printf "bob ALL=(root) NOPASSWD: /show"; for i in $(seq 20000); do printf ", /show"; done; echo; } > /etc/sudoers.d/long; chmod 0440 /etc/sudoers.d/long; wc -c /etc/sudoers.d/long'
hostile no-setuid 'chmod 0755 /usr/bin/sudo'
hostile not-root-owned 'chown 1000 /usr/bin/sudo; chmod 4755 /usr/bin/sudo'
sudoers_subset; chown 0:0 /usr/bin/sudo; chmod 4755 /usr/bin/sudo
row nnp-pax pax 'setpriv --no-new-privs sudo /show'
row nnp-root root 'setpriv --no-new-privs sudo /show'
A1000=$(printf 'a%.0s' $(seq 1000)); A131000=$(printf 'a%.0s' $(seq 131000))
row long-argv pax "sudo /show $(for i in $(seq 120); do printf '%s ' "$A1000"; done) | wc -c"
row long-arg pax "sudo /show $A131000 | wc -c"
row ld-preload pax 'LD_PRELOAD=/nope.so sudo /usr/bin/env'
echo "##### done"
