#!/bin/bash
# px53 on kasumi: the kernel's cost of the pin, trunk d733bf4 (wolf 0.2.32) against the branch (0.2.33):
# kmain_console's and kmain_session's sections, native and release, built in px13-ubuntu.
L=$HOME/lanes/px53
[ -d $L/trunk/kernel ] || { mkdir -p $L/trunk && git -C $L/pax archive d733bf4 | tar -x -C $L/trunk; }
for t in trunk pax; do
  for k in kmain_console kmain_session; do
    for tier in native release; do
      flag=; [ $tier = release ] && flag=--release
      mkdir -p $L/build/cost/$t-$k-$tier
      podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
        cd $L/$t && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && \$PAX_WOLF --version | head -n 1 && tools/build-kernel $flag --src kernel/$k.lu $L/build/cost/$t-$k-$tier >/dev/null 2>&1 && size -A $L/build/cost/$t-$k-$tier/$k.elf | grep -E '^\.(text|rodata|data|bss) '" 2>/dev/null | sed "s/^/$t $k $tier /"
    done
  done
done
