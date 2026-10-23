#!/bin/bash
# px65, kasumi: item 1's first chain, at the pins alone (the kernel, lupin,
# std, the dev compiler, su, sigwolf, edwolf; pelt, boreutils and the user
# tools still at their old pins): mkw and tour, then the suites the pins
# reach, against their committed references.   chain-a.sh   (PX65_TREE)
L=$HOME/lanes/px65; P=$L/pax/notes/px65
bash "$P/mkw.sh" a-mkw
bash "$P/regress.sh" a mpx5-jobs mpx5-accounts mpx5-lupin:localhost/px57-rust
echo "chain-a: done $(date -Is)"
