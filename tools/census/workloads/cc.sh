# make + cc building a small C program (cpkg's first shape: a Makefile,
# two translation units, a header, an archive, a link), then running it.
# Scope: the whole tree (make, its /bin/sh, the gcc driver, cc1, as,
# collect2, ld, ar) and the program.
SCOPE='*'
workload() {
    cp -R /census/cc /work/cc
    cd /work/cc
    T make CC=cc
    T ./hello census
    T make clean
}
