# bash running the same POSIX script, the bash-only script (arrays,
# [[ ]], process substitution, mapfile, coproc, read -t), and a login
# shell's startup (/etc/profile). Scope: the bash image (Arch's /bin/sh
# is bash, so make's and system()'s shells land here too when named so).
SCOPE='/usr/bin/bash /usr/bin/sh /bin/sh /bin/bash'
workload() {
    cp -R /census/shell /work/shell
    cd /work/shell
    T /usr/bin/bash census.sh
    T /usr/bin/bash bashisms.sh
    T /usr/bin/bash -l -c 'echo login'
    printf 'echo interactive-ish; exit 0\n' | T /usr/bin/bash -i
}
