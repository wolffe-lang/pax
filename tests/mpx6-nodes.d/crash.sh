# tests/mpx6-nodes.d/crash.sh — the crash row with a raw write (px79): `/`
# is vda2, journalled (tools/mkdisk --gpt --root), and this is init. The
# first boot writes files to /churn (the first 100 synced, the rest left
# to the journal's next commit), rewrites the GPT's first 34 sectors
# through /dev/vda with the bytes already there and writes one sector of
# a pattern at LBA 100 (between the table and the first partition, in no
# partition's window) while `/` is mounted with changes not yet
# committed, writes 100 more files, then waits: the host kills QEMU
# there. The second boot (the journal replayed) reads the sector back
# and lists /churn.
if [ -e /etc/nodes/crashed ]; then
    echo "crash: the second boot"
    /bin/nodes rd /dev/vda 51200 512
    ls /churn > /tmp/churn.txt
    /bin/nodes rd /tmp/churn.txt 0 4096
    echo "crash: end"
    exit 0
fi
echo "crash: start"
mkdir /churn
i=0
while [ $i -lt 100 ]; do echo "file $i" > /churn/f$i; i=$((i + 1)); done
echo yes > /etc/nodes/crashed
/bin/nodes sync
while [ $i -lt 200 ]; do echo "file $i" > /churn/f$i; i=$((i + 1)); done
/bin/nodes rewrite /dev/vda 0 17408
/bin/nodes mark /dev/vda 51200 0x7078373963726173
while [ $i -lt 300 ]; do echo "file $i" > /churn/f$i; i=$((i + 1)); done
echo "crash: waiting"
read line
