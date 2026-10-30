# px77d s3: px77b's recipe at the px77d head (the release pair in the container, the live payload),
# then the triage stick from its kernel and live archive, the KVM checks, and the stick read twice.
set -x
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
H=fedb6f5f4353619008970e21a11124300bf46552
rm -rf $L/out
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-build --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 -v "$L:$L" -w "$L/pax" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash "$L/build-inside.sh" > $L/logs/build-inside.log 2>&1
echo "build-inside exit $?"
OUTDIR=$L/out taskset -c 0-5 bash $L/stick.sh $L/out/kernel/kmain_console.elf $H $L/out/pax-triage-fedb6f5f.img > $L/logs/stick-final.log 2>&1
echo "stick final exit $?"
for e in 1 10; do
  ENTRY=$e bash $L/repro.sh 12g final-e$e $L/out/pax-triage-fedb6f5f.img kvm vga file 4G 2 70 > $L/logs/run-final-e$e.log 2>&1; echo "run final e$e exit $?"
done
sha256sum $L/out/pax-triage-fedb6f5f.img | tee $L/image-hasu-read-1.sha256
sha256sum $L/out/pax-triage-fedb6f5f.img | tee $L/image-hasu-read-2.sha256
