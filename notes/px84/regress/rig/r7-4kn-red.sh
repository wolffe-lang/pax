set -uo pipefail
L=/mnt/steamlib/lanes/px84
I=$L/build/r7-inputs
rm -rf $I $L/build/r7-4kn-red
mkdir -p $I/build
ln -s $L/build/r5-install/inputs/build/disktools $I/build/disktools
ln -s $L/build/r5-install/inputs/build/full $I/build/full
( cd $L/plant-4kn && tools/mkinstall $I/build/install-gate/bin ) || { echo 'PLANT BUILD FAILED'; exit 2; }
PAX_INSTALL_FAULT=4kn python3 -I tests/mpx6-install.d/install.py "$PWD" $I $L/build/r7-4kn-red no vdb > $L/build/r7-4kn-red.out 2>&1
rc=$?
tail -c 3000 $L/build/r7-4kn-red.out | grep -av '^\s*$' | tail -15
if [ $rc -ne 0 ]; then echo "RED as planted: install.py rc=$rc (planner accepts 4096-byte sectors)"; exit 0; fi
echo 'NOT RED: the 4Kn row passed with the planted planner'; exit 1
