#!/bin/bash
# px50 on kasumi: the kernel's cost, trunk d0a48be against the branch: kmain_console's and kmain_session's sections, native and release.
L=$HOME/lanes/px50
[ -d $L/trunk/kernel ] || { mkdir -p $L/trunk && git -C $L/pax archive d0a48be | tar -x -C $L/trunk; }
for t in trunk pax; do
  for k in kmain_console kmain_session; do
    for tier in native release; do
      flag=; [ $tier = release ] && flag=--release
      mkdir -p $L/build/cost/$t-$k-$tier
      podman run --rm -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
        cd $L/$t && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tools/build-kernel $flag --src kernel/$k.lu $L/build/cost/$t-$k-$tier >/dev/null 2>&1 && size -A $L/build/cost/$t-$k-$tier/$k.elf | grep -E '^\.(text|rodata|data|bss) '" 2>/dev/null | sed "s/^/$t $k $tier /"
    done
  done
done
