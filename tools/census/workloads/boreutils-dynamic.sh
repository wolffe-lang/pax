# The same suite against the DYNAMIC build (exactly tools/build's link:
# PIE, ld.so, libc, libm, libgcc_s). Scope: the boreutils binaries only.
SCOPE='/stage/bore/dyn/*'
workload() {
    cp -R /stage/boreutils /work/boreutils
    cd /work/boreutils
    BORE_ORACLE_ANY=1 BORE_GNU_PREFIX= T python3 tools/difftest --bin /stage/bore/dyn
}
