# px77d s2: the stick from kout2 (d7af9a7f's kernel sources) and four entries under KVM.
set -x
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
C=${C:-d7af9a7f32129b7668ba8db51e57dbf694959539}
T=${T:-t2}
K=${K:-$L/kout2/kmain_console.elf}
taskset -c 0-5 bash $L/stick.sh $K $C $L/test/$T.img > $L/logs/stick-$T.log 2>&1; echo "stick $T exit $?"
for e in ${ENTRIES:-1 3 10 11}; do
  ENTRY=$e bash $L/repro.sh 12g $T-e$e $L/test/$T.img kvm vga file 4G 2 ${SECS:-70} > $L/logs/run-$T-e$e.log 2>&1; echo "run $T e$e exit $?"
done
