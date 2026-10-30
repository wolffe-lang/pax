# px77d s4: the final stick's entry 1 on the x2APIC-ID machine and at kasumi's 32 GiB / 16 CPUs.
set -x
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
IMG=$L/out/pax-triage-fedb6f5f.img
MACHINE='q35,pit=off,kernel-irqchip=split' PRE='-device intel-iommu,intremap=on,eim=on -device host-x86_64-cpu,socket-id=1,core-id=0,thread-id=0' \
  bash $L/repro.sh 12g final-x2apic $IMG kvm vga file 4G 1,maxcpus=512,sockets=2,cores=256,threads=1 75 > $L/logs/run-final-x2apic.log 2>&1; echo "run x2apic exit $?"
bash $L/repro.sh 36g final-32g $IMG kvm vga none 32G 16 75 > $L/logs/run-final-32g.log 2>&1; echo "run 32g exit $?"
