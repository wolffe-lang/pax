yes | head -n 3
{ echo first; sleep 1; [ -f got ] && : > concurrent; } | { read a; : > got; }
ls
