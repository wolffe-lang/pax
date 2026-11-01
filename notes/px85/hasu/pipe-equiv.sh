#!/usr/bin/env bash
# px85 (pax#256): each rewritten pipe prints what the old one printed.
#   pipe-equiv.sh ELF...
# For each ELF: every symbol the five tests look up, and every name nm
# lists more than once (where "the first match" matters), through the old
# sym()/symsize() and the new; mpx3-user's two disassembly pipes on
# pax_isr_common; then mpx6-ahci's recording awk on a log holding the
# session twice. Prints one line per comparison that differs and a count.
set -uo pipefail
old_sym() { nm "$1" | awk -v s="$2" '$3 == s { print "0x" $1; exit }'; } # pipe-shape: ok (the old form, compared)
new_sym() { nm "$1" | awk -v s="$2" '$3 == s && !f { print "0x" $1; f = 1 }'; }
old_size() { nm -S "$1" | awk -v s="$2" 'NF == 4 && $4 == s { print $2; exit }'; } # pipe-shape: ok (the old form, compared)
new_size() { nm -S "$1" | awk -v s="$2" 'NF == 4 && $4 == s && !f { print $2; f = 1 }'; }
names='__pax_data_start __pax_image_end __pax_rodata_end __pax_rodata_start __pax_text_end __pax_text_start
pax_bad_stack pax_gdt pax_idt pax_int3 pax_ist1_stack pax_ist1_top pax_syscall_entry pax_tss pax_ud2
pax_enter_user pax_peek_user pax_sysret pax_isr_common pax_interrupt kmain no_such_symbol'
n=0 bad=0
for elf in "$@"; do
    dups=$(nm "$elf" | awk 'NF == 3 { c[$3]++ } END { for (k in c) if (c[k] > 1) print k }')
    for s in $names $dups; do
        a=$(old_sym "$elf" "$s"); b=$(new_sym "$elf" "$s"); n=$((n + 1))
        [ "$a" = "$b" ] || { echo "DIFF sym $elf $s: '$a' vs '$b'"; bad=$((bad + 1)); }
        a=$(old_size "$elf" "$s"); b=$(new_size "$elf" "$s"); n=$((n + 1))
        [ "$a" = "$b" ] || { echo "DIFF symsize $elf $s: '$a' vs '$b'"; bad=$((bad + 1)); }
    done
    objdump -d --no-show-raw-insn "$elf" > "$elf.dis"
    body() { awk -v f="<$1>:" '$2 == f { on = 1; next } on && NF == 0 { exit } on { sub(/^[^\t]*\t/, ""); print }' "$elf.dis" | tr -s ' '; }
    a=$(body pax_isr_common | awk 'seen { print; exit } /^call.*<pax_interrupt>/ { seen = 1 }') # pipe-shape: ok (the old form, compared)
    b=$(body pax_isr_common | awk 'seen && !d { print; d = 1 } /^call.*<pax_interrupt>/ { seen = 1 }'); n=$((n + 1))
    [ "$a" = "$b" ] && [ -n "$a" ] || { echo "DIFF after-call $elf: '$a' vs '$b'"; bad=$((bad + 1)); }
    after=$b
    a=$(body pax_isr_common | awk 'seen && /^cmpq \$0x100,0x78\(%rsp\)/ { c = 1; next } c { print; exit } /^mov %rax,%rsp/ { seen = 1 }') # pipe-shape: ok (the old form, compared)
    b=$(body pax_isr_common | awk 'seen && /^cmpq \$0x100,0x78\(%rsp\)/ { c = 1; next } c && !d { print; d = 1 } /^mov %rax,%rsp/ { seen = 1 }'); n=$((n + 1))
    [ "$a" = "$b" ] && [ -n "$a" ] || { echo "DIFF cmp $elf: '$a' vs '$b'"; bad=$((bad + 1)); }
    echo "$elf: $(echo $names $dups | wc -w) names; after the call '$after'; after the compare '$b'"
    rm -f "$elf.dis"
done
log=$(mktemp)
printf 'boot\nAHCI BEGIN inventory\nA\nAHCI SESSION END\ntail\nAHCI BEGIN inventory\nB\nAHCI SESSION END\n' > "$log"
a=$(awk '/^AHCI BEGIN inventory$/{on=1} on{print} /^AHCI SESSION END$/{exit}' "$log")
b=$(cat "$log" | awk '/^AHCI BEGIN inventory$/ && !done{on=1} on{print} /^AHCI SESSION END$/{on=0; done=1}'); n=$((n + 1))
[ "$a" = "$b" ] || { echo "DIFF ahci: '$a' vs '$b'"; bad=$((bad + 1)); }
rm -f "$log"
echo "pipe-equiv: $n comparisons, $bad differ"
echo "END pipe-equiv exit=$bad"
[ "$bad" = 0 ]
