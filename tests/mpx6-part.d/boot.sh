echo part: start
echo part: begin partitions
cat /proc/partitions
echo part: end partitions
ls -ln /home
stat -c '%n %D %u:%g %a' /home /home/pax
echo "a note on the disk that booted" > /home/pax/notes.txt
cat /home/pax/notes.txt
echo part: end
