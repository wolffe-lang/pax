# Filesystems and installer choices

## 1. Evidence and the system today

**Recommendation:** qualify the existing journal, then add a deliberately narrow ext3 formatter and installer profile. That is the shortest route to a useful second choice. It does **not** remove ext2's block-address or file-size limits. Larger files and volumes need separately qualified ext4 features; btrfs starts as a read-only interoperability project, not as the next root default.

This is a census and plan, not a filesystem implementation or a fresh disk qualification. PAX documentation was inspected at `4007eaa02f02a42b985349079aae9673b6af175e` on 2026-11-13. No kernel, filesystem-tool, bootloader or installer implementation source was read. No new Linux or PAX guest was run and no physical disk was accessed.

Evidence labels throughout:

- **Observed record:** an existing test transcript inspected here, with its named PASS and containing step's successful END. It establishes that historical run only.
- **Read:** a published document, specification or issue. Even a document saying “measured” is not a new measurement here.
- **Derived:** arithmetic or a dependency inferred from those documents, not an execution result.
- **Estimate / proposed:** future work, neither an implemented capability nor a schedule commitment.

### Census

| Area | Present capability and boundary | Evidence |
|---|---|---|
| Persistent kernel filesystems | Two documented ext-family profiles, ext2 and ext3, through the same ext2 backend; both read and write. No documented ext4 or btrfs mount. | Read: [disk calls](../docs/CENSUS.md#served-since-px04-the-disk-px63), [mounts](../docs/CENSUS.md#served-since-px04-root-on-the-disk-px67), [journal](../docs/BOOT.md#the-journal-px68). |
| In-memory and synthetic filesystems | Writable rootfs/tree and tmpfs; kernel-provided devtmpfs, proc and sysfs. These are not alternative persistent root formats. `mount(2)` accepts tmpfs, but refuses user-requested proc/sysfs/devtmpfs mounts and mounts inside the kernel's trees. | Read: CENSUS mount table; [tree](../kernel/README.md#the-writable-tree-px27). |
| FAT32 | ESP written/read by `paxfat` through raw device windows, not a kernel-mounted FAT filesystem. | Read: [upgrade mount](px93-the-upgrade.md#41-the-change), BOOT “Writing a disk on PAX”. |
| Host image builder | `mkdisk --gpt --root` makes ext3 by default using pinned e2fsprogs; `--no-journal` selects ext2. `PAX_EXT2_WRITER` applies only to ext2 and rejects journalled requests. | Read: [BOOT](../docs/BOOT.md#writing-a-disk-on-pax-px69), lines 825–829 at the inspected revision. |
| On-machine installer | `pax-install` formats plain ext2 with `paxext2`; no filesystem choice and no journal. Whole-disk fresh installs only. | Read: [guided installation](../docs/BOOT.md#guided-installation). |
| Historical installer measurement | Three inspected release-image legs, starting from an old PAX install, FAT32 and ext4, each end with an ext2 root, boot it alone, read a pre-reboot witness and pass independent filesystem checks. | Observed record: [legs.log](px92/logs/legs.log), M7/M8/M10/M11 and `END sleg-pax exit=0`, `END sleg-fat32 exit=0`, `END sleg-ext4 exit=0`; image kernel `9c88ec8ac016d7a6df911b3922ff3cfb596188e8`. “ext4” in that leg names the erased input, **not** an ext4 install or mount. |
| Journal safety | Ordered metadata journalling and replay are documented, but seven failure-handling findings remain a release blocker at this census revision. | Read: [issue 411](https://github.com/wolffe-lang/pax/issues/411). Its required QEMU rows are not measured results. |

The open-PR listing at inspection contained neither the journal-failure branch's PR nor the one-processor census PR. This note does not assume either is merged or validated. Recheck those dependencies before commissioning implementation. The file-tree documentation already describes interrupt-disabled, one-CPU operations; the proposed interface below must not turn that into an unreviewed SMP promise.

### Limits are different at each layer

| Limit | Value / refusal | Meaning and evidence |
|---|---|---|
| Installer/formatter root volume | 8 MiB through **17,592,186,040,320 bytes**, or 16 TiB minus 4 KiB; larger disks get explicitly unused space | Read: BOOT lines 802–829 and 946–952. Derived: `(2^32 − 1) × 4096`. This is a 32-bit **block count**, not a 2 TiB disk ceiling. |
| Kernel ext2/ext3 file | Documented maximum at 4 KiB blocks: **2 TiB minus 512 bytes**, also bounded by indirect-map reach at smaller block sizes | Read: [large-disk census §4.2](px84-the-big-disk.md#42-the-kernel-past-4-gib-and-past-2-tib-the-32-bit-audit). This note has not exercised the maximum-size boundary. |
| `paxext2` source regular file | **0xffffffff bytes**, 4 GiB minus one byte | Read: BOOT lines 820–823. A format menu does not widen the population tool. |
| Memory tree | Documented 1 GiB file, 16,384 inode records, a frame budget | Read: kernel README “The writable tree”. A memory-tree limit is not the on-disk inode count. Current extreme-boundary behavior is not requalified here. |
| Offline PAX checker | At most **4,194,304 blocks**, **1,048,576 inodes**, **512 groups**; exit 8, `volume exceeds checker capacity` | Read: [rescue](../docs/BOOT.md#checking-a-volume-from-rescue). Derived: block-count ceiling is 16 GiB with 4 KiB blocks, possibly reduced by the other bounds. This is far below the formatter's ceiling. Large volumes need Linux's offline e2fsck today. |
| Journal reuse guard | Issue 411 reports groups ≥512 unguarded, and allocation failure silently unguarded | Read, unresolved: first 64 GiB with conventional 32,768-block, 4 KiB groups; **not** a supported-volume ceiling to advertise or a guarantee below it. |
| Disk geometry and layout | Installer requires 512-byte logical sectors; 1 MiB BIOS partition, fixed 64 MiB ESP, root from byte 69,206,016; FAT writer documented 33 MiB–2 GiB volumes | Read: BOOT. GPT sector addresses and transport offsets already exceed 32 bits; changing the filesystem does not implement 4Kn. |

The earlier [large-address transcript](px84/regress/r3-highlinux.log) contains four PASS rows for Linux↔PAX high-address data on virtio/NVMe, zero SKIPs, and its own exit-0 marker. It lacks the later recorder's END shape; it is corroborating historical output, not this note's gate or a fresh maximum-capacity qualification. In particular, a small file located past 2 TiB is not a file larger than 2 TiB.

### Feature acceptance and refusals

This is the **documented** matrix, not an exhaustive current feature-bit probe. A follow-on must publish actual accepted masks and named refusals from a binary before expanding them.

| Profile | Accepted / handled | Refused, degraded or unqualified |
|---|---|---|
| ext2 legacy maps | Revisions 0/1; 1/2/4 KiB blocks; FILETYPE; LARGE_FILE; sparse superblocks; direct through triple-indirect maps; holes; hard links and fast/slow symlinks | [Original backend note](px63-virtio-blk-and-ext2.md#9-limits-named) names EXTENTS, 64BIT and FLEX_BG as incompatible refusals; unknown RO_COMPAT makes the volume read-only. Only 4 KiB was suite-qualified there. Do not infer arbitrary compatible features are safe to modify. |
| Indexed directories | Linear traversal; modifying a directory clears INDEX_FL, rather than maintaining an htree | Read: same note. This is not qualified ext4 hashed-directory writing. |
| Extended attributes | Original backend note says neither read nor written, external blocks kept | Not a preservation contract for rename/delete/restore; current regular-file xattr/ACL/flag APIs remain unqualified by the public census. |
| ext3 | Internal inode-8 journal; documented v2 superblock, 32-bit tags and revocations; `data=ordered` only | External journals and other journal features are outside the documented served profile. Issue 411 contradicts the broad “anything else refused” claim: compatible and RO-compatible journal masks were ignored, and UUID identity was not checked. Treat checksums, unknown masks and mismatched identity as **unqualified/unsafe**, not already proven refusals. |
| Mount names/options | `ext3` on a journal-free volume returns EINVAL; `ext2` on a journalled volume still uses its journal. Unknown type returns ENODEV. | A string or magic is not positive durability evidence. MS_BIND/MS_MOVE/propagation return EINVAL; MNT_DETACH is refused. No documented journal-mode selector. |
| PAX offline checker | Legacy maps and a bounded journal replay subset | External journals, checksum/64-bit journal features, external attribute blocks, indexed-directory validation, nonempty orphan chains and ambiguous indirect/directory corruption are not repaired. A refusal is never a clean result. |

Issue 411's seven gates are: no commit after failed data/log/precommit barrier; no log clearing after failed checkpoint; no writable journal without flush support; bounded fail-closed reuse guards including allocation failure; all journal feature classes validated; journal/filesystem identity matched; failed cache writes kept dirty. Retake recovery and independent e2fsck after injected EIO and cuts, including cuts during recovery. Earlier happy-path crash tests do not discharge these findings. Likewise, `data=ordered` is not atomic replacement of arbitrary file contents or protection from a disk lying about flushes.

### Consumers

| Consumer | What the root must provide | Consequence |
|---|---|---|
| pxg package manager | Durable file and directory sync, same-filesystem rename, safe held-directory traversal, recoverable intents and an actual qualified journal signal for the root's device | [Transactions X2/X5/X11](https://github.com/wolffe-lang/paxage/blob/2c69152ba9aa760ec5104b65a23ef961bfa83368/docs/TRANSACTIONS.md): Linux ext3/ext4 require an active device-matched journal; plain ext2 refuses. **PAX ext-family roots also currently refuse** pending native positive proof. Installing ext3 alone does not enable pxg mutation. |
| Denward backup/restore | Bounded no-follow inventory; exact sparse/metadata capability or refusal; stable offline/quiescent source; verified backup before mutation; fresh qualified journalled target and maintenance boot gate | [Backup](https://github.com/wolffe-lang/denward/blob/39393c249e57a318868098267ec972dbec5529fb/spec/backup-v1.md), [restore](https://github.com/wolffe-lang/denward/blob/39393c249e57a318868098267ec972dbec5529fb/spec/restore-state-v1.md), [library request 156](https://github.com/wolffe-lang/wolf-std/issues/156). Data verbs are disabled in the inspected scaffold. Filesystem work is necessary, not sufficient: bounded inventory and encryption qualification remain separate. |
| `pax-install --upgrade` / `pax-upgrade` | Installed manifest and identity, supported root reader/writer, working sync/rename, verified ESP assets and enough staging space | [Upgrade design](px93-the-upgrade.md#41-the-change) assumes partition 2, root label/geometry, fixed ESP offset; [staging](px115-upgrade-over-ssh.md#25-staging-where-how-much-what-cleans-it) moves `~/.pax-upgrade` to `/var/lib/pax-upgrade` on the same filesystem. Separate `/home` breaks that rename assumption. The staged **new kernel**, rescue and installed kernel must all read the chosen format. |

An ext2 upgrade's resumable file-level record is not filesystem crash consistency. Fresh-install logs likewise are evidence, not authority to resume a partial format. A journalled root does not make raw GPT/FAT/boot-configuration changes transactional.

## 2. The filesystem seam

**Read:** a common file/tree interface already exists; [the two-store design](px63-virtio-blk-and-ext2.md#4-what-was-built) puts volume inodes behind tree records and reuses their mapped pages. **Not established:** a separately specified, arbitrary-filesystem backend interface. The documentation describes an ext2-specific second store, not a pluggable VFS. No source-level call-site count is claimed. The table is a documented dependency census and proposed contract, not an implementation audit.

| Operation | Documented owner / current coupling | Smallest second-format contract |
|---|---|---|
| Names, credentials, descriptors, cwd, permissions | `kernel/files`; paths walked a component at a time, nodes held by tree index; special proc/dev paths | Keep syscall policy here. Dispatch lookup/readdir/readlink through a typed backend handle; retain byte-name limits, no-follow semantics and stable held-parent identity. |
| Inode identity and lifetime | `kernel/tree`; memory index plus volume/inode side table, held records and eviction | `(mount identity, backend inode identity, generation)` plus hold/release; backend identity must hold a btrfs subvolume/root identity as well as inode number. Never assume ext2 inode widths or reuse generations. |
| Stat, ownership, modes and times | `tree` mirrors some fields, asks ext2 for others; `files` emits Linux structures | Common metadata result with explicit available fields; backend setters with checked narrowing. No successful empty metadata for unsupported enumeration. |
| File bytes, truncate and holes | `tree` routes memory versus volume operations; ext2 indirect mapping/allocation | Bounded positional read/write/truncate, checked 64-bit offsets; separate exact-extent query from allocation counts and zero-filled bytes. Format owns allocation; memory backend need not invent disk blocks. |
| Directories, links, rename/unlink | `tree` over ext2's directory/block operations, EXDEV across stores | Mount-aware atomic namespace operation with defined failure state; directory sync; persistent inode lifetime after unlink. No generic code should edit ext2 directory blocks. |
| `mmap`, exec and writeback | `vm`/`files`/`tree` page path; shared dirty pages must reach disk | Page fill/writeback and invalidation, truncate/mapping coherence, clear ownership of dirty/error state. Keep file-page cache separate from device-block cache. |
| Mount, root selection, remount, shutdown | `fstab`, `tree`, boot/root path and `files`; ext2/ext3 strings and identity lookup | Probe without writes, accept an explicit feature profile, mount/replay only under declared policy; stable filesystem UUID/mount ID; remount and unmount return errors, no silent fallback to another root. |
| Sync and recovery | `block` cache plus ext2 metadata tagging and `journal` | Backend sync with file/directory/volume scope; sticky errors and successful-flush requirements. Generic layer must not equate “sync callback exists” with journal capability. |
| Raw device I/O | `block` and transport drivers, partition offsets, cache, exclusive claim | Checked device-range reads/writes, cache identity/invalidation and barrier capability. COW publication ordering belongs to its backend, not an ext3 transaction wrapper around every write. |
| Pseudo-filesystems | `procfs`, sysfs/dev nodes and memory tree, synthesized stat/mount tables | Explicit virtual/read-only/mutable capabilities and unsupported operations; no dummy ext2 superblock. Keep the existing user-visible mount restrictions initially. |

**Proposed staged refactor, 2–4 lanes estimated:**

1. Specify identity, metadata, errors and sync contracts; introduce an ext2/ext3 adapter with no behavior change. Keep ext2's journal private. Gate `mpx6-ext2`, `mpx6-journal`, `mpx6-root`, `mpx6-nodes`, `mpx6-fsck` and the issue-411 failure corpus.
2. Route lookup, held inode life, I/O and mappings through the seam, retaining memory and disk adapters. Gate `mpx3-tree`, `mpx3-maps`, loader/exec, disk-root users/den and every storage suite. Plant mount-ID aliasing, EXDEV and truncate-cache mistakes separately.
3. Adapt synthetic nodes and root/mount dispatch without changing mount policy; gate proc/stat/mountinfo, permissions, root/installer/upgrade and full no-disk regression. Add a read-only test backend to prove calls no longer assume ext2. Only then attach another on-disk format.

At every step run the existing full regression set as well as the named affected suites, on the project's required firmware/compiler legs. “Keep green” is acceptance work, not a claim that these suites ran in this notes pass. Define lock order, reentrancy, transaction reservation and cache pin lifetimes before allowing yields or multiple CPUs; do not bundle scheduler changes with the first format adapter.

## 3. Candidates, cost and backup fidelity

### Source boundary

Published documents consulted on 2026-11-13, not their linked implementations:

- [ext4 overview](https://www.kernel.org/doc/html/latest/filesystems/ext4/overview.html), [inode block maps and extents](https://www.kernel.org/doc/html/latest/filesystems/ext4/ifork.html), [group descriptors](https://www.kernel.org/doc/html/latest/filesystems/ext4/group_descr.html), [checksums](https://www.kernel.org/doc/html/latest/filesystems/ext4/checksums.html), [directories](https://www.kernel.org/doc/html/latest/filesystems/ext4/directory.html), [journal](https://www.kernel.org/doc/html/latest/filesystems/ext4/journal.html).
- [btrfs on-disk format](https://btrfs.readthedocs.io/en/latest/dev/On-disk-format.html) and [design](https://btrfs.readthedocs.io/en/latest/dev/dev-btrfs-design.html).
- PAX's [source catalogue](../docs/SOURCES.md) and the public consumer documents above. POSIX file operations and the cited syscall/tool manuals define API/oracle contracts, not a universal power-loss guarantee.

The ext4 documents give fields, endian rules, feature masks, extent trees, htrees, checksums and JBD/JBD2 layouts. They are not a complete executable validation or recovery specification. Resolve ambiguities in offsets, checksum inputs, hash variants and feature combinations by an independently specified fixture and black-box Linux/e2fsprogs behavior; publish the evidence before accepting the feature. In particular, ext4's metadata and its journal have separate feature masks and checksum formats.

The btrfs on-disk page explicitly warns that it is incomplete and outdated, with TODO item descriptions. The design page describes COW and tree publication, not a complete crash-recovery specification. Exact acceptance/recovery for newer incompatibility bits, log-tree replay, delayed references, free-space variants and all backreference forms is not established by these pages. There may be answers in implementation source, but that source is forbidden here. Those are **specification blockers**, not permission to infer a compatible writer. No claim is made that source is the only possible future evidence: a public specification or a sufficiently discriminating black-box experiment can resolve a particular question.

For every candidate, pin the Linux guest and binary tool versions by digest and record their enabled feature set; never inherit a distribution's changing mkfs defaults. Oracles are binaries inside disposable Linux QEMU guests: `mke2fs`, `dumpe2fs`, `debugfs`, `e2fsck -fn`, or `mkfs.btrfs`, `btrfs inspect-internal dump-super/dump-tree`, `btrfs check --readonly`, Linux mounts and independent logical-tree digests. Never run repair on the only fixture copy. A clean checker is one oracle, not proof of durability.

### Stages and lane estimates

A lane here means one bounded implementation/review/test unit, including a negative plant, Linux differential and QEMU integration evidence. Ranges are **estimates derived from the work packages listed**, not observed throughput or elapsed weeks. They assume existing block drivers, compiler and test harness, single-device 4 KiB profiles, independent review, and no major compiler/runtime defect. Shared seam, consumer APIs, repair tooling and installer integration are listed separately; do not add overlapping rows twice. Documentation gaps can make btrfs writer cost unbounded until the specification gate clears.

| Candidate | Read-only stage and done-when | Read-write stage and done-when | Estimated incremental lanes |
|---|---|---|---|
| ext3 baseline, defects fixed | Requalify clean-volume reading, dirty-volume policy, UUID and all feature masks; a requested no-write inspection must preserve the image hash. Dirty no-replay inspection is refused or explicitly inconsistent, never called a current snapshot. Existing reader, not a new format project. | Issue 411 closed by its tests; capability proof; journal formatter; installer and reboot/upgrade/recovery matrix. Commit/checkpoint/replay cuts, EIO, ENOSPC and reuse exhaustion all fail closed. Ordered mode only. | **3–5 after the issue-411 fix**: capability/reader qualification 1; formatter 1; installer/end-to-end integration 1–3. Fix work itself is an existing dependency, not included. |
| ext4 extents, legacy-size profile | Extent headers, depth, sorted/nonoverlapping logical ranges, checked physical ranges; inline root and multi-level trees, holes and unwritten extents read as Linux does; corrupt/deep/looping trees refuse without writes. Clean image only initially. | Allocate/split/merge/free/truncate under journal reservations; initialized versus unwritten conversion; cut each structural change and recovery. Bidirectional Linux writes/PAX reads and PAX writes/Linux reads, clean e2fsck. | **1–2 RO + 2–4 RW**. Does not alone widen existing `i_blocks` accounting or the population tool. |
| ext4 64bit and large-file accounting | Wider group descriptors, high addresses/counts, overflow-safe cache keys and ranges; sparse fixtures cross the old 16 TiB boundary. Qualify `huge_file` accounting if selected, independently of extents. | Widen allocators, formatter/checker and JBD2 tags/revokes when high blocks can be logged; high-address allocate/free/crash/replay. Publish the supported upper bound, not the format's theoretical maximum. | **1–2 RO + 2–3 RW**, after the seam and chosen ext4 profile. Review the documented 48-bit cache key before any larger claim. |
| ext4 metadata checksums | Superblock, descriptors, bitmaps, inodes, extent nodes, directory tails and selected journal checksum versions; flip each field independently and refuse corruption. | Update every affected checksum with correct seed/identity and ordering; torn metadata/log blocks cannot be accepted. Qualify checksum-seed variants separately. Checksums detect, not repair. | **1–2 RO + 2–3 RW**. Larger descriptors store fuller checksums in some structures; do not confuse this with 64bit being mandatory for all checksums. |
| ext4 hashed directories | htree roots/nodes/leaves, supported hash algorithms and collision continuation, malformed indexes and complete enumeration. Linear fallback alone is not validation of an index. | Indexed insertion, split, collision, rename, unlink and directory checksum maintenance, cut at every update. Never clear the index flag and advertise indexed writes. | **1 RO + 1–2 RW**. Deliberately restrict hash variants before expanding. |
| ext4 flexible groups | Read bitmap/inode-table locations outside their nominal group with filesystem bounds and overlap checks; flex groups are not `meta_bg`. | Allocate across flex groups and maintain all summaries and checksums; full/partial groups, ENOSPC and crash consistency. `meta_bg`, `bigalloc`, lazy initialization and resize remain explicit separate gates. | **1 RO + 1–2 RW**. |
| btrfs narrow single-device profile | First a documentation/fixture gate, then superblocks and mirror selection, chunk mapping (including metadata DUP if accepted), tree traversal, inode/directory/extent reads and checksums. Explicit default subvolume selection; sparse, inline and preallocated data; compressed extents only after named codec qualification. Refuse unknown features, unsupported profiles, inconsistent generations and a pending log needing replay. Compare bytes and metadata with Linux; assert zero writes. | Separate design/review gate, then COW mutation, reservation/ENOSPC, references/backreferences, allocation/free space, checksum updates, crash-safe root publication and recovery; fsync/log-tree behavior must be specified or conservatively implemented with full commits and incompatible dirty logs refused. Then Linux reopens PAX-written images, independent check, cuts/EIO at every publication boundary and during recovery. No multi-device, RAID, balance, send/receive, quotas or online resize in this estimate. | **3–5 RO** (including specification admission), **8–15 additional RW** only if remaining specification gaps close; repair/rescue and installer add **2–4**. Not a quote for general btrfs compatibility. |
| Own COW format | A new public disk specification, validators, reader and independent fixture generator | Allocation, transaction publication, data checksums, fsync, crash recovery, repair/export tools and longevity testing; no Linux filesystem oracle for the new format | **2–4 specification/RO + 8–16 RW/tooling** as a planning allowance, not a trustworthy release estimate. Simpler bytes can be cheaper to implement, not demonstrably cheaper to make trustworthy. |

**Power-loss and boot implications:**

- ext3 and each ext4 stage need correct device barriers, sticky error propagation and journal replay. The recovered state must respect acknowledged syncs; an unacknowledged operation can be absent. Ordered metadata does not make in-place data overwrite atomic. Test torn sectors, reordered/unflushed subsets, device EIO and recovery interrupted again, not just process kills or an orderly QEMU shutdown.
- btrfs COW keeps older reachable blocks until publication, but only with correct reference accounting, write ordering and superblock/generation selection. A checksum or snapshot cannot excuse an incorrect publication protocol; acknowledged fsync behavior and a pending log are independent work.
- An own COW design has the same obligations and no independent deployed checker. Do not choose it to evade missing btrfs documentation or to accelerate the first safe install.
- **Every candidate keeps the ESP.** Limine loads its kernel/assets there; it does not need an ext4 or btrfs driver. PAX's early root mount, staged-upgrade archive reader, rescue kernel and user-space formatter/checker all need the selected profile. Keep boot files outside snapshots, and explicitly test compatibility of both old rescue and new upgrade images. Root snapshots do not roll back the ESP.

**Recommended order:** issue-411 correction → qualified ext3 capability and formatter → ext3 installer/maintenance/consumer qualification → the small backend seam and backup capability work → ext4 extents, then 64bit/large-file accounting if capacity requires it, checksums, hashed directories and flex groups, each as an explicit profile → btrfs read-only experiment → a separate decision on btrfs writing. Ext4's five feature rows total **13–22 incremental lanes** after shared groundwork, before formatter/rescue/installer qualification; a combined profile needs an additional interaction matrix, not five isolated greens. Do not expose a list of raw feature checkboxes to an installer user.

### What backup and restore need

The library request's six independent contracts are bounded directory iteration, parent-handle traversal, bounded readlink, exact sparse maps, ACL/xattr/flag census, and mount identity/read-only reporting. A syscall number in CENSUS is not qualification of its flags, wrapper allocation bound or backend behavior. Denward's v1 manifest does not preserve arbitrary ACL/xattr/flags: it must detect them and refuse unsupported metadata rather than silently drop it. Its 256 MiB inventory ceiling and entry/extent admission are separate gates.

| Root candidate | Sparse maps | xattrs, ACLs, inode flags | Read-only / snapshot signal | Restore consequence |
|---|---|---|---|---|
| Plain ext2 today | Holes supported in legacy maps; exact regular-file SEEK_DATA/SEEK_HOLE or equivalent is unqualified. Zero bytes and `st_blocks` are not a map; punched blocks are documented as retained. | Format can hold ext-family metadata; current safe enumeration/setters unqualified, original backend does not read/write xattrs. | Remount RO and mountinfo/statfs documented; raw-device writable aliases must still be excluded. No snapshot contract. | Not a qualified restore target under current journal requirement. A quiescent source may become usable only after inventory/refusal APIs qualify. |
| Corrected ext3 | Same representation and API work as ext2 | Same work; a journal preserves neither unenumerated metadata nor missing restore setters | Same RO/offline strategy; journal state identifies recovery status, not a snapshot | First practical target after actual installer, journal signal and maintenance recovery pass. No automatic backup enablement. |
| Incremental ext4 | Extents help enumeration, but distinguish initialized/unwritten extents and holes; publish exactness, bounded counts and logical-size checks | Qualify external/inline attributes, ACL/capability presence, flags and unsupported encryption/verity metadata; broad format support does not imply v1 archive support | No native snapshot in this proposed ext4 profile; quiesce/offline and exclude writable aliases | Larger-file targets eventually; every selected feature also belongs in the restore admission/repair matrix. |
| btrfs RO, then RW | Logical sparse layout is distinct from compression, shared physical extents and preallocation. Preserve v1 logical holes, not undocumented physical topology. | Enumerate xattrs/ACLs/flags and refuse any unrepresentable metadata; do not mistake inode permission bits for full ACLs | A future read-only subvolume snapshot could stabilize a source. Need validated subvolume/root identity, RO property, handle binding and exclusion of raw writes; multi-subvolume consistency is separate | RO stage is only a prospective backup source. RW target still blocked by Denward's current journal-only policy: a separately specified/qualified COW durability contract and consumer change are required. |
| Own COW | Entire contract and independent validator new | Entire contract new | Snapshot publication and quiescence semantics new | No current restore advantage; no release shortcut. |

## 4. Installer options and screens

A choice is available only when **formatting + population + mount/read/write + reboot + upgrade + recovery/checking + consumer admission** all agree on one versioned profile. Preserve the old scripted contract and refuse unsupported choices before opening the target for writing. Store the selected profile, geometry, image identity and destructive scope in a new plan version, bound to its confirmation. Never reinterpret an already issued token.

Status below means documented behavior at the census revision. “Needs user space” includes independent tests and validation, not just another prompt; “needs kernel” does not imply source was inspected.

| Decision | Status and prerequisite | Proposed question / presentation |
|---|---|---|
| Target and destructive scope | Exists: inventory, allow-list, exclusive claim, identity/geometry recheck; whole-disk erase only. Keep every refusal. | “Which disk should PAX erase?” Show model, serial, capacity and node; never select silently. |
| Filesystem | Exists: ext2 preview only. Needs user-space journal formatter and installer verification; kernel fail-closed/capability work before ext3 recommendation. Ext4/btrfs require §3. | “Root filesystem: ext3, ordered journal (qualified profile), or ext2 developer preview (no journal)?” Until qualified, show ext3 as unavailable with reason, not a selectable promise. |
| Journal mode | Exists in kernel: ordered ext3 only, not an installer option. Other modes need kernel and oracle work. | “Journal mode: ordered (fixed for this profile).” Do not offer writeback, full-data journalling, external journals or disabling barriers. |
| Layout / separate home | Kernel can mount a second ext2/ext3 volume; guided layout is fixed. Needs planner, population, fstab, root identity, backup boundaries and cross-filesystem upgrade staging. No preserve/reuse partition flow exists. | “Use one root volume, or create a separate home volume?” Initially one root only; later require sizes and say both are erased. Preserve-existing-home is a different feature. |
| ESP size | Fixed 64 MiB; needs planner/FAT bounds, alignment/free-space checks, stale-signature cleanup and removal of upgrader fixed-offset assumptions. FAT writer supports 33 MiB–2 GiB, not arbitrary sizes. | “Boot partition size?” Recommend calculated space for current and recovery assets with headroom, show what fits; retain 64 MiB only for its existing qualified profile. |
| Host name | README says no host name yet. Needs kernel name setter/reporting and boot configuration; writing `/etc/hostname` alone is insufficient. | “Name this computer:” Offer only after uname/gethostname-facing behavior and reboot persistence qualify. |
| Time zone | Image carries UTC; user-space zone database, validated choice and consumers' local-time behavior need qualification. No new filesystem required. | “Time zone: UTC” initially; later searchable region/city, while hardware/system time remains UTC. |
| Keyboard layout | Documented US mapping shared by PS/2 and USB. Needs kernel/configurable translation plus persistence, console and rescue tests. | “Keyboard layout: US” initially; offer a test field before passwords when more layouts work. |
| Accounts/passwords | Exists: user name, uid/gid 1000, sudo membership, optional root/user passwords; scripted accounts locked. Needs validation/recovery UX for any new policy. | “Your user name:” and existing “Set a password for root now?” / new account equivalent. Warn that root console access remains passwordless until an administrator has a password. Never log secrets. |
| Network | Kernel DHCP/static configuration exists through `/etc/pax-net`; guided selection needs user-space validation and persistence tests; unsupported links must not block offline install. | “Network: automatic (DHCP), static address, or configure later?” Show address/prefix/gateway/DNS fields only for static, bounded optional connectivity check. |
| Packages | Exists: verified offline image and explicit games yes/no. General package selection needs qualified pxg root, repository/trust setup and offline error semantics; not just a download screen. | “Install the optional games? y/n” now. Later “Optional packages from this verified offline set:” with space totals; never silently fetch. |
| Encryption at rest | No documented encrypted block/root stack. Needs kernel crypto/block mapping or a fully specified alternate path, secure entropy and key derivation, unlock/rescue environment, key lifecycle, user-space formatter and adversarial qualification. An age-encrypted backup is not an encrypted root. | “Disk encryption: unavailable in this release.” Later explain unencrypted ESP, passphrase/recovery-key handling and recovery before offering it. Filesystem choice alone cannot supply it. |

**Screen proposal (future profile-aware guided path):**

1. Welcome: developer-preview/security limitations; install versus upgrade versus cancel; no writes. State backup requirement and whole-disk scope.
2. Disk inventory: current protections and refusal reasons; paged numbered selection, `n`/`p`, Enter, `q`/EOF cancel.
3. Storage: only qualified filesystem profiles; fixed mode with explanation; root size/unused capacity; layout and ESP controls only when their complete path qualifies. No in-place conversion.
4. Identity and locale: user name, implemented host/time/keyboard settings; clearly show unavailable settings without accepting inert answers.
5. Connectivity and optional offline content: DHCP/static/later and games; future package list only from qualified trusted inputs. No network prerequisite for the base install.
6. Review: target identity, exact destructive ranges, filesystem/profile, mount layout, unused capacity, capacity/checker limits, all proposed configuration and passwordless-console warning. Ask the existing exact word `yes`; anything else cancels. A changed choice invalidates the plan.
7. Password prompts before disk writes, as today; cancellation or failure aborts rather than silently accepting half-configured accounts. No password in the transcript. Then acquire/revalidate the target and execute each checked phase, recording progress and sync failures.
8. Verification and finish: read-back boot/configuration/profile identity, independent checks in qualification tests; explain rescue/recovery limitations and remove-media/reboot or poweroff choice. Do not call a failed partial install bootable or resumable merely because a phase was logged.

The existing scripted invocations remain **exactly**:

```text
pax-install --dry-run --target vdb --user pax --games no
pax-install --install --ext2-preview --target vdb --user pax --games no   --seed SEED_FROM_PLAN --confirm 'EXACT_CONFIRMATION_FROM_PLAN'
```

These continue to mean plain ext2. New formats need an additive, separately versioned interface and tests, not a new meaning for `--ext2-preview`, omitted flags, `yes`, the recorded seed or an old confirmation token. Guided mode must not start asking for the scripted identity token. An unattended old script cannot acquire a new question or a different default filesystem.

## 5. Decisions, first contracts and validation

### Decisions recommended

1. **Safety before format choice.** Options: expose ext3 now, wait for btrfs, or qualify the existing journal first. Recommend the last: issue 411 is a prerequisite, followed by the three contracts below. Keep plain ext2 explicitly a developer preview; never infer durable mutation from an ext magic or mount name.
2. **Bounded profiles rather than generic ext4 support.** Options: a broad feature launch, ext3 forever, or incremental ext4 RO/RW gates. Recommend incremental profiles, with extents first and 64bit/large-file accounting driven by actual capacity needs. Corrected ext3 changes durability, not the format limits.
3. **A small filesystem seam.** Options: duplicate ext2 assumptions in every caller, redesign the entire VFS, or adapt the documented tree seam in stages. Recommend the last, with no simultaneous SMP/scheduler change.
4. **btrfs as an explicitly gated experiment.** Options: next default root, RO-first interoperability, or a new COW format. Recommend RO-first after specification admission; no writer commitment until recovery gaps close. An own COW design is not a cheaper trust shortcut.
5. **Restore is a capability contract, not a filesystem badge.** Options: flatten unknown metadata, trust filesystem names, or qualify exact bounded APIs and fail closed. Recommend qualification and explicit refusal, plus maintenance boot integration. Snapshot support may help later but does not replace source identity, metadata or consumer durability policy.
6. **Preserve automation and defer layout/encryption expansion.** Options: change defaults in place, add inert questions, or version new profiles and stage usable controls. Recommend additive/versioned choices, exact legacy tokens, fixed ordered mode, and current single-root/ESP layout until cross-volume staging and recovery work. No physical conversion is proposed.

### The first three implementation contracts

These start **after** the journal-failure correction's green head, not instead of that work. Estimated one lane each initially; split any contract whose failure matrix cannot fit a bounded review. The 3–5-lane baseline allowance above reserves room for that split.

**First: qualify the root's durability capability.**

- Scope: a versioned, read-only query tied to a held root/device/mount identity. Report actual feature profile, journal active/recovered/failed state, ordered mode, read-only state and barrier availability. A sticky failure revokes qualification immediately; a prior answer is not a lifetime token. No filesystem-format changes.
- Before implementation: specify how consumers revalidate identity and observe a failure between query and sync; native package-manager qualification must require the positive signal, not a fabricated `/proc/fs/jbd2` directory.
- Done when: no-journal, wrong device, readonly, unsupported-feature, missing-flush and failed-journal controls refuse; matched healthy ext3 accepts only on the tested profile. File/directory fsync and rename recovery agree with Linux under EIO and power cuts. Dirty RO inspection is explicitly tested for no writes. Carry every issue-411 row; plant false-positive journal qualification. Consumer adoption can be a separate reviewed change, never silently relaxed.

**Second: format the narrow journalled profile on PAX.**

- Scope: extend the offline disk-tool path with an explicit ext3 profile, not a menu or in-place ext2 conversion. Specify internal journal allocation, inode 8, UUID, feature masks, journal size/minimum geometry, initialized contents and free-space accounting. Preserve legacy ext2 output and the source-file bound unless widened in a separately tested change.
- Done when: a PAX-produced scratch volume is accepted by Linux and e2fsck, Linux-produced matching volumes by PAX; read back all superblocks, inode tables, journal map and population metadata. Tiny/full/partial-group and large-address cases, bad geometry and allocation failures have named outcomes. Cut formatting at each phase: incomplete output is not advertised as a completed install. Plant a journal allocation/bitmap mismatch; keep disktools, ext2, journal and checker compatibility rows green.

**Third: expose ext3 in the installer and its recovery path.**

- Scope: additive versioned profile choice, exact old scripted path retained; write and verify the selected profile; bind it into boot/fstab/manifest/plan identity. Keep one root, the existing ESP geometry and ordered mode. Add maintenance/rescue entry behavior needed by consumers without enabling unfinished restore verbs.
- Done when: install each profile to a fresh and a previously used disposable QEMU disk, boot it alone under BIOS/UEFI, check the root with Linux, reboot persistent data, and upgrade from both supported profiles. Staged new kernel and rescue read the same profile; wrong/unsupported images refuse before writes. Cut install, upgrade, consumer transaction and recovery phases; unrelated disk hashes remain equal. Old scripted byte tokens and cancellation behavior are golden rows. Plant a selected-profile/actual-superblock mismatch. No real-disk qualification is implied.

Subsequent work is the 2–4-lane backend seam, bounded backup APIs/maintenance qualification (estimate 2–4 owning-project lanes, independent of format choice), checker capacity and then §3's format stages. Do not postpone safe backup admission merely to obtain snapshots. If only ext2-size limits motivate the work, budget ext4's addressing and tooling, not merely the ext3 menu.

### This note's checks and remaining uncertainty

- Prediction was committed first in [prediction.txt](px140/prediction.txt). The documented host/installer split, independent consumer gates and the existing but ext2-coupled tree seam matched it; no elapsed-time prediction was made.
- The notes check verifies five top-level sections, the exact two legacy commands against BOOT, the host/installer format distinction, numeric ceiling arithmetic, required candidate/API coverage, local link targets and public-text hygiene. Its deliberately wrong “installer formats ext3” plant must fail `installer-format-distinction`; this tests the census check, **not** a kernel durability gate.
- Historical installer evidence above was inspected down to PASS and END; no SKIP is counted as a result. The other capability tables are explicitly Read/Derived, and all lane counts are estimates.
- No fresh behavioral probe, filesystem feature-mask dump, source-level seam count, maximum-size test or new crash-safety result was obtained. Those are named acceptance work, not omitted passes. No compute-pool job was needed.
- README was read in full. This notes-only change moves no command or implemented capability. Its existing general journal durability prose and BOOT's “anything else refused” need reconciliation with issue 411 when that correction lands; this note does not certify them. No unrelated README rewrite is included.
- Nothing here enables btrfs writes, converts a disk, changes a scripted token, declares an ext3 root qualified for pxg/Denward, or grants filesystem snapshots a backup guarantee.
