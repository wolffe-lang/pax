#!/usr/bin/env bash
# px78b (pax#254): the sizes of nm's write(2)s into a pipe, for the head's native kernel (strace, stdout only).
elf=$1
strace -f -e trace=write -o /tmp/nm-writes nm "$elf" | cat > /dev/null
grep -E 'write\(1,' /tmp/nm-writes | sed -E 's/.*\) = ([0-9]+)$/\1/' | sort | uniq -c | sort -rn
echo "writes: $(grep -cE 'write\(1,' /tmp/nm-writes); bytes: $(nm "$elf" | wc -c)"
