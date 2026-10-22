#!/bin/bash
# sh20: what else the shell writes while a subshell with redirections of
# its own runs: a trap's action for a signal the shell heard meanwhile.
# usage: notice4.sh SH
SH=$1
D=${TMPDIR:-/tmp}/sh20-notice4.$$
mkdir -p "$D"
n=0
row() {
  n=$((n + 1))
  rm -f "$D/f"
  out=$(cd "$D" && "$SH" -c "$1"'; echo "st=$?"' 2>"$D/e")
  printf '%02d %s\n   out: %s\n   err: %s\n   file: %s\n' "$n" "$1" \
    "$(printf %s "$out" | tr '\n' '|')" "$(tr '\n' '|' < "$D/e")" \
    "$(cat "$D/f" 2>/dev/null | tr '\n' '|')"
}
row "trap 'echo got' USR1; ( kill -USR1 \$\$; sleep 0.2; echo in ) >f"
row "trap 'echo got' USR1; { ( kill -USR1 \$\$; sleep 0.2; echo in ); } >f"
row "trap 'echo got' USR1; ( sh -c 'kill -USR1 \$PPID; sleep 0.2; echo in' ) >f"
row "trap 'echo got >&2' USR1; ( kill -USR1 \$\$; sleep 0.2 ) 2>f"
row "trap 'echo got' USR1; { kill -USR1 \$\$; sleep 0.2; echo in; } >f"
row "trap 'echo got' USR1; ( kill -USR1 \$\$; sleep 0.2; echo in ) >f | cat"
rm -rf "$D"
