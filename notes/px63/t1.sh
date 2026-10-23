echo t1: start
ls -l /mnt
stat /mnt
cat /mnt/hello.txt
echo "written on PAX" > /mnt/pax-was-here.txt
mkdir /mnt/newdir
echo inside > /mnt/newdir/f
ls -l /mnt /mnt/newdir
cat /mnt/pax-was-here.txt /mnt/newdir/f
/bin/disk read /mnt
echo t1: end
