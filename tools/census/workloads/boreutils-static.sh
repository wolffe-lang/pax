# boreutils' own differential suite (tools/difftest, every case file),
# run against the STATIC build: M-PX3's binary. Scope: the boreutils
# binaries only; the python harness and GNU's side are not counted.
# BORE_ORACLE_ANY: the image's coreutils is 9.12, not the 9.11 oracle of
# record; the verdicts are not the census's subject, the calls are.
SCOPE='/stage/bore/static/*'
workload() {
    cp -R /stage/boreutils /work/boreutils
    cd /work/boreutils
    BORE_ORACLE_ANY=1 BORE_GNU_PREFIX= T python3 tools/difftest --bin /stage/bore/static
}
