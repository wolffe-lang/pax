import json, pathlib, subprocess, sys, time
label, out, *command = sys.argv[1:]
p = pathlib.Path(out)
start = time.monotonic()
with p.with_suffix('.controller.log').open('wb') as log:
    child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    while True:
        try:
            rc = child.wait(timeout=60)
            break
        except subprocess.TimeoutExpired:
            serial = p.with_suffix('.serial.log')
            data = serial.read_bytes() if serial.exists() else b''
            print(f'{label}: {time.monotonic()-start:.1f}s, completed child exits {data.count(b"exit_group 0 after 1 runs")}', flush=True)
result = {'label': label, 'seconds': time.monotonic()-start, 'rc': rc}
p.with_suffix('.timing.json').write_text(json.dumps(result)+'\n')
print(json.dumps(result), flush=True)
if rc:
    print(p.with_suffix('.controller.log').read_text(), flush=True)
sys.exit(rc)
