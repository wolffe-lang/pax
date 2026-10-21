#!/bin/bash
# px56, on nomad-1: the worktree's tracked and new files to kasumi's clone (~/lanes/px56/pax), no .git; nothing built here.
cd $HOME/lanes/px56/pax || exit 2
{ git ls-files; git ls-files --others --exclude-standard; } | rsync -a --files-from=- . kasumi:lanes/px56/pax/
ssh kasumi "cd ~/lanes/px56/pax && git status --short | head -40"
