#!/bin/bash
# px46: Linux's su(1), black-box, inside a THROWAWAY container (px13-ubuntu:
# Ubuntu 24.04, util-linux 2.39.3's su) as the container's root, with the
# accounts made in that container only. Nothing of su is read but what it
# shows. Two configurations: "ubuntu" as installed, and "bare" with
# ENV_PATH/ENV_SUPATH taken out of /etc/login.defs and /etc/environment
# emptied (what su does when nothing configures it).
#   su-ct.sh SHOWBIN [SU]      (run inside the container, as its root)
# With SU, that program (PAX's su, user/su) is put in place of
# /usr/bin/su, mode 0755 and not set-ID, and the same rows are run.
set -u
cp "$1" /show; chmod 755 /show
if [ -n "${2:-}" ]; then
    cp "$2" /usr/bin/su; chmod 0755 /usr/bin/su
    echo "== su replaced by $2 ($(sha256sum /usr/bin/su | cut -d' ' -f1))"
fi
# the image's own account at 1000 (Ubuntu 24.04's `ubuntu`) is removed first
for u in $(awk -F: '$3 == 1000 || $3 == 990 || $3 == 1001 { print $1 }' /etc/passwd); do userdel -r "$u" 2>&1 | sed 's/^/userdel: /'; done
for g in $(awk -F: '$3 == 1000 || $3 == 990 || $3 == 1001 || $3 == 2000 { print $1 }' /etc/group); do groupdel "$g" 2>&1 | sed 's/^/groupdel: /'; done
groupadd -g 1000 pax; groupadd -g 990 lobo; groupadd -g 2000 pack; groupadd -g 1001 bob
useradd -u 1000 -g 1000 -G pack -d /home/pax -m -s /show pax
useradd -u 990 -g 990 -d /srv/lobo -s /bin/false lobo
useradd -u 1001 -g 1001 -d /home/bob -s /show bob    # no home made
groupadd -g 1002 nosh; useradd -u 1002 -g 1002 -d /home/nosh -m nosh; usermod -s '' nosh   # an empty shell field
echo "== accounts"; grep -E '^(root|pax|lobo|bob):' /etc/passwd; grep -E '^(root|pax|lobo|pack|bob):' /etc/group
echo "== shadow fields (method only)"; sed -E 's/^([^:]*):([^:]*):.*/\1 \2/; s/ \$y\$.*/ yescrypt-hash-cut/' /etc/shadow | grep -E '^(root|pax|lobo|bob) '
echo "== su: $(su --version 2>&1 | head -n 1 | sed 's/^su: --version: not built.*/(PAX su)/'); $(readlink -f "$(command -v su)"); mode $(stat -c '%a %U:%G' "$(command -v su)")"
mkdir -p /work
row() { # name, then the command line (run by bash -c) as the caller environment gives it
    local name=$1; shift
    echo "=== ROW $name"
    echo "\$ $*"
    (cd /work && env -i HOME=/ TERM=linux PAX=1 PATH=/bin:/usr/bin:/sbin:/usr/sbin PWD=/work FOO=bar bash -c "$*" </dev/null >/work/o 2>/work/e); rc=$?
    echo "--- stdout"; cat /work/o
    echo "--- stderr"; cat /work/e
    echo "--- rc $rc"
}
asuser() { # run "$@" as pax (1000:1000, groups 1000 2000) via setpriv, from the container's root
    echo "setpriv --reuid=1000 --regid=1000 --init-groups --reset-env -- $*"
}
pty_row() { # name, command: run on a pseudo-terminal (python pty), stdin the terminal, nothing typed but a newline after 1 s
    local name=$1; shift
    echo "=== ROW $name (on a terminal)"
    echo "\$ $*"
    python3 - "$@" <<'PY'
import os, pty, sys, time, select
pid, fd = pty.fork()
if pid == 0:
    os.chdir("/work")
    os.execve("/bin/bash", ["bash", "-c", sys.argv[1]], {"HOME": "/", "TERM": "linux", "PATH": "/bin:/usr/bin:/sbin:/usr/sbin"})
buf = bytearray(); t0 = time.time(); sent = False
while True:
    r, _, _ = select.select([fd], [], [], 0.05)
    if r:
        try:
            d = os.read(fd, 4096)
        except OSError:
            break
        if not d: break
        buf += d
    if not sent and time.time() - t0 > 1.0:
        os.write(fd, b"\r"); sent = True
    if time.time() - t0 > 15: break
p, st = os.waitpid(pid, 0)
sys.stdout.write("--- terminal %r\n--- rc %d\n" % (bytes(buf), os.waitstatus_to_exitcode(st)))
sys.stdout.write("--- seconds %.1f\n" % (time.time() - t0))
PY
}
runall() {
    row su-user 'su pax'
    row su-user-c 'su pax -c "the command"'
    row su-user-c-args 'su pax -c "the command" one two'
    row su-user-args 'su pax one two'
    row su-dash 'su - pax'
    row su-l 'su -l pax'
    row su-login 'su --login pax'
    row su-dash-c 'su - pax -c "the command"'
    row su-m 'su -m pax'
    row su-p 'su -p pax'
    row su-dash-m 'su - -m pax'
    row su-s 'su -s /show lobo'
    row su-lobo 'su lobo'
    row su-root-s 'su -s /show'
    row su-dash-root-s 'su - -s /show root'
    row su-s-dash-root 'su -s /show -'
    row su-status 'PX46_STATUS=3 su pax'
    row su-status-dash 'PX46_STATUS=3 su - pax -c x'
    row su-killed 'su -s /bin/bash pax -c "kill -TERM \$\$"'
    row su-nohome 'su - bob'
    row su-nohome-plain 'su bob'
    row su-nosuch 'su nosuch'
    row su-nosuch-c 'su nosuch -c x'
    row su-badopt 'su -x pax'
    row su-badlong 'su --bogus pax'
    row su-c-noarg 'su pax -c'
    row su-noshell 'su -s /nope pax'
    row su-twonames 'su pax lobo'
    row su-help-status 'su --help >/dev/null'
    row su-m-shellvar 'SHELL=/bin/bash su -m pax -c "echo shell=\$0"'
    row su-emptyshell 'su nosh -c "echo shell=\$0"'
    row su-user-dash-late 'su pax -'
    row su-c-twice 'su pax -c first -c second'
    row su-s-noarg 'su pax -s'
    row user-su-root "$(asuser su root -c x)"
    row user-su-noname "$(asuser su)"
    row user-su-lobo "$(asuser su lobo)"
    row user-su-self "$(asuser su pax)"
    row user-su-dash "$(asuser su - pax -c x)"
    row user-su-nosuch "$(asuser su nosuch)"
    row user-su-badopt "$(asuser su -x pax)"
    pty_row user-su-root-tty "$(asuser su root -c x)"
    pty_row user-su-self-tty "$(asuser su pax)"
    pty_row user-su-nosuch-tty "$(asuser su nosuch)"
}
echo "##### configuration ubuntu"
grep -E '^(ENV_PATH|ENV_SUPATH|UMASK|ALWAYS_SET_PATH)' /etc/login.defs; echo "/etc/environment: $(cat /etc/environment)"
runall
echo "##### configuration bare"
sed -i -E '/^(ENV_PATH|ENV_SUPATH)/d' /etc/login.defs
: > /etc/environment
grep -E '^(ENV_PATH|ENV_SUPATH|UMASK|ALWAYS_SET_PATH)' /etc/login.defs; echo "/etc/environment: $(cat /etc/environment)"
runall
echo "##### configuration bare, no pam_env, pam_mail or pam_umask; ENV_PATH PATH=/bin, ENV_SUPATH /bin"
# the lines that name those three modules are taken out of /etc/pam.d (a
# configuration change, measured by its effect; no module is read)
for f in /etc/pam.d/*; do sed -i -E '/pam_(env|mail|umask)\.so/d' "$f"; done
echo 'ENV_PATH	PATH=/bin' >> /etc/login.defs
echo 'ENV_SUPATH	/bin' >> /etc/login.defs
grep -E '^(ENV_PATH|ENV_SUPATH|UMASK|ALWAYS_SET_PATH)' /etc/login.defs; echo "/etc/environment: $(cat /etc/environment)"
runall
echo "##### done"
