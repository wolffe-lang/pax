/* Bounded-value witnesses derived from px146 W3-W6. Each child only
   requests a signal or a documented syscall error; the parent must survive. */
#include "common.h"
struct ksigaction { u64 handler, flags, restorer, mask; };
static void handler(int s) { (void)s; }
__asm__(".globl wit_restorer\nwit_restorer:\n mov $15, %eax\n syscall\n hlt\n");
extern void wit_restorer(void);
static i64 install(u64 address, u64 flags) {
    struct ksigaction sa = {address, 0x04000000UL | flags, (u64)wit_restorer, 0};
    return sys6(13, SIGUSR1, (i64)&sa, 0, 8, 0, 0);
}
static void child(int mode) {
    if (mode == 3) {
        require(install((u64)handler, 0) == 0);
        i64 rax = 62, pid = sys(39, 0, 0, 0);
        __asm__ volatile("mov %%rsp, %%r12\n mov $64, %%rsp\n syscall\n mov %%r12, %%rsp"
                         : "+a"(rax) : "D"(pid), "S"((i64)SIGUSR1) : "rcx", "r11", "r12", "memory");
        finish(98);
    }
    if (mode == 4) {
        u64 ss[3] = {0xfffffffffffff000UL, 0, 0x2000};
        i64 r = sys(131, (i64)ss, 0, 0);
        if (r == -22) finish(22);
        require(r == 0 && install((u64)handler, 0x08000000UL) == 0);
        sys(62, sys(39, 0, 0, 0), SIGUSR1, 0);
        finish(98);
    }
    if (mode == 5) {
        u64 args[11] = {0};
        args[4] = SIGCHLD; args[5] = 0xffffffffffff0000UL; args[6] = 0x20000;
        i64 r = sys(435, (i64)args, 88, 0);
        if (r == 0) finish(98);
        finish(r == -22 ? 22 : 98);
    }
    if (mode == 6) {
        i64 r = install(0x8000000000000000UL, 0);
        if (r == -22) finish(22);
        require(r == 0);
        sys(62, sys(39, 0, 0, 0), SIGUSR1, 0);
        finish(98);
    }
    /* Positive control: a valid handler returns through rt_sigreturn. */
    require(install((u64)handler, 0) == 0);
    require(sys(62, sys(39, 0, 0, 0), SIGUSR1, 0) == 0);
    finish(0);
}
void wit_main(i64 *sp) {
    char **argv = (char **)(sp + 1);
    int mode = sp[0] > 1 ? argv[1][0] - '0' : 0;
    /* The witness is unprivileged, including the normal control. */
    require(sys(119, 1000, 1000, 1000) == 0 && sys(117, 1000, 1000, 1000) == 0);
    i64 c = sys6(56, SIGCHLD, 0, 0, 0, 0, 0);
    require(c >= 0);
    if (c == 0) child(mode);
    int status = -1;
    require(sys6(61, c, (i64)&status, 0, 0, 0, 0) == c);
    out("security: W"); dec(mode); out(" child status "); dec(status); out("\n");
    finish(0);
}
