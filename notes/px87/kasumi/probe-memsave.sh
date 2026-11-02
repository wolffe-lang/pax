#!/usr/bin/env bash
# px87 (in the container, under the lock): does QMP memsave take a higher-half address as an unsigned
# number, or only as int64? A stopped QEMU (-S), no disk; one memsave each way at pax_serial_log_count's
# kind of address (0xffffffff8xxxxxxx), and the replies printed whole.
#   ctr.sh probe-memsave bin/probe-memsave.sh
set -uo pipefail
W=/home/mfwolffe/lanes/px87/b/probe-memsave
rm -rf "$W"; mkdir -p "$W"
qemu-system-x86_64 --version | head -1
qemu-system-x86_64 -machine q35 -accel tcg -S -display none -nodefaults -m 64M \
    -qmp "unix:$W/qmp.sock,server=on,wait=off" > "$W/qemu.out" 2>&1 &
qp=$!
python3 - "$W" <<'EOF'
import json, os, socket, sys, time
w = sys.argv[1]
for _ in range(100):
    if os.path.exists(w + '/qmp.sock'):
        break
    time.sleep(0.1)
s = socket.socket(socket.AF_UNIX); s.connect(w + '/qmp.sock'); fh = s.makefile('rwb')
def call(cmd, **a):
    fh.write(json.dumps({'execute': cmd, 'arguments': a} if a else {'execute': cmd}).encode() + b'\n'); fh.flush()
    while True:
        m = json.loads(fh.readline())
        if 'return' in m or 'error' in m:
            return m
json.loads(fh.readline()); call('qmp_capabilities')
addr = 0xffffffff80123450
print('unsigned val %#x: %s' % (addr, json.dumps(call('memsave', val=addr, size=8, filename=w + '/u.bin'))))
print('int64 val %d (the same address): %s' % (addr - (1 << 64), json.dumps(call('memsave', val=addr - (1 << 64), size=8, filename=w + '/s.bin'))))
call('quit')
EOF
rc=$?
wait "$qp"
echo "probe-memsave: python exit $rc"
exit "$rc"
