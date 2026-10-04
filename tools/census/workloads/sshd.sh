# sshd (OpenSSH, Arch's build) serving one key-authenticated user: a
# command, a pty session, and scp both ways. Scope: sshd, its
# privilege-separated children (sshd-session, sshd-auth) and the sftp
# server scp drives; the user's shell and commands are counted under
# their own workloads.
SCOPE='/usr/bin/sshd /usr/lib/ssh/sshd-session /usr/lib/ssh/sshd-auth /usr/lib/ssh/sftp-server'
workload() {
    ssh-keygen -A
    id census > /dev/null 2>&1 || useradd -m -s /bin/bash census
    rm -f /root/k /root/k.pub
    ssh-keygen -q -t ed25519 -N '' -f /root/k
    install -d -m 700 -o census -g census /home/census/.ssh
    install -m 600 -o census -g census /root/k.pub /home/census/.ssh/authorized_keys
    T /usr/bin/sshd -D -e -p 2222 -o PidFile=/run/sshd-census.pid > /work/sshd.log 2>&1 &
    i=0
    until ssh-keyscan -p 2222 127.0.0.1 > /dev/null 2>&1; do
        i=$((i + 1)); [ $i -ge 100 ] && { echo "sshd never answered"; return 1; }
        sleep 0.1
    done
    o="-p 2222 -i /root/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
    ssh $o census@127.0.0.1 'echo hello from sshd; id -un'
    ssh -tt $o census@127.0.0.1 'tty; exit 0' < /dev/null
    head -c 1048576 /dev/urandom > /work/blob
    scp -q -P 2222 -i /root/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        /work/blob census@127.0.0.1:blob
    scp -q -P 2222 -i /root/k -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        census@127.0.0.1:blob /work/blob.back
    cmp /work/blob /work/blob.back && echo "scp round trip intact"
    kill "$(cat /run/sshd-census.pid)"
    wait
}
