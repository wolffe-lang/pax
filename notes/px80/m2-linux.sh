#!/usr/bin/env bash
# px80 item 1 and R-px80-2: the new ld.lld on Linux, by px60's M2 recipe
# (notes/px60/m2.sh): the static musl wolf 0.2.35 (user/wolf.sums' bytes)
# builds hello, loop and signal (user/wolf/), linking through the bundle's cc
# (CC, PAX_LLD, PAX_CC_SYSROOT), each run and its output read. Rows:
#   new-bundle   lld 18.1.8, the bundle's sysroot (px60's, decompressed)
#   new-packed   lld 18.1.8, the sysroot as its packages ship it: Alpine 3.20's
#                musl-dev 1.2.5-r4 CRT and libc.a, Rust 1.97.1's musl
#                self-contained libunwind.a (compressed debug sections)
#   old-packed   lld 17.0.6 on the packaged sysroot (px60's packaging error)
#   old-bundle   lld 17.0.6 on the bundle's sysroot (the dev ISO before px80)
# then zstd: a C object compiled with -gz=zstd and -gz=zlib, linked by both.
# And the provenance of the bundle's sysroot: the packaged files decompressed by
# Alpine's llvm-objcopy 17 (px60's decompress.sh) against user/wolf-link.sums.
# kasumi, CPUs 0-3, under the block's lock.
set -uo pipefail
ulimit -c 0
L=$HOME/lanes/px80
O=$L/m2
rm -rf "$O"; mkdir -p "$O/packed" "$O/decomp" "$O/tmp"
podman run --rm --cpuset-cpus 0-3 -v "$L:$L:Z" -e O="$O" localhost/px80-lld sh -c '
 set -eu
 apk info -v musl-dev llvm17
 for f in crt1.o crti.o crtn.o libc.a; do cp /usr/lib/$f "$O/packed/"; done
 for f in crt1.o crti.o crtn.o libc.a; do llvm-objcopy --decompress-debug-sections "$O/packed/$f" "$O/decomp/$f"; done
 printf "int px80_zstd(void) { return 42; }\n" > "$O/z.c"
 printf "int px80_zstd(void);\nint main(void) { return px80_zstd() == 42 ? 0 : 1; }\n" > "$O/zmain.c"
 clang -c -g -gz=zstd "$O/z.c" -o "$O/z-zstd.o"
 clang -c -g -gz=zlib "$O/z.c" -o "$O/z-zlib.o"
 clang -c "$O/zmain.c" -o "$O/zmain.o"
 readelf -SW "$O/z-zstd.o" | grep -c " C " | sed "s/^/z-zstd.o compressed sections: /"
'
podman run --rm -v "$L:$L:Z" localhost/px57-rust \
    cp /opt/rust/rustup/toolchains/1.97.1-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-musl/lib/self-contained/libunwind.a "$O/packed/"
podman run --rm -v "$L:$L:Z" -e O="$O" localhost/px80-lld sh -c 'llvm-objcopy --decompress-debug-sections "$O/packed/libunwind.a" "$O/decomp/libunwind.a"'
echo "== the packaged sysroot (compressed sections per file)"
for f in "$O"/packed/*; do printf '%s %s %s\n' "${f##*/}" "$(sha256sum "$f" | cut -c1-16)" "$(readelf -SW "$f" 2>/dev/null | grep -c ' C ')"; done
echo "== the packaged files decompressed (px60's decompress.sh) against user/wolf-link.sums"
for k in 1 2; do
    while read -r n s b; do
        case $n in sysroot/*) f=$O/decomp/${n#sysroot/}
            [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$s" ] && echo "read $k: $n decompressed = the bundle's" || echo "read $k: $n decompressed DIFFERS from the bundle's" ;;
        esac
    done < "$L/pax/user/wolf-link.sums"
done
mkdir -p "$O/bundle-sysroot"; cp "$L"/link-old/sysroot/* "$O/bundle-sysroot/"
taskset -c 0-3 podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" -e O="$O" -w "$O" \
    localhost/px80-ubuntu bash -c '
 set -uo pipefail
 export WOLF_STD=$L/dev/std TMPDIR=$O/tmp CC=$L/link-old/cc
 [ -d "$WOLF_STD" ] || { echo "no std tree at $WOLF_STD (verify.sh makes it)"; exit 2; }
 for row in new-bundle new-packed old-packed old-bundle; do
   case $row in new-*) export PAX_LLD=$L/lld-out/ld.lld ;; old-*) export PAX_LLD=$L/link-old/ld.lld ;; esac
   case $row in *-bundle) export PAX_CC_SYSROOT=$O/bundle-sysroot ;; *-packed) export PAX_CC_SYSROOT=$O/packed ;; esac
   echo "== $row: $($PAX_LLD --version), sysroot $PAX_CC_SYSROOT"
   mkdir -p "$O/$row"
   for name in hello loop signal; do
     rc=0; $L/wolf-bin/wolf build --no-cache $L/pax/user/wolf/$name.lu -o "$O/$row/$name" > "$O/$row/$name.build.log" 2>&1 || rc=$?
     echo "$row $name build rc=$rc"
     [ "$rc" = 0 ] || { grep -m3 -E "error|lld" "$O/$row/$name.build.log" | sed "s/^/    /"; continue; }
     t=$(readelf -hW "$O/$row/$name" | sed -n "s/^ *Type: *//p"); i=$(readelf -lW "$O/$row/$name" | grep -c INTERP); d=$(readelf -dW "$O/$row/$name" | grep -c "no dynamic section")
     out=$("$O/$row/$name" 2>&1); r=$?
     echo "$row $name: $t, PT_INTERP $i, no-dynamic $d, run rc=$r, sha $(sha256sum "$O/$row/$name" | cut -c1-16), first line: $(printf "%s\n" "$out" | head -n 1)"
   done
 done
 for name in hello loop signal; do
   for p in "new-bundle new-packed" "new-bundle old-bundle"; do set -- $p
     [ -f "$O/$1/$name" ] && [ -f "$O/$2/$name" ] && { cmp -s "$O/$1/$name" "$O/$2/$name" && echo "$name: $1 = $2 byte for byte" || echo "$name: $1 differs from $2"; }
   done
 done
 echo "== compressed debug sections, zstd and zlib"
 for z in zstd zlib; do for which in new old; do
   b=$L/lld-out/ld.lld; [ "$which" = old ] && b=$L/link-old/ld.lld
   rc=0; $b -static $O/bundle-sysroot/crt1.o $O/bundle-sysroot/crti.o $O/zmain.o $O/z-$z.o $O/bundle-sysroot/libc.a $O/bundle-sysroot/crtn.o -o $O/z-$z-$which > $O/z-$z-$which.log 2>&1 || rc=$?
   r=-; [ "$rc" = 0 ] && { $O/z-$z-$which; r=$?; }
   echo "$z $which lld: link rc=$rc run rc=$r $(head -c 300 $O/z-$z-$which.log | tr "\n" " ")"
 done; done
'
echo "m2-linux.sh done $(date -Is)"
