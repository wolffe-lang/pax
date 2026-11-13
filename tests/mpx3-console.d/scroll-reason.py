#!/usr/bin/env python3
"""Validate the complete scroll reason, not an arbitrary suffix.

The legacy form remains valid for previously built --images inputs. The
current detailed form must report exactly five costs per direction and
its declared minima must agree with them. Timings are measurements, not
fixed performance limits. Forced ways and no display remain distinct.
"""
import re
import sys

NUM = r'[0-9]+'
PREFIX = rf'read ({NUM}), write ({NUM}) cycles; copy when read <= ({NUM}) x write'
COSTS = rf'{NUM}(?:,{NUM}){{4}}'
DETAIL = (PREFIX + rf'; minimum of 5 samples; reads \[({COSTS})\]; '
          rf'writes \[({COSTS})\]; window ({NUM}) cycles, ({NUM}) us'
          r'(?:; injected (outlier|slow))?')


def validate(way, reason):
    forced = {'fbread': 'copy', 'fbwrite': 'redraw', 'no screen': 'none'}
    if reason in forced:
        expected = forced[reason]
        return None if way == expected else f'by {way}, though {reason!r} requires {expected}'
    match = re.fullmatch(PREFIX, reason)
    detailed = False
    if match is None:
        match = re.fullmatch(DETAIL, reason)
        detailed = True
    if match is None:
        return 'the way has an unrecognized or incomplete probe reason: ' + repr(reason)
    read, write, factor = map(int, match.group(1, 2, 3))
    if detailed:
        reads = [int(n) for n in match[4].split(',')]
        writes = [int(n) for n in match[5].split(',')]
        if read != min(reads) or write != min(writes):
            return 'the printed minima disagree with the five retained samples: ' + repr(reason)
    expected = 'copy' if read <= factor * write else 'redraw'
    return None if way == expected else f'by {way}, but its probe numbers require {expected}: {reason!r}'


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: scroll-reason.py WAY REASON')
    error = validate(*sys.argv[1:])
    if error is not None:
        print(error)
        raise SystemExit(1)
