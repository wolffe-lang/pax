/* sysret-ss.c - B17 (px112, pax#340): the stack segment ring 3 holds after
   a system call, and after interrupts taken in ring 3.

   PAX returns from a system call by SYSRETQ, which loads SS from STAR's
   SYSRET selector base plus 8 (kernel/user's STAR, boot/isr.S's
   pax_sysret). Intel's SDM (vol. 2, SYSRET) sets the selector's privilege
   bits to 3 whatever the base holds; some processors do not, and there a
   base without them leaves SS at privilege 0 in ring 3. Nothing notices
   until an interrupt is taken in ring 3: its IRETQ back checks SS against
   the code segment's privilege and raises #GP with the selector (0x18),
   and PAX panics. pax#340's hosted run met it at the first program.

   So this program makes a system call, reads SS and CS, then stays in
   ring 3 for 200 ms across the 100 Hz timer's interrupts (a busy loop,
   with a clock_gettime between turns, each one a SYSRETQ again), and
   reads SS once more. It prints one line and exits 0 when SS is 0x1b
   and CS 0x23 both times, 1 otherwise. On a processor that forces the
   privilege bits it cannot go red; the hosted mpx5-burrowd job, the one
   that boots PAX under KVM on its runner's own processor, is where it can.

   A static x86-64 Linux program against the baseline glibc's libc.a
   (tests/mpx5-burrowd builds it with gcc -static -no-pie). */
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/syscall.h>

static unsigned short read_ss(void)
{
    unsigned short v;
    __asm__ volatile ("mov %%ss, %0" : "=r"(v));
    return v;
}

static unsigned short read_cs(void)
{
    unsigned short v;
    __asm__ volatile ("mov %%cs, %0" : "=r"(v));
    return v;
}

static long ms_since(const struct timespec *t0)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (t.tv_sec - t0->tv_sec) * 1000 + (t.tv_nsec - t0->tv_nsec) / 1000000;
}

int main(void)
{
    syscall(SYS_getpid);
    unsigned short ss1 = read_ss(), cs1 = read_cs();
    struct timespec t0;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    long ms = 0;
    unsigned long turns = 0;
    while (ms < 200) {
        for (volatile unsigned long i = 0; i < 1000000; i++) {
        }
        turns++;
        ms = ms_since(&t0);
    }
    unsigned short ss2 = read_ss(), cs2 = read_cs();
    int ok = ss1 == 0x1b && cs1 == 0x23 && ss2 == 0x1b && cs2 == 0x23;
    printf("%s: ss 0x%x cs 0x%x after a system call; ss 0x%x cs 0x%x after %ld ms in ring 3 (%lu turns)\n",
           ok ? "ok" : "wrong", ss1, cs1, ss2, cs2, ms, turns);
    return ok ? 0 : 1;
}
