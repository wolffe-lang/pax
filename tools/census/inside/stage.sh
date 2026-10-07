#!/bin/sh
# stage.sh — fetch and build everything the workloads run, into /stage.
# Runs inside the census container (tools/census/census stage). Nothing
# here is traced; every input is pinned in pins.sh and refused on a
# digest mismatch.
set -eu
. /census/inside/pins.sh
S=/stage
mkdir -p "$S/dl"
cd "$S"

fetch() { # fetch <url> <sha256> <out>
    [ -f "$3" ] || curl -sSfL --retry 3 --retry-delay 5 -o "$3" "$1"
    have=$(sha256sum "$3" | cut -d' ' -f1)
    if [ "$have" != "$2" ]; then
        echo "stage: REFUSED $3: sha256 $have, pin wants $2" >&2
        rm -f "$3"; exit 1
    fi
    echo "stage: $3 sha256 $have OK"
}
tree() { # tree <repo> <rev> <dir> [path]
    rm -rf "$3" "$3.git"; mkdir -p "$3"
    git init -q "$3.git"
    git -C "$3.git" fetch -q --depth 1 "$1" "$2"
    git -C "$3.git" archive "FETCH_HEAD${4:+:$4}" | tar -x -C "$3"
    echo "stage: $1 at $(git -C "$3.git" rev-parse FETCH_HEAD)"
    rm -rf "$3.git"
}

fetch "$WOLF_URL" "$WOLF_SHA256" dl/wolf.tar.gz
rm -rf wolf; mkdir wolf; tar -xzf dl/wolf.tar.gz -C wolf --strip-components=1
wolf/wolf --version | head -1

fetch "$LOBO_URL" "$LOBO_SHA256" dl/lobo.tar.gz
rm -rf lobo; mkdir lobo; tar -xzf dl/lobo.tar.gz -C lobo --strip-components=1
lobo/lobo -v 2>&1 | head -1

tree "$STD_REPO" "$STD_REV" std std
tree "$BORE_REPO" "$BORE_REV" boreutils
tree "$LOBO_REPO" "$LOBO_REV" lobo-site demo/reel

# boreutils, two ways. dyn: exactly as tools/build does (wolf links with
# `cc`: PIE, ld.so, libc/libm/libgcc_s). static: the same objects and
# link line with -static added by a `cc` first on PATH, M-PX3's shape.
mkdir -p static-cc
cat > static-cc/cc <<'CC'
#!/bin/sh
exec /usr/bin/cc -static "$@"
CC
chmod +x static-cc/cc
rm -rf bore; mkdir -p bore/dyn bore/static
cd boreutils
for f in src/*.lu; do
    case "$f" in *_test.lu) continue ;; esac
    n=$(basename "$f" .lu)
    WOLF_STD=$S/std "$S/wolf/wolf" build --release --deny-warnings "$f" -o "$S/bore/dyn/$n"
    PATH=$S/static-cc:$PATH WOLF_STD=$S/std "$S/wolf/wolf" build --release --no-cache \
        --deny-warnings "$f" -o "$S/bore/static/$n"
done
cd "$S"
file bore/dyn/echo bore/static/echo

# lobo's demo site (index.html, files/big.bin), written by the site's own
# wolf program. lobo serves it in the lobo workload.
cd lobo-site
WOLF_STD=$S/std "$S/wolf/wolf" run build/main.lu
cd "$S"
( cd bore && sha256sum dyn/* static/* ) > bore.sha256
sha256sum lobo/lobo wolf/wolf > bin.sha256
echo "stage: done"
