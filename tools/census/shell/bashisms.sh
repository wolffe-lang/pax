# bashisms.sh — the bash-only shapes scripts lean on: arrays and
# associative arrays, [[ ]] with regex, process substitution, mapfile,
# printf -v, here strings, coproc, read -t, $RANDOM, extglob, brace
# expansion, and a DEBUG-free trap on ERR.
set -uo pipefail
shopt -s extglob nullglob
declare -A seen
arr=(alpha beta gamma)
for w in "${arr[@]}"; do seen[$w]=1; done
echo "${#arr[@]} ${!seen[*]}"
[[ "beta-2" =~ ^([a-z]+)-([0-9])$ ]] && echo "regex ${BASH_REMATCH[1]}"
mapfile -t lines < <(printf '%s\n' one two three)
echo "mapfile ${#lines[@]}"
diff <(printf 'a\nb\n') <(printf 'a\nc\n') > /dev/null || echo "procsub diff"
printf -v padded '%05d' 42; echo "$padded"
read -r first rest <<< "here string words"; echo "$first"
coproc CO { read -r l; echo "co:$l"; }
echo ping >&"${CO[1]}"
read -r reply <&"${CO[0]}"; echo "$reply"
wait
if read -r -t 0.1 x < <(sleep 1); then echo "read $x"; else echo "read timed out"; fi
echo {1..3} file.{a,b}
r=$RANDOM; (( r >= 0 )) && echo "random ok"
trap 'echo trapped ERR' ERR
false
echo "$BASHPID $$ $PPID" > /dev/null
echo done
