echo read: start
ls -l /mnt
ls -la /mnt/pax /mnt/links /mnt/modes /mnt/owners /mnt/times /mnt/names /mnt/big
ls -l /mnt/many | head -n 4
ls /mnt/many | wc -l
stat /mnt/hello.txt /mnt/pax/notes.txt /mnt/pax/notes-link /mnt/links/fast /mnt/links/slow /mnt/times/y2039 /mnt/owners/high /mnt/modes/sticky /mnt/big/hundred.bin
readlink /mnt/links/fast /mnt/links/slow /mnt/links/dangling
cat /mnt/hello.txt /mnt/pax/notes.txt /mnt/links/fast /mnt/deep/a/b/c/d/e/leaf.txt
wc -c /mnt/big/hundred.bin
/bin/disk read /mnt
/bin/disk sum /mnt/big/hundred.bin
echo read: end
