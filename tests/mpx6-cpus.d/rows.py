"""The one CPU census row checks the boot and independently opened proc view."""
import pathlib
import re
import sys

text = pathlib.Path(sys.argv[1]).read_text(errors="replace").replace("\r", "")
n = sys.argv[2]
source = "unavailable" if n == "unknown" else "ACPI MADT"
disabled = int(sys.argv[3]) if len(sys.argv) > 3 else 0
line = f"processors: available {n}, active 1; source {source}"
extra = "" if n == "unknown" else f"online-capable 0\ndisabled {disabled}\n"
proc = f"CPU-PROC begin\navailable {n}\nactive 1\nsource {source}\n{extra}CPU-PROC end"
if text.count(line + "\n") != 1 or proc not in text:
    print(f"FAIL CPU-CENSUS smp={n}: boot summary or proc record differs")
    print(text)
    raise SystemExit(1)
print(f"PASS CPU-CENSUS smp={n}: available={n} active=1 boot=proc")
registers = pathlib.Path(sys.argv[1] + '.cmd1')
if n != 'unknown' and disabled == 0:
    if not registers.exists():
        print('FAIL CPU-PARKED missing all-processor register observation')
        raise SystemExit(1)
    ips = [int(v, 16) for v in re.findall(r'\b(?:RIP|EIP)=([0-9a-f]+)', registers.read_text())]
    if len(ips) != int(n) or not ips[0] >= 0xffffffff80000000 or any(ip >= 0xffffffff80000000 for ip in ips[1:]):
        print(f'FAIL CPU-PARKED unexpected processor instruction pointers: {ips}')
        raise SystemExit(1)
    print(f'PASS CPU-PARKED {len(ips)-1} secondary processors outside the kernel')
