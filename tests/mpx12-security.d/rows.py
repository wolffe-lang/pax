"""tests/mpx12-security.d/rows.py — the rows of tests/mpx12-security (its header has each).

    rows.py WORK KERNEL.elf TIER FIRMWARE...

Builds the probe (probe.c, static, no libc) and one archive whose /etc/pax-run runs it three times
(`secprobe addr` twice, then `secprobe`), makes an ISO with the console kernel KERNEL, and boots it
on each firmware in each CPU mode: `kvm-host` (KVM, `-cpu host`; only where /dev/kvm is usable, and a
loud SKIP elsewhere unless PAX_REQUIRE_KVM=1), `tcg-max` (TCG, `-cpu max`) and `tcg-qemu64` (TCG,
`-cpu qemu64`: no SMEP, SMAP or UMIP). tools/qemu-halt proves each halt and keeps the monitor's
`info registers` (CR0, CR4, EFER) and `info tlb` (every page's NX and W bits) of the halted machine.
Prints PASS, FAIL, SKIP and MEASURE lines at column 0; exits 1 when any row failed."""
import os
import re
import subprocess
import sys
from pathlib import Path

WORK, KERNEL, TIER = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
LEGS = sys.argv[4:]
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NAMES = ['nx', 'wp', 'smep', 'smap', 'umip', 'kernel-wx', 'kstack-guard', 'ist-guard', 'kpti', 'ibrs',
         'arch-capabilities', 'aslr', 'user-wx', 'stack-nx', 'null-page']
CPU_BOUND = {'smep', 'smap', 'umip', 'ibrs'}  # on, off, or absent when the CPU lacks it
# The census's measured state of what ring 3 cannot see (each its own scripted witness elsewhere:
# kpti tests/mpx3-user U2's shared kernel half, kstack-guard tests/mpx2-sched S5's overflow into the
# guard). A later stage that changes one changes this line in the same commit.
KERNEL_STATE = {'kstack-guard': 'on', 'kpti': 'off'}
CR0_WP, CR4_UMIP, CR4_SMEP, CR4_SMAP, EFER_NXE = 1 << 16, 1 << 11, 1 << 20, 1 << 21, 1 << 11
bad = False


def say(s):
    print(s, flush=True)


def fail(row, why):
    global bad
    bad = True
    say(f'FAIL {row}: {why}')


def run(argv, **kw):
    r = subprocess.run([str(x) for x in argv], capture_output=True, **kw)
    if r.returncode:
        raise RuntimeError(f'{argv[:2]}: exit {r.returncode}: {r.stderr.decode(errors="replace")[-600:]}')
    return r


def build():
    a = WORK / 'in'
    a.mkdir(parents=True, exist_ok=True)
    probe = a / 'secprobe'
    run(['cc', '-static', '-nostdlib', '-ffreestanding', '-fno-pie', '-no-pie', '-fno-stack-protector', '-O1',
         '-w', '-o', probe, HERE / 'probe.c'])
    (a / 'pax-run').write_text('/bin/secprobe addr\n/bin/secprobe addr\n/bin/secprobe\n')
    cpio = WORK / 'security.cpio'
    run([ROOT / 'tools/mkinitramfs', cpio, '/dev/', '/proc/', '/sys/', '/tmp/:1777', f'/bin/secprobe={probe}',
         f'/etc/pax-run={a / "pax-run"}'])
    conf = WORK / 'security.conf'
    conf.write_text('timeout: 0\nquiet: yes\n\n/PAX\n    protocol: limine\n    path: boot():/boot/pax\n'
                    '    module_path: boot():/boot/initramfs.cpio\n    cmdline: nonet pax.nobeep pax.nomarks\n')
    iso = WORK / 'security.iso'
    run([ROOT / 'tools/mkimage', '--conf', conf, '--add', cpio, 'initramfs.cpio', KERNEL, iso])
    return iso


def modes():
    kvm = os.access('/dev/kvm', os.R_OK | os.W_OK)
    out = []
    if kvm:
        out.append(('kvm-host', 'kvm', 'host'))
    elif os.environ.get('PAX_REQUIRE_KVM') == '1':
        fail('S0', 'PAX_REQUIRE_KVM=1 and /dev/kvm is not usable')
    else:
        say(f'SKIP S-kvm-host {TIER} reason=no-usable-dev-kvm (not measured: the KVM -cpu host rows ran nowhere here)')
    out += [('tcg-max', 'tcg', None), ('tcg-qemu64', 'tcg', 'qemu64')]
    return out


def boot(iso, leg, mode, accel, cpu):
    d = WORK / f'{leg}-{mode}'
    d.mkdir(parents=True, exist_ok=True)
    log = d / 'serial.log'
    argv = [ROOT / 'tools/qemu-halt', '--firmware', leg, '--accel', accel, '--serial', log, '--timeout', '600',
            '--no-screen', '--elf', KERNEL, '--marker', 'halt|PANIC .*', '--cmd', 'info tlb',
            '--qemu', '-m', '--qemu', '512M']
    if cpu:
        argv += ['--qemu', '-cpu', '--qemu', cpu]
    argv.append(iso)
    r = subprocess.run([str(x) for x in argv], capture_output=True)
    (d / 'qemu-halt.out').write_bytes(r.stdout + r.stderr)
    text = log.read_bytes().decode('latin-1').replace('\r', '') if log.exists() else ''
    regs = Path(str(log) + '.halt').read_text(errors='replace') if Path(str(log) + '.halt').exists() else ''
    tlb = Path(str(log) + '.cmd1').read_text(errors='replace') if Path(str(log) + '.cmd1').exists() else ''
    return r.returncode, text, regs, tlb


def reg(regs, name):
    m = re.findall(rf'\b{name}=([0-9a-f]+)', regs)
    return int(m[-1], 16) if m else None


def parse(block):
    out = []
    for line in block.split('\n'):
        if line:
            out.append(line.split(' '))
    return out


def blocks(text):
    got = {}
    for k in ('1', '2'):
        m = re.search(rf'^px146: BEGIN pax-security {k}\n(.*?)^px146: END pax-security {k}$', text, re.M | re.S)
        got[k] = m.group(1) if m else None
    return got


def ist_guard_from_elf():
    """'off' when the page below some IST stack lies inside the image (the kernel maps the whole image,
    so that page is mapped); 'on' otherwise. From `nm` of the kernel, a black box."""
    syms = {}
    for line in run(['nm', KERNEL]).stdout.decode().splitlines():
        p = line.split()
        if len(p) == 3:
            syms[p[2]] = int(p[0], 16)
    lo = syms.get('__pax_image_start')
    hi = syms.get('__pax_image_end')
    stacks = [syms.get(f'pax_ist{i}_stack') for i in range(1, 5)]
    if lo is None or hi is None or None in stacks:
        return None
    below = [(s & ~0xfff) - 1 for s in stacks]
    return 'off' if any(lo <= b < hi for b in below) else 'on'


def kernel_wx_from_tlb(tlb):
    """(pages seen in the kernel half, pages both writable and executable there) from `info tlb`:
    `ADDR: PHYS FLAGS`, FLAGS QEMU's nine (X for NX, then G, PS, D, A, PCD, PWT, U, W) with '-' for clear."""
    seen = wx = 0
    for line in tlb.splitlines():
        m = re.match(r'\s*([0-9a-f]{16}): [0-9a-f]+ (\S{9})\s*$', line)
        if not m:
            continue
        va, fl = int(m.group(1), 16), m.group(2)
        if va < 0xffff800000000000:
            continue
        seen += 1
        if fl[0] != 'X' and fl[8] == 'W':
            wx += 1
    return seen, wx


def check(leg, mode, rc, text, regs, tlb, ist_elf):
    tag = f'{TIER} {leg} {mode}'
    if rc != 0 or 'px146: probe done' not in text:
        tail = ' | '.join(text.strip().split('\n')[-4:])
        fail(f'S1 {tag}', f'the boot did not run the probe to its end and halt (qemu-halt {rc}); last lines: {tail}')
        return
    got = blocks(text)
    lines = parse(got['1'] or '')
    names = [l[0] for l in lines]
    state = {l[0]: (l[1] if len(l) == 2 else None) for l in lines}
    why = []
    if got['1'] is None:
        why.append('no /proc/pax-security block')
    elif got['1'] != got['2']:
        why.append('two reads differ')
    if names != NAMES:
        why.append(f'names {names} are not {NAMES}')
    for n, s in state.items():
        ok = s in (('on', 'off', 'absent') if n in CPU_BOUND else ('on', 'off'))
        if n == 'arch-capabilities':
            ok = s == 'absent' or bool(s and re.fullmatch(r'0x[0-9a-f]{16}', s))
        if not ok:
            why.append(f'{n} {s!r} is not a state')
    if why:
        fail(f'S1 {tag}', '; '.join(why) + ' — ' + repr((got['1'] or text[-300:])[:400]))
        return
    say(f'PASS S1 {tag}: /proc/pax-security read twice in seven-byte reads, the same {len(NAMES)} lines in order, each a state')
    say(f'MEASURE {tag} ' + ' '.join(f'{n}={state[n]}' for n in NAMES))

    cpu = re.search(r'^px146: cpuid nx (\d) smep (\d) smap (\d) umip (\d) ibrs (\d) arch-capabilities (\d)$', text, re.M)
    cr0, cr4, efer = reg(regs, 'CR0'), reg(regs, 'CR4'), reg(regs, 'EFER')
    boot_line = re.search(r'^user: syscall .* smep (\d), smap (\d)$', text, re.M)
    why = []
    if not cpu or cr0 is None or cr4 is None or efer is None:
        fail(f'S2 {tag}', f'no CPUID line or no CR0/CR4/EFER in the halted machine (cpuid {bool(cpu)}, regs {cr0} {cr4} {efer})')
    else:
        has = dict(zip(['nx', 'smep', 'smap', 'umip', 'ibrs', 'arch-capabilities'], [c == '1' for c in cpu.groups()]))
        bits = {'smep': cr4 & CR4_SMEP, 'smap': cr4 & CR4_SMAP, 'umip': cr4 & CR4_UMIP}
        for n in ('smep', 'smap', 'umip'):
            want = ('on' if bits[n] else 'off') if has[n] else 'absent'
            if state[n] != want:
                why.append(f'{n} says {state[n]}, CPUID {int(has[n])} and CR4 bit {int(bool(bits[n]))} say {want}')
        if state['nx'] != ('on' if efer & EFER_NXE else 'off'):
            why.append(f'nx says {state["nx"]}, EFER {efer:#x}')
        if state['wp'] != ('on' if cr0 & CR0_WP else 'off'):
            why.append(f'wp says {state["wp"]}, CR0 {cr0:#x}')
        if boot_line and (boot_line.group(1) == '1') != (state['smep'] == 'on'):
            why.append(f'the boot line says smep {boot_line.group(1)}')
        if boot_line and (boot_line.group(2) == '1') != (state['smap'] == 'on'):
            why.append(f'the boot line says smap {boot_line.group(2)}')
        if (state['ibrs'] == 'absent') == has['ibrs']:
            why.append(f'ibrs says {state["ibrs"]}, CPUID.7.EDX[26] {int(has["ibrs"])}')
        if (state['arch-capabilities'] == 'absent') == has['arch-capabilities']:
            why.append(f'arch-capabilities says {state["arch-capabilities"]}, CPUID.7.EDX[29] {int(has["arch-capabilities"])}')
        if why:
            fail(f'S2 {tag}', '; '.join(why))
        else:
            say(f'PASS S2 {tag}: nx, wp, smep, smap and umip agree with the halted machine\'s EFER {efer:#x}, CR0 {cr0:#x} '
                f'and CR4 {cr4:#x} and with CPUID in ring 3; ibrs and arch-capabilities with CPUID')

    def wit(row, name, says, expect_if_on, expect_if_off, what):
        m = re.search(rf'^px146: witness {name} (.*)$', text, re.M)
        seen = m.group(1) if m else None
        want = expect_if_on if says == 'on' else expect_if_off
        if seen != want:
            fail(f'{row} {tag}', f'{name}: /proc/pax-security says {says}, so {what} should give {want!r}; it gave {seen!r}')
        else:
            say(f'PASS {row} {tag}: {name} {says}: {what} gave {seen!r}')

    wit('S3', 'nx-exec', state['nx'], 'segv', 'ran', 'a call into a read-write page')
    wit('S4', 'umip', 'on' if state['umip'] == 'on' else 'off', 'segv', 'ran', 'SGDT in ring 3')
    wit('S5', 'user-wx', state['user-wx'], 'mmap err -13 mprotect err -13', 'mmap ok mprotect ok',
        'PROT_READ|PROT_WRITE|PROT_EXEC by mmap and by mprotect')
    wit('S6', 'null-page', state['null-page'], 'err -12', 'ok', 'mmap MAP_FIXED of address 0')
    addrs = re.findall(r'^px146: addr (.*)$', text, re.M)
    if len(addrs) != 2:
        fail(f'S7 {tag}', f'{len(addrs)} addr lines, not 2')
    elif (addrs[0] == addrs[1]) != (state['aslr'] == 'off'):
        fail(f'S7 {tag}', f'aslr says {state["aslr"]}, and two runs gave {addrs[0]!r} and {addrs[1]!r}')
    else:
        say(f'PASS S7 {tag}: aslr {state["aslr"]}: two runs placed stack, mmap, brk and text {"the same" if addrs[0] == addrs[1] else "apart"} ({addrs[0]})')
    wit('S8', 'stack-nx', state['stack-nx'], 'segv', 'ran', 'a call onto the stack')

    why = []
    for n, v in KERNEL_STATE.items():
        if state[n] != v:
            why.append(f'{n} says {state[n]}, the census measured {v} (change this row with the stage that changes it)')
    if ist_elf is None:
        why.append('no IST or image symbols in the kernel')
    elif state['ist-guard'] != ist_elf:
        why.append(f'ist-guard says {state["ist-guard"]}, the image places a mapped page below an IST stack: {ist_elf}')
    seen, wx = kernel_wx_from_tlb(tlb)
    if seen == 0:
        why.append('no kernel-half page in the halted machine\'s info tlb')
    elif state['kernel-wx'] != ('on' if wx == 0 else 'off'):
        why.append(f'kernel-wx says {state["kernel-wx"]}, info tlb has {wx} writable executable kernel pages of {seen}')
    if why:
        fail(f'S9 {tag}', '; '.join(why))
    else:
        say(f'PASS S9 {tag}: kernel-wx {state["kernel-wx"]} ({seen} kernel pages in info tlb, {wx} W+X), '
            f'ist-guard {state["ist-guard"]} (the image\'s symbols), kstack-guard {state["kstack-guard"]}, kpti {state["kpti"]}')


def main():
    try:
        iso = build()
    except RuntimeError as e:
        fail(f'S0 {TIER}', f'build: {e}')
        return
    ist_elf = ist_guard_from_elf()
    for leg in LEGS:
        for mode, accel, cpu in modes():
            rc, text, regs, tlb = boot(iso, leg, mode, accel, cpu)
            check(leg, mode, rc, text, regs, tlb, ist_elf)


main()
sys.exit(1 if bad else 0)
