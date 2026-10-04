# dash running the census's POSIX script (shell/census.sh) and a login
# shell's startup. Scope: the dash image only (the utilities the script
# runs are counted under their own workloads, or not at all).
SCOPE='/usr/bin/dash'
workload() {
    cp -R /census/shell /work/shell
    cd /work/shell
    T /usr/bin/dash census.sh
    T /usr/bin/dash -l -c 'echo login'
    printf 'echo interactive-ish; exit 0\n' | T /usr/bin/dash -i
}
