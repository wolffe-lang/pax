# font — the screen's glyphs (px19)

`spleen-8x16.bdf` is **Spleen 2.2.0**'s 8×16 bitmap font, by Frederic
Cambus, copied unmodified from the release tarball
`https://github.com/fcambus/spleen/releases/download/2.2.0/spleen-2.2.0.tar.gz`
(sha256 `ec42925c…`; the BDF itself `4a3d97ee…`). Spleen is released
under the BSD 2-Clause licence, kept here as `LICENSE.spleen` (the
tarball's `LICENSE`, unmodified, `f33fe867…`); the BDF's own header
carries the copyright notice and `SPDX-License-Identifier:
BSD-2-Clause`. The BSD 2-Clause licence is compatible with PAX's
GPL-3.0: it asks that the notice and the disclaimer travel with the
source and with binaries' documentation, which this file and
`LICENSE.spleen` do.

`tools/mkfont` turns the BDF into `boot/font.S`, the 256-glyph table
the kernel draws from (code points 0–255; one without a glyph in the
font is drawn as `?`), and `tools/mkfont --check` says whether the
committed `boot/font.S` is what the BDF gives. `tools/screen-ref`, the
host-side reference renderer `tests/mpx3-screen` compares the screen
with, reads the BDF itself, not `boot/font.S`.
