# sh20: corners of the forked shapes, each line's answer compared with dash's
( set -e; false; echo no ); echo "1 set-e: $?"
trap 'echo t-exit' EXIT; ( exit 3 ); echo "2 exit: $?"; trap - EXIT
( trap 'echo sub-exit' EXIT; echo in ); echo "3 sub-exit-trap"
f() { ( return 7 ); echo "4 r=$?"; }; f
x=$(exit 4); echo "5 cmdsub-exit: $?"
x=$( (exit 5) ); echo "6 nested: $?"
d=$(pwd); ( cd / && pwd ); [ "$(pwd)" = "$d" ] && echo "7 cwd kept"
umask 022; ( umask 077 ); echo "8 umask $(umask)"
a=1; ( a=2; echo "9 in $a" ); echo "9 out $a"
( echo "10 to-err" >&2 ) 2>&1 | cat
{ echo "11 a"; echo b >&2; } 2>/dev/null | cat
cat <<EOT | ( read l; echo "12 got $l" )
x
EOT
( sleep 0.1; echo "13 late" ) & wait $!; echo "13 st=$?"
exec 3>&1; ( echo "14 to3" >&3 ); exec 3>&-
for i in 1 2 3; do ( [ $i = 2 ] && exit 9; echo "15 $i" ); done
( ( ( echo "16 deep" ) ) )
echo "17 $( echo $( echo nested ) )"
x=$(printf 'a\n\n\n'); echo "18 [$x]"
x=$(i=0; while [ $i -lt 20000 ]; do echo line$i; i=$((i+1)); done); echo "19 ${#x}"
echo hi | { x=$(cat); echo "21 [$x]"; }
( set -u; echo $undefined_v ) 2>/dev/null; echo "22 after=$?"
trap '' INT; x=$( ( trap ) ); echo "23 [$x]"; trap - INT
( exec >/dev/null; echo hidden ); echo "24 visible"
g() { echo "25 g"; }; ( g ) | cat
( echo "26 a"; sleep 0.1 ) | ( cat; echo "26 b" )
y=$(sh -c 'exit 3'; echo "x$?"); echo "27 $y"
( : ) ; echo "28 $?"; ( false ) ; echo "28 $?"
v=$( { echo one; echo two; } | tail -n 1 ); echo "29 $v"
z=0; while [ $z -lt 3 ]; do ( echo "30 $z" ); z=$((z+1)); done | wc -l | tr -d ' '
echo "31 $( (echo a; echo b) | sort -r | tr '\n' ' ')"
( echo "32 $$" ) | { read p; [ "${p#32 }" = "$$" ] && echo "32 pid kept"; }
w=$( ( sleep 0.1; echo bg ) & echo fg; wait ); echo "33 $w" | tr '\n' ' '; echo
( kill -TERM $(sh -c 'echo $PPID') ) 2>/dev/null; echo "34 $?"
echo "35 end"
