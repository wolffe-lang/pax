"""K2: capture proves pitch; the guest timeline proves onset and hold.

QEMU's WAV backend follows host progress. Its duration is diagnostic, not
a second independent clock for guest ticks (pax#202).
"""
import math
from pathlib import Path
import sys


def check(notes, timeline, want):
    tones = [line.split() for line in notes.splitlines() if line.startswith('tone ')]
    events = [line.split() for line in timeline.splitlines() if line.startswith('event ')]
    if len(tones) < len(want):
        return 'FAIL only %d tones in the capture' % len(tones)
    scale = tones[-len(want):]
    hz = [float(t[9]) for t in scale]
    lengths = [float(t[7]) for t in scale]
    bad = []
    for i, (h, w) in enumerate(zip(hz, want)):
        if not math.isfinite(h) or abs(h - w) / w > 0.01:
            bad.append('note %d %.2f Hz, table %.2f' % (i + 1, h, w))
    if any(not math.isfinite(v) or v <= 0 for v in lengths):
        bad.append('capture contains a nonpositive or nonfinite duration')
    ons = [(int(e[1]), int(e[3]), int(e[5])) for e in events if e[4] == 'on']
    if len(ons) < 8:
        return 'FAIL the kernel timeline has %d tones' % len(ons)
    next_tick = {int(a[1]): int(b[3]) - int(a[3])
                 for a, b in zip(events, events[1:]) if a[4] == 'on'}
    last = ons[-8:]
    starts = [tick for _, tick, _ in last]
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    for i, gap in enumerate(gaps):
        if abs(gap - 50) > 3:
            bad.append('onset %d is %d ticks after the one before' % (i + 2, gap))
    span = starts[-1] - starts[0]
    if abs(span - 350) > 3:
        bad.append('the onsets span %d ticks' % span)
    held = [next_tick.get(i, -1) for i, _, _ in last]
    for i, duration in enumerate(held):
        if abs(duration - 48) > 3:
            bad.append('note %d held %d ticks' % (i + 1, duration))
    summary = ('Hz ' + ' '.join('%.2f' % h for h in hz)
               + '; capture duration (diagnostic) ' + ' '.join('%.1f' % t for t in lengths) + ' ms'
               + '; kernel onsets ' + ' '.join(str(t) for t in gaps)
               + ' ticks, span %d, held ' % span + ' '.join(str(t) for t in held) + ' ticks')
    return ('FAIL ' + '; '.join(bad) + ' | ' if bad else 'PASS ') + summary


if __name__ == '__main__':
    try:
        print(check(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text(),
                    [float(x) for x in sys.argv[3:]]))
    except (ValueError, IndexError, OSError) as error:
        print('FAIL malformed K2 evidence: ' + str(error))
        sys.exit(1)
