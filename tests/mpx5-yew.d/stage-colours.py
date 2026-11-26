#!/usr/bin/env python3
"""Stage only verified outputs of the editor suite into the SSH rig's root."""
import hashlib
from pathlib import Path
import re
import shutil
import sys


def stage(images, root, repository):
    match = re.search(r'^YEW_REV=([0-9a-f]{40})$', (repository / 'user/yew.pin').read_text(), re.M)
    if match is None:
        raise ValueError('no literal editor revision')
    source = (images / 'yew/source.txt').read_text().splitlines()
    if not source or source[0] != 'yew ' + match[1]:
        raise ValueError('editor input source revision differs from the current pin')
    for project, name in (('yew', 'yew'), ('termwolf', 'termwolf')):
        fields = (images / project / 'sums.txt').read_text().split()
        data = (images / project / name).read_bytes()
        if (len(fields) != 3 or fields[0] != name
                or hashlib.sha256(data).hexdigest() != fields[1] or len(data) != int(fields[2])):
            raise ValueError(name + ' differs from its builder sums')
        target = root / 'bin' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(images / project / name, target)
        target.chmod(0o755)
    sample = root / 'home/pax/keyword.lu'
    sample.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(repository / 'tests/mpx5-yew.d/keyword.lu', sample)
    sample.chmod(0o644)


if __name__ == '__main__':
    try:
        stage(*(Path(arg) for arg in sys.argv[1:]))
    except (OSError, ValueError) as error:
        print('FAIL yew-ssh-staged-input ' + str(error), flush=True)
        raise SystemExit(1)
    print('PASS yew-ssh-staged-input source revision and both builder sums', flush=True)
