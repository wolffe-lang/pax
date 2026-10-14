#!/bin/bash
# px41 on kasumi: K8 under a lighter load (4 loops on CPUs 12-15, one a CPU), ten boots of trunk's play,
# then ten of the head's (w6); after k8.sh.
L=~/lanes/px41
while [ ! -f $L/ev/k8.done ]; do sleep 20; done
$L/st/k8loop.sh $L/t-trunk 10 4 12-15 $L/ev/k8-trunk-load4
$L/st/k8loop.sh $L/t-w6 10 4 12-15 $L/ev/k8-w6-load4
echo done > $L/ev/k8b.done
