#!/bin/bash
# px57 on kasumi: the kernel's cost of the pin, trunk ebbef86 (wolf 0.2.33) against the branch (0.2.34):
# kmain_console's and kmain_session's sections, native and release, built in px13-ubuntu.
L=$HOME/lanes/px57; X=${PX57_TREE:-$L/pax}
[ -d $L/trunk/kernel ] || { mkdir -p $L/trunk && git -C $X archive ebbef86 | tar -x -C $L/trunk; }
for t in trunk branch; do
  d=$L/trunk; [ $t = branch ] && d=$X
  for k in kmain_console kmain_session; do
    for tier in native release; do
      flag=; [ $tier = release ] && flag=--release
      o=$L/build/cost/$t-$k-$tier; mkdir -p $o
      podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
        cd $d && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && \$PAX_WOLF --version | head -n 1 && tools/build-kernel $flag --src kernel/$k.lu $o >/dev/null 2>&1 && sha256sum $o/$k.elf && size -A $o/$k.elf | grep -E '^\.(text|rodata|data|bss) '" 2>/dev/null | sed "s/^/$t $k $tier /"
    done
  done
done
