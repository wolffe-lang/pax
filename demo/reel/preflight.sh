#!/bin/bash
# preflight.sh — run off camera before filming the PAX reel. It checks
# QEMU, the ISOs' shas, the source snapshot and the terminal's size, then
# boots pax-reel.iso headless once (about 30 s) and waits for the
# finale's PANIC line. It starts nothing that outlives it: the one QEMU
# it starts is killed by its own process id. Last line: GO or NO GO.
#
#   bash /Users/mfwolffe/scratch/wolf/pax-demo/preflight.sh
demo=/Users/mfwolffe/scratch/wolf/pax-demo
qemu=/opt/homebrew/bin/qemu-system-x86_64
fail=0
ok()  { printf 'ok    %s\n' "$*"; }
bad() { printf 'FAIL  %s\n' "$*"; fail=1; }
warn() { printf 'warn  %s\n' "$*"; }

cd "$demo" || { echo "NO GO: no $demo"; exit 1; }

# 1. QEMU
if [ -x "$qemu" ]; then ok "qemu: $("$qemu" --version | head -n 1)"; else bad "no $qemu (brew install qemu)"; fi

# 2. the ISOs, by sha
if shasum -a 256 -c SHA256SUMS >/dev/null 2>&1; then
    ok "isos: $(cut -c1-12 SHA256SUMS | paste -sd' ' -) (shasum -c SHA256SUMS)"
else
    bad "isos: shasum -a 256 -c SHA256SUMS does not pass"
fi

# 3. the source snapshot scene 0 shows
n=$(find src/kernel -name '*.lu' 2>/dev/null | xargs cat 2>/dev/null | wc -l | tr -d ' ')
if [ "${n:-0}" -gt 0 ] && [ -f src/kernel/kmain_reel.lu ]; then ok "source: $n lines of wolf in src/kernel, kmain_reel.lu present"; else bad "source: src/kernel missing"; fi

# 4. the terminal
set -- $(stty size </dev/tty 2>/dev/null); rows=${1:-0}; cols=${2:-0}
if [ "$cols" -ge 125 ]; then ok "terminal: $cols columns (125 fit every line of finale a)"; else bad "terminal: $cols columns; widen to 125 or more (the apic line is 124)"; fi
[ "$cols" -ge 145 ] || warn "terminal: finale b's PANIC line is 145 columns; under that it wraps"
[ "$rows" -ge 30 ] || warn "terminal: $rows rows; 30 or more keep a whole stage on screen"

# 5. one headless boot, to the PANIC line
log=$demo/logs/preflight.serial.log
rm -f "$log"
"$qemu" -machine q35 -cpu max -m 256M -display none -serial "file:$log" -monitor none -nic none -no-reboot \
    -cdrom "$demo/pax-reel.iso" </dev/null >"$log.qemu" 2>&1 &
qpid=$!
t=0
while [ $t -lt 90 ]; do
    if grep -q '^PANIC stack overflow thread' "$log" 2>/dev/null; then break; fi
    kill -0 $qpid 2>/dev/null || break
    sleep 1; t=$((t + 1))
done
kill $qpid 2>/dev/null; wait $qpid 2>/dev/null
if grep -q '^PANIC stack overflow thread' "$log" 2>/dev/null; then
    ok "boot: pax-reel.iso reached its PANIC line in about ${t} s (logs/preflight.serial.log)"
else
    bad "boot: no PANIC line within ${t} s; see logs/preflight.serial.log"
fi

if [ "$fail" = 0 ]; then echo GO; else echo "NO GO"; exit 1; fi
