#!/bin/bash
# px52 on kasumi: evprobe and fdtab built in px13-ubuntu (tools/mknet's and tools/mkjobs' compiler lines), then
# evprobe run in a throwaway rootless container (black-box Linux: kasumi's own kernel), as root and as 1000:1000,
# twice each.   linux-probes.sh
L=$HOME/lanes/px52; P=$L/pax; O=$L/ev/linux-probes
mkdir -p $O $L/bin
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cd $P && cc -O1 -Wall -Wextra -static -no-pie -Wl,--build-id=none -Wl,-z,noexecstack -o $L/bin/evprobe user/net/evprobe.c && cc -static -no-pie -O1 -pthread -Wall -Wextra -Wno-unused-result -Wno-unused-function -Wl,--build-id=none -Wl,-z,noexecstack -o $L/bin/fdtab user/elf/fdtab.c && sha256sum $L/bin/evprobe $L/bin/fdtab" || exit 1
for i in 1 2; do
  taskset -c 0-3 podman run --rm --network none -v $L/bin:/x:ro localhost/px13-ubuntu /x/evprobe > $O/evprobe-root.$i.txt; echo "root $i: $?"
  taskset -c 0-3 podman run --rm --network none --user 1000:1000 -v $L/bin:/x:ro localhost/px13-ubuntu /x/evprobe > $O/evprobe-user.$i.txt; echo "user $i: $?"
done
echo "kernel $(uname -r)"
sha256sum $O/*.txt
