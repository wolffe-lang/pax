#!/usr/bin/env python3
"""Linux-only RSS reference for the same snapshot/copy, never QEMU RSS."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
program,source,dest=map(Path,sys.argv[1:])
t=time.monotonic()
p=subprocess.Popen([program,source,dest,str(dest)+'.attrs'])
_,status,usage=os.wait4(p.pid,0)
p.returncode=os.waitstatus_to_exitcode(status)
assert p.returncode==0,p.returncode
print(json.dumps({'host':'Linux container; not PAX','workload':'source snapshot, copy, metadata, recheck',
                  'elapsed_seconds':round(time.monotonic()-t,3),'peak_rss_kib':usage.ru_maxrss,
                  'source_files':sum(x.is_file() for x in source.rglob('*'))}))
