#!/bin/sh
# E4-linux-depth in the Linux guest: read /mnt/six, whose leaf's own depth field disagrees with its parent's, and
# say what the kernel did: `depth-read: STATUS` (cat's exit) and the count of `EXT4-fs error` lines it logged.
export PATH=/usr/bin:/bin
cat /mnt/six > /dev/null 2>&1
echo "depth-read: $?"
echo "depth-errors: $(dmesg | grep -c 'EXT4-fs error')"
