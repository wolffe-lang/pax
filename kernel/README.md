# kernel/

The wolf kernel. Empty until px01 (first light), which waits on the KWC
campaign (`sprints/compiler/91-freestanding/` in the planning repo): wolf has
to emit a freestanding x86-64 object before PAX can hold a line of it. The
requirements the boot protocol puts on that object are in `docs/BOOT.md`.
