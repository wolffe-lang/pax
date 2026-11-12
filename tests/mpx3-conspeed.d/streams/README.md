# The recorded streams px129's console timing replays

Each directory is one stream for `user/elf/conspeed.c`: `setup` written once untimed, then `1`, `2`, …
replayed in rotation, one write each. All were recorded on a Linux pseudo-terminal of 256 x 90 cells
(the console's grid at 2560 x 1440) with `TERM=linux`, the programs being the ones the installed image
ships, run unmodified; the queries a Linux VT answers were answered and then removed from the streams
(a replay's answer would land in the replaying shell's input).

- `fuss`: yew (`/bin/yew`, sha256 `edcca94a…cdb14bb4`) started as `yew .` in a clone of a small
  repository with one modified and one untracked file, which opens F mode. `setup` is its opening
  (26,856 bytes: the loading frame, then the tree); `1` is Down (169 bytes) and `2` Up (172 bytes):
  each rewrites the two rows the selection leaves and enters, 63 cells each, and nothing else.
- `fussopen`: F mode's opening as a frame: `1` is `ESC [ H ESC [ 2 J` and `fuss/setup`, `2` the clear
  alone.
- `cub`: cub (`~/Games/cub/cub`, sha256 `8056dfd4…cdb1045f`) under strace, its writes to standard
  output one by one: `setup` is the screen's modes and the writes from its first whole gameplay
  frame to the first step; `1` to `4` are four steps up (Up typed 0.1 s apart), one write each,
  81,019 to 82,157 bytes: the view moves, so almost every cell is written again.
