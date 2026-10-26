# qualify.sh — written by tests/mpx5-clef.d/qualify.py (as02b): clef on the
# image over the copied corpus, its expansion and its refusals. POSIX sh.
cd /usr/share/clef || exit 9
/bin/mkdir /tmp/q || exit 9
echo 'Q version --version'
/usr/bin/clef --version > /tmp/q/version.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/version.out
echo 'Q version end'
echo 'Q c01 --64 -o /tmp/q/c01.o corpus/muzzle/notes/lc01-probes/q2/crt0.S'
/usr/bin/clef --64 -o /tmp/q/c01.o corpus/muzzle/notes/lc01-probes/q2/crt0.S > /tmp/q/c01.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c01.out
echo "-- obj"
/bin/base64 /tmp/q/c01.o
echo 'Q c01 end'
echo 'Q c02 --64 -o /tmp/q/c02.o corpus/muzzle/notes/lc01-probes/q2/sys.S'
/usr/bin/clef --64 -o /tmp/q/c02.o corpus/muzzle/notes/lc01-probes/q2/sys.S > /tmp/q/c02.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c02.out
echo "-- obj"
/bin/base64 /tmp/q/c02.o
echo 'Q c02 end'
echo 'Q c03 --64 -o /tmp/q/c03.o corpus/muzzle/notes/lc01-probes/q9/cell.S'
/usr/bin/clef --64 -o /tmp/q/c03.o corpus/muzzle/notes/lc01-probes/q9/cell.S > /tmp/q/c03.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c03.out
echo "-- obj"
/bin/base64 /tmp/q/c03.o
echo 'Q c03 end'
echo 'Q c04 --64 -o /tmp/q/c04.o corpus/muzzle/src/crt0.S'
/usr/bin/clef --64 -o /tmp/q/c04.o corpus/muzzle/src/crt0.S > /tmp/q/c04.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c04.out
echo "-- obj"
/bin/base64 /tmp/q/c04.o
echo 'Q c04 end'
echo 'Q c05 --64 -o /tmp/q/c05.o corpus/muzzle/src/sys.S'
/usr/bin/clef --64 -o /tmp/q/c05.o corpus/muzzle/src/sys.S > /tmp/q/c05.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c05.out
echo "-- obj"
/bin/base64 /tmp/q/c05.o
echo 'Q c05 end'
echo 'Q c06 --64 -o /tmp/q/c06.o corpus/pax/boot/console.S'
/usr/bin/clef --64 -o /tmp/q/c06.o corpus/pax/boot/console.S > /tmp/q/c06.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c06.out
echo "-- obj"
/bin/base64 /tmp/q/c06.o
echo 'Q c06 end'
echo 'Q c07 --64 -o /tmp/q/c07.o corpus/pax/boot/cpu.S'
/usr/bin/clef --64 -o /tmp/q/c07.o corpus/pax/boot/cpu.S > /tmp/q/c07.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c07.out
echo "-- obj"
/bin/base64 /tmp/q/c07.o
echo 'Q c07 end'
echo 'Q c08 --64 -o /tmp/q/c08.o corpus/pax/boot/event.S'
/usr/bin/clef --64 -o /tmp/q/c08.o corpus/pax/boot/event.S > /tmp/q/c08.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c08.out
echo "-- obj"
/bin/base64 /tmp/q/c08.o
echo 'Q c08 end'
echo 'Q c09 --64 -o /tmp/q/c09.o corpus/pax/boot/font.S'
/usr/bin/clef --64 -o /tmp/q/c09.o corpus/pax/boot/font.S > /tmp/q/c09.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c09.out
echo "-- obj"
/bin/base64 /tmp/q/c09.o
echo 'Q c09 end'
echo 'Q c10 --64 -o /tmp/q/c10.o corpus/pax/boot/fpu.S'
/usr/bin/clef --64 -o /tmp/q/c10.o corpus/pax/boot/fpu.S > /tmp/q/c10.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c10.out
echo "-- obj"
/bin/base64 /tmp/q/c10.o
echo 'Q c10 end'
echo 'Q c11 --64 -o /tmp/q/c11.o corpus/pax/boot/io.S'
/usr/bin/clef --64 -o /tmp/q/c11.o corpus/pax/boot/io.S > /tmp/q/c11.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c11.out
echo "-- obj"
/bin/base64 /tmp/q/c11.o
echo 'Q c11 end'
echo 'Q c12 --64 -o /tmp/q/c12.o corpus/pax/boot/isr.S'
/usr/bin/clef --64 -o /tmp/q/c12.o corpus/pax/boot/isr.S > /tmp/q/c12.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c12.out
echo "-- obj"
/bin/base64 /tmp/q/c12.o
echo 'Q c12 end'
echo 'Q c13 --64 -o /tmp/q/c13.o corpus/pax/boot/net.S'
/usr/bin/clef --64 -o /tmp/q/c13.o corpus/pax/boot/net.S > /tmp/q/c13.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c13.out
echo "-- obj"
/bin/base64 /tmp/q/c13.o
echo 'Q c13 end'
echo 'Q c14 --64 -o /tmp/q/c14.o corpus/pax/boot/sched.S'
/usr/bin/clef --64 -o /tmp/q/c14.o corpus/pax/boot/sched.S > /tmp/q/c14.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c14.out
echo "-- obj"
/bin/base64 /tmp/q/c14.o
echo 'Q c14 end'
echo 'Q c15 --64 -o /tmp/q/c15.o corpus/pax/boot/screen.S'
/usr/bin/clef --64 -o /tmp/q/c15.o corpus/pax/boot/screen.S > /tmp/q/c15.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c15.out
echo "-- obj"
/bin/base64 /tmp/q/c15.o
echo 'Q c15 end'
echo 'Q c16 --64 -o /tmp/q/c16.o corpus/pax/boot/sound.S'
/usr/bin/clef --64 -o /tmp/q/c16.o corpus/pax/boot/sound.S > /tmp/q/c16.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c16.out
echo "-- obj"
/bin/base64 /tmp/q/c16.o
echo 'Q c16 end'
echo 'Q c17 --64 -o /tmp/q/c17.o corpus/pax/boot/speaker.S'
/usr/bin/clef --64 -o /tmp/q/c17.o corpus/pax/boot/speaker.S > /tmp/q/c17.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c17.out
echo "-- obj"
/bin/base64 /tmp/q/c17.o
echo 'Q c17 end'
echo 'Q c18 --64 -o /tmp/q/c18.o corpus/pax/boot/start.S'
/usr/bin/clef --64 -o /tmp/q/c18.o corpus/pax/boot/start.S > /tmp/q/c18.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c18.out
echo "-- obj"
/bin/base64 /tmp/q/c18.o
echo 'Q c18 end'
echo 'Q c19 --64 -o /tmp/q/c19.o corpus/pax/boot/stub/pax-stub.s'
/usr/bin/clef --64 -o /tmp/q/c19.o corpus/pax/boot/stub/pax-stub.s > /tmp/q/c19.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c19.out
echo "-- obj"
/bin/base64 /tmp/q/c19.o
echo 'Q c19 end'
echo 'Q c20 --64 -o /tmp/q/c20.o corpus/pax/boot/tree.S'
/usr/bin/clef --64 -o /tmp/q/c20.o corpus/pax/boot/tree.S > /tmp/q/c20.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c20.out
echo "-- obj"
/bin/base64 /tmp/q/c20.o
echo 'Q c20 end'
echo 'Q c21 --64 -o /tmp/q/c21.o corpus/pax/boot/unix.S'
/usr/bin/clef --64 -o /tmp/q/c21.o corpus/pax/boot/unix.S > /tmp/q/c21.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c21.out
echo "-- obj"
/bin/base64 /tmp/q/c21.o
echo 'Q c21 end'
echo 'Q c22 --64 -o /tmp/q/c22.o corpus/pax/boot/user.S'
/usr/bin/clef --64 -o /tmp/q/c22.o corpus/pax/boot/user.S > /tmp/q/c22.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c22.out
echo "-- obj"
/bin/base64 /tmp/q/c22.o
echo 'Q c22 end'
echo 'Q c23 --64 -o /tmp/q/c23.o corpus/pax/tests/mkw.d/boot/io.S'
/usr/bin/clef --64 -o /tmp/q/c23.o corpus/pax/tests/mkw.d/boot/io.S > /tmp/q/c23.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c23.out
echo "-- obj"
/bin/base64 /tmp/q/c23.o
echo 'Q c23 end'
echo 'Q c24 --64 -o /tmp/q/c24.o corpus/pax/user/elf/ask.S'
/usr/bin/clef --64 -o /tmp/q/c24.o corpus/pax/user/elf/ask.S > /tmp/q/c24.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c24.out
echo "-- obj"
/bin/base64 /tmp/q/c24.o
echo 'Q c24 end'
echo 'Q c25 --64 -o /tmp/q/c25.o corpus/pax/user/elf/hello.S'
/usr/bin/clef --64 -o /tmp/q/c25.o corpus/pax/user/elf/hello.S > /tmp/q/c25.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c25.out
echo "-- obj"
/bin/base64 /tmp/q/c25.o
echo 'Q c25 end'
echo 'Q c26 --64 -o /tmp/q/c26.o corpus/pax/user/elf/hold.S'
/usr/bin/clef --64 -o /tmp/q/c26.o corpus/pax/user/elf/hold.S > /tmp/q/c26.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c26.out
echo "-- obj"
/bin/base64 /tmp/q/c26.o
echo 'Q c26 end'
echo 'Q c27 --64 -o /tmp/q/c27.o corpus/pax/user/elf/reboot.S'
/usr/bin/clef --64 -o /tmp/q/c27.o corpus/pax/user/elf/reboot.S > /tmp/q/c27.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c27.out
echo "-- obj"
/bin/base64 /tmp/q/c27.o
echo 'Q c27 end'
echo 'Q c28 --64 -o /tmp/q/c28.o corpus/pax/user/elf/seven.S'
/usr/bin/clef --64 -o /tmp/q/c28.o corpus/pax/user/elf/seven.S > /tmp/q/c28.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c28.out
echo "-- obj"
/bin/base64 /tmp/q/c28.o
echo 'Q c28 end'
echo 'Q c29 --64 -o /tmp/q/c29.o corpus/pax/user/play/kd.S'
/usr/bin/clef --64 -o /tmp/q/c29.o corpus/pax/user/play/kd.S > /tmp/q/c29.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c29.out
echo "-- obj"
/bin/base64 /tmp/q/c29.o
echo 'Q c29 end'
echo 'Q c30 --64 -o /tmp/q/c30.o corpus/pax/user/programs.S'
/usr/bin/clef --64 -o /tmp/q/c30.o corpus/pax/user/programs.S > /tmp/q/c30.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c30.out
echo "-- obj"
/bin/base64 /tmp/q/c30.o
echo 'Q c30 end'
echo 'Q c31 --64 -o /tmp/q/c31.o corpus/pax/user/termwolf/tio.S'
/usr/bin/clef --64 -o /tmp/q/c31.o corpus/pax/user/termwolf/tio.S > /tmp/q/c31.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c31.out
echo "-- obj"
/bin/base64 /tmp/q/c31.o
echo 'Q c31 end'
echo 'Q c32 --64 -o /tmp/q/c32.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/asm/seven_x86_64.S'
/usr/bin/clef --64 -o /tmp/q/c32.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/asm/seven_x86_64.S > /tmp/q/c32.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c32.out
echo "-- obj"
/bin/base64 /tmp/q/c32.o
echo 'Q c32 end'
echo 'Q c33 --64 -o /tmp/q/c33.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding/rt_stub.S'
/usr/bin/clef --64 -o /tmp/q/c33.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding/rt_stub.S > /tmp/q/c33.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c33.out
echo "-- obj"
/bin/base64 /tmp/q/c33.o
echo 'Q c33 end'
echo 'Q c34 --64 -o /tmp/q/c34.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding/start.S'
/usr/bin/clef --64 -o /tmp/q/c34.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding/start.S > /tmp/q/c34.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c34.out
echo "-- obj"
/bin/base64 /tmp/q/c34.o
echo 'Q c34 end'
echo 'Q c35 --64 -o /tmp/q/c35.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_alloc/heap.S'
/usr/bin/clef --64 -o /tmp/q/c35.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_alloc/heap.S > /tmp/q/c35.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c35.out
echo "-- obj"
/bin/base64 /tmp/q/c35.o
echo 'Q c35 end'
echo 'Q c36 --64 -o /tmp/q/c36.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_device/dev_window.S'
/usr/bin/clef --64 -o /tmp/q/c36.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_device/dev_window.S > /tmp/q/c36.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c36.out
echo "-- obj"
/bin/base64 /tmp/q/c36.o
echo 'Q c36 end'
echo 'Q c37 --64 -o /tmp/q/c37.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_interrupt/boot.S'
/usr/bin/clef --64 -o /tmp/q/c37.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_interrupt/boot.S > /tmp/q/c37.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c37.out
echo "-- obj"
/bin/base64 /tmp/q/c37.o
echo 'Q c37 end'
echo 'Q c38 --64 -o /tmp/q/c38.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_interrupt/isr.S'
/usr/bin/clef --64 -o /tmp/q/c38.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_interrupt/isr.S > /tmp/q/c38.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c38.out
echo "-- obj"
/bin/base64 /tmp/q/c38.o
echo 'Q c38 end'
echo 'Q c39 --64 -o /tmp/q/c39.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_static/table.S'
/usr/bin/clef --64 -o /tmp/q/c39.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_static/table.S > /tmp/q/c39.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c39.out
echo "-- obj"
/bin/base64 /tmp/q/c39.o
echo 'Q c39 end'
echo 'Q c40 --64 -o /tmp/q/c40.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_threads/threads.S'
/usr/bin/clef --64 -o /tmp/q/c40.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/freestanding_threads/threads.S > /tmp/q/c40.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c40.out
echo "-- obj"
/bin/base64 /tmp/q/c40.o
echo 'Q c40 end'
echo 'Q c41 --64 -o /tmp/q/c41.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/pkg/ffi/kernel/kern/io.S'
/usr/bin/clef --64 -o /tmp/q/c41.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/pkg/ffi/kernel/kern/io.S > /tmp/q/c41.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c41.out
echo "-- obj"
/bin/base64 /tmp/q/c41.o
echo 'Q c41 end'
echo 'Q c42 --64 -o /tmp/q/c42.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/shr_range/rd.S'
/usr/bin/clef --64 -o /tmp/q/c42.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/shr_range/rd.S > /tmp/q/c42.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c42.out
echo "-- obj"
/bin/base64 /tmp/q/c42.o
echo 'Q c42 end'
echo 'Q c43 --64 -o /tmp/q/c43.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/stale_global/kernel/stale.S'
/usr/bin/clef --64 -o /tmp/q/c43.o corpus/wolf-lang/crates/wolf_driver/tests/fixtures/stale_global/kernel/stale.S > /tmp/q/c43.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c43.out
echo "-- obj"
/bin/base64 /tmp/q/c43.o
echo 'Q c43 end'
echo 'Q expand --expand corpus/pax/boot/isr.S'
/usr/bin/clef --expand corpus/pax/boot/isr.S > /tmp/q/expand.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/expand.out
echo 'Q expand end'
echo 'Q provenance --provenance -o /tmp/q/provenance.o corpus/pax/boot/isr.S'
/usr/bin/clef --provenance -o /tmp/q/provenance.o corpus/pax/boot/isr.S > /tmp/q/provenance.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/provenance.out
echo "-- obj"
/bin/base64 /tmp/q/provenance.o
echo 'Q provenance end'
echo 'Q c-form -c corpus/pax/boot/io.S -o /tmp/q/c-form.o --target=x86_64-unknown-none-elf'
/usr/bin/clef -c corpus/pax/boot/io.S -o /tmp/q/c-form.o --target=x86_64-unknown-none-elf > /tmp/q/c-form.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/c-form.out
echo "-- obj"
/bin/base64 /tmp/q/c-form.o
echo 'Q c-form end'
echo 'Q r-none '
/usr/bin/clef  > /tmp/q/r-none.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-none.out
echo 'Q r-none end'
echo 'Q r-option --bogus corpus/pax/boot/io.S'
/usr/bin/clef --bogus corpus/pax/boot/io.S > /tmp/q/r-option.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-option.out
echo 'Q r-option end'
echo 'Q r-c-source bad/main.c'
/usr/bin/clef bad/main.c > /tmp/q/r-c-source.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-c-source.out
echo 'Q r-c-source end'
echo 'Q r-target-no-c --target=x86_64-unknown-none-elf corpus/pax/boot/io.S'
/usr/bin/clef --target=x86_64-unknown-none-elf corpus/pax/boot/io.S > /tmp/q/r-target-no-c.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-target-no-c.out
echo 'Q r-target-no-c end'
echo 'Q r-expand-o --expand -o /tmp/q/r-expand-o.o corpus/pax/boot/io.S'
/usr/bin/clef --expand -o /tmp/q/r-expand-o.o corpus/pax/boot/io.S > /tmp/q/r-expand-o.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-expand-o.out
echo 'Q r-expand-o end'
echo 'Q r-foreign --target=aarch64-unknown-none -c corpus/pax/boot/io.S -o /tmp/q/r-foreign.o'
/usr/bin/clef --target=aarch64-unknown-none -c corpus/pax/boot/io.S -o /tmp/q/r-foreign.o > /tmp/q/r-foreign.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-foreign.out
echo 'Q r-foreign end'
echo 'Q r-same -o /tmp/q/self.S /tmp/q/self.S'
/usr/bin/clef -o /tmp/q/self.S /tmp/q/self.S > /tmp/q/r-same.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-same.out
echo 'Q r-same end'
echo 'Q r-missing nosuch.S'
/usr/bin/clef nosuch.S > /tmp/q/r-missing.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-missing.out
echo 'Q r-missing end'
echo 'Q r-source --64 -o /tmp/q/keep.o bad/unknown.S'
echo previous > /tmp/q/keep.o
/usr/bin/clef --64 -o /tmp/q/keep.o bad/unknown.S > /tmp/q/r-source.out 2>&1
echo "rc=$?"
echo "-- out"
/bin/base64 /tmp/q/r-source.out
echo "-- obj"
/bin/base64 /tmp/q/keep.o
echo 'Q r-source end'
echo "Q all end"
