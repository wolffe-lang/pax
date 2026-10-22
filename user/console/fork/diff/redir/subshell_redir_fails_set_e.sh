# a subshell whose own redirection fails ends with 2, and under set -e
# that ends the shell, as any failing command does (dash, black box)
( echo hi ) >/nonexistent/dir/f; echo "1 $?"
{ ( echo hi ); } >/nonexistent/dir/f; echo "2 $?"
set -e
( echo hi ) >/nonexistent/dir/f
echo not-reached
