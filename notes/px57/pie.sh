#!/bin/bash
# px57 on kasumi: what the musl target builds WITHOUT `-C relocation-model=static` (tools/mklupin's flag):
# the same tag, toolchain and command but that flag, in the throwaway Rust image; the ELF type and segments.
L=$HOME/lanes/px57
podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z localhost/px57-rust bash -c '
  set -e; w=/tmp/pie; mkdir -p $w; cd $w
  git init -q src; cd src
  git fetch -q --depth 1 https://github.com/wolffe-lang/wolf-interp refs/tags/v0.1.55:refs/tags/v0.1.55
  git -c advice.detachedHead=false checkout -q refs/tags/v0.1.55; git log --oneline -1
  CARGO_TARGET_DIR=$w/target RUSTFLAGS="-C target-feature=+crt-static" cargo build -q --release --locked --target x86_64-unknown-linux-musl
  b=$w/target/x86_64-unknown-linux-musl/release/lupin
  sha256sum $b; readelf -hW $b | grep -E "Type|Entry"; readelf -lW $b | grep -E "LOAD|INTERP|DYNAMIC"; readelf -dW $b | head -3; $b --version'
