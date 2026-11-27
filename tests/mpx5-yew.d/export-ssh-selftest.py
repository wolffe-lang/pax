#!/usr/bin/env python3
"""Private SSH fixtures stay private; only copied evidence is uploaded."""
from pathlib import Path
import runpy,stat,tempfile
ROOT=Path(__file__).resolve().parents[2]
job=(ROOT/'.github/workflows/ci.yml').read_text().split('\n  mpx5-yew:',1)[1].split('\n  mpx5-screen:',1)[0]
assert 'build/mpx5-burrowd-runs/**' not in job,'upload must not traverse the root-owned private SSH fixture'
assert 'build/yew-ssh-artifacts/' in job and 'export-ssh.py' in job,'SSH evidence exporter/upload missing'
export=runpy.run_path(str(Path(__file__).with_name('export-ssh.py')))['export']
with tempfile.TemporaryDirectory() as d:
 p=Path(d);source=p/'private';source.mkdir(mode=0o711)
 leg=source/'native-bios';leg.mkdir(mode=0o711);client=leg/'client';client.mkdir(mode=0o700)
 expected={'native-bios/client/yew-ssh-colour.raw':b'colour','native-bios/client/yew-ssh-session.raw':b'session','native-bios/client/ssh.log':b'client log','native-bios/serial.log':b'boot log'}
 for name,data in expected.items():(source/name).write_bytes(data)
 secret=client/'id_ed25519';secret.write_bytes(b'PRIVATE FIXTURE KEY');secret.chmod(0o600)
 before={str(f.relative_to(source)):stat.S_IMODE(f.stat().st_mode) for f in source.rglob('*')}
 target=p/'public';export(source,target)
 files={str(f.relative_to(target)):f.read_bytes() for f in target.rglob('*') if f.is_file()};assert files==expected
 assert before=={str(f.relative_to(source)):stat.S_IMODE(f.stat().st_mode) for f in source.rglob('*')},'export changed private fixture modes'
 for f in target.rglob('*'):assert stat.S_IMODE(f.stat().st_mode)==(0o755 if f.is_dir() else 0o644)
 assert stat.S_IMODE(target.stat().st_mode)==0o755
 # Missing setup still permits always() to upload the other suite evidence.
 export(p/'absent',p/'empty');assert not list((p/'empty').iterdir())
print('PASS SSH artifact isolation, exact evidence set, public modes and private-key exclusion')
