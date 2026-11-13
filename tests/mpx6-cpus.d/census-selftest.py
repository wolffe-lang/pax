#!/usr/bin/env python3
"""Exercise the census scanner on deliberately small independent fixtures."""
import importlib.util
import os
from pathlib import Path
import tempfile
import sys
sys.dont_write_bytecode = True

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cpu_census', root / 'tests/mpx6-cpus.d/census.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
    p = Path(tmp)
    (p / 'kernel').mkdir()
    (p / 'boot').mkdir()
    (p / 'kernel/test.lu').write_text('''// sync.irq_save() is only a comment
var shared: u64 = 0
pub fn work() {
    let text = "sync.acquire(sync.heap())"
    let s = sync.irq_save()
    unsafe { pax_irq_save() }
    let l = sync.acquire(sync.heap())
    paging.unmap(0, 0)
    paging.free_user(0)
}
''')
    (p / 'boot/test.S').write_text('.section .bss\npax_words:\n.zero 8\n.text\npax_entry:\ncli\n')
    rows = mod.inventory(p)
    got = [(r[0], r[3]) for r in rows]
    assert got == [('global','<module>'),('irq-save','work'),('irq-save','work'),('lock','work'),
                   ('mapping-change','work'),('space-free','work'),('assembly-state','pax_words'),('cli','pax_entry')], got
print('PASS CPU-SCANNER comments, strings, direct masking, state and containing functions')
