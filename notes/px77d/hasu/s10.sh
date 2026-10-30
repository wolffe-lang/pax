# px77d s10: the fix stick at 9db67a66 by px77b's recipe (boot/limine-fix.conf), its KVM smoke and its two reads.
set -x
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
H=9db67a661012415082e538bf89c3c8422ad9ae65
cd $L/pax && git fetch -q origin px77d && git checkout -q -f $H && git clean -fdq tests && git rev-parse HEAD
sed -e "s|fedb6f5f4353619008970e21a11124300bf46552|$H|" -e 's|"$L/out"|"$L/out-f"|g' $L/build-inside.sh > $L/build-inside-f.sh
rm -rf $L/out-f
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-build --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0  -v "$L:$L" -w "$L/pax" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*'  localhost/px75-ubuntu:2 taskset -c 0-5 bash "$L/build-inside-f.sh" > $L/logs/build-inside-f.log 2>&1
echo "build-inside-f exit $?"
CONF=$L/pax/boot/limine-fix.conf OUTDIR=$L/out-f taskset -c 0-5 bash $L/stick.sh $L/out-f/kernel/kmain_console.elf $H $L/out-f/pax-fix-9db67a66.img > $L/logs/stick-f.log 2>&1
echo "stick f exit $?"
for e in 1 2; do ENTRY=$e MENU_AT=3 bash $L/repro.sh 12g fix-e$e $L/out-f/pax-fix-9db67a66.img kvm vga file 4G 2 70 > $L/logs/run-fix-e$e.log 2>&1; echo "run fix e$e exit $?"; done
bash $L/repro.sh 36g fix-32g $L/out-f/pax-fix-9db67a66.img kvm vga none 32G 16 80 > $L/logs/run-fix-32g.log 2>&1; echo "run fix 32g exit $?"
sha256sum $L/out-f/pax-fix-9db67a66.img | tee $L/fix-hasu-read-1.sha256
sha256sum $L/out-f/pax-fix-9db67a66.img | tee $L/fix-hasu-read-2.sha256
