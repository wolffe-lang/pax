#!/usr/bin/env python3
"""The judge of one leg of tests/distribution-warren: warren's console rows' transcript into the suite's rows.

    judge.py INDEX FIRMWARE KEYBOARD ASKED EXIT TRANSCRIPT

INDEX is the leg's place in --legs (1 for W1, 2 for W2), ASKED the comma list of rows the leg was asked, EXIT the
exit status of warren's tests/pax/console_rows.py, TRANSCRIPT its output. For each asked row Cn it prints one suite
row `PASS Wi-Cn FIRMWARE KEYBOARD: …` or `FAIL Wi-Cn …`: a row passes only when the transcript holds exactly one
`PASS Cn FIRMWARE KEYBOARD:` line and no FAIL line for it. A row that printed nothing fails; it is never a skip.
Then the leg's own row, `PASS Wi …` or `FAIL Wi …`, which fails when the transcript has no one CONSOLE-ROWS line
for this firmware and keyboard (the leg did not finish), when that line says PASS while an asked row printed no
PASS, when the exit is 0 while an asked row printed no PASS, or when the exit is not 0 while every asked row
passed. The exit is 0 only when every row it printed passed.
"""
import re
import sys
from pathlib import Path

ROW = re.compile(r'^(PASS|FAIL) (C[0-9]+) (\S+) (\S+): ?(.*)$')


def judge(index, fw, kbd, asked, rc, text):
    """Returns (held, lines): the suite's rows for this leg, each line also printed."""
    leg = f'W{index}'
    lines = text.splitlines()
    seen = {}
    for line in lines:
        m = ROW.match(line)
        if m and m[3] == fw and m[4] == kbd:
            seen.setdefault(m[2], []).append((m[1], m[5]))
    out = []

    def say(ok, name, what):
        out.append(f'{"PASS" if ok else "FAIL"} {name} {fw} {kbd}: {what}')
        print(out[-1], flush=True)

    no_pass = []
    for r in asked:
        got = seen.get(r, [])
        if not any(v == 'PASS' for v, _ in got):
            no_pass.append(r)
        if len(got) == 1 and got[0][0] == 'PASS':
            say(True, f'{leg}-{r}', got[0][1][:300])
        elif not got:
            say(False, f'{leg}-{r}', 'printed nothing (a row that printed nothing fails; it is never a skip)')
        elif len(got) > 1:
            say(False, f'{leg}-{r}', 'printed %d times: %s' % (len(got), ' / '.join(v for v, _ in got)))
        else:
            say(False, f'{leg}-{r}', got[0][1][:300])
    extra = sorted(set(seen) - set(asked), key=lambda r: int(r[1:]))
    summary = [line for line in lines if line.startswith(f'CONSOLE-ROWS {fw} {kbd}: ')]
    why = []
    if len(summary) != 1:
        why.append('%s CONSOLE-ROWS line for %s %s: the leg did not finish' % ('no' if not summary else str(len(summary)), fw, kbd))
    elif summary[0].split(': ', 1)[1].startswith('PASS') and no_pass:
        why.append('its CONSOLE-ROWS line says PASS, and %s printed no PASS' % ','.join(no_pass))
    if rc == 0 and no_pass:
        why.append('exit 0, and %s printed no PASS' % ','.join(no_pass))
    if rc != 0 and not no_pass and len(seen) and all(len(seen.get(r, [])) == 1 for r in asked):
        why.append(f'exit {rc} with every asked row PASS')
    if why:
        say(False, leg, '; '.join(why))
    else:
        say(True, leg, f'{len(asked)} rows asked, exit {rc}' + (f'; rows not asked, printed: {",".join(extra)}' if extra else ''))
    return all(line.startswith('PASS ') for line in out), out


def main(argv):
    if len(argv) != 6:
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 2
    index, fw, kbd, asked, rc, transcript = argv
    text = Path(transcript).read_text(errors='replace') if Path(transcript).exists() else ''
    return 0 if judge(int(index), fw, kbd, asked.split(','), int(rc), text)[0] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
