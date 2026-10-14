#!/bin/bash
# px41 on kasumi: K8 under 12 loops on CPUs 12-15, ten boots of trunk's play, then ten of the head's (w6).
L=~/lanes/px41
$L/st/k8loop.sh $L/t-trunk 10 12 12-15 $L/ev/k8-trunk-load12
$L/st/k8loop.sh $L/t-w6 10 12 12-15 $L/ev/k8-w6-load12
echo done > $L/ev/k8.done
