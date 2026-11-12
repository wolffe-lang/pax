#!/usr/bin/env python3
"""tests/distribution-ligature.d/judge.py SMALL.log BIG.log SMALL_MIB BIG_MIB HALT_SMALL HALT_BIG

The rows of tests/distribution-ligature, from the two typed sessions' serial logs (session.sh's `DLIG `
lines, ldtime's measurements among them). Prints `PASS <row>: …` or `FAIL <row>: …` at column 0 for each,
a MEASURE line per measured link, and exits 1 if any row failed. HALT_* are qemu-halt's exit codes."""
import re
import sys
from pathlib import Path

HELLO = 'hello from a program built on PAX|status=0|'
NETPROC = 'got: ping|reply: pong|child: hello from echo|child status: 0|status=0|'
PELT = 'pelt-ok|status=3|'
failed = []


def lines(path):
    raw = Path(path).read_bytes().decode('utf-8', 'replace')
    raw = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', raw).replace('\r', '\n')
    return raw.split('\n')


def dlig(text):
    return [l[5:] for l in text if l.startswith('DLIG ')]


def row(name, ok, detail):
    print(('PASS ' if ok else 'FAIL ') + name + ': ' + detail)
    if not ok:
        failed.append(name)


def builds(d):
    out = {}
    for l in d:
        m = re.match(r'build (\S+) (lig|lld) rc=(\d+) output=(yes|no)$', l)
        if m:
            out[(m[1], m[2])] = (int(m[3]), m[4] == 'yes')
    return out


def runs(d):
    out = {}
    for l in d:
        m = re.match(r'run (\S+) (\S+) ([0-9a-f]{16}) (.*)$', l)
        if m:
            out[(m[1], m[2])] = m[4]
    return out


def why(d, label):
    return [l.split(': ', 1)[1] for l in d if l.startswith('why ' + label + ': ')]


def first(d, prefix):
    return next((l for l in d if l.startswith(prefix)), None)


def main():
    small_log, big_log, small_mib, big_mib, halt_small, halt_big = sys.argv[1:7]
    s_text, b_text = lines(small_log), lines(big_log)
    s, b = dlig(s_text), dlig(b_text)
    sb, sr, bb, br = builds(s), runs(s), builds(b), runs(b)

    v = first(s, 'version ')
    rel = first(s, 'release ')
    row('L0-package', v is not None and v.startswith('version ligature ') and rel is not None and rel.startswith('release ligature ')
        and len(rel.split()) == 3, f'{v!r}, /etc/pax-release: {rel!r}')

    env = first(s, 'env ')
    d = first(s, 'default ')
    dd = first(s, 'digests ')
    shas = {k: h for k, h in (x.split('=') for x in dd.split()[1:]) if re.fullmatch(r'[0-9a-f]{64}', h)} if dd else {}
    note = d.split(' ', 2)[2] if d and len(d.split(' ', 2)) > 2 else ''
    row('L1-default-lld', env == 'env WOLF_LD=[unset]' and d is not None and d.startswith('default rc=0')
        and sr.get(('hello', 'default')) == HELLO and 'default' in shas and shas['default'] == shas.get('lld') and shas['default'] != shas.get('lig')
        and (note == '' or 'linking through /usr/bin/ld.lld' in note),
        f'{env!r}; the default build {d!r}; its program the bytes lld links ({shas.get("default", "?")[:16]}), not ligature\'s')

    o = first(s, 'optin ')
    row('L2-opt-in', o == 'optin rc=0 notes=0' and sr.get(('hello', 'optin')) == HELLO,
        f'WOLF_LD=/usr/bin/ligature: {o!r}, the program prints {sr.get(("hello", "optin"))!r}')

    row('L3-hello', sb.get(('hello', 'lig')) == (0, True) and sb.get(('hello', 'lld')) == (0, True)
        and sr.get(('hello', 'lig')) == HELLO == sr.get(('hello', 'lld')) and 'lig' in shas and shas.get('optin') == shas['lig'],
        f'ligature {sb.get(("hello", "lig"))}, lld {sb.get(("hello", "lld"))}; both print {HELLO!r}; two ligature links byte-identical ({shas.get("lig", "?")[:16]})')

    row('L4-net-process', sb.get(('netproc', 'lig')) == (0, True) and sb.get(('netproc', 'lld')) == (0, True)
        and sr.get(('netproc', 'lig')) == NETPROC == sr.get(('netproc', 'lld')),
        f'ligature {sb.get(("netproc", "lig"))}, lld {sb.get(("netproc", "lld"))}; {sr.get(("netproc", "lig"))!r} and {sr.get(("netproc", "lld"))!r}')

    self_line = first(s, 'self ')
    lv = sr.get(('ligature', 'lig'), '')
    row('L5-self-link', sb.get(('ligature', 'lig')) == (0, True) and sb.get(('ligature', 'lld')) == (0, True)
        and lv.startswith('ligature ') and lv == sr.get(('ligature', 'lld'))
        and self_line is not None and self_line.startswith('self rc=0 ') and 'lig' in shas and self_line.split()[2] == shas['lig'],
        f'ligature compiled and linked by itself on PAX prints {lv.split("|")[0]!r}; it links hello to the shipped ligature\'s bytes: {self_line!r}')

    r = first(s, 'refused ')
    rw = why(s, 'refused')
    row('L6-refusal', r is not None and re.match(r'refused rc=[1-9]\d* output=no$', r) is not None
        and any('selected linker' in w for w in rw) and any('ligature' in w for w in rw),
        f'{r!r}; {rw[:2]!r}')

    lig, lld = sb.get(('pelt', 'lig')), sb.get(('pelt', 'lld'))
    pw = why(s, 'pelt-lig')
    if lig is not None and lig[0] == 0:
        row('L7-pelt-at-small', False, f'ligature linked pelt at {small_mib} MiB: ligature#35 looks fixed, so this '
            'expected refusal must become a link row (and the default can be reconsidered)')
    else:
        row('L7-pelt-at-small', lig is not None and lig[1] is False and any('selected linker' in w for w in pw)
            and lld == (0, True) and sr.get(('pelt', 'lld')) == PELT,
            f'at {small_mib} MiB ligature refuses by name, no output, no fallback (ligature#35): {pw[:2]!r}; '
            f'lld links pelt and it prints {sr.get(("pelt", "lld"))!r}')

    for key, want in (('pelt', PELT), ('den', None)):
        got = (br.get((key, 'lig')), br.get((key, 'lld')))
        row(f'L8-{key}-at-big', bb.get((key, 'lig')) == (0, True) and bb.get((key, 'lld')) == (0, True)
            and got[0] is not None and got[0] == got[1] and (want is None or got[0] == want),
            f'{key} at {big_mib} MiB: ligature {bb.get((key, "lig"))}, lld {bb.get((key, "lld"))}; {got[0]!r} and {got[1]!r}')

    row('L8-den-by-lld-at-small', sb.get(('den', 'lld')) == (0, True)
        and sr.get(('den', 'lld')) is not None and sr.get(('den', 'lld')) == br.get(('den', 'lld')),
        f'den at {small_mib} MiB by lld: {sb.get(("den", "lld"))}, {sr.get(("den", "lld"))!r}')

    meas = []
    for text, mib in ((s, small_mib), (b, big_mib)):
        for l in text:
            m = re.match(r'ldtime (\S+) wall_ms=(\d+) user_ms=(\d+) sys_ms=(\d+) maxrss_kib=(\d+) status=(\d+)$', l)
            if m:
                meas.append((mib, m[1], int(m[2]), int(m[3]) + int(m[4]), int(m[5]), int(m[6])))
    for mib, label, wall, cpu, rss, st in meas:
        print(f'MEASURE guest={mib}MiB {label} wall_ms={wall} cpu_ms={cpu} peak_mib={rss / 1024:.0f} status={st}')
    want = {(small_mib, f'{n}-{l}') for n in ('hello', 'netproc', 'ligature') for l in ('lig', 'lld')} | \
           {(big_mib, f'{n}-{l}') for n in ('pelt', 'den') for l in ('lig', 'lld')} | {(small_mib, 'pelt-lld'), (small_mib, 'den-lld')}
    have = {(mib, label) for mib, label, wall, cpu, rss, st in meas if rss > 0 and st == 0}
    row('L9-measured', want <= have, f'{len(meas)} links measured (wait4: wall, CPU, peak); missing or empty: {sorted(want - have)}')

    clean = []
    for name, text, halt in (('small', s_text, halt_small), ('big', b_text, halt_big)):
        joined = '\n'.join(text)
        ok = halt == '0' and 'PAX: init /bin/env ended with status 0; nothing left to run' in joined \
            and not re.search(r'^PANIC ', joined, re.M) and f'end {name}' in dlig(text)
        clean.append(ok)
        row(f'L10-clean-{name}', ok, f'halt={halt}, the session reached its end, init ended with status 0, no panic')
    sys.exit(1 if failed else 0)


main()
