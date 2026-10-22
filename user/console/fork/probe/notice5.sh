#!/bin/bash
# sh20: a subshell's own redirection that fails, and set -e, here-documents
# and the job text around it (what moving the redirections into the
# child could change). usage: notice5.sh SH
SH=$1
D=${TMPDIR:-/tmp}/sh20-notice5.$$
mkdir -p "$D"
n=0
row() {
  n=$((n + 1))
  rm -f "$D/f"
  out=$(cd "$D" && "$SH" -c "$1"'; echo "st=$?"' 2>"$D/e")
  printf '%02d %s\n   out: %s\n   err: %s\n   file: %s\n' "$n" "$1" \
    "$(printf %s "$out" | tr '\n' '|')" "$( [ -s "$D/e" ] && echo some)" \
    "$(cat "$D/f" 2>/dev/null | tr '\n' '|')"
}
row "( echo hi ) >/nonexistent/f; echo \"a \$?\""
row "{ ( echo hi ); } >/nonexistent/f; echo \"a \$?\""
row "set -e; ( echo hi ) >/nonexistent/f; echo after"
row "set -e; { ( echo hi ); } >/nonexistent/f; echo after"
row "set -e; ( false ) >f; echo after"
row "set -e; { ( false ); } >f; echo after"
row "set -e; if ( false ) >f; then :; fi; echo after"
row "set -e; ( false ) >f || echo or; echo after"
row "( cat ) <<E
doc
E"
row "{ ( cat ); } <<E >f
doc
E"
row "x=\$( ( echo cap ) 2>f ); echo \"[\$x]\""
row "( echo one; echo two >&2 ) 2>&1 >f"
row "exec 3>f; ( echo three >&3 ) 3>&-; exec 3>&-"
row "( exit 3 ) >f; echo \"e \$?\""
row "set -u; ( echo \$nope ) 2>f; echo \"u \$?\""
row "set -C; echo x >f; ( echo y ) >f; echo \"C \$?\""
row "( read v; echo \"got \$v\" ) <f"
row "echo in >f; ( read v; echo \"got \$v\" ) <f"
row "trap 'echo exit-trap' EXIT; ( echo sub ) >f"
row "( echo a ) >f >&2"
rm -rf "$D"
