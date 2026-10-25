#!/usr/bin/env python3
"""Every external status stays loud; persisted phases and argv are independent."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

program,work=map(Path,sys.argv[1:]);work.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=work,prefix='executor-') as tmp:
    w=Path(tmp)
    mock=w/'mock'
    mock.write_text('#!/usr/bin/python3\nimport json,sys\nprint(json.dumps(sys.argv[2:]))\n'
                    'print("error: planted zero-exit diagnostic" if sys.argv[1]=="diagnostic" else "ok")\n'
                    'sys.exit(0 if sys.argv[1]=="diagnostic" else int(sys.argv[1]))\n')
    mock.chmod(0o755)
    for status in ['0','1','2','127','diagnostic']:
        d=w/status;d.mkdir();disk=d/'log.img';disk.write_bytes(bytes(131072))
        p=subprocess.run([program,disk,mock,d,status],capture_output=True,text=True)
        expected=0 if status=='0' else 1
        assert p.returncode==expected,(status,p.stdout,p.stderr)
        records=[json.loads(x) for x in disk.read_bytes()[65536:].split(b'\0',1)[0].splitlines()]
        assert records[0]['state']=='started'
        assert records[-1]['state']==('durable' if status=='0' else 'failed'),records
        assert json.loads((d/'witness.out').read_text().splitlines()[0])==['literal; $(touch NEVER)','two words']
        assert not (d/'NEVER').exists()
        if status=='2': assert 'exit=2' in records[-1]['detail']
        print('PASS I-external-'+status+': status/diagnostic checked and phase persisted; argv literal')
