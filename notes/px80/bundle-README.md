# PAX native link bundle: lld 18.1.8 and musl 1.2.5

These are the files the PAX development image uses to link native wolf
programs on PAX itself: a static `ld.lld`, a small `cc` front end that turns
the wolf compiler's link line into an `ld.lld` call, and musl's C runtime
objects. The same `ld.lld` links PAX's kernel. Nothing here is a C or
assembly compiler.

Every file is an x86-64 Linux static executable or an x86-64 ELF object or
archive. The executables have no interpreter and no dynamic section, so they
run on PAX and on any x86-64 Linux.

| file | what it is | bytes | sha256 |
|---|---|---:|---|
| `ld.lld` | LLVM's linker, lld 18.1.8, X86 only, static | 68,594,984 | `9fa7191f0e22887486cd52bbc95f261ad0be71a6ab29f1c1cc13322a34d4ca4a` |
| `cc` | the link-only front end (PAX's `notes/px60/cc.rs`), Rust 1.97.1, static musl | 499,760 | `3161aea27abb8beeb669cc6499fa9dc162014b69eecc6fb0d169eed5def25b11` |
| `sysroot/crt1.o` | musl 1.2.5's start file | 5,560 | `51dba24287eb9b1e74f3c7cb8ea5464491d3a4ba54c016722f149179d08f90f6` |
| `sysroot/crti.o` | musl 1.2.5's `_init` prologue | 2,816 | `5cbc84c78a23cdddda0db8cdcd5ec3b5a15b6b555510bd97e4c5a0334aca7b49` |
| `sysroot/crtn.o` | musl 1.2.5's `_init` epilogue | 2,760 | `d884ee5f9120490b98bb43496f88983ee379a0d2ebf027574fcca7eae9aaa1e7` |
| `sysroot/libc.a` | musl 1.2.5's static C library | 10,961,970 | `8e69a73c464a86fd8b278f3aa08ab2640b720157e92b45a2d34441c22248ddd4` |
| `sysroot/libunwind.a` | LLVM's libunwind, as Rust 1.97.1 ships it for x86_64-unknown-linux-musl | 201,794 | `264296d61db52859cc7a8cd6a7a09fc62bde189aa3ea8867fb62ef5129b694bc` |

`wolf-link.sums` lists the same names, digests and sizes, one file a line, and
is byte for byte the record PAX keeps in its repository as
`user/wolf-link.sums`. To check a copy:

```sh
awk '{print $2 "  " $1}' wolf-link.sums | sha256sum -c -
```

## Where each file comes from

`ld.lld` was built from `llvm-project-18.1.8.src.tar.xz`, LLVM's release
tarball (sha256 `0b58557a6d32ceee97c8d533a59b9212d87e0fc4d2833924eb6c611247db2f2a`,
132,067,260 bytes, signed by LLVM's release key, fingerprint
`474E 2231 6ABF 4785 A88C 6E8E A2C7 94A9 8641 9D8A`). The build ran in
Alpine 3.20 with clang 17.0.6, libc++, libc++abi, LLVM's libunwind and
compiler-rt, all linked static, against musl 1.2.5, with zlib 1.3.2 and
zstd 1.5.6 built in, so it reads compressed debug sections in either format.
The recipe is `notes/px80/build-lld.sh` in PAX's repository, with its
container file beside it.

`cc` is compiled from `notes/px60/cc.rs` in PAX's repository with Rust
1.97.1 for `x86_64-unknown-linux-musl` (`-C relocation-model=static -C
strip=symbols -C link-arg=-Wl,--build-id=none`); the same command gives the
same bytes, which PAX's CI checks on every run of its `mpx5-wolf` suite.

The four musl files are Alpine 3.20's `musl-dev` 1.2.5-r4 with their debug
sections decompressed by `llvm-objcopy --decompress-debug-sections` (LLVM
17's, Alpine's); the code and the debug content are unchanged. `libunwind.a`
is Rust 1.97.1's, rewritten by the same command; it has no compressed
section. They were decompressed because the lld this bundle replaces had no
zlib. This `ld.lld` reads the packaged files as they ship, and the programs it
links from them are the same bytes as from these.

## What links with it

- wolf 0.2.35's native programs: on PAX's development image `wolf build
  hello.lu` runs `cc`, which runs `ld.lld` against `sysroot/`
  (`PAX_LLD` and `PAX_CC_SYSROOT` move either); the result is a static
  ET_EXEC that runs on PAX and on Linux.
- PAX's kernel, both of wolf's tiers: `ld.lld -nostdlib -static -z
  max-page-size=0x1000 -T boot/kernel.ld start.o <objects> <runtime archive>`.
  lld 17.0.6, which this bundle replaces, could not link the release tier's
  kernel (a relaxed GOT reference out of range at the top of the address
  space); 18.1.8 links it.

## Licences

| part | licence | file |
|---|---|---|
| `ld.lld` (LLVM, lld, and the libc++, libc++abi, libunwind and compiler-rt linked into it) | Apache-2.0 WITH LLVM-exception | `LICENSES/llvm/llvm-LICENSE.TXT`, `lld-LICENSE.TXT`, `libunwind-LICENSE.TXT`; the third-party notices of LLVM's Support library beside them |
| musl 1.2.5 (`sysroot/crt*.o`, `sysroot/libc.a`, and the musl linked into `ld.lld` and `cc`) | MIT | `LICENSES/musl/COPYRIGHT` |
| zlib 1.3.2 (in `ld.lld`) | Zlib | `LICENSES/zlib/LICENSE` |
| zstd 1.5.6 (in `ld.lld`) | BSD-3-Clause | `LICENSES/zstd/LICENSE` |
| `sysroot/libunwind.a` | Apache-2.0 WITH LLVM-exception | `LICENSES/llvm/libunwind-LICENSE.TXT` |
| Rust 1.97.1's standard library (in `cc`) | MIT OR Apache-2.0 | `LICENSES/rust/` |
| `cc`'s own code (`notes/px60/cc.rs`) | GPL-3.0, with the wolf Training Data Permission | `LICENSES/pax/LICENSE`, `LICENSES/pax/LICENSE-TRAINING-DATA` |

The sources: LLVM's at its release page (the tarball above), musl's at
musl.libc.org, zlib's at zlib.net, zstd's at github.com/facebook/zstd,
Rust's at its 1.97.1 release, and `cc`'s in PAX's repository.
