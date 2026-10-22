#!/bin/bash
# sh20: notice.sh's third set, braces that hold a subshell alone where
# the shell forks them (a stage, a substitution, after &). usage: notice3.sh SH
SH=$1
D=${TMPDIR:-/tmp}/sh20-notice3.$$
mkdir -p "$D"
K='kill -TERM $(sh -c '"'"'echo $PPID'"'"')'
P="sh -c 'kill -TERM \$\$'"
n=0
row() {
  n=$((n + 1))
  rm -f "$D/f"
  out=$(cd "$D" && "$SH" -c "$1"'; echo "st=$?"' 2>"$D/e")
  printf '%02d %s\n   out: %s\n   err: %s\n   file: %s\n' "$n" "$1" \
    "$(printf %s "$out" | tr '\n' '|')" "$(tr '\n' '|' < "$D/e")" \
    "$(cat "$D/f" 2>/dev/null | tr '\n' '|')"
}
row "{ ( $K ); } 2>f | cat"
row "x=\$( { ( $K ); } 2>f ); echo \"[\$x]\""
row "{ ( $K ); } 2>f & wait \$!"
row "( { ( $K ); } 2>/dev/null ) 2>f"
row "{ ( ( $K ) 2>/dev/null ); } 2>f"
row "{ ( $P ); } 2>f | cat"
row "{ ( $K; : ); } 2>f | cat"
row ": | { ( $K ); } 2>f"
row "{ ( $K ) 2>f; } | cat"
row "{ { ( $K ); } 2>/dev/null; } 2>f | cat"
row "x=\$( ( $K ) 2>f; echo after ); echo \"[\$x]\""
row "x=\$( { ( $K ); :; } 2>f ); echo \"[\$x]\""
rm -rf "$D"
