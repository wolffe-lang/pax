#!/usr/bin/env bash
# px92: the dev leg's D3 red, discriminated on Linux (black box): the binary `wolf build` made on the installed
# 860 (dumped from the leg's target image), and the same program built on Linux by the dev image's own toolchain
# (its /usr/bin/{wolf,wolf-cimport-worker,libwolf_rt.a,cc,ld.lld}, /usr/lib/wolf-musl and compiler-std, bind-
# mounted at the dev image's paths), each run with `one two`; and a count program. Inside px78-ubuntu:1.
set -uo pipefail
L=/home/mfwolffe/lanes/px92 G=/home/mfwolffe/lanes/px92/diag
cd "$G"
echo "== the PAX-built binary, run on Linux"
file pax-built-px92args 2>/dev/null | cut -c1-200; sha256sum pax-built-px92args
./pax-built-px92args one two; echo "status $?"
export WOLF_STD=/usr/share/wolf/compiler-std PATH=/usr/bin:/bin
rm -rf "$G/lin"; mkdir -p "$G/lin/a" "$G/lin/c"   # one program per directory: a directory's .lu files are one module (D32)
cp "$G/px92args.lu" "$G/lin/a/"
printf 'fn main() {\n    let a = env_args()\n    print("count {a.len}")\n}\n' > "$G/lin/c/count.lu"
echo "== built on Linux by the dev image's toolchain"
wolf --version | head -1
(cd "$G/lin/a" && wolf build px92args.lu; echo "build status $?"; sha256sum px92args; ./px92args one two; echo "status $?")
(cd "$G/lin/c" && wolf build count.lu; echo "build status $?"; ./count one two; echo "status $?")
cp "$G/lin/c/count.lu" "$G/count.lu"
echo "== the PAX-built and Linux-built binaries: $(cmp -s "$G/lin/a/px92args" "$G/pax-built-px92args" && echo identical || echo differ)"
