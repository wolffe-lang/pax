#!/usr/bin/env python3
"""Copy only public SSH evidence; never relax private fixture permissions."""
from pathlib import Path
import os,stat,sys


def export(source,target):
    source,target=Path(source),Path(target)
    target.mkdir(mode=0o755,parents=True);target.chmod(0o755)
    if not source.exists():
        print('SSH artifacts: no fixture output; retain other suite evidence',flush=True);return
    assert source.is_dir() and not source.is_symlink(),'invalid SSH fixture source'
    def failure(error):raise error
    for parent,dirs,names in os.walk(source,followlinks=False,onerror=failure):
        parent=Path(parent);dirs[:]=[n for n in dirs if not (parent/n).is_symlink()]
        for name in sorted(names):
            if not (name.endswith('.log') or (name.startswith('yew-ssh-') and name.endswith('.raw'))):continue
            src=parent/name
            if not stat.S_ISREG(src.lstat().st_mode):continue
            relative=src.relative_to(source);dst=target/relative;directory=target
            for part in relative.parts[:-1]:
                directory=directory/part
                if not directory.exists():directory.mkdir(mode=0o755);directory.chmod(0o755)
            with dst.open('xb') as stream:stream.write(src.read_bytes())
            dst.chmod(0o644)
            print('SSH artifact '+str(relative),flush=True)

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('usage: export-ssh.py SOURCE NEW_TARGET')
    export(*sys.argv[1:])
