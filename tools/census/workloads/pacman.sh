# pacman in the container: a forced refresh, a full upgrade, an install
# with dependencies, scriptlets and hooks (nginx: sysusers, tmpfiles),
# queries, and a removal. Scope: the whole process tree (gpg, hooks and
# scriptlets are part of what a package manager needs from a kernel).
SCOPE='*'
workload() {
    T pacman -Syy --noconfirm
    T pacman -Syu --noconfirm
    T pacman -S --noconfirm jq tree nginx
    T pacman -Qi jq
    T pacman -Qkk tree
    T pacman -Rns --noconfirm tree
}
