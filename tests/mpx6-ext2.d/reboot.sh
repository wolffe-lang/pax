echo reboot: start
if [ -f /home/pax/notes.txt ]; then
    echo reboot: the second boot
    cat /home/pax/notes.txt
    ls -l /home/pax
    echo reboot: end
else
    echo reboot: the first boot
    ls -la /home/pax
    echo "a note that outlives the power going off" > /home/pax/notes.txt
    chown 1000:1000 /home/pax/notes.txt
    ls -l /home/pax
    /bin/reboot
    echo reboot: reboot returned
fi
