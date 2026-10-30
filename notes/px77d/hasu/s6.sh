# px77d s6: the planted break seen red (triage without CR4.MCE, on a scratch copy), then the
# bisection stick at the px77d head by px77b's recipe, its KVM smoke and its two reads.
set -x
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
H=089896db5098159e2c4f85b852f9d26755be7c1f
# 1. the plant, in a copy of the tree (the clone is never edited)
rm -rf $L/plant-mce && cp -a $L/pax $L/plant-mce && cd $L/plant-mce && git checkout -q -f $H
python3 -I -c "
p='boot/triage.S'; s=open(p).read(); o='        orq     \$0x40, %rax             /* CR4.MCE: a machine check is drawn */\n'
assert o in s; open(p,'w').write(s.replace(o, ''))"
git diff --stat
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-plant --memory 12g --pids-limit 16384 --ulimit core=0:0 --device /dev/kvm  -v "$L:$L" -w "$L/plant-mce" -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build-plant -e TMPDIR=$L/tmp -e PAX_TRIAGE_FIRMWARE=uefi  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*'  localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tests/mpx6-triage' > $L/logs/plant-mce.log 2>&1
echo "plant mce exit $?"
# 2. the bisection stick
cd $L/pax && git fetch -q origin px77d && git checkout -q -f $H && git rev-parse HEAD
sed -e "s|fedb6f5f4353619008970e21a11124300bf46552|$H|" -e 's|"$L/out"|"$L/out-b"|g' $L/build-inside.sh > $L/build-inside-b.sh
grep -n "out-b\|$H" $L/build-inside-b.sh | head -3
rm -rf $L/out-b
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-build --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0  -v "$L:$L" -w "$L/pax" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*'  localhost/px75-ubuntu:2 taskset -c 0-5 bash "$L/build-inside-b.sh" > $L/logs/build-inside-b.log 2>&1
echo "build-inside-b exit $?"
CONF=$L/pax/boot/limine-bisect.conf OUTDIR=$L/out-b taskset -c 0-5 bash $L/stick.sh $L/out-b/kernel/kmain_console.elf $H $L/out-b/pax-bisect-089896db.img > $L/logs/stick-b.log 2>&1
echo "stick b exit $?"
for e in 1 2 6 8; do ENTRY=$e bash $L/repro.sh 12g bisect-e$e $L/out-b/pax-bisect-089896db.img kvm vga file 4G 2 70 > $L/logs/run-bisect-e$e.log 2>&1; echo "run bisect e$e exit $?"; done
sha256sum $L/out-b/pax-bisect-089896db.img | tee $L/bisect-hasu-read-1.sha256
sha256sum $L/out-b/pax-bisect-089896db.img | tee $L/bisect-hasu-read-2.sha256
