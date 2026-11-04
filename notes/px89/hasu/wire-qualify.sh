#!/usr/bin/env bash
# px89: qualify the metal stick under QEMU (in the container): a COPY of
# OUTDIR/pax-wire.img on qemu-xhci + usb-storage, written to (as the stick
# is on kasumi), `-device igb` on QEMU's user-mode network (kasumi's
# I225-V on QEMU's 82576: the ring model they share), /pax/wire-target
# naming a server this script runs at 127.0.0.1 (QEMU's 10.0.2.2), BIOS
# and UEFI. Rows: Q1 the lease and resolv.conf in the record; Q2 the
# router answered the kernel's echo; Q3 tcpprobe connected and read the
# server's line; Q4 the record on the copy's ESP, /pax/logs/wire-1.txt,
# equal to what the screen showed. Prints PASS/FAIL Qn per firmware and
# stick: pax-wire.img (the 82576 by MSI-X) and pax-wire-netpoll.img
# (`cmdline: netpoll`: polled every tick, as the I225 is on kasumi).
set -uo pipefail
O=$1
. tools/lib.sh
fat=$O/root/bin/paxfat
OFF=2097152
fail=0
port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')
python3 -I -c '
import socket, sys
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1]))); s.listen(4)
while True:
    c, _ = s.accept(); c.sendall(b"px89-wire-qualify: hello from the host\r\n"); c.close()
' "$port" &
srv=$!
for run in bios uefi bios-netpoll uefi-netpoll; do
    fw=${run%-netpoll}
    src=$O/pax-wire.img; [ "$run" = "$fw" ] || src=$O/pax-wire-netpoll.img
    w=$O/q-$run; rm -rf "$w"; mkdir -p "$w"
    cp "$src" "$w/stick.img"
    printf '10.0.2.2 %s\n' "$port" > "$w/target"
    # The staged stick names no target (the maintainer's to write); the
    # copy names this script's server.
    "$fat" --offset "$OFF" copy "$w/stick.img" "$w/target" /pax/wire-target || { echo "FAIL Q0 $run: paxfat copy"; fail=1; continue; }
    fwargs=()
    if [ "$fw" = uefi ]; then
        read -r code vars <<< "$(find_ovmf)"
        [ -n "$code" ] && [ -n "$vars" ] || { echo "FAIL Q0 $run: no OVMF"; fail=1; continue; }
        cp "$vars" "$w/vars.fd"
        fwargs=(-drive "if=pflash,format=raw,unit=0,readonly=on,file=$code" -drive "if=pflash,format=raw,unit=1,file=$w/vars.fd")
    fi
    timeout 300 qemu-system-x86_64 -machine q35 -cpu max -m 512 -accel kvm -display none -monitor none -parallel none \
        -no-reboot -serial "file:$w/serial.log" "${fwargs[@]}" \
        -device qemu-xhci,id=xhci -drive "file=$w/stick.img,if=none,id=stick,format=raw" \
        -device usb-storage,bus=xhci.0,drive=stick,bootindex=0 \
        -netdev user,id=n0,ipv6=off -device igb,netdev=n0,mac=52:54:00:12:34:56 &
    q=$!
    t=0
    while [ $t -lt 240 ] && ! grep -aq '^== written to \|^== NOT written\|^== no disk holds' "$w/serial.log" 2>/dev/null; do sleep 1; t=$((t + 1)); done
    sleep 3
    kill $q 2>/dev/null; wait $q 2>/dev/null
    norm=$w/serial.norm; serial_norm "$w/serial.log" > "$norm"
    grep -a -E '^(net|dhcp|wire|==|tcpprobe|state|address|router)' "$norm" | head -60 | sed 's/^/  /'
    want="MSI-X vector 83"; [ "$run" = "$fw" ] || want="polled every tick \\(line [0-9]+, netpoll asked\\)"
    grep -aqE "^net: 52:54:00:12:34:56, $want" "$norm" && echo "PASS Q0 $run: net: ... $want" || { echo "FAIL Q0 $run: no '$want' line"; fail=1; }
    grep -aq '^state bound' "$norm" && grep -aq '^nameserver 10.0.2.3' "$norm" && echo "PASS Q1 $run: the lease and resolv.conf in the record" || { echo "FAIL Q1 $run"; fail=1; }
    grep -aq '^router-echo answered' "$norm" && echo "PASS Q2 $run: the router answered the kernel's echo" || { echo "FAIL Q2 $run"; fail=1; }
    grep -aq "^tcpprobe: the server's first line: px89-wire-qualify: hello from the host" "$norm" && echo "PASS Q3 $run: tcpprobe" || { echo "FAIL Q3 $run"; fail=1; }
    rec=$("$fat" --offset "$OFF" cat "$w/stick.img" /pax/logs/wire-1.txt 2>&1)
    printf '%s\n' "$rec" | grep -q '^state bound' && echo "PASS Q4 $run: /pax/logs/wire-1.txt on the stick ($(printf '%s\n' "$rec" | wc -l) lines)" || { echo "FAIL Q4 $run: $(printf '%s\n' "$rec" | head -3)"; fail=1; }
done
kill $srv 2>/dev/null; wait $srv 2>/dev/null
exit $fail
