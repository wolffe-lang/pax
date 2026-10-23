echo write: start
/bin/disk clock
/bin/disk write /mnt/w
mkdir /mnt/sh
mkdir /mnt/sh/a
mkdir /mnt/sh/a/b
echo one > /mnt/sh/one.txt
echo appended >> /mnt/sh/one.txt
cp /mnt/sh/one.txt /mnt/sh/a/two.txt
mv /mnt/sh/a/two.txt /mnt/sh/a/b/three.txt
ln -s ../one.txt /mnt/sh/a/link
ln /mnt/sh/one.txt /mnt/sh/hard
chmod 600 /mnt/sh/one.txt
chown 1000:1000 /mnt/sh/a/b/three.txt
touch /mnt/sh/new-empty
cat /mnt/sh/a/link
rm /mnt/sh/a/link
rmdir /mnt/sh/a/b
cat /mnt/sh/a/b/three.txt /mnt/sh/hard
ls /mnt/sh /mnt/sh/a /mnt/sh/a/b
rm -r /mnt/sh/a
ls /mnt/sh
cat /mnt/pre/kept.txt
rm /mnt/pre/gone.txt
mv /mnt/pre/kept.txt /mnt/pre/moved.txt
ls /mnt /mnt/pre
echo write: end
