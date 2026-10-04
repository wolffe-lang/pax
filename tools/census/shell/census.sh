# census.sh — a POSIX shell script with the shapes real scripts have:
# variables and arithmetic, functions, loops, case, tests, globs, here
# documents, redirections, pipelines, command substitution, subshells,
# background jobs and wait, traps, cd, read from a file, umask, and
# external commands found on PATH. Run by dash and by bash.
set -u
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM
cd "$tmp" || exit 1
umask 022

count() { n=0; for _ in "$@"; do n=$((n + 1)); done; echo "$n"; }
i=0
while [ "$i" -lt 50 ]; do
    printf 'line %d\n' "$i" >> data.txt
    i=$((i + 1))
done
echo "args: $(count a b c d)"

cat > conf.ini <<'INI'
name = census
mode = trace
INI
while IFS=' =' read -r k v; do
    case $k in
        name) echo "name is $v" ;;
        mode) echo "mode is $v" ;;
        *) echo "unknown $k" ;;
    esac
done < conf.ini

lines=$(wc -l < data.txt)
echo "lines: $lines"
grep -c 'line 4' data.txt
sort -r data.txt | head -n 3 | tr 'a-z' 'A-Z'
( cd / && pwd )
mkdir -p a/b/c && touch a/1.txt a/2.txt a/b/3.txt
for f in a/*.txt; do [ -f "$f" ] && echo "glob $f"; done
if [ -d a/b ] && [ ! -e a/zzz ]; then echo "tests ok"; fi
exec 3> fd3.txt
echo "to fd 3" >&3
exec 3>&-
cat fd3.txt
sleep 0.1 &
sleep 0.1 &
wait
echo "jobs done"
x=$( (echo nested; echo sub) | wc -l)
echo "nested $x"
false || echo "or-list"
true && echo "and-list"
command -v ls > /dev/null && echo "found ls"
kill -0 $$ && echo "self alive"
cmdsub=`date +%Y > /dev/null; echo back`
echo "$cmdsub"
echo done
