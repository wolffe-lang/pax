#!/usr/bin/env bash
# px113 (pax#327): yew's build, its pin against its compiler, on one host.
# Four cells: yew 0ccb2c67 and 2eb9cb9b, each built with wolf 0.2.35 and wolf
# 0.2.36, each wolf with the std its release archive bundles (the std each
# yew pin names is its compiler's bundled tree). The build is tools/mkyew's:
# `wolf build --release --no-cache --deny-warnings src/yew.lu` through a `cc`
# that adds -static, in the baseline Ubuntu 24.04 image (localhost/px88-ubuntu:1),
# no network, --memory 12g, pinned to the block's CPUs (A 0-5, B 6-11; never C).
#
# Inputs staged by digest, each downloaded twice and the two hashed equal:
# the wolf release archives (the digests yew's own wolf-toolchain.toml names)
# and yew's codeload source archives (the digests user/yew.pin names).
#
# Each cell takes the block's three locks for itself, in the one order
# (hasu-block-X, hasu-X, hasu-X-light): a measurement holds the light lock
# too. A cell that will not build is written down as failed, with its error,
# and is retried once without --deny-warnings, labelled so, never counted as
# the cell. Detached by the caller (setsid -f); pid file, log, exit marker.
set -u
X=${1:?block A or B}
case $X in A) CPUS=0-5 ;; B) CPUS=6-11 ;; *) echo "block A or B (no timing on C)"; exit 2 ;; esac
L=/home/mfwolffe/lanes/px113/sep
P=/home/mfwolffe/lanes/hasu-env/bin/podman
IMG=localhost/px88-ubuntu:1
MARK=$L/sep.marker
RES=$L/results.tsv
echo $$ > "$L/sep.pid"
trap 'echo 143 > "$MARK"; exit 143' TERM
trap 'echo 130 > "$MARK"; exit 130' INT
trap 'echo 129 > "$MARK"; exit 129' HUP
say() { echo "$(date -u +%FT%TZ) $*"; }

say "uptime: $(uptime)"
free=$(df -BG --output=avail /home/mfwolffe/lanes | tail -1 | tr -dc 0-9)
say "disk free: ${free} GB"
[ "$free" -ge 35 ] || { say "under 35 GB free: not starting"; echo 3 > "$MARK"; exit 3; }

fetch() { # url sha256 out
    local i got=()
    for i in 1 2; do
        curl -sSfL --retry 3 -o "$3.$i" "$1" || { say "download $i of $1 failed"; return 1; }
        got+=("$(sha256sum "$3.$i" | cut -d' ' -f1)")
    done
    say "$(basename "$3"): $i reads ${got[0]} ${got[1]} (want $2)"
    [ "${got[0]}" = "$2" ] && [ "${got[1]}" = "$2" ] || { say "digest mismatch: $3"; return 1; }
    mv "$3.1" "$3"; rm -f "$3.2"
}
mkdir -p "$L/in" "$L/w"
cd "$L/in" || exit 2
fetch https://github.com/wolffe-lang/wolf-lang/releases/download/v0.2.35/wolf-0.2.35-x86_64-unknown-linux-gnu.tar.gz \
    4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a wolf-0.2.35.tar.gz || { echo 4 > "$MARK"; exit 4; }
fetch https://github.com/wolffe-lang/wolf-lang/releases/download/v0.2.36/wolf-0.2.36-x86_64-unknown-linux-gnu.tar.gz \
    d383c74c8cd123b9d9dfaa268271d4f004294f85c2b230237d0ef07027d9500d wolf-0.2.36.tar.gz || { echo 4 > "$MARK"; exit 4; }
fetch https://codeload.github.com/wolffe-lang/yew/tar.gz/0ccb2c67661a2dd789b5ce86180d592370a79c31 \
    d2ef6674865306bf5bc910b0541814210069c981a70bdbefdbf7a11e6f54ef15 yew-0ccb2c67.tar.gz || { echo 4 > "$MARK"; exit 4; }
fetch https://codeload.github.com/wolffe-lang/yew/tar.gz/2eb9cb9b2a8e33d788011aa6a81c3e633241c67c \
    049c6f36323edfd975552f248aba39272e9ca729e2cee825bfa7ec0a3df12dad yew-2eb9cb9b.tar.gz || { echo 4 > "$MARK"; exit 4; }
for v in 0.2.35 0.2.36; do
    rm -rf "$L/w/wolf-$v"; mkdir -p "$L/w/wolf-$v"
    tar -xzf "wolf-$v.tar.gz" -C "$L/w/wolf-$v" --strip-components=1
    say "wolf $v: $("$L/w/wolf-$v/wolf" --version | head -n 1); STD-REV $(cat "$L/w/wolf-$v/std/STD-REV" 2>/dev/null || echo none)"
    [ -f "$L/w/wolf-$v/std/STD-REV" ] || { say "wolf $v's archive bundles no std"; echo 5 > "$MARK"; exit 5; }
done
say "image: $($P image inspect --format '{{.Id}}' $IMG)"
printf 'cell\tyew\twolf\tflags\texit\treal_s\tuser_s\tsys_s\tbytes\tsha256\tstart\n' > "$RES"

cell() { # yew-short wolf-version flags
    local y=$1 v=$2 flags=$3 name="yew-$1-wolf-$2${4:-}"
    local src=$L/w/$name
    rm -rf "$src" "$L/w/out-$name"; mkdir -p "$src" "$L/w/out-$name"
    tar -xzf "$L/in/yew-$y.tar.gz" -C "$src" --strip-components=1
    say "cell $name: waiting on block $X's locks"
    local started
    flock -w 21600 /home/mfwolffe/lanes/hasu-block-$X.lock \
      flock -w 21600 /home/mfwolffe/lanes/hasu-$X.lock \
      flock -w 21600 /home/mfwolffe/lanes/hasu-$X-light.lock \
      "$P" run --rm --network none --memory 12g \
        -v "$L/w:/w" -w "/w/$name" "$IMG" bash -c '
          set -u
          mkdir -p /opt/ccbin
          printf "#!/bin/sh\nexec /usr/bin/cc -static \"\$@\"\n" > /opt/ccbin/cc; chmod +x /opt/ccbin/cc
          export PATH=/opt/ccbin:$PATH WOLF_STD=/w/wolf-'"$v"'/std TIMEFORMAT="%R %U %S"
          echo "start $(date -u +%FT%TZ) on $(nproc) CPUs, then taskset '"$CPUS"'" | tee /w/out-'"$name"'/started
          { time taskset -c '"$CPUS"' /w/wolf-'"$v"'/wolf build --release --no-cache '"$flags"' src/yew.lu -o /w/out-'"$name"'/yew > /w/out-'"$name"'/build.log 2>&1; echo "rc $?" > /w/out-'"$name"'/rc; } 2> /w/out-'"$name"'/time
          exit $?'
    local prc=$? rc t bytes sha
    started=$(sed -n 's/^start \([^ ]*\) .*/\1/p' "$L/w/out-$name/started" 2>/dev/null)
    rc=$(sed -n 's/^rc //p' "$L/w/out-$name/rc" 2>/dev/null); rc=${rc:-$prc}
    t=$(tail -n 1 "$L/w/out-$name/time" 2>/dev/null)
    if [ "$rc" = 0 ] && [ -f "$L/w/out-$name/yew" ]; then
        bytes=$(stat -c %s "$L/w/out-$name/yew"); sha=$(sha256sum "$L/w/out-$name/yew" | cut -d' ' -f1)
    else
        bytes=-; sha=-
        say "cell $name: FAILED rc=$rc (podman $prc); the build's last lines:"; tail -n 15 "$L/w/out-$name/build.log" 2>/dev/null | sed 's/^/    /'
    fi
    set -- $t
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$y" "$v" "${flags:-none}" "$rc" "${1:--}" "${2:--}" "${3:--}" "$bytes" "$sha" "$started" >> "$RES"
    say "cell $name: rc=$rc time(real user sys)=$t bytes=$bytes"
    rm -rf "$src"
    [ "$rc" = 0 ]
}
# Interleaved: the two CI cells first apart, then the two crossed.
fails=0
for c in "0ccb2c67 0.2.35" "2eb9cb9b 0.2.36" "0ccb2c67 0.2.36" "2eb9cb9b 0.2.35"; do
    set -- $c
    if ! cell "$1" "$2" --deny-warnings; then
        fails=$((fails + 1))
        cell "$1" "$2" "" "-no-deny-warnings" || true
    fi
done
say "done: $fails of 4 cells failed as mkyew builds them"
cat "$RES"
echo "$fails" > "$MARK"
