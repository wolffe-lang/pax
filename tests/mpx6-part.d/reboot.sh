echo part: start
if [ -f /home/pax/notes.txt ]; then
    echo part: the second boot
    cat /home/pax/notes.txt
    echo part: end
else
    echo part: the first boot
    echo "written before the reboot" > /home/pax/notes.txt
    cat /home/pax/notes.txt
    /bin/reboot
    echo part: reboot returned
fi
