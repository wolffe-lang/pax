#!/bin/sh
# ext4.py's walk in the Linux guest (tools/linux-blk, the image at /mnt): every name but lost+found's, sorted, as
# `walk: PATH MODEHEX SIZE WHAT` (WHAT a file's sha256, a link's target, a directory's -), then the count of
# `EXT4-fs error` lines the kernel logged. The guest's /bin/sh is busybox; its applets live in /usr/bin.
export PATH=/usr/bin:/bin
cd /mnt || exit 2
find . -mindepth 1 ! -path './lost+found*' | sort | while read -r p; do
    p=${p#./}; m=$(stat -c %f "$p"); s=$(stat -c %s "$p")
    if [ -L "$p" ]; then w=$(readlink "$p"); elif [ -d "$p" ]; then w=-; else w=$(sha256sum "$p" | cut -d' ' -f1); fi
    echo "walk: $p $m $s $w"
done
echo "walk-errors: $(dmesg | grep -c 'EXT4-fs error')"
