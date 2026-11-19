/* tests/mpx6-logs.d/guest/endtrace.c PID — the rows' tracer of logd's end (G10, pax#472), root's, never in a
 * shipped image. It attaches to PID with ptrace(2), runs it from system call stop to system call stop, and
 * prints, in the order they return:
 *     ET open PATH = FD         open(2) and openat(2)
 *     ET write fd=FD = N        write(2), pwrite64(2), writev(2)
 *     ET sync NR fd=FD = N      fsync(2) 74, fdatasync(2) 75, sync(2) 162, syncfs(2) 306
 *     ET close fd=FD
 *     ET signal N               a signal on its way to PID (passed on as it came)
 *     ET end STATUS             PID is gone
 * The row sends PID a SIGTERM and reads the order from these lines. ptrace(2), wait(2) and syscall(2) are the
 * manual pages'; a system call's entry stop shows -ENOSYS in rax and its number in orig_rax.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

#define PT_PEEKDATA 2
#define PT_GETREGS 12
#define PT_ATTACH 16
#define PT_SYSCALL 24
#define PT_SETOPTIONS 0x4200
#define PT_O_TRACESYSGOOD 1

static long pt(long req, long pid, unsigned long addr, unsigned long data) {
    return syscall(SYS_ptrace, req, pid, addr, data);
}

/* The NUL-ended string at `addr` in the tracee, at most `max - 1` bytes of it. */
static void peek_string(long pid, unsigned long addr, char *to, size_t max) {
    size_t n = 0;
    to[0] = 0;
    while (n + 1 < max) {
        unsigned long word = 0;
        if (pt(PT_PEEKDATA, pid, addr + n, (unsigned long)&word) < 0) break;
        for (size_t k = 0; k < sizeof word && n + 1 < max; k++, n++) {
            to[n] = (char)(word >> (8 * k));
            if (!to[n]) return;
        }
    }
    to[n] = 0;
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: endtrace PID\n"); return 2; }
    long pid = atol(argv[1]);
    int st = 0, sig = 0, inside = 0;
    struct user_regs_struct r, at;
    char path[256];
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (pt(PT_ATTACH, pid, 0, 0) < 0) { printf("ET FAIL attach to %ld: %s\n", pid, strerror(errno)); return 1; }
    if (waitpid((pid_t)pid, &st, __WALL) < 0 || !WIFSTOPPED(st)) { printf("ET FAIL no stop after the attach\n"); return 1; }
    if (pt(PT_SETOPTIONS, pid, 0, PT_O_TRACESYSGOOD) < 0) { printf("ET FAIL options: %s\n", strerror(errno)); return 1; }
    printf("ET attached %ld\n", pid);
    memset(&at, 0, sizeof at);
    for (;;) {
        if (pt(PT_SYSCALL, pid, 0, (unsigned long)sig) < 0) { printf("ET FAIL resume: %s\n", strerror(errno)); return 1; }
        sig = 0;
        if (waitpid((pid_t)pid, &st, __WALL) < 0) { printf("ET FAIL wait: %s\n", strerror(errno)); return 1; }
        if (WIFEXITED(st) || WIFSIGNALED(st)) { printf("ET end 0x%x\n", st); return 0; }
        if (!WIFSTOPPED(st)) continue;
        int s = WSTOPSIG(st);
        if (s != (SIGTRAP | 0x80)) {
            if (s == SIGTRAP) continue;
            printf("ET signal %d\n", s);
            sig = s;
            continue;
        }
        if (pt(PT_GETREGS, pid, 0, (unsigned long)&r) < 0) { printf("ET FAIL registers: %s\n", strerror(errno)); return 1; }
        if ((long)r.rax == -ENOSYS && !inside) { at = r; inside = 1; continue; }   /* the entry stop */
        if (!inside) at = r;                                                       /* an exit with no entry seen */
        inside = 0;
        long nr = (long)at.orig_rax, ret = (long)r.rax;
        switch (nr) {
        case SYS_open: case SYS_openat:
            peek_string(pid, nr == SYS_open ? at.rdi : at.rsi, path, sizeof path);
            printf("ET open %s = %ld\n", path, ret);
            break;
        case SYS_write: case SYS_pwrite64: case SYS_writev:
            printf("ET write fd=%ld = %ld\n", (long)at.rdi, ret);
            break;
        case SYS_fsync: case SYS_fdatasync: case SYS_sync: case SYS_syncfs:
            printf("ET sync %ld fd=%ld = %ld\n", nr, nr == SYS_sync ? -1L : (long)at.rdi, ret);
            break;
        case SYS_close:
            printf("ET close fd=%ld\n", (long)at.rdi);
            break;
        default:
            break;
        }
    }
}
