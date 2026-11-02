# pm00 sources

Read date for every entry below: **2026-11-02 (UTC)**. These are documentation, specifications, man pages, papers and advisories, not implementation source. A Git tree listing establishes a filename, not correctness. Historical notes describe their own pinned revision; newer facts are identified separately. No package-manager binary was run.

## Project authorities and capability evidence

| ID | URL / revision | What was taken |
|---|---|---|
| P01 | [Lane rules](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/the-lane-rules-1031.md), [contract](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/pm/00-the-design/pm00-the-design.md), [RULES](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/RULES.md) | Scope, clean room, notes-only exception to plants, hand-back. Read from the local planning checkout; these documents, not older hosting or lane assumptions, govern this work. |
| P02 | [PAX index](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/pax/index.md), [metal campaign](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/pax/p6-the-metal-campaign.md) | Rolling binary distro, recipe spirit, cpkg/muzzle, M-PX5, historical network milestones and P6 independent of package management. |
| P03 | [s51](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/compiler/11-tooling/s51-package-manager.md), [study](https://github.com/wolffe-lang/wolf/blob/48cf14f/refs/reports/07-modules-stdlib-tooling.md) | Language MVS, integrity ledger, capabilities, transparency and D33. These are design history, not proof that every proposed feature shipped. |
| P04 | [libc index](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/libc/index.md) | cpkg belongs with muzzle; index's lc01/varargs status is historical. |
| P05 | [HOSTING](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/HOSTING.md) | Only hosting authority used: nginx on almanta, restricted-script CI deploy model, no lane SSH/configuration, hasu not a package endpoint. No live hosting claim or probe. |
| P06 | [PAX README](https://github.com/wolffe-lang/pax/blob/3e28a8bc/README.md) | Lines 20–22 storage/network; 125 journalled image roots; 156–159 power-cut caveat; 193–217 installer makes plain ext2; 290–310 hosted toolchain bridge; 344–349 rescue capacity limits. Read whole. |
| P07 | [PAX syscall census](https://github.com/wolffe-lang/pax/blob/3e28a8bc/docs/CENSUS.md) | Lines 651 flock semantics; 667 fsync/fdatasync on directories and volumes; 668 syncfs; 674–684 disk rename/link/metadata and EXDEV. Old census measurements are not current implementation counts. |
| P08 | [px68 journal](https://github.com/wolffe-lang/pax/blob/3e28a8bc/notes/px68-the-journal.md) | Ordered-data ext3 support, explicit flush/commit sequence, crash tests and residual limitations; plain ext2 still has no journal. |
| P09 | [px63 storage](https://github.com/wolffe-lang/pax/blob/3e28a8bc/notes/px63-virtio-blk-and-ext2.md), [px36 links](https://github.com/wolffe-lang/pax/blob/3e28a8bc/notes/px36-the-file-changes.md), [px62 flock](https://github.com/wolffe-lang/pax/blob/3e28a8bc/notes/px62-mremap-and-file-mmap.md) | Disk writeback versus durability; hard/symbolic links and rename behaviour; open-file-description locks released at last close. Relevant sections, not implementation source. |
| P10 | [px21 IP](https://github.com/wolffe-lang/pax/blob/3e28a8bc/notes/px21-ip-and-icmp.md), [px22 UDP](https://github.com/wolffe-lang/pax/blob/3e28a8bc/notes/px22-udp-and-sockets.md), [kernel module documentation](https://github.com/wolffe-lang/pax/blob/3e28a8bc/kernel/README.md) | Static QEMU addressing, UDP and DNS witness (C/glibc, not a wolf resolver); TCP and sockets followed. Historical 'no TCP' paragraphs are superseded by P06 and P02. Filename-only tree query found no DHCP/DNS/I225 module at the base. |
| P11 | [wolf-std README](https://github.com/wolffe-lang/wolf-std/blob/78b9d3cbc41d51db44d18c40b6694403644d1c83/README.md), [nursery catalog](https://github.com/wolffe-lang/wolf-std/blob/78b9d3cbc41d51db44d18c40b6694403644d1c83/std/x/README.md) | Documented SHA-2, Ed25519 and TLS APIs; nursery/constant-time and lane limitations. No crypto implementation opened. |
| P12 | [wolf-std changelog at local/PAX pin](https://github.com/wolffe-lang/wolf-std/blob/78b9d3cbc41d51db44d18c40b6694403644d1c83/CHANGELOG.md), [current trunk changelog](https://github.com/wolffe-lang/wolf-std/blob/dee6206fa99025336ca7a01845ef80cf9f6dc09a/CHANGELOG.md) | fs.sync/fs.sync_dir/exclusive create; sc67's absent standalone bounded resolver; sc75's bounded strbuf and 0.2.36 pins. Current prefix checked through GitHub API, not an update to the local clone. |
| P13 | [den README](https://github.com/wolffe-lang/den/blob/516e238b9eaa95d047e30d3b3add5d9f78b3581c/README.md), [MAP](https://github.com/wolffe-lang/den/blob/516e238b9eaa95d047e30d3b3add5d9f78b3581c/docs/MAP.md) | README 441–484 RFC1950/1951 codec API, whole-object bounds and historical measurements; 488–494 TLS limitations; MAP 185 digest adapter. No codec or network implementation opened. |
| P14 | [vc15 contract](https://github.com/wolffe-lang/wolf/blob/48cf14f/sprints/den/15-the-wire/vc15-the-wire.md) | Items 1–3 are file:// and git:// protocol v2, not HTTP. GitHub den trunk read as 13bc2caa46efa152ea7709da0b84180a9f350d85; no merged vc15 note found at lookup. |
| P15 | [wolf package specification](https://github.com/wolffe-lang/wolf-lang/blob/7d026c6de0cdade60b8cc9f8eb408aa9500cf0a6/spec/08-package.md) | Lines 3–6 D33; 53–58 MVS status; 65–94 actual b3 ledger and keyed-blake3 tree-head signature tag, not an asymmetric distribution trust anchor; 103–132 capability audit. |
| P16 | [wolf-lang#515](https://github.com/wolffe-lang/wolf-lang/issues/515), [current muzzle README](https://github.com/wolffe-lang/muzzle/blob/6dd9033f449f46f421a3b340d46cc49b27186fc9/README.md) | Issue API: CLOSED 2026-10-25T04:48:02Z; closing comment attributes s263/#930 at a5378e3f. Muzzle now lc02 stdio over wolf 0.2.36 C variadics; not a complete POSIX libc. Old planning blocker is stale, remaining ABI/runtime work is real. |
| P17 | [boreutils README](https://github.com/wolffe-lang/boreutils/blob/trunk/README.md), [lobo README](https://github.com/wolffe-lang/lobo/blob/trunk/README.md) | Local documentation: checksum family with large-file tests (boreutils lines 278–296); lobo is a server/reverse proxy, not evidence of a reusable bounded download API. Moving URLs, historical local prose; no current performance inference. |

## Mutable-distribution documentation and public failures

All read 2026-11-02; source excerpts were researched independently under this lane's clean-room restriction and synthesized here. Unverified properties stay explicitly unknown rather than being inferred from a command's name.

| ID | URL | What was taken |
|---|---|---|
| A01 | https://man.archlinux.org/man/pacman.8.en | Compressed tar, sync/local databases, dependency/epoch behavior, upgrade/removal, backup-file hashes and pacnew/pacsave, hooks/scriptlet options. |
| A02 | https://man.archlinux.org/man/makepkg.8.en | PKGBUILD phases, temporary package root, SOURCE_DATE_EPOCH normalization, compression selection, integrity/PGP checks and signing. |
| A03 | https://man.archlinux.org/man/apk-v2.5.en | v2 concatenated gzip/tar signature-control-data streams, PKGINFO key=value, datahash and per-file pax checksums. |
| A04 | https://man.archlinux.org/man/apk-v3.5.en | v3 ADB/SIG/DATA block structure, embedded hashes and signature coverage; not v2 with another extension. |
| A05 | https://man.archlinux.org/man/apk.8.en | Compression generation choices, database lock, world/add/del/fix, protected paths, hooks and trusted keys. |
| A06 | https://man.voidlinux.org/xbps-create.1 | Package-tree input, metadata/provides/conflicts/config lists, none/gzip/bzip2/xz/lz4/zstd choices, zstd default. |
| A07 | https://man.voidlinux.org/xbps-install.1 | Repository precedence, predicates, downgrade/reinstall, held packages, download/unpack phases and new-key approval. |
| A08 | https://docs.voidlinux.org/xbps/index.html | Database repair tools, rerun after XBPS self-update, alternatives, services not restarted automatically. |
| A09 | https://www.debian.org/doc/manuals/debian-reference/ch02.en.html | Release/Packages/Sources chain, source workflow, apt candidates/preferences, mixed-suite warnings and partial-install repair. First 100,000 characters read; historical MD5 discussion is not today's hash-policy specification. |
| A10 | https://manpages.debian.org/bookworm/dpkg/dpkg.1.en.html | Status states, conffiles, maintainer scripts/triggers, remove/purge, unsafe-io synchronization warning and recovery. |
| A11 | https://rpm.org/docs/4.20.x/man/rpm.8 | Archive+metadata/scripts, install versus upgrade and multiple versions, independent DB/file operations; no end-to-end atomicity claim. |
| A12 | https://dnf.readthedocs.io/en/latest/command_ref.html | Candidate/best/skip-broken, cache expiry, distro-sync, install-only packages, removal and limitations of history undo/rollback. |
| A13 | https://www.mankier.com/3/libsolv | Documentation mirror: libsolv is a SAT dependency-resolution library; not evidence of every DNF policy or version-order detail. |
| A14 | https://security.archlinux.org/package/pacman | Historical CVE-2019-9686 traversal and CVE-2019-18182/18183 injection tracker entries, fixed package versions; no current-vulnerability claim. |
| A15 | https://security.alpinelinux.org/vuln/CVE-2021-30139 | Historical apk tar-parser buffer overflow, fixed 2.10.6/2.12.5 branches; not an APK-v3 advisory. |
| A16 | https://voidlinux.org/news/2021/07/signing-disruption.html | 2021-07-17 repository/signing disruption; restoration estimate is not a verified restoration date. |
| A17 | https://lists.debian.org/debian-security-announce/2019/msg00010.html | DSA-4371, APT HTTP redirect/content injection, Stretch fixed 1.4.9. |
| A18 | https://access.redhat.com/security/cve/cve-2021-3421 | Crafted RPM package may corrupt database; advisory preconditions, not a complete affected-version census. |

## Immutable trees and language distribution

All read 2026-11-02. A deployment's atomic activation is not automatically an fsync/power-cut guarantee.

| ID | URL | What was taken |
|---|---|---|
| I01 | https://nix.dev/manual/nix/2.28/ | Store variants, binary cache/narinfo, immutable additions, profile activation/rollback and GC; introduction does not prove every build reproducible. |
| I02 | https://docs.brew.sh/Bottles | Gzip tar bottles, formula/platform SHA-256, relocation/Cellar constraints, BrewTestBot and CPU-baseline caution. |
| I03 | https://ostreedev.github.io/ostree/introduction/ | Content-addressed trees, hardlink deployment, atomic upgrades, per-deployment three-way /etc handling, shared /var. |
| I04 | https://ostreedev.github.io/ostree/formats/ | Bare/archive-z2 modes, individually gzip-compressed content, commit-paired static delta parts/fallbacks; delta format is documented as internal, not copied here. |
| I05 | https://docs.flatpak.org/en/latest/under-the-hood.html | Application/runtime refs, OSTree local storage, hardlinks, metadata permissions and runtime sandbox; not a builder reproducibility proof. |
| I06 | https://go.dev/ref/mod | Static proxy endpoints, MVS/major paths, ZIP restrictions and names+contents hash domain, signed sumdb inclusion/consistency, concurrent module cache and explicit fallback rules. First 200,000 characters read; final tail not consulted. |
| I07 | https://doc.rust-lang.org/cargo/reference/registry-index.html | Sparse HTTP/config/per-crate JSON-lines, SemVer/requirements/archive checksum/yank, ETag/Last-Modified/304 and stale CDN failure mode. |
| I08 | https://discourse.nixos.org/t/security-advisory-privilege-escalations-in-nix-lix-and-guix/66017 | 2025-06-24 coordinated privilege-escalation advisory; Guix CVE-2025-46415/46416 distinguished from Nix/Lix flaws. Sandboxed builds are a privileged boundary, not inherently safe. |

## Trust and interchange specifications

All read 2026-11-02. Specification prose and vectors only, not sample implementations or linked library source.

| ID | URL | What was taken |
|---|---|---|
| T01 | https://theupdateframework.github.io/specification/latest/ | Read version 1.0.37: roles, thresholds, exact versions, expiry/fixed update time, sequential root rotation, role-key revocation, bounded downloads, consistent snapshots and clock limitations. |
| T02 | https://ssl.engineering.nyu.edu/papers/cappos_mirror_ccs_08.pdf | Cappos/Samuel/Baker/Hartman, CCS 2008, all ten pages: replay/freeze/mix-and-match/endless-data, aggregate metadata and standalone verification. Historical attacks, not current bug claims. Web tool cached the PDF for reading; no source or executable was fetched. |
| F01 | https://www.rfc-editor.org/rfc/rfc8032.html | Ed25519 scheme/lengths, canonical point/scalar rejection, algorithm variants and verification-policy distinction; specification/security sections only, no sample implementation used. |
| F02 | https://www.rfc-editor.org/rfc/rfc8878.html | Zstd frame/window/content-size/block/dictionary rules; decoder budgets, concatenation/skippable frames and non-authenticating checksum. |
| F03 | https://www.rfc-editor.org/rfc/rfc1951.html | Deflate stream/history limits and invalid encodings; fixed history does not bound output; historical text compression ratios are not PAX data. |
| F04 | https://www.rfc-editor.org/rfc/rfc1952.html | Gzip headers/members/trailer, filename scan bounds, CRC and modulo-2^32 ISIZE; no sample CRC implementation used. |
| F05 | https://tukaani.org/xz/xz-file-format.txt | XZ v1.2.1 framing, bounded varints, index/filter/dictionary/check structure. Not a complete standalone LZMA2 algorithm reference. |
| F06 | https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pax.html | POSIX.1-2024 ustar/pax format sections: 512-byte records, headers/checksums, extended length/keyword precedence. Relevant earlier material read, final approximately 33k characters not read. |
| F07 | https://engineering.fb.com/2016/08/31/core-infra/smaller-and-faster-data-compression-with-zstandard/ | 2016 vendor-reported Silesia/zstd1.0 versus zlib/gzip conditions and numbers; contextual evidence only, no current PAX benchmark or numeric xz claim. |

Failed reads are not evidence: Guix's guix.gnu.org manual endpoints returned 403 in the first pass; ArchWiki partial-upgrade page was access-denied; facebook.github.io/zstd returned 404. Follow-up documentation, if obtained, is recorded separately. No blocked page was counted as proof of absence.
