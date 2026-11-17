#!/usr/bin/env python3
"""Reproducible textual census, not a proof of concurrency safety.

Emit every explicit irq-save/lock site, top-level mutable scalar, assembly
storage label, and TLB invalidation/free-user call. Comments and strings are
removed before matching; source lines and containing wolf functions survive.
Implicit exclusion of entire syscalls and handlers still needs manual review.
The generated inventory is intentionally exhaustive, including
boot-only state and test kernels, rather than silently judging them safe.
"""
import argparse
import json
from pathlib import Path
import re


def code_only(text):
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"'
    return re.sub(pattern, lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]), text)


def inventory(root):
    rows = []
    for path in sorted((root / 'kernel').rglob('*.lu')):
        clean = code_only(path.read_text())
        fn = '<module>'
        depth = 0
        for no, line in enumerate(clean.splitlines(), 1):
            match = re.search(r'\bfn\s+(\w+)\s*\(', line)
            if match:
                fn = match[1]
            patterns = [('irq-save', r'\b(?:sync\.irq_save|pax_irq_save)\s*\('),
                        ('lock', r'\bsync\.acquire\s*\('),
                        ('tlb', r'\bpax_(?:invlpg|set_cr3)\s*\('),
                        ('space-free', r'\bpaging\.free_user\s*\('),
                        ('mapping-change', r'\bpaging\.(?:unmap|protect_user)\s*\(')]
            for kind, pattern in patterns:
                if re.search(pattern, line) and not line.lstrip().startswith('extern '):
                    rows.append([kind, str(path.relative_to(root)), no, fn, line.strip()])
            if depth == 0 and re.match(r'\s*(?:pub\s+)?var\s+', line):
                rows.append(['global', str(path.relative_to(root)), no, '<module>', line.strip()])
            depth += line.count('{') - line.count('}')
            if depth == 0:
                fn = '<module>'
    for path in sorted((root / 'boot').glob('*.S')):
        clean = code_only(path.read_text())
        section = ''
        label = ''
        for no, line in enumerate(clean.splitlines(), 1):
            if '.section' in line or line.strip() in ('.text', '.data', '.bss'):
                section = line.strip()
            m = re.match(r'(pax_\w+):', line)
            if m:
                label = m[1]
                if '.bss' in section:
                    rows.append(['assembly-state', str(path.relative_to(root)), no, label, section])
            if re.match(r'\s*cli\b', line):
                rows.append(['cli', str(path.relative_to(root)), no, label, 'cli'])
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--check', type=Path)
    a = ap.parse_args()
    rows = inventory(a.root)
    if a.check:
        expected = json.loads(a.check.read_text())
        if rows != expected:
            print('FAIL CPU-INVENTORY source sites changed; regenerate and review the census')
            raise SystemExit(1)
        print(f'PASS CPU-INVENTORY {len(rows)} source sites')
    else:
        print(json.dumps(rows, indent=2))
