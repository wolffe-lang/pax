#!/bin/bash
# px58 on kasumi: the Linux virtual terminal's side of the keyboard's keys
# and of the queries (notes/px58/vtkeys.c as pid 1 of kasumi's own kernel
# image under QEMU, TCG, a VGA display, the PS/2 keyboard); the keys sent
# through a second monitor once `ps2> ` is on the serial log, as
# tests/mpx5-yew sends them to PAX. Twice, the two compared.
#   vt-run.sh OUTDIR
L=$HOME/lanes/px58; P=$L/pax; O=$1
mkdir -p $O
K=/usr/lib/modules/$(uname -r)/vmlinuz
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $O/vtkeys $P/notes/px58/vtkeys.c && sha256sum $O/vtkeys $P/notes/px58/vtkeys.c" || exit 1
$P/tools/mkinitramfs $O/vt.cpio /vtkeys=$O/vtkeys:755 > $O/vt.cpio.txt
for n in 1 2; do
  rm -f $O/vt$n.log $O/vt$n.sock
  timeout 600 taskset -c 4-15 qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m 512 -display none -no-reboot -nic none \
      -kernel $K -initrd $O/vt.cpio -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/vtkeys" \
      -serial file:$O/vt$n.log -monitor unix:$O/vt$n.sock,server=on,wait=off < /dev/null > $O/vt$n.qemu.log 2>&1 &
  q=$!
  python3 - $O/vt$n.log $O/vt$n.sock "up down right left home end pgup pgdn insert delete dot" <<'PY'
import socket, sys, time
serial, sock, keys = sys.argv[1], sys.argv[2], sys.argv[3].split()
end = time.time() + 500
while time.time() < end:
    try:
        if b"ps2> " in open(serial, "rb").read():
            break
    except OSError:
        pass
    time.sleep(0.2)
else:
    print("vt-run: no ps2> prompt"); sys.exit(1)
time.sleep(1)
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect(sock); s.settimeout(5)
def cmd(c):
    s.sendall((c + "\n").encode()); time.sleep(0.3)
    try: s.recv(65536)
    except OSError: pass
cmd("")
for k in keys: cmd("sendkey " + k)
print("vt-run: sent", " ".join(keys))
PY
  wait $q; echo "run $n: qemu $?"
  tr -d '\r' < $O/vt$n.log | grep -a '^VT \|=== px58'
done
tr -d '\r' < $O/vt1.log | grep -a '^VT ' > $O/vt1.rows; tr -d '\r' < $O/vt2.log | grep -a '^VT ' > $O/vt2.rows
cmp -s $O/vt1.rows $O/vt2.rows && echo "the two runs: the same rows" || echo "the two runs DIFFER"
echo "kernel: $K $(sha256sum $K | cut -d' ' -f1) ($(uname -r)); $(qemu-system-x86_64 --version | head -n1)"
