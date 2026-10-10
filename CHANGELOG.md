# Changelog

pax has no release yet; this file starts with px17, whose contract asks
for a paragraph under an Unreleased heading. Earlier work is told in
`notes/` (one note per lane) and the planning repository's
`sprints/pax/index.md`.

## Unreleased

- **Pipes, redirection and `cd` (px17).** pelt `3e7516c` (H2, wolf
  0.2.26) is the shell PAX boots, and its plumbing runs as on Linux:
  `ls /bin | wc -l`, `cat /etc/motd > /dev/null`, `cd /etc; cat motd`,
  a group reading one file through two children, `cd`'s errors — each
  typed session byte-identical to Linux's (`tests/mpx3-shell`,
  `shell-plumb`). New system calls: `pipe`, `pipe2`, `socketpair`,
  `sendto`, `recvfrom`, `fcntl`, `chdir`, `fchdir`; `getcwd` answers the
  real directory; `clone` without CLONE_VM is a **fork** (wolf 0.2.26's
  spawn forks, measured) on a copy of the caller's address space.
  Descriptors now share open files (one offset across `dup` and a
  child's copy, Linux's rule; px14's per-descriptor position is gone);
  pipes hold 65536 bytes, block, end at the last writer, and a write
  with no reader dies of SIGPIPE (status 13) under the default action
  (not pid 1) or answers -EPIPE; every process's end closes its
  descriptors. The tour's closing line now reads "All in wolf. Linux
  programs run on it unmodified: a shell, its pipes, its tools."
  Named drift: a seqpacket socket's record boundaries, a SIGPIPE
  handler not run, CLONE_CHILD_CLEARTID not kept, a fork copies every
  page.
