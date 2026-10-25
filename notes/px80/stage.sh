#!/usr/bin/env bash
# px80 item 4: stage the native link bundle for a release (the publication is
# not a lane's): $L/stage/pax-wolf-link-18.1.8/ with ld.lld, cc, sysroot/, the
# record (user/wolf-link.sums), README.md (notes/px80/bundle-README.md) and
# LICENSES/, each file held to the record twice; a reproducible tar.xz of it
# (sorted names, mtime of the tree commit, owner 0, mode as staged) and its
# sha256, read twice; the dev ISO beside it, read twice. The licence texts come
# from their projects' own release files, only the licence member extracted:
# LLVM's three LICENSE.TXT (llvm, lld, libunwind) and the Support library's
# third-party notices from the verified llvm-project tarball; musl's COPYRIGHT
# from musl-1.2.5.tar.gz (its .asc checked against musl.pub); zlib's LICENSE
# from zlib-1.3.2.tar.gz and zstd's LICENSE from zstd-1.5.6.tar.gz (each
# against its project's published sha256 or signature); Rust 1.97.1's
# licence directory from the toolchain that built cc; PAX's own two files.
set -euo pipefail
L=$HOME/lanes/px80
P=$L/pax
N=pax-wolf-link-18.1.8
S=$L/stage; B=$S/$N; D=$L/stage-dl
rm -rf "$S"; mkdir -p "$B/sysroot" "$B/LICENSES/llvm" "$B/LICENSES/musl" "$B/LICENSES/zlib" "$B/LICENSES/zstd" "$B/LICENSES/rust" "$B/LICENSES/pax" "$D"
# the bundle, from the dev ISO's verified copy
cp -p "$L/dev/link-out/ld.lld" "$L/dev/link-out/cc" "$B/"
cp -p "$L/dev/link-out/sysroot/"* "$B/sysroot/"
cp "$P/user/wolf-link.sums" "$B/wolf-link.sums"
cp "$P/notes/px80/bundle-README.md" "$B/README.md"
for k in 1 2; do (cd "$B" && awk '{print $2"  "$1}' wolf-link.sums | sha256sum -c --quiet - && echo "staged bundle read $k: the record's seven files"); done
# LLVM
T=$L/src/llvm-project-18.1.8.src
cp "$T/llvm/LICENSE.TXT" "$B/LICENSES/llvm/llvm-LICENSE.TXT"
cp "$T/lld/LICENSE.TXT" "$B/LICENSES/llvm/lld-LICENSE.TXT"
cp "$T/libunwind/LICENSE.TXT" "$B/LICENSES/llvm/libunwind-LICENSE.TXT"
cp "$T/llvm/lib/Support/COPYRIGHT.regex" "$B/LICENSES/llvm/Support-COPYRIGHT.regex"
cp "$T/llvm/lib/Support/BLAKE3/LICENSE" "$B/LICENSES/llvm/Support-BLAKE3-LICENSE"
cp "$T/llvm/include/llvm/Support/LICENSE.TXT" "$B/LICENSES/llvm/Support-include-LICENSE.TXT"
# musl 1.2.5
cd "$D"
curl -fsSL --retry 3 -O https://musl.libc.org/releases/musl-1.2.5.tar.gz
curl -fsSL --retry 3 -O https://musl.libc.org/releases/musl-1.2.5.tar.gz.asc
curl -fsSL --retry 3 -O https://musl.libc.org/musl.pub
export GNUPGHOME=$L/gnupg-musl; rm -rf "$GNUPGHOME"; mkdir -m 700 "$GNUPGHOME"
gpg --batch --quiet --import musl.pub
gpg --batch --verify musl-1.2.5.tar.gz.asc musl-1.2.5.tar.gz
sha256sum musl-1.2.5.tar.gz; sha256sum musl-1.2.5.tar.gz
tar -xzf musl-1.2.5.tar.gz -O musl-1.2.5/COPYRIGHT > "$B/LICENSES/musl/COPYRIGHT"
# zlib 1.3.2
curl -fsSL --retry 3 -O https://zlib.net/zlib-1.3.2.tar.gz
# zlib.net signs it with a key it does not serve beside it: held instead to the
# sha512 Alpine's 3.20 aports record for the zlib-static that ld.lld linked
curl -fsSL --retry 3 -o zlib.APKBUILD https://gitlab.alpinelinux.org/alpine/aports/-/raw/3.20-stable/main/zlib/APKBUILD
want=$(awk '/^sha512sums=/{f=1} f && /zlib-1.3.2.tar.gz/ {print $1; exit}' zlib.APKBUILD | tr -d '"')
got=$(sha512sum zlib-1.3.2.tar.gz | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$got" ] || { echo "zlib-1.3.2.tar.gz sha512 $got; Alpine's APKBUILD: $want"; exit 1; }
echo "zlib-1.3.2.tar.gz sha512 = Alpine 3.20's APKBUILD record"
sha256sum zlib-1.3.2.tar.gz; sha256sum zlib-1.3.2.tar.gz
tar -xzf zlib-1.3.2.tar.gz -O zlib-1.3.2/LICENSE > "$B/LICENSES/zlib/LICENSE"
# zstd 1.5.6
curl -fsSL --retry 3 -O https://github.com/facebook/zstd/releases/download/v1.5.6/zstd-1.5.6.tar.gz
curl -fsSL --retry 3 -O https://github.com/facebook/zstd/releases/download/v1.5.6/zstd-1.5.6.tar.gz.sha256
sha256sum -c zstd-1.5.6.tar.gz.sha256
tar -xzf zstd-1.5.6.tar.gz -O zstd-1.5.6/LICENSE > "$B/LICENSES/zstd/LICENSE"
cd "$L"
# Rust 1.97.1 (cc's standard library and its musl target's self-contained objects)
podman run --rm -v "$B/LICENSES/rust:/out:Z" localhost/px57-rust bash -c '
 d=/opt/rust/rustup/toolchains/1.97.1-x86_64-unknown-linux-gnu/share/doc/rust
 cp $d/COPYRIGHT-library.html /out/ && cp -R $d/licenses /out/'
# PAX (cc's source, notes/px60/cc.rs)
cp "$P/LICENSE" "$P/LICENSE-TRAINING-DATA" "$B/LICENSES/pax/"
for f in $(find "$B/LICENSES" -type f); do [ -s "$f" ] || { echo "empty licence file: $f"; exit 1; }; done
find "$B" -type d -exec chmod 755 {} +
find "$B" -type f -exec chmod 644 {} +
chmod 755 "$B/ld.lld" "$B/cc"
(cd "$B" && find . -type f | LC_ALL=C sort | xargs sha256sum > "$S/$N.contents.sha256")
t=$(git -C "$P" log -1 --format=%ct)
tar --sort=name --mtime="@$t" --owner=0 --group=0 --numeric-owner --format=gnu -C "$S" -cf - "$N" | xz -9 -T1 > "$S/$N.tar.xz"
(cd "$S" && sha256sum "$N.tar.xz" > "$N.tar.xz.sha256")
sha256sum "$S/$N.tar.xz"; sha256sum "$S/$N.tar.xz"; wc -c < "$S/$N.tar.xz"
cp -p "$L/dev/out/pax-dev.iso" "$S/pax-dev.iso"
(cd "$S" && sha256sum pax-dev.iso > pax-dev.iso.sha256)
sha256sum "$S/pax-dev.iso"; sha256sum "$S/pax-dev.iso"; wc -c < "$S/pax-dev.iso"
cmp "$S/pax-dev.iso" "$L/dev/out/pax-dev.iso" && echo "staged ISO = the booted ISO"
ls -la "$S"
echo "stage.sh done $(date -Is)"
