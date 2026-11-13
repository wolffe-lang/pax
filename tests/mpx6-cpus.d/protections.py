#!/usr/bin/env python3
"""Attach reviewed protection descriptions to every explicit masking site."""
import json
from pathlib import Path
import sys

rows = json.loads(Path(sys.argv[1]).read_text())
protection = {
 'bootlog': 'persistent console bytes, length and checksum; mark/seal publication',
 'bootmark': 'CMOS selector/data transaction and boot-stage record',
 'clock': 'counter extension: previous, elapsed, fraction and rollover diagnostics',
 'dhcp': 'client counters, receive-message staging and lease file publication',
 'fstab': 'writeback pass, tree/volume/block cache and flush counters',
 'mouse': 'reader allocation/lifetime, pointer identities and per-reader event rings',
 'net': 'device poll and check-before-block receive state',
 'netd': 'loopback peek/deliver/done transaction and protocol wakeups',
 'pci': 'configuration-address port plus configuration-data port transaction',
 'sched': 'current thread, slot lifetimes, FIFO links, waits and switch publication',
 'screen': 'parser, back/front grids, dirty bounds, batch ownership, pointer and answer queue',
 'serial': 'UART output and shared serial-log length/bytes before screen output',
 'sync': 'primitive only: local IF state, not inter-processor mutual exclusion',
 'user': 'shutdown sequencing and shared end-command state',
 'xhci': 'controller/slot/endpoint records, ring publication, completion and buffer lifetime',
}
xhci = {
 'page':'physical-frame allocation for controller DMA',
 'raw_flush':'raw-report ring snapshot before logging outside the masked section',
 'command':'command enqueue or completion observation around scheduler waits',
 'control':'control transfer enqueue or completion observation around scheduler waits',
 'pointer':'mouse registration shared with the interrupt path',
 'configure':'device endpoint publication shared with event handling',
 'bulk':'polled bulk transfer and ring completion state',
 'command_now':'polled command ring and completion state',
 'control_now':'polled control transfer and completion state',
 'discard_allocations':'controller-owned frames and slot allocation rollback',
 'detach':'unlink/stop device records before freeing their DMA buffers',
}
locks = {
 'console':'whole kernel log lines, NOT every console or screen access',
 'heap':'heap free lists, page descriptors, class allocation and mappings',
 'net':'network rings, DMA descriptors, counters and transmit staging',
 'arp':'neighbor cache, pending queues and shared ARP composition frame',
 'ip':'IP identification, transmit frame and loopback queue',
 'icmp':'echo request state and error-rate limiter',
 'udp':'socket records, rings and shared UDP composition frame',
 'tcp':'connection/listener/time-wait tables, timers and transmit frame',
}
import re
result = []
for kind, path, line, fn, code in rows:
    if kind not in ('irq-save','lock'):
        continue
    module = Path(path).parts[1]
    if kind == 'lock':
        m = re.search(r'sync\.acquire\(sync\.(\w+)\(', code)
        what = locks[m[1]] if m else 'test lock/counter selected by the scheduling witness'
        need = 'retain atomic exclusion; make every competing access use the same lock and enforce lock order'
    elif module.startswith('kmain_') or module in ('heapthreads','pax_tour','schedtest'):
        what = 'boot/test orchestration: spawn/await, snapshots or final halt; no secondary CPU currently enters it'
        need = 'boot CPU owns initialization; test snapshots need all-CPU quiescence, not just local IF clear'
    else:
        what = protection[module]
        if module == 'xhci': what = xhci[fn]
        need = 'big kernel lock first; then an owner lock/lifetime protocol covering IRQ and thread callers'
        if module == 'sync': need = 'keep IF save on the invoking stack; callers must separately exclude remote CPUs'
    result.append({'site':f'{path}:{line}', 'function':fn, 'protection':what, 'needed':need})
print(json.dumps(result, indent=2))
