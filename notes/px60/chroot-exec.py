#!/usr/bin/env python3
"""Census launcher; used only inside px60's throwaway container."""
import os
import sys
os.chroot(sys.argv[1])
os.chdir("/")
os.environ.update(PATH="/usr/bin:/bin", HOME="/", WOLF_STD="/usr/share/wolf/std")
os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
