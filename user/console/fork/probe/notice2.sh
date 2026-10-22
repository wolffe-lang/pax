#!/bin/bash
# sh20: notice.sh's second set, the compound commands around a subshell.
# usage: notice2.sh SH
SH=$1
D=${TMPDIR:-/tmp}/sh20-notice2.$$
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
row "{ ( $K ); :; } 2>f"
row "{ :; ( $K ); } 2>f"
row "{ { ( $K ); }; } 2>f"
row "{ ( $K ) 2>/dev/null; } 2>f"
row "{ ( $K ) && :; } 2>f"
row "{ ! ( $K ); } 2>f"
row "{ ( $K ) & wait \$!; } 2>f"
row "while :; do ( $K ); break; done 2>f"
row "if :; then ( $K ); fi 2>f"
row "case x in x) ( $K );; esac 2>f"
row "{ $P; :; } 2>f"
row "{ ( $P ); :; } 2>f"
row "{ ( $K ); } 2>f >/dev/null"
row "{ ( $K ); } 2>&1 | cat"
row "( $K ) 2>&1 | cat"
row "{ ( $K ); } 3>f"
row "exec 2>f; ( $K )"
row "{ ( echo in >&2; $K ); } 2>f"
row "( echo in >&2; $K ) 2>f"
row "{ ( $K; ); echo out >&2; } 2>f"
rm -rf "$D"
