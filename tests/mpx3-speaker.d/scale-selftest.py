"""A stretched host capture is not a guest-clock fault; wrong ticks are."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('scale', Path(__file__).with_name('scale.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
want = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
notes = '\n'.join('tone %d start 0 end 1 length %s Hz %s' % (i, 651.8 if i == 6 else 480, hz)
                  for i, hz in enumerate(want))
events = '\n'.join('event %d tick %d on 100\nevent %d tick %d off 0' %
                   (i*2, i*50, i*2+1, i*50+48) for i in range(8))
assert m.check(notes, events, want).startswith('PASS ')
for name, n, e in [
    ('pitch', notes.replace('261.63', '280.0'), events),
    ('nonfinite', notes.replace('261.63', 'nan'), events),
    ('zero-capture', notes.replace('length 480', 'length 0'), events),
    ('hold', notes, events.replace('tick 48 off', 'tick 10 off')),
    ('onset', notes, events.replace('tick 50 on', 'tick 60 on')),
    ('missing-tones', '', events),
    ('missing-off', notes, events.rsplit('\n', 1)[0]),
]:
    assert m.check(n, e, want).startswith('FAIL '), name
    print('PASS K2 rejects ' + name)
print('PASS K2: capture stall accepted; frequency, onset and hold faults rejected')
