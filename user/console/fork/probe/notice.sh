#!/bin/bash
# sh20: where a shell says that a signal ended a child, when the child is
# under a redirection of descriptor 2. Each shape runs as `SH -c`; its
# stdout, then what reached the shell's own stderr ("err:"), then what
# the redirection's file got ("file:"). usage: notice.sh SH
SH=$1
D=${TMPDIR:-/tmp}/sh20-notice.$$
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
row "( $K ) 2>f"
row "( :; $K ) 2>f"
row "( $P ) 2>f"
row "( $P; : ) 2>f"
row "( exec $P ) 2>f"
row "{ $P; } 2>f"
row "$P 2>f"
row "{ ( $K ); } 2>f"
row "{ ( $P ); } 2>f"
row "f() { ( $K ); }; f 2>f"
row "for i in 1; do ( $K ); done 2>f"
row "( ( $K ) ) 2>f"
row "( ( $K ) 2>f )"
row "( $K ) 2>f | cat"
row ": | ( $K ) 2>f"
row "x=\$( ( $K ) 2>f ); echo \"[\$x]\""
row "if ( $K ) 2>f; then :; fi"
row "( $K ) 2>f && echo and"
row "set -m; ( $K ) 2>f"
row "set -m; ( :; $K ) 2>f"
row "set -m; ( $P ) 2>f"
row "set -m; { ( $K ); } 2>f"
row "( $K ) 2>f & wait \$!"
rm -rf "$D"
