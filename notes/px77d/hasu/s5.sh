# px77d s5: where OVMF puts RAM-backed GOP framebuffers (ramfb, virtio-gpu-pci) at 32 GiB.
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
IMG=$L/out/pax-triage-fedb6f5f.img
for d in ramfb vgpu; do bash $L/repro.sh 36g fb-$d $IMG kvm $d none 32G 4 70 > $L/logs/run-fb-$d.log 2>&1; echo "run $d exit $?"; done
