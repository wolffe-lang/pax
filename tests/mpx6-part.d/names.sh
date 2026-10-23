echo part: start
echo part: begin partitions
cat /proc/partitions
echo part: end partitions
stat -c '%n %D' /home /mnt/a /mnt/b /mnt/c /mnt/d /mnt/e /mnt/f /mnt/g /mnt/h
echo part: end
