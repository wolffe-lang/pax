{ i=0; while [ $i -lt 30000 ]; do echo $i; i=$((i+1)); done; : > finished; } | head -n 1
ls
f() { i=0; while [ $i -lt 30000 ]; do printf '%s\n' line; i=$((i+1)); done; : > finished2; }; f | sed -n 2q
ls; echo after
