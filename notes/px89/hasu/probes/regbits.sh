#!/usr/bin/env bash
# px89: the field/bit lines of one register section of a datasheet's text.
#   regbits.sh FILE 'heading text' [LINES]
f=$1 h=$2 n=${3:-260}
a=$(grep -n -F "$h" "$f" | awk -F: '$1>2500{print $1}' | tail -1)
[ -n "$a" ] || { echo "no heading: $h"; exit 1; }
awk -v a=$a -v n=$n 'NR>=a && NR<=a+n' "$f" | grep -E '^\s{0,6}[A-Za-z_0-9/ -]{1,22}\s{2,}[0-9]+(:[0-9]+)?\s{2,}' | sed 's/   */  /g' | cut -c1-110
