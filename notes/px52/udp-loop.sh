#!/bin/bash
# px52 on kasumi (pax#86): mpx4-udp's `user` boot, native tier, UEFI, TCG, the way tests/mpx4-udp's `boot`
# starts it — two ports from its pick_ports (taken from PICKER, trunk's or this branch's tests/mpx4-udp),
# tools/udp-host started first and waited for (its `bound` line), then tools/qemu-halt with the suite's QEMU
# arguments (the forward, the device, the dump) — N times. Each boot runs to the kernel's first line (`PAX:
# sockets`, given as the marker: qemu-halt then finds the machine not halted, says so and ends QEMU itself),
# and udp-host is ended by its recorded pid. udp-host and qemu-halt under taskset -c 0-3. Each boot is one of:
#   booted   the kernel's first line came;
#   refused  QEMU ended at once, its serial log empty and its own log not (what push run 39086412018 shows);
#   silent   QEMU ran 120 s and the kernel printed nothing.
#   udp-loop.sh TAG N PICKER IMAGES-DIR plain|load|churn
# load: four busy loops, one on each of cpus 0-3, for the loop's length. churn: the whole loop in a private
# network namespace (unshare --user --map-current-user --net --keep-caps: the uid unchanged, lo up, nothing of
# it on the host's ports or another lane's), beside a process on cpu 15 binding UDP sockets to port 0 on
# 127.0.0.1 as fast as it can and holding the newest HOLD (8000) of them. Every helper is this script's own
# child, ended by its recorded pid.
L=$HOME/lanes/px52; P=$L/pax
T=$1 N=$2 PF=$3 W=$4 MODE=${5:-plain}
HOLD=${PX52_HOLD:-8000}
O=$L/ev/udp-loop/$T
if [ "$MODE" = churn ] && [ -z "${PX52_IN_NS:-}" ]; then
    exec unshare --user --map-current-user --net --keep-caps env PX52_IN_NS=1 bash "$0" "$@"
fi
mkdir -p $O
export PAX_CACHE=$L/cache PAX_BUILD=$O/build
mkdir -p $PAX_BUILD
cd $P
. tools/lib.sh
eval "$(awk '/^pick_ports\(\) \{/,/^}/' "$PF")"
type pick_ports > /dev/null || { echo "no pick_ports in $PF"; exit 2; }
MAC=$(sed -n 's/^MAC=//p' tests/mpx4-udp | head -n 1)
iso=$W/native/kmain_sockets-user.iso elf=$W/native/kmain_sockets.elf
[ -f "$iso" ] && [ -f "$elf" ] || { echo "no $iso or $elf"; exit 2; }
helpers=()
cleanup() { local h; for h in ${helpers[@]+"${helpers[@]}"}; do kill "$h" 2>/dev/null; done; }
trap cleanup EXIT
if [ "$MODE" = churn ]; then
    ip link set lo up || { echo "no lo"; exit 2; }
    taskset -c 15 python3 -c '
import collections, resource, socket, sys
hold = int(sys.argv[1])
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (min(hard, hold + 256), hard))
q = collections.deque()
while True:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    q.append(s)
    if len(q) > hold:
        q.popleft().close()
' "$HOLD" & helpers+=($!)
    sleep 2
fi
if [ "$MODE" = load ]; then
    for c in 0 1 2 3; do taskset -c $c bash -c 'while :; do :; done' & helpers+=($!); done
fi
lo=32768 hi=60999
read -r lo hi < /proc/sys/net/ipv4/ip_local_port_range
{
    echo "tag $T, mode $MODE, $N boots, picker $PF ($(sha256_of "$PF" | cut -c1-16)), image $(sha256_of "$iso" | cut -c1-16)"
    echo "kernel $(uname -r), $(qemu-system-x86_64 --version | head -n 1), ip_local_port_range $lo $hi, netns $(readlink /proc/self/ns/net), helpers ${helpers[*]:-none}"
} > $O/head.txt
cat $O/head.txt
: > $O/loop.tsv
nb=0 nr=0 ns=0 no=0
for n in $(seq 1 $N); do
    ports=$(pick_ports "$n")
    port=${ports% *}
    inr=no; [ "$port" -ge "$lo" ] && [ "$port" -le "$hi" ] && inr=yes
    log=$O/b$n.serial.log
    rm -f $log $log.*
    t0=$(date +%s%N)
    taskset -c 0-3 tools/udp-host --echo-to "$port" --soak 10000 --boot 120 --wait 900 > $log.end 2>&1 &
    hp=$!
    w=0
    while [ "$w" -lt 9000 ] && ! grep -q '^udp-host: 127.0.0.1 port\|^udp-host: FAIL' "$log.end" 2>/dev/null; do sleep 0.1; w=$((w + 1)); done
    taskset -c 0-3 tools/qemu-halt --firmware uefi --serial "$log" --timeout 120 --accel tcg --elf "$elf" --marker 'PAX: sockets' \
        --qemu -netdev --qemu "user,id=n0,ipv6=off,hostfwd=udp:127.0.0.1:$port-:7" \
        --qemu -device --qemu "virtio-net-pci,netdev=n0,mac=$MAC" --qemu -object --qemu "filter-dump,id=f0,netdev=n0,file=$O/b$n.pcap" \
        "$iso" > $log.verdict 2>&1
    kill "$hp" 2>/dev/null; wait "$hp" 2>/dev/null
    el=$(awk -v a="$t0" -v b="$(date +%s%N)" 'BEGIN { printf "%.1f", (b - a) / 1e9 }')
    rm -f $O/b$n.pcap
    if serial_norm "$log" | grep -qx 'PAX: sockets'; then
        cls=booted; nb=$((nb + 1)); why=
    elif [ ! -s "$log" ] && [ -s "$log.qemu.log" ]; then
        cls=refused; nr=$((nr + 1)); why=$(head -n 1 "$log.qemu.log")
    elif grep -q 'within 120s' "$log.verdict"; then
        cls=silent; ns=$((ns + 1)); why="$(wc -c < "$log") serial bytes; $(serial_norm "$log" | grep -c . ) lines"
    else
        cls=other; no=$((no + 1)); why=$(head -n 1 "$log.verdict")
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$n" "$port" "$inr" "$cls" "$el" "$why" >> $O/loop.tsv
    [ "$cls" = booted ] && rm -f $log $log.mon* $log.halt $log.typed
    [ $((n % 10)) = 0 ] && echo "after $n: booted $nb, refused $nr, silent $ns, other $no"
done
echo "$T: $N boots ($MODE): booted $nb, refused $nr, silent $ns, other $no; ports in $lo-$hi: $(awk -F'\t' '$3 == "yes"' $O/loop.tsv | wc -l)" | tee $O/summary.txt
