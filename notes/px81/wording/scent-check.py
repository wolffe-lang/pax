from pathlib import Path
import runpy
import subprocess
root=Path('/home/mfwolffe/lanes/px81')
old={}
source=subprocess.run(['git','-C',str(root/'pax'),'show','1a52c4b7:tests/mpx5-scent.d/rows.py'],check=True,capture_output=True,text=True).stdout
exec(compile(source,'rows-at-1a52c4b7','exec'),old)
new=runpy.run_path(str(root/'pax/tests/mpx5-scent.d/rows.py'))
assert len(old['ROWS']) == len(new['ROWS']) == 49
for role in ('scent','scent-user'):
 p=root/'wording/ci-scent'/('mpx5-scent-native-bios-'+role+'.session.norm')
 text=p.read_text()
 before=old['held'](text.split('\n')); after=new['held'](text.split('\n'))
 assert len(before)==1 and 'pelt cannot pass byte FF' in before[0],before
 assert not after,after
 print('PASS',role,': old row RED, measured refusal GREEN; all49 rows retained')
 want=new['ROWS'][-3][1][-1]
 assert 'cannot be carried yet' in want,want
 for replacement in ('', 'grep: ?: No such file or directory',want.replace('line 50','line 49')):
  assert new['held'](text.replace(want,replacement).split('\n')),replacement
 print('PASS',role,': missing refusal, old substitution and wrong line number RED')
