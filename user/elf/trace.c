/* px102: Linux ABI measurement and PAX's red-first tracing witness.
 * No libc, headers or debugger implementation. Sources: ptrace(2),
 * wait(2), proc_pid_mem(5), proc_pid_status(5), x86-64 psABI A.2.1;
 * register layout/offsets already measured by notes/px102/gdb/.
 *
 * Usage: trace /absolute/path/to/tracee [core|syscall|exec|errors|stops|regs|step|notify|notify-syscall|exitkill|detach-exit|fork-event|vfork-event|vfork-order|clone-event|attach|seize|replace-signal|seize-fork|fault-handler|untraced-db|fault-segv|fault-ill|fault-fpe|fault-pass|group-exit|group-exit-event|exec-thread|tracer-thread|traceme-thread|blocked-read|blocked-sleep|blocked-futex|blocked-restart|blocked-eintr|memory|perm]
 * Each invocation owns exactly one child. The tracee is ET_EXEC at fixed
 * text/data addresses, checked by tools/mktrace. Only pids and descriptors
 * are normalized: report equality to the child's pid and an open's success.
 * Notification/control modes compare valid si_uid with getuid(); an
 * SI_KERNEL control stop instead requires its unused uid word to be zero.
 * Registers, status words, siginfo codes, memory and errors are not masked.
 * A failed prerequisite prints FAIL and kills/reaps only our own child.
 * Run inside a disposable pid namespace/container, or PAX, with a deadline.
 */
typedef unsigned long u64;
typedef long i64;
struct regs {
    u64 r15, r14, r13, r12, rbp, rbx, r11, r10, r9, r8;
    u64 rax, rcx, rdx, rsi, rdi, orig_rax, rip, cs, flags, rsp, ss;
    u64 fs_base, gs_base, ds, es, fs, gs;
};
struct iovec { void *base; u64 len; };
struct siginfo { int signo, error, code, pad; u64 fields[14]; };
_Static_assert(sizeof(struct regs) == 216, "register layout");
_Static_assert(sizeof(struct siginfo) == 128, "siginfo layout");
#define TEXT 0x401000UL
#define BREAK (TEXT + 1)
#define SYSCALL (TEXT + 7)
#define STORE (TEXT + 9)
#define AFTER_STORE (TEXT + 16)
#define DATA 0x402000UL
#define DR(n) (848 + 8 * (n))
#define WALL 0x40000000
#define TRACEME 0
#define PEEKTEXT 1
#define PEEKDATA 2
#define PEEKUSER 3
#define POKETEXT 4
#define POKEDATA 5
#define POKEUSER 6
#define CONT 7
#define KILL 8
#define STEP 9
#define GETREGS 12
#define SETREGS 13
#define GETFPREGS 14
#define ATTACH 16
#define SETOPTIONS 0x4200
#define GETEVENTMSG 0x4201
#define GETSIGINFO 0x4202
#define GETREGSET 0x4204

static i64 child;
static volatile int notify_code, notify_status;
static volatile unsigned notify_pid, notify_uid;
extern void trace_restorer(void);
static void child_notice(int signo, struct siginfo *si, void *context) {
    (void)signo; (void)context;
    notify_code = si->code;
    notify_status = (int)si->fields[1];
    notify_pid = (unsigned)si->fields[0];
    notify_uid = (unsigned)(si->fields[0] >> 32);
}
__asm__(".global trace_restorer\ntrace_restorer:\nmov $15,%rax\nsyscall\nud2\n");
static struct regs r;
static i64 call(i64 nr, i64 a, i64 b, i64 c, i64 d, i64 e) {
    register i64 r10 __asm__("r10") = d;
    register i64 r8 __asm__("r8") = e;
    i64 ret;
    __asm__ volatile("syscall" : "=a"(ret)
        : "a"(nr), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8)
        : "rcx", "r11", "memory");
    return ret;
}
static void text(const char *s) {
    u64 n = 0;
    while (s[n]) n++;
    while (n) {
        i64 k = call(1, 1, (i64)s, n, 0, 0);
        if (k == -4) continue;
        if (k <= 0) { call(231, 112, 0, 0, 0, 0); for (;;) {} }
        s += k; n -= k;
    }
}
static void number(u64 v, unsigned base) {
    char b[32]; unsigned n = 0;
    do { b[n++] = "0123456789abcdef"[v % base]; v /= base; } while (v);
    while (n) { char c[2] = { b[--n], 0 }; text(c); }
}
static void dec(const char *name, i64 v) {
    text(name); text("=");
    if (v < 0) { text("-"); number(0UL - (u64)v, 10); }
    else number(v, 10);
    text("\n");
}
static void hex(const char *name, u64 v) {
    text(name); text("=0x"); number(v, 16); text("\n");
}
static int equal(const char *a, const char *b) {
    while (*a && *a == *b) { a++; b++; }
    return *a == *b;
}
static void zero(void *p, u64 n) {
    unsigned char *b = p;
    while (n--) *b++ = 0;
}
static __attribute__((noreturn)) void done(int code) {
    call(231, code, 0, 0, 0, 0); for (;;) {}
}
static i64 ptrace(i64 req, u64 addr, u64 data) {
    return call(101, req, child, addr, data, 0);
}
static __attribute__((noreturn)) void fail(const char *name) {
    text("FAIL "); text(name); text("\n");
    if (child > 0) {
        /* Clear TRACEEXIT first, so cleanup cannot leave an event-stop. */
        ptrace(SETOPTIONS, 0, 0);
        call(62, child, 9, 0, 0, 0);
        int s;
        while (call(61, child, (i64)&s, WALL, 0, 0) == -4) {}
    }
    done(1);
}
static void ok(const char *name, i64 ret) {
    dec(name, ret);
    if (ret != 0) fail(name);
}
static int wait_child(const char *name) {
    int s = 0;
    i64 ret;
    do { ret = call(61, child, (i64)&s, WALL, 0, 0); } while (ret == -4);
    if (ret != child) { dec("wait.error", ret); fail(name); }
    hex(name, (unsigned)s);
    if ((s & 255) != 127) child = 0;
    return s;
}
static void stopped(const char *name) {
    if ((wait_child(name) & 255) != 127) fail(name);
}
static void waitid_peek(void) {
    struct siginfo si;
    zero(&si, sizeof(si));
    ok("waitid.nowait", call(247, 1, child, (i64)&si, WALL | 6 | 0x1000000, 0));
    dec("waitid.signo", si.signo); dec("waitid.code", si.code);
    dec("waitid.pid", (unsigned)si.fields[0] == (u64)child);
    dec("waitid.status", (int)si.fields[1]);
}
static void getregs(void) {
    zero(&r, sizeof(r));
    ok("getregs", ptrace(GETREGS, 0, (u64)&r));
}
static void siginfo(void) {
    struct siginfo si;
    zero(&si, sizeof(si));
    ok("getsiginfo", ptrace(GETSIGINFO, 0, (u64)&si));
    dec("siginfo.signo", si.signo);
    dec("siginfo.errno", si.error);
    dec("siginfo.code", si.code);
    hex("siginfo.addr", si.fields[0]);
}
/* Raw ptrace PEEK stores to data; unlike libc, its return is not the word. */
static u64 peek(const char *name, i64 req, u64 addr) {
    u64 value = 0;
    ok("peek.return", ptrace(req, addr, (u64)&value));
    hex(name, value);
    return value;
}
static void resume(i64 req, const char *name) {
    ok("resume", ptrace(req, 0, 0));
    stopped(name);
}
static void path(char *dst, i64 pid, int task, const char *leaf) {
    char num[24]; unsigned n = 0, k = 0;
    const char *s = "/proc/";
    while (*s) dst[k++] = *s++;
    do { num[n++] = '0' + pid % 10; pid /= 10; } while (pid);
    unsigned digits = n;
    while (n) dst[k++] = num[--n];
    if (task) {
        s = "/task/"; while (*s) dst[k++] = *s++;
        n = digits; while (n) dst[k++] = num[--n];
    }
    s = leaf; while (*s) dst[k++] = *s++;
    dst[k] = 0;
}
static i64 trace_status(void) {
    char name[80], buf[4096]; path(name, child, 0, "/status");
    i64 fd = call(2, (i64)name, 0, 0, 0, 0);
    dec("status.open", fd < 0 ? fd : 0);
    if (fd < 0) fail("status.open");
    u64 used = 0;
    while (used < sizeof(buf) - 1) {
        i64 n = call(0, fd, (i64)(buf + used), sizeof(buf) - 1 - used, 0, 0);
        if (n == -4) continue;
        if (n < 0) fail("status.read");
        if (!n) break;
        used += n;
    }
    buf[used] = 0;
    ok("status.close", call(3, fd, 0, 0, 0, 0));
    const char *key = "TracerPid:";
    i64 tracer = -1;
    for (u64 i = 0; i < used; i++) {
        if (i && buf[i - 1] != '\n') continue;
        u64 j = 0;
        while (key[j] && i + j < used && key[j] == buf[i + j]) j++;
        if (key[j]) continue;
        i += j;
        while (i < used && (buf[i] == ' ' || buf[i] == '\t')) i++;
        tracer = 0;
        while (i < used && buf[i] >= '0' && buf[i] <= '9') tracer = tracer * 10 + buf[i++] - '0';
        break;
    }
    dec("status.tracer-is-parent", tracer == call(39, 0, 0, 0, 0, 0));
    return tracer;
}
static void memory(void) {
    u64 value = peek("data.initial", PEEKDATA, DATA);
    ok("pokedata", ptrace(POKEDATA, DATA, ~0UL));
    peek("data.minus-one", PEEKDATA, DATA);
    ok("pokedata.restore", ptrace(POKEDATA, DATA, value));
    for (int task = 0; task < 2; task++) {
        char name[80]; path(name, child, task, "/mem");
        i64 fd = call(2, (i64)name, 2, 0, 0, 0);
        dec(task ? "task.mem.open" : "pid.mem.open", fd < 0 ? fd : 0);
        if (fd < 0) fail("mem.open");
        u64 out = 0;
        i64 got = call(17, fd, (i64)&out, 8, DATA, 0);
        dec("mem.pread", got); hex("mem.data", out);
        if (got != 8) fail("mem.pread");
        unsigned char cc = 0xcc, nop = 0x90;
        dec("mem.pwrite.text", call(18, fd, (i64)&cc, 1, BREAK, 0));
        peek("mem.text.patched", PEEKTEXT, BREAK);
        dec("mem.pwrite.restore", call(18, fd, (i64)&nop, 1, BREAK, 0));
        dec("mem.unmapped.read", call(17, fd, (i64)&out, 8, 0, 0));
        dec("mem.unmapped.write", call(18, fd, (i64)&out, 8, 0, 0));
        ok("mem.close", call(3, fd, 0, 0, 0, 0));
    }
}
static void registers(void) {
    getregs();
    hex("exec.rip", r.rip); hex("regs.cs", r.cs); hex("regs.ss", r.ss);
    peek("user.cs", PEEKUSER, 17 * 8);
    peek("user.ss", PEEKUSER, 20 * 8);
    peek("user.dr6.initial", PEEKUSER, DR(6));
    peek("user.dr7.initial", PEEKUSER, DR(7));
    struct regs other;
    struct iovec io = { &other, sizeof(other) };
    zero(&other, sizeof(other));
    ok("getregset.prstatus", ptrace(GETREGSET, 1, (u64)&io));
    dec("getregset.length", io.len);
    hex("regset.cs", other.cs); hex("regset.ss", other.ss);
    int same = 1;
    for (u64 i = 0; i < sizeof(r); i++)
        if (((unsigned char *)&r)[i] != ((unsigned char *)&other)[i]) same = 0;
    dec("regset.equals.regs", same);
    unsigned char fp[512]; zero(fp, sizeof(fp));
    ok("getfpregs", ptrace(GETFPREGS, 0, (u64)fp));
    hex("fp.fcw", fp[0] | ((u64)fp[1] << 8));
    hex("fp.mxcsr", fp[24] | ((u64)fp[25] << 8) | ((u64)fp[26] << 16) | ((u64)fp[27] << 24));
    io.base = fp; io.len = sizeof(fp);
    ok("getregset.prfpreg", ptrace(GETREGSET, 2, (u64)&io));
    dec("getregset.fp.length", io.len);
}
static void exit_tracee(void) {
    ok("continue.exit", ptrace(CONT, 0, 0));
    int status = wait_child("exit.status");
    if (child) fail("exit.still-stopped");
    if (status != (37 << 8)) fail("exit.code");
    dec("wait.echild", call(61, -1, (i64)&status, WALL | 1, 0, 0));
}
static void steps(void) {
    resume(CONT, "int3.status");
    getregs(); r.rdi = 0x55667788; r.orig_rax = ~0UL;
    ok("setregs", ptrace(SETREGS, 0, (u64)&r));
    getregs(); hex("setregs.rdi", r.rdi); hex("setregs.cs", r.cs); hex("setregs.ss", r.ss);
    resume(STEP, "step.nop.status"); siginfo(); getregs(); hex("step.nop.rip", r.rip);
    peek("step.dr6", PEEKUSER, DR(6));
    resume(STEP, "step.mov.status"); siginfo(); getregs(); hex("step.mov.rip", r.rip);
    resume(STEP, "step.syscall.status"); siginfo(); getregs();
    hex("step.syscall.rip", r.rip); dec("step.syscall.pid", r.rax == (u64)child);
    peek("step.syscall.dr6", PEEKUSER, DR(6));
    resume(CONT, "int3.second.status");
    exit_tracee();
}
static void notice(const char *name) {
    text(name); text(" code="); number((unsigned)notify_code, 10);
    text(" status="); number((unsigned)notify_status, 10);
    text(" pid="); number(notify_pid == (unsigned)child, 10);
    text(" uid="); number(notify_uid == (unsigned)call(102, 0, 0, 0, 0, 0), 10);
    text("\n");
}
static void resume_notice(const char *name) {
    ok("resume", ptrace(CONT, 0, 0));
    waitid_peek();
    stopped(name);
}
static void notifications(void) {
    notice("notify.initial");
    ok("notify.options", ptrace(SETOPTIONS, 0, 0x50));
    resume_notice("notify.exec.status"); notice("notify.exec");
    resume(CONT, "notify.int3.status"); notice("notify.int3");
    resume(CONT, "notify.second.status");
    resume_notice("notify.exit-event.status"); notice("notify.exit-event");
    u64 message = 0;
    ok("notify.eventmsg", ptrace(GETEVENTMSG, 0, (u64)&message));
    hex("notify.exit-message", message);
    exit_tracee();
    /* wait_child clears child after the exit; retain the raw si_pid only
       as a nonzero check here, with exit status and uid unnormalized. */
    dec("notify.final.code", notify_code);
    dec("notify.final.status", notify_status);
    dec("notify.final.pid-present", notify_pid != 0);
}
static void stops(void) {
    resume(CONT, "int3.status"); siginfo();
    resume(CONT, "int3.second.status"); siginfo();
    exit_tracee();
}
static void core(void) {
    trace_status();
    registers();
    memory();
    resume(CONT, "int3.status"); siginfo(); getregs(); hex("int3.rip", r.rip);
    u64 instruction = peek("break.original", PEEKTEXT, BREAK);
    ok("poketext.break", ptrace(POKETEXT, BREAK, (instruction & ~255UL) | 0xcc));
    resume(CONT, "break.status"); siginfo(); getregs(); hex("break.rip", r.rip);
    ok("poketext.restore", ptrace(POKETEXT, BREAK, instruction));
    r.rip = BREAK; r.rdi = 0x55667788; r.orig_rax = ~0UL;
    ok("setregs", ptrace(SETREGS, 0, (u64)&r));
    getregs(); hex("setregs.rdi", r.rdi); hex("setregs.cs", r.cs); hex("setregs.ss", r.ss);
    resume(STEP, "step.nop.status"); siginfo(); getregs(); hex("step.nop.rip", r.rip);
    peek("step.dr6", PEEKUSER, DR(6));
    resume(STEP, "step.mov.status"); siginfo(); getregs(); hex("step.mov.rip", r.rip);
    resume(STEP, "step.syscall.status"); siginfo(); getregs();
    hex("step.syscall.rip", r.rip); dec("step.syscall.pid", r.rax == (u64)child);
    peek("step.syscall.dr6", PEEKUSER, DR(6));
    ok("watch.dr0", ptrace(POKEUSER, DR(0), DATA));
    ok("watch.dr7", ptrace(POKEUSER, DR(7), 0x90101)); /* 8-byte write */
    ok("watch.clear.dr6", ptrace(POKEUSER, DR(6), 0));
    resume(CONT, "watch.status"); siginfo(); getregs(); hex("watch.rip", r.rip);
    peek("watch.dr6", PEEKUSER, DR(6)); peek("watch.dr7.read", PEEKUSER, DR(7));
    peek("watch.value", PEEKDATA, DATA);
    ok("watch.disable", ptrace(POKEUSER, DR(7), 0));
    resume(CONT, "int3.second.status"); siginfo();
    exit_tracee();
}
static void syscall_rows(int reports) {
    getregs(); r.rip = SYSCALL; r.rax = 39;
    ok("syscall.setregs", ptrace(SETREGS, 0, (u64)&r));
    ok("syscall.options", ptrace(SETOPTIONS, 0, 1));
    resume(24, "syscall.entry.status");
    if (reports) notice("notify.syscall-entry");
    getregs();
    hex("syscall.entry.rip", r.rip); dec("syscall.entry.rax", r.rax);
    dec("syscall.entry.orig_rax", r.orig_rax);
    resume(24, "syscall.exit.status");
    if (reports) notice("notify.syscall-exit");
    getregs();
    hex("syscall.exit.rip", r.rip); dec("syscall.exit.pid", r.rax == (u64)child);
    dec("syscall.exit.orig_rax", r.orig_rax);
    ok("exit.options", ptrace(SETOPTIONS, 0, 0x40));
    resume(CONT, "syscall.int3.status");
    resume(CONT, "event.exit.status");
    u64 message = 0;
    ok("geteventmsg.exit", ptrace(GETEVENTMSG, 0, (u64)&message));
    hex("event.exit.message", message);
    exit_tracee();
}
static void errors(void) {
    u64 value = 0;
    dec("error.peek.unmapped", ptrace(PEEKDATA, 0, (u64)&value));
    dec("error.poke.unmapped", ptrace(POKEDATA, 0, 1));
    dec("error.peek.bad-buffer", ptrace(PEEKDATA, DATA, 0));
    dec("error.getregs.bad-buffer", ptrace(GETREGS, 0, 0));
    dec("error.setregs.bad-buffer", ptrace(SETREGS, 0, 0));
    dec("error.getsiginfo.bad-buffer", ptrace(GETSIGINFO, 0, 0));
    dec("error.peekuser.unaligned", ptrace(PEEKUSER, 1, (u64)&value));
    dec("peekuser.padding", ptrace(PEEKUSER, 912, (u64)&value));
    hex("peekuser.padding.value", value);
    dec("error.peekuser.outside", ptrace(PEEKUSER, 4096, (u64)&value));
    struct iovec io = { &r, 7 };
    dec("error.regset.unaligned-length", ptrace(GETREGSET, 1, (u64)&io));
    io.len = 8;
    dec("regset.short", ptrace(GETREGSET, 1, (u64)&io));
    dec("regset.short.length", io.len);
    dec("error.regset.bad-iovec", ptrace(GETREGSET, 1, 0));
    dec("error.regset.unknown", ptrace(GETREGSET, 0x7fffffff, (u64)&io));
    dec("error.poke.dr4", ptrace(POKEUSER, DR(4), 0));
    dec("error.poke.dr5", ptrace(POKEUSER, DR(5), 0));
    dec("error.options.unknown", ptrace(SETOPTIONS, 0, 0x80000000));
    dec("error.request.unknown", ptrace(0x7fffffff, 0, 0));
    dec("error.attach.self", call(101, ATTACH, call(39, 0, 0, 0, 0, 0), 0, 0, 0));
    dec("error.attach.traced", ptrace(ATTACH, 0, 0));
    ok("dr0.valid", ptrace(POKEUSER, DR(0), DATA));
    dec("error.dr7.execute.length", ptrace(POKEUSER, DR(7), 0x40001));
    dec("error.dr7.io", ptrace(POKEUSER, DR(7), 0x20001));
    ok("dr7.disabled", ptrace(POKEUSER, DR(7), 0));
    ok("dr0.unaligned", ptrace(POKEUSER, DR(0), DATA + 1));
    dec("error.dr7.unaligned", ptrace(POKEUSER, DR(7), 0x90001));
    ok("dr7.disabled.again", ptrace(POKEUSER, DR(7), 0));
    ok("ptrace.kill", ptrace(KILL, 0, 0));
    if (wait_child("kill.status") != 9) fail("kill.status");
}
static unsigned char thread_stack[8192] __attribute__((aligned(16)));
static volatile unsigned thread_ctid;
extern i64 trace_spawn_thread(void *stack, volatile unsigned *ctid);
extern i64 trace_vfork_exec(const char *self);
__asm__(".global trace_spawn_thread\ntrace_spawn_thread:\n"
        "mov %rsi,%r10\nmov %rdi,%rsi\nmov $0x1250f00,%edi\n"
        "xor %edx,%edx\nxor %r8d,%r8d\nmov $56,%eax\nsyscall\n"
        "test %rax,%rax\njnz 1f\nmov $19,%edi\nmov $60,%eax\nsyscall\nud2\n1: ret\n"
        ".global trace_vfork_exec\ntrace_vfork_exec:\npush %r12\nmov %rdi,%r12\n"
        "mov $58,%eax\nsyscall\ntest %rax,%rax\njnz 2f\n"
        "sub $24,%rsp\nmov %r12,(%rsp)\nlea 3f(%rip),%rax\nmov %rax,8(%rsp)\n"
        "movq $0,16(%rsp)\nmov %rsp,%rsi\nmov %r12,%rdi\nxor %edx,%edx\n"
        "mov $59,%eax\nsyscall\nmov $111,%edi\nmov $60,%eax\nsyscall\nud2\n"
        "2: pop %r12\nret\n3: .asciz \"orphan-target\"\n");
static __attribute__((noreturn)) void role_fork(void) {
    i64 pid = call(57, 0, 0, 0, 0, 0);
    if (pid == 0) done(19);
    if (pid < 0) done(111);
    int status = 0; i64 got;
    do { got = call(61, pid, (i64)&status, 0, 0, 0); } while (got == -4);
    done(got == pid && status == (19 << 8) ? 37 : 112);
}
static __attribute__((noreturn)) void role_vfork(const char *self) {
    i64 pid = trace_vfork_exec(self);
    if (pid <= 0) done(111);
    int status = 0; i64 got;
    do { got = call(61, pid, (i64)&status, 0, 0, 0); } while (got == -4);
    done(got == pid && status == (23 << 8) ? 37 : 112);
}
static __attribute__((noreturn)) void role_clone(void) {
    thread_ctid = 1;
    if (trace_spawn_thread(thread_stack + sizeof(thread_stack), &thread_ctid) <= 0) done(111);
    for (;;) {
        unsigned value = thread_ctid;
        if (!value) break;
        call(202, (i64)&thread_ctid, 0, value, 0, 0); /* clear-child-tid uses shared FUTEX_WAKE */
    }
    /* Keep exit_group from racing the tracer's collection of the thread's
       individual status: Linux otherwise may report the group's 37. */
    __asm__ volatile("int3");
    done(37);
}
static int event_mode(const char *mode) {
    return equal(mode, "fork-event") || equal(mode, "vfork-event") ||
           equal(mode, "vfork-order") || equal(mode, "clone-event");
}
static int wait_other(i64 pid, const char *name) {
    i64 parent = child; child = pid;
    int status = wait_child(name);
    child = parent;
    return status;
}
static void cont_other(i64 pid) { ok("resume.other", call(101, CONT, pid, 0, 0, 0)); }
static void no_parent_event(void) {
    int status = 0;
    dec("event.parent.nohang", call(61, child, (i64)&status, WALL | 1, 0, 0));
}
static void parent_child_signal(i64 target) {
    if (wait_child("event.parent.sigchld") != 0x117f) fail("event.parent.sigchld");
    struct siginfo si; zero(&si, sizeof(si));
    ok("event.parent.getsiginfo", ptrace(GETSIGINFO, 0, (u64)&si));
    dec("event.sigchld.code", si.code);
    dec("event.sigchld.status", (int)si.fields[1]);
    dec("event.sigchld.pid", (unsigned)si.fields[0] == (u64)target);
    ok("event.parent.suppress", ptrace(CONT, 0, 0));
}
static void child_events(const char *mode) {
    int vf = equal(mode, "vfork-event") || equal(mode, "vfork-order");
    int clone = equal(mode, "clone-event");
    int child_first = equal(mode, "vfork-order");
    if (!equal(mode, "seize-fork")) ok("event.options", ptrace(SETOPTIONS, 0, vf ? 0x34 : clone ? 8 : 2));
    resume(CONT, "event.parent.status");
    u64 target = 0;
    ok("event.child.message", ptrace(GETEVENTMSG, 0, (u64)&target));
    dec("event.child.valid", target != 0 && target != (u64)child);
    if (!target || target == (u64)child) fail("event.child.pid");
    if (wait_other(target, "event.child.initial") != (equal(mode, "seize-fork") ? 0x80057f : 0x137f)) fail("event.child.initial");
    if (vf) {
        if (!child_first) { ok("event.parent.resume", ptrace(CONT, 0, 0)); no_parent_event(); }
        cont_other(target);
        if (wait_other(target, "event.child.exec") != 0x4057f) fail("event.child.exec");
        if (child_first) { no_parent_event(); ok("event.parent.resume", ptrace(CONT, 0, 0)); }
        if (wait_child("event.vfork.done") != 0x5057f) fail("event.vfork.done");
        u64 message = 0;
        ok("event.vfork.message", ptrace(GETEVENTMSG, 0, (u64)&message));
        dec("event.vfork.child", message == target);
        ok("event.parent.wait-child", ptrace(CONT, 0, 0));
        cont_other(target);
        if (wait_other(target, "event.child.exit") != (23 << 8)) fail("event.child.exit");
        parent_child_signal(target);
    } else if (clone) {
        ok("event.parent.resume", ptrace(CONT, 0, 0));
        cont_other(target);
        if (wait_other(target, "event.child.exit") != (19 << 8)) fail("event.child.exit");
        if (wait_child("event.parent.after-thread") != 0x57f) fail("event.parent.after-thread");
        ok("event.parent.after-thread.resume", ptrace(CONT, 0, 0));
    } else {
        cont_other(target);
        if (wait_other(target, "event.child.exit") != (19 << 8)) fail("event.child.exit");
        ok("event.parent.resume", ptrace(CONT, 0, 0));
        parent_child_signal(target);
    }
    if (wait_child("event.parent.exit") != (37 << 8)) fail("event.parent.exit");
    int status;
    dec("event.echild", call(61, -1, (i64)&status, WALL | 1, 0, 0));
}
static volatile u64 control_flag, control_seen;
static int control_ackfd;
extern void trace_signal_recover(void), control_single_step(void), control_tf_after(void);
__asm__(".global trace_signal_recover\ntrace_signal_recover:\nmov $37,%edi\nmov $60,%eax\nsyscall\nud2\n"
        ".global control_single_step,control_tf_after\ncontrol_single_step:\npushfq\norq $0x100,(%rsp)\npopfq\nnop\ncontrol_tf_after:\nret\n");
struct control_packet { i64 sig, code; u64 from, addr; };
static void control_handler(int sig, struct siginfo *si, void *ctx) {
    control_seen |= sig == 10 ? 1 : sig == 12 ? 2 : sig == 11 ? 4 : 8;
    u64 *gregs = (u64 *)((unsigned char *)ctx + 40);
    if (sig == 11) gregs[16] = (u64)trace_signal_recover;
    if (sig == 5) gregs[17] &= ~0x100UL;
    struct control_packet packet = { sig, si->code, si->fields[0], si->fields[0] };
    call(1, control_ackfd, (i64)&packet, sizeof(packet), 0, 0);
}
static void control_action(int sig) {
    struct { u64 handler, flags, restorer, mask; } action = {
        (u64)control_handler, 0x14000004, (u64)trace_restorer, 0
    };
    if (call(13, sig, (i64)&action, 0, 8, 0)) done(111);
}
static void control_ack(int fd, int fault, int step) {
    struct control_packet packet; u64 have = 0;
    while (have < sizeof(packet)) {
        i64 n = call(0, fd, (i64)((unsigned char *)&packet + have), sizeof(packet) - have, 0, 0);
        if (n == -4) continue;
        if (n <= 0) fail("control.ack.read");
        have += n;
    }
    dec("control.ack.signal", packet.sig); dec("control.ack.code", packet.code);
    if (step) dec("control.ack.next-rip", packet.addr == (u64)control_tf_after);
    else if (fault) hex("control.ack.addr", packet.addr);
    else {
        dec("control.ack.sender-parent", (unsigned)packet.from == (unsigned)call(39, 0, 0, 0, 0, 0));
        dec("control.ack.uid", (unsigned)(packet.from >> 32) == (unsigned)call(102, 0, 0, 0, 0, 0));
    }
}
static void control_info(void) {
    struct siginfo si; zero(&si, sizeof(si));
    ok("control.getsiginfo", ptrace(GETSIGINFO, 0, (u64)&si));
    dec("control.signal", si.signo); dec("control.code", si.code);
    dec("control.sender-parent", (unsigned)si.fields[0] == (unsigned)call(39, 0, 0, 0, 0, 0));
    dec("control.sender-target", (unsigned)si.fields[0] == (u64)child);
    dec("control.sender-zero", (unsigned)si.fields[0] == 0);
    /* ATTACH's SI_KERNEL stop has a zeroed union; other control stops
       in these same-uid cases identify the caller/target's real uid. */
    dec("control.sender-uid", (unsigned)(si.fields[0] >> 32) == (si.code == 128 ? 0U : (unsigned)call(102, 0, 0, 0, 0, 0)));
}
static int controlled_mode(const char *mode) {
    return equal(mode, "attach") || equal(mode, "seize") || equal(mode, "replace-signal") ||
           equal(mode, "fault-handler") || equal(mode, "untraced-db") || equal(mode, "seize-fork");
}
static void controlled(const char *mode) {
    int fds[2]; ok("control.pipe", call(293, (i64)fds, 0, 0, 0, 0));
    control_ackfd = fds[1]; control_flag = control_seen = 0;
    child = call(57, 0, 0, 0, 0, 0);
    if (child < 0) fail("control.fork");
    if (child == 0) {
        call(3, fds[0], 0, 0, 0, 0);
        control_action(10); control_action(12); control_action(11); control_action(5);
        char ready = 'R';
        if (call(1, fds[1], (i64)&ready, 1, 0, 0) != 1) done(111);
        if (equal(mode, "untraced-db")) { control_single_step(); done(37); }
        if (equal(mode, "fault-handler")) {
            if (call(101, TRACEME, 0, 0, 0, 0)) done(111);
            call(62, call(39, 0, 0, 0, 0, 0), 19, 0, 0, 0);
            __asm__ volatile("xor %%eax,%%eax; mov (%%rax),%%rax" ::: "rax", "memory");
            done(111);
        }
        while (control_flag != 37) {
            if (control_flag == 1) {
                control_flag = 2;
                if (equal(mode, "seize-fork")) role_fork();
                i64 pid = call(39, 0, 0, 0, 0, 0);
                call(234, pid, pid, 10, 0, 0);
            }
            __asm__ volatile("pause" ::: "memory");
        }
        u64 expected = equal(mode, "attach") ? 1 : equal(mode, "replace-signal") ? 2 : 0;
        done(control_seen == expected ? 37 : 113);
    }
    call(3, fds[1], 0, 0, 0, 0);
    char ready = 0;
    if (call(0, fds[0], (i64)&ready, 1, 0, 0) != 1 || ready != 'R') fail("control.ready");
    if (equal(mode, "untraced-db")) {
        control_ack(fds[0], 0, 1);
    } else if (equal(mode, "fault-handler")) {
        stopped("control.initial.status");
        resume(CONT, "control.fault.status"); siginfo();
        ok("control.pass-fault", ptrace(CONT, 0, 11));
        control_ack(fds[0], 1, 0);
    } else {
        int seized = equal(mode, "seize") || equal(mode, "seize-fork");
        if (seized) {
            dec("control.seize.bad-addr", ptrace(0x4206, 1, 0));
            dec("control.seize.bad-options", ptrace(0x4206, 0, 0x80000000));
            ok("control.seize", ptrace(0x4206, 0, equal(mode, "seize-fork") ? 2 : 0));
            int status = 0;
            dec("control.seize.nohang", call(61, child, (i64)&status, WALL | 1, 0, 0));
            dec("control.running.getregs", ptrace(GETREGS, 0, (u64)&r));
            ok("control.interrupt", ptrace(0x4207, 0, 0));
        } else ok("control.attach", ptrace(ATTACH, 0, 0));
        waitid_peek(); stopped("control.stop.status"); control_info();
        if (!seized) dec("control.interrupt-unseized", ptrace(0x4207, 0, 0));
        dec("control.attach-again", ptrace(ATTACH, 0, 0));
        if (equal(mode, "seize-fork")) {
            ok("control.start-fork", ptrace(POKEDATA, (u64)&control_flag, 1));
            child_events(mode);
            call(3, fds[0], 0, 0, 0, 0);
            return;
        }
        if (equal(mode, "attach")) {
            ok("control.inject-usr1", ptrace(CONT, 0, 10)); control_ack(fds[0], 0, 0);
            ok("control.send-usr2", call(62, child, 12, 0, 0, 0));
            stopped("control.usr2.status"); control_info();
            ok("control.finish", ptrace(POKEDATA, (u64)&control_flag, 37));
        } else if (equal(mode, "replace-signal")) {
            ok("control.self-signal", ptrace(POKEDATA, (u64)&control_flag, 1));
            resume(CONT, "control.self-signal.status"); control_info();
            ok("control.finish", ptrace(POKEDATA, (u64)&control_flag, 37));
        }
        dec("control.detach.bad-signal", ptrace(17, 0, 65));
        ok("control.detach", ptrace(17, 0, equal(mode, "replace-signal") ? 12 : 0));
        if (equal(mode, "replace-signal")) control_ack(fds[0], 0, 0);
        if (equal(mode, "seize")) {
            dec("control.detached.getregs", ptrace(GETREGS, 0, (u64)&r));
            dec("control.tracer-zero", trace_status() == 0);
            char name[80]; path(name, child, 0, "/mem");
            i64 fd = call(2, (i64)name, 2, 0, 0, 0); if (fd < 0) fail("control.mem.open");
            u64 value = 37;
            dec("control.mem.finish", call(18, fd, (i64)&value, 8, (u64)&control_flag, 0));
            call(3, fd, 0, 0, 0, 0);
        }
    }
    if (wait_child("control.exit.status") != (37 << 8)) fail("control.exit.status");
    call(3, fds[0], 0, 0, 0, 0);
}
static int fault_mode(const char *mode) {
    return equal(mode, "fault-segv") || equal(mode, "fault-ill") || equal(mode, "fault-fpe") || equal(mode, "fault-pass");
}
static void fault_rows(const char *mode) {
    getregs(); r.rip = TEXT + (equal(mode, "fault-ill") ? 0x40 : equal(mode, "fault-fpe") ? 0x60 : 0x50);
    r.orig_rax = ~0UL;
    ok("fault.setregs", ptrace(SETREGS, 0, (u64)&r));
    resume(CONT, "fault.status"); siginfo();
    if (equal(mode, "fault-pass")) {
        ok("fault.inject-term", ptrace(CONT, 0, 15));
        if (wait_child("fault.passed.status") != 15) fail("fault.passed.status");
    } else {
        getregs(); hex("fault.rip", r.rip); r.rip = TEXT + 0x80;
        ok("fault.recover", ptrace(SETREGS, 0, (u64)&r));
        exit_tracee();
    }
}
/* px102 lifecycle witnesses (notes/px102/lifecycle.txt). A thread body
 * runs C on its own stack; its return is a thread exit(0). Threads print
 * only in turn (phase), so the transcript has one order on both kernels. */
extern i64 trace_spawn_body(void *stack, volatile unsigned *ctid, void (*body)(void));
__asm__(".global trace_spawn_body\ntrace_spawn_body:\n"
        "mov %rsi,%r10\nmov %rdx,%r9\nmov %rdi,%rsi\nmov $0x1250f00,%edi\n"
        "xor %edx,%edx\nxor %r8d,%r8d\nmov $56,%eax\nsyscall\n"
        "test %rax,%rax\njnz 1f\ncall *%r9\nxor %edi,%edi\nmov $60,%eax\nsyscall\nud2\n1: ret\n");
static unsigned char body_stack[16384] __attribute__((aligned(16)));
static volatile unsigned body_ctid, block_word, group_ready, phase;
static const char *self_path;
static i64 other_child;
static void yield(void) { call(24, 0, 0, 0, 0, 0); }
static __attribute__((noreturn)) void block_forever(void) {
    for (;;) call(202, (i64)&block_word, 0, 0, 0, 0); /* FUTEX_WAIT, shared key */
}
static void spawn(void (*body)(void)) {
    body_ctid = 1;
    if (trace_spawn_body(body_stack + sizeof(body_stack), &body_ctid, body) <= 0) done(111);
}
static void join(void) {
    for (;;) { unsigned v = body_ctid; if (!v) break; call(202, (i64)&body_ctid, 0, v, 0, 0); }
}
static void group_block(void) { group_ready = 1; block_forever(); }
static __attribute__((noreturn)) void role_group(void) {
    spawn(group_block);
    while (!group_ready) yield();
    done(37);
}
static void exec_body(void) {
    char *av[] = { (char *)self_path, "orphan-target", 0 }; char *ev[] = { 0 };
    call(59, (i64)self_path, (i64)av, (i64)ev, 0, 0);
    done(111);
}
static __attribute__((noreturn)) void role_exec_thread(void) {
    spawn(exec_body);
    block_forever();
}
static int lifecycle_mode(const char *mode) {
    return equal(mode, "group-exit") || equal(mode, "group-exit-event") || equal(mode, "exec-thread");
}
static i64 wait_any(const char *name, int *status) {
    i64 got;
    do { got = call(61, -1, (i64)status, WALL, 0, 0); } while (got == -4);
    if (got <= 0) { dec("wait.error", got); fail(name); }
    hex(name, (unsigned)*status);
    return got;
}
static void lifecycle(const char *mode) {
    int events = equal(mode, "group-exit-event"), xthread = equal(mode, "exec-thread");
    ok("life.options", ptrace(SETOPTIONS, 0, xthread ? 0x18 : events ? 0x48 : 8));
    resume(CONT, "life.parent.status");
    u64 tid = 0;
    ok("life.child.message", ptrace(GETEVENTMSG, 0, (u64)&tid));
    dec("life.child.valid", tid != 0 && tid != (u64)child);
    if (!tid || tid == (u64)child) fail("life.child.pid");
    if (wait_other(tid, "life.thread.initial") != 0x137f) fail("life.thread.initial");
    int s = 0;
    if (xthread) {
        ok("life.parent.resume", ptrace(CONT, 0, 0));
        cont_other(tid);
        i64 who = wait_any("exec.event.status", &s);
        dec("exec.event.pid-is-leader", who == child);
        dec("exec.event.pid-is-thread", who == (i64)tid);
        u64 former = 0;
        ok("exec.eventmsg", call(101, GETEVENTMSG, who, 0, (i64)&former, 0));
        dec("exec.former-is-thread", former == tid);
        dec("exec.former-is-leader", former == (u64)child);
        dec("exec.thread.getregs", call(101, GETREGS, tid, 0, (i64)&r, 0));
        ok("exec.resume", call(101, CONT, who, 0, 0, 0));
        who = wait_any("exec.exit.status", &s);
        dec("exec.exit.pid-is-leader", who == child);
    } else {
        cont_other(tid);
        ok("life.parent.resume", ptrace(CONT, 0, 0));
        if (events) {
            i64 who[2]; int st[2];
            for (int k = 0; k < 2; k++) {
                do { who[k] = call(61, -1, (i64)&st[k], WALL, 0, 0); } while (who[k] == -4);
                if (who[k] <= 0) { dec("wait.error", who[k]); fail("group.event.wait"); }
            }
            dec("group.event.distinct", who[0] != who[1]);
            const char *label[2] = { "group.event.leader", "group.event.thread" };
            i64 pid[2] = { child, (i64)tid };
            for (int j = 0; j < 2; j++) {
                int k = who[0] == pid[j] ? 0 : who[1] == pid[j] ? 1 : -1;
                text(label[j]); text(".seen="); number(k >= 0, 10); text("\n");
                if (k < 0) fail(label[j]);
                hex(label[j], (unsigned)st[k]);
                u64 message = 0;
                ok("group.event.message.get", call(101, GETEVENTMSG, pid[j], 0, (i64)&message, 0));
                hex("group.event.message", message);
            }
            cont_other(tid);
            ok("group.event.leader.resume", ptrace(CONT, 0, 0));
        }
        i64 first = wait_any("group.first.status", &s);
        dec("group.first.is-thread", first == (i64)tid);
        i64 second = wait_any("group.second.status", &s);
        dec("group.second.is-leader", second == child);
    }
    child = 0;
    dec("life.echild", call(61, -1, (i64)&s, WALL | 1, 0, 0));
}
static i64 tracer_pid_of(i64 pid) {
    char name[80], buf[4096]; path(name, pid, 0, "/status");
    i64 fd = call(2, (i64)name, 0, 0, 0, 0);
    if (fd < 0) return -1;
    i64 used = 0, n;
    while ((n = call(0, fd, (i64)(buf + used), sizeof(buf) - 1 - used, 0, 0)) > 0 || n == -4) if (n > 0) used += n;
    call(3, fd, 0, 0, 0, 0);
    buf[used] = 0;
    for (i64 i = 0; i < used; i++) {
        if (i && buf[i - 1] != '\n') continue;
        const char *key = "TracerPid:"; i64 j = 0;
        while (key[j] && buf[i + j] == key[j]) j++;
        if (key[j]) continue;
        i += j; while (buf[i] == ' ' || buf[i] == '\t') i++;
        i64 v = 0; while (buf[i] >= '0' && buf[i] <= '9') v = v * 10 + buf[i++] - '0';
        return v;
    }
    return -1;
}
/* A bounded WNOHANG poll: a stop that never arrives is a named FAIL. */
static i64 poll_wait(i64 pid, int *status) {
    i64 got = 0;
    for (u64 n = 0; n < 2000000 && (got = call(61, pid, (i64)status, WALL | 1, 0, 0)) == 0; n++) yield();
    return got;
}
static void seize_body(void) {
    struct regs mine;
    dec("tthread.seize", call(101, 0x4206, child, 0, 0, 0));
    dec("tthread.interrupt", call(101, 0x4207, child, 0, 0, 0));
    int s = 0;
    i64 got = poll_wait(child, &s);
    dec("tthread.wait.found", got == child);
    if (got != child) fail("T-tracer-thread-stop");
    hex("tthread.stop.status", (unsigned)s);
    dec("tthread.getregs", call(101, GETREGS, child, 0, (i64)&mine, 0));
    phase = 1;
    while (phase != 2) yield();
}
static void traceme_body(void) {
    struct regs mine;
    i64 c = call(57, 0, 0, 0, 0, 0);
    if (c == 0) {
        if (call(101, TRACEME, 0, 0, 0, 0)) done(111);
        call(62, call(39, 0, 0, 0, 0, 0), 19, 0, 0, 0);
        done(37);
    }
    if (c < 0) fail("mthread.fork");
    other_child = c;
    int s = 0;
    i64 got = poll_wait(c, &s);
    dec("mthread.wait.found", got == c);
    if (got != c) fail("T-traceme-thread-stop");
    hex("mthread.stop.status", (unsigned)s);
    dec("mthread.getregs", call(101, GETREGS, c, 0, (i64)&mine, 0));
    phase = 1;
    while (phase != 2) yield();
    ok("mthread.resume", call(101, CONT, c, 0, 0, 0));
    do { got = call(61, c, (i64)&s, WALL, 0, 0); } while (got == -4);
    dec("mthread.exit.found", got == c);
    hex("mthread.exit.status", (unsigned)s);
}
static int thread_tracer_mode(const char *mode) {
    return equal(mode, "tracer-thread") || equal(mode, "traceme-thread");
}
static void thread_tracers(const char *mode) {
    phase = 0;
    if (equal(mode, "traceme-thread")) {
        spawn(traceme_body);
        while (phase != 1) yield();
        dec("mthread.leader.getregs", call(101, GETREGS, other_child, 0, (i64)&r, 0));
        phase = 2;
        join();
        int s = 0;
        dec("mthread.echild", call(61, -1, (i64)&s, WALL | 1, 0, 0));
        return;
    }
    int fds[2];
    ok("tthread.pipe", call(293, (i64)fds, 0x800, 0, 0, 0)); /* O_NONBLOCK */
    child = call(57, 0, 0, 0, 0, 0);
    if (child < 0) fail("tthread.fork");
    if (child == 0) {
        call(3, fds[1], 0, 0, 0, 0);
        for (;;) {
            char b; i64 n = call(0, fds[0], (i64)&b, 1, 0, 0);
            if (n == 1) done(37);
            if (n == 0) done(111);
            yield();
        }
    }
    call(3, fds[0], 0, 0, 0, 0);
    spawn(seize_body);
    while (phase != 1) yield();
    dec("tthread.leader.getregs", ptrace(GETREGS, 0, (u64)&r));
    int s = 0;
    dec("tthread.leader.nohang", call(61, child, (i64)&s, WALL | 1, 0, 0));
    phase = 2;
    join();
    i64 tracer = -1;
    for (u64 n = 0; n < 200000 && (tracer = tracer_pid_of(child)) != 0; n++) yield();
    dec("tthread.detached", tracer == 0);
    ok("tthread.attach", ptrace(ATTACH, 0, 0));
    stopped("tthread.attach.status");
    getregs();
    char go = 'G';
    dec("tthread.release", call(1, fds[1], (i64)&go, 1, 0, 0));
    ok("tthread.detach", ptrace(17, 0, 0));
    if (wait_child("tthread.exit.status") != (37 << 8)) fail("tthread.exit.status");
    dec("tthread.echild", call(61, -1, (i64)&s, WALL | 1, 0, 0));
    call(3, fds[1], 0, 0, 0, 0);
}
/* px102 blocked-call witnesses (notes/px102/restart.txt): the target
 * blocks, the tracer attaches; the registers shown and how the call ends. */
static volatile u64 blocked_word;
static volatile int blocked_seen;
static void blocked_handler(int sig, struct siginfo *si, void *ctx) { (void)sig; (void)si; (void)ctx; blocked_seen = 1; }
static int blocked_mode(const char *mode) {
    return equal(mode, "blocked-read") || equal(mode, "blocked-sleep") || equal(mode, "blocked-futex") ||
           equal(mode, "blocked-restart") || equal(mode, "blocked-eintr");
}
static __attribute__((noreturn)) void blocked_target(const char *mode, int rfd, int ready) {
    if (equal(mode, "blocked-restart") || equal(mode, "blocked-eintr")) {
        struct { u64 handler, flags, restorer, mask; } action = {
            (u64)blocked_handler, equal(mode, "blocked-restart") ? 0x14000004 : 0x04000004, (u64)trace_restorer, 0
        };
        if (call(13, 10, (i64)&action, 0, 8, 0)) done(111);
    }
    char c = 'R';
    if (call(1, ready, (i64)&c, 1, 0, 0) != 1) done(111);
    if (equal(mode, "blocked-sleep")) {
        struct { i64 sec, nsec; } t = { 0, 600000000 };
        i64 rc = call(35, (i64)&t, 0, 0, 0, 0);
        done(rc == 0 ? 37 : rc == -4 ? 36 : 112);
    }
    if (equal(mode, "blocked-futex")) {
        i64 rc = call(202, (i64)&blocked_word, 0, 0, 0, 0);
        done(rc == -11 ? 37 : rc == -4 ? 36 : rc == 0 ? 35 : 112);
    }
    char b; i64 n = call(0, rfd, (i64)&b, 1, 0, 0);
    done(n == 1 ? (blocked_seen ? 37 : 38) : n == -4 ? (blocked_seen ? 36 : 35) : 112);
}
/* Let the target reach its blocking call: yield, then (Linux) wait for
 * /proc/<pid>/stat's state S. Nothing here is printed. */
static void settle(void) {
    for (int k = 0; k < 200; k++) yield();
    char name[80], buf[512]; path(name, child, 0, "/stat");
    for (int k = 0; k < 20000; k++) {
        i64 fd = call(2, (i64)name, 0, 0, 0, 0);
        if (fd < 0) return;
        i64 n = call(0, fd, (i64)buf, sizeof(buf) - 1, 0, 0);
        call(3, fd, 0, 0, 0, 0);
        if (n <= 0) return;
        buf[n] = 0;
        i64 i = n - 1; while (i > 0 && buf[i] != ')') i--;
        if (i + 2 < n && buf[i + 2] != 'R') return;
        yield();
    }
}
static void blocked_regs(const char *name) {
    getregs();
    text(name); text(".rax="); if ((i64)r.rax < 0) { text("-"); number(0UL - r.rax, 10); } else number(r.rax, 10); text("\n");
    text(name); text(".orig_rax="); if ((i64)r.orig_rax < 0) { text("-"); number(0UL - r.orig_rax, 10); } else number(r.orig_rax, 10); text("\n");
    u64 before = 0;
    ok("peek.return", ptrace(PEEKTEXT, r.rip - 2, (u64)&before));
    text(name); text(".after-syscall="); number((before & 0xffff) == 0x050f, 10); text("\n");
}
static void blocked(const char *mode) {
    int data[2], ready[2];
    ok("blocked.pipe", call(293, (i64)data, 0, 0, 0, 0));
    ok("blocked.ready-pipe", call(293, (i64)ready, 0, 0, 0, 0));
    child = call(57, 0, 0, 0, 0, 0);
    if (child < 0) fail("blocked.fork");
    if (child == 0) { call(3, data[1], 0, 0, 0, 0); call(3, ready[0], 0, 0, 0, 0); blocked_target(mode, data[0], ready[1]); }
    call(3, data[0], 0, 0, 0, 0); call(3, ready[1], 0, 0, 0, 0);
    char c = 0;
    if (call(0, ready[0], (i64)&c, 1, 0, 0) != 1 || c != 'R') fail("blocked.ready");
    settle();
    ok("blocked.attach", ptrace(ATTACH, 0, 0));
    stopped("blocked.attach.status");
    blocked_regs("blocked.attach");
    char go = 'G';
    if (equal(mode, "blocked-restart") || equal(mode, "blocked-eintr")) {
        ok("blocked.resume", ptrace(CONT, 0, 0));
        settle();
        ok("blocked.signal", call(62, child, 10, 0, 0, 0));
        stopped("blocked.signal.status");
        blocked_regs("blocked.signal");
        ok("blocked.deliver", ptrace(CONT, 0, 10));
        if (equal(mode, "blocked-restart")) { settle(); dec("blocked.write", call(1, data[1], (i64)&go, 1, 0, 0)); }
    } else {
        if (equal(mode, "blocked-futex")) ok("blocked.futex.change", ptrace(POKEDATA, (u64)&blocked_word, 1));
        ok("blocked.options", ptrace(SETOPTIONS, 0, 1));
        resume(24, "blocked.entry.status");
        blocked_regs("blocked.entry");
        if (equal(mode, "blocked-read")) dec("blocked.write", call(1, data[1], (i64)&go, 1, 0, 0));
        resume(24, "blocked.exit.status");
        blocked_regs("blocked.exit");
        ok("blocked.continue", ptrace(CONT, 0, 0));
    }
    wait_child("blocked.end.status");
    if (child) fail("blocked.still-stopped");
    int s = 0;
    dec("blocked.echild", call(61, -1, (i64)&s, WALL | 1, 0, 0));
    call(3, data[1], 0, 0, 0, 0); call(3, ready[0], 0, 0, 0, 0);
}
static void tracer_exit(const char *self, int exitkill) {
    if (call(39, 0, 0, 0, 0, 0) != 1) {
        text("FAIL tracer-exit-needs-pid1\n"); done(2);
    }
    int pipe[2];
    ok("orphan.pipe", call(293, (i64)pipe, 0x80000, 0, 0, 0));
    child = call(57, 0, 0, 0, 0, 0);
    if (child < 0) fail("orphan.fork");
    if (child == 0) {
        call(3, pipe[0], 0, 0, 0, 0);
        child = call(57, 0, 0, 0, 0, 0);
        if (child < 0) fail("orphan.target-fork");
        if (child == 0) {
            if (call(101, TRACEME, 0, 0, 0, 0)) done(111);
            char *av[] = { (char *)self, "orphan-target", 0 };
            char *ev[] = { 0 };
            call(59, (i64)self, (i64)av, (i64)ev, 0, 0);
            done(111);
        }
        stopped("orphan.ready.status");
        ok("orphan.options", ptrace(SETOPTIONS, 0, exitkill ? 0x100000 : 0));
        u64 pid = child;
        if (call(1, pipe[1], (i64)&pid, 8, 0, 0) != 8) fail("orphan.publish");
        done(0); /* target is still in the initial exec stop */
    }
    call(3, pipe[1], 0, 0, 0, 0);
    u64 target = 0;
    i64 n;
    do { n = call(0, pipe[0], (i64)&target, 8, 0, 0); } while (n == -4);
    call(3, pipe[0], 0, 0, 0, 0);
    if (n != 8 || !target) fail("orphan.pid-message");
    if (wait_child("tracer.exit.status") != 0) fail("tracer.exit.status");
    child = target; /* pid 1 now owns the orphan, on both kernels */
    if (wait_child("tracee.after-tracer.status") != (exitkill ? 9 : (23 << 8))) fail("tracee.after-tracer.status");
}

/* px102 memory witnesses (notes/px102/memory.txt). The target maps
 * fixed regions, stops at int3, and later reports what it sees in r15
 * at a second stop. Sources: ptrace(2) PEEK/POKE, proc_pid_mem(5). */
#define MA 0x500000UL   /* two private anonymous pages */
#define MB 0x502000UL   /* a PROT_NONE page that held bytes */
#define MC 0x503000UL   /* read-only private file page */
#define MC2 0x504000UL  /* a second private mapping of the same file page */
#define MD 0x505000UL   /* shared anonymous page; MD+0x1000 is unmapped */
static i64 mmap6(u64 addr, u64 len, u64 prot, u64 flags, i64 fd) {
    register i64 r10 __asm__("r10") = flags;
    register i64 r8 __asm__("r8") = fd;
    register i64 r9 __asm__("r9") = 0;
    i64 ret;
    __asm__ volatile("syscall" : "=a"(ret) : "a"(9), "D"(addr), "S"(len), "d"(prot), "r"(r10), "r"(r8), "r"(r9)
        : "rcx", "r11", "memory");
    return ret;
}
static int memory_mode(const char *mode) { return equal(mode, "memory"); }
static __attribute__((noreturn)) void role_mem(void) {
    if (mmap6(MA, 0x2000, 3, 0x32, -1) != (i64)MA) done(111);
    if (mmap6(MB, 0x1000, 3, 0x32, -1) != (i64)MB) done(111);
    if (mmap6(MD, 0x1000, 3, 0x21, -1) != (i64)MD) done(111);
    for (u64 i = 0; i < 0x2000; i++) ((volatile unsigned char *)MA)[i] = (unsigned char)(i * 7 + 1);
    for (u64 i = 0; i < 0x1000; i++) ((volatile unsigned char *)MB)[i] = 0x5a;
    for (u64 i = 0; i < 0x1000; i++) ((volatile unsigned char *)MD)[i] = 0x3c;
    if (call(10, MB, 0x1000, 0, 0, 0)) done(111); /* PROT_NONE */
    i64 fd = call(2, (i64)self_path, 0, 0, 0, 0);
    if (fd < 0) done(111);
    if (mmap6(MC, 0x1000, 1, 2, fd) != (i64)MC) done(111);
    if (mmap6(MC2, 0x1000, 1, 2, fd) != (i64)MC2) done(111);
    call(3, fd, 0, 0, 0, 0);
    __asm__ volatile("int3");
    u64 bits = 0;
    if (*(volatile unsigned char *)MD == 0xab) bits |= 1;
    if (*(volatile unsigned char *)MC == 0xcc) bits |= 2;
    if (*(volatile unsigned char *)MC2 != 0xcc) bits |= 4;
    if (*(volatile unsigned char *)(MA + 0xffd) == 0x88) bits |= 8;
    __asm__ volatile("mov %0,%%r15\nint3" : : "r"(bits) : "r15");
    char *av[] = { (char *)self_path, "orphan-target", 0 }; char *ev[] = { 0 };
    call(59, (i64)self_path, (i64)av, (i64)ev, 0, 0);
    done(111);
}
static void bytes(const char *name, const unsigned char *b, u64 n) {
    text(name); text("=");
    for (u64 i = 0; i < n; i++) { number(b[i] >> 4, 16); number(b[i] & 15, 16); }
    text("\n");
}
static i64 memfd(const char *leaf, int self) {
    char name[80]; path(name, child, 0, leaf);
    if (self) { const char *s = "/proc/self/mem"; u64 k = 0; while ((name[k] = s[k])) k++; }
    return call(2, (i64)name, 2, 0, 0, 0);
}
static void memory_rows(void) {
    resume(CONT, "mem.ready.status");
    u64 w = 0;
    dec("mem.cross.peek", ptrace(PEEKDATA, MA + 0xffd, (u64)&w)); hex("mem.cross.peek.value", w);
    dec("mem.cross.poke", ptrace(POKEDATA, MA + 0xffd, 0x1122334455667788UL));
    dec("mem.cross.poke.low", ptrace(PEEKDATA, MA + 0xff8, (u64)&w)); hex("mem.cross.poke.low.value", w);
    dec("mem.cross.poke.high", ptrace(PEEKDATA, MA + 0x1000, (u64)&w)); hex("mem.cross.poke.high.value", w);
    dec("mem.none.peek", ptrace(PEEKDATA, MB, (u64)&w)); hex("mem.none.peek.value", w);
    dec("mem.none.poke", ptrace(POKEDATA, MB, 0x77));
    dec("mem.none.after", ptrace(PEEKDATA, MB, (u64)&w)); hex("mem.none.after.value", w);
    dec("mem.ro.peek", ptrace(PEEKDATA, MC, (u64)&w)); hex("mem.ro.peek.value", w);
    dec("mem.ro.poke", ptrace(POKEDATA, MC, (w & ~255UL) | 0xcc));
    dec("mem.ro.after", ptrace(PEEKDATA, MC, (u64)&w)); hex("mem.ro.after.value", w);
    dec("mem.private.other", ptrace(PEEKDATA, MC2, (u64)&w)); hex("mem.private.other.value", w);
    dec("mem.shared.peek", ptrace(PEEKDATA, MD, (u64)&w)); hex("mem.shared.peek.value", w);
    dec("mem.shared.poke", ptrace(POKEDATA, MD, (w & ~255UL) | 0xab));
    dec("mem.edge.peek", ptrace(PEEKDATA, MD + 0xff9, (u64)&w)); hex("mem.edge.peek.value", w);
    dec("mem.edge.poke", ptrace(POKEDATA, MD + 0xff9, 0));
    dec("mem.kernel.peek", ptrace(PEEKDATA, 0xffff800000000000UL, (u64)&w));
    dec("mem.noncanonical.peek", ptrace(PEEKDATA, 0x0001000000000000UL, (u64)&w));
    i64 fd = memfd("/mem", 0);
    dec("mem.open", fd < 0 ? fd : 0);
    if (fd < 0) fail("mem.open");
    unsigned char buf[32]; zero(buf, sizeof(buf));
    dec("mem.cross.pread", call(17, fd, (i64)buf, 16, MA + 0xff8, 0)); bytes("mem.cross.pread.bytes", buf, 16);
    zero(buf, sizeof(buf));
    dec("mem.edge.pread", call(17, fd, (i64)buf, 16, MD + 0xff8, 0)); bytes("mem.edge.pread.bytes", buf, 16);
    dec("mem.hole.pread", call(17, fd, (i64)buf, 16, MD + 0x1000, 0));
    dec("mem.zero.pread", call(17, fd, (i64)buf, 0, MD + 0x1000, 0));
    dec("mem.kernel.pread", call(17, fd, (i64)buf, 8, 0xffff800000000000UL, 0));
    dec("mem.negative.pread", call(17, fd, (i64)buf, 8, (u64)-1, 0));
    zero(buf, sizeof(buf));
    dec("mem.none.pread", call(17, fd, (i64)buf, 4, MB, 0)); bytes("mem.none.pread.bytes", buf, 4);
    unsigned char pat[16]; for (int i = 0; i < 16; i++) pat[i] = (unsigned char)(0xa0 + i);
    dec("mem.edge.pwrite", call(18, fd, (i64)pat, 16, MD + 0xff8, 0));
    dec("mem.none.pwrite", call(18, fd, (i64)pat, 4, MB, 0));
    dec("mem.ro.pwrite", call(18, fd, (i64)pat, 4, MC + 8, 0));
    dec("mem.lseek", call(8, fd, MA + 0xffc, 0, 0, 0));
    zero(buf, sizeof(buf));
    dec("mem.lseek.read", call(0, fd, (i64)buf, 8, 0, 0)); bytes("mem.lseek.read.bytes", buf, 8);
    dec("mem.lseek.pos", call(8, fd, 0, 1, 0, 0));
    dec("mem.after.edge", ptrace(PEEKDATA, MD + 0xff8, (u64)&w)); hex("mem.after.edge.value", w);
    dec("mem.after.none", ptrace(PEEKDATA, MB, (u64)&w)); hex("mem.after.none.value", w);
    dec("mem.after.ro", ptrace(PEEKDATA, MC + 8, (u64)&w)); hex("mem.after.ro.value", w);
    i64 self = memfd("", 1);
    dec("mem.self.open", self < 0 ? self : 0);
    if (self >= 0) {
        static volatile u64 mine = 0x0102030405060708UL;
        u64 got = 0;
        dec("mem.self.pread", call(17, self, (i64)&got, 8, (u64)&mine, 0)); hex("mem.self.value", got);
        u64 put = 0x1111111122222222UL;
        dec("mem.self.pwrite", call(18, self, (i64)&put, 8, (u64)&mine, 0)); hex("mem.self.after", mine);
        call(3, self, 0, 0, 0, 0);
    }
    resume(CONT, "mem.second.status");
    getregs(); hex("mem.target.saw", r.r15);
    ok("mem.exec.cont", ptrace(CONT, 0, 0));
    int st = wait_child("mem.exec.status");
    if ((st & 255) != 127) fail("mem.exec.status");
    zero(buf, sizeof(buf));
    dec("mem.held.pread", call(17, fd, (i64)buf, 8, MA, 0));
    dec("mem.held.pwrite", call(18, fd, (i64)pat, 4, MA, 0));
    call(3, fd, 0, 0, 0, 0);
    char name[80]; path(name, child, 0, "/mem");
    i64 fd2 = call(2, (i64)name, 2, 0, 0, 0);
    dec("mem.reopen", fd2 < 0 ? fd2 : 0);
    if (fd2 >= 0) { dec("mem.reopen.pread", call(17, fd2, (i64)buf, 8, MA, 0)); call(3, fd2, 0, 0, 0, 0); }
    ok("mem.final.cont", ptrace(CONT, 0, 0));
    int fin = wait_child("mem.final.status");
    if (child) fail("mem.final.stopped");
    if (fin != (23 << 8)) fail("mem.final.code");
}

/* px102 permission witnesses (notes/px102/perm.txt). Root-started: it
 * forks targets with different credentials and dumpable states, drops to
 * uid/gid 1000, then asks to attach and to open the target's mem and
 * environ. Every target is a descendant (no Yama scope in play). */
static int perm_mode(const char *mode) { return equal(mode, "perm"); }
static __attribute__((noreturn)) void perm_child(int variant, int ready, int go) {
    if (variant == 1) { call(119, 1000, 1000, 1000, 0, 0); call(117, 2000, 2000, 2000, 0, 0); }
    if (variant >= 2 && variant <= 4) { call(119, 1000, 1000, 1000, 0, 0); call(117, 1000, 1000, 1000, 0, 0); }
    if (variant == 3) call(157, 4, 1, 0, 0, 0);   /* PR_SET_DUMPABLE 1 */
    if (variant == 4) call(157, 4, 0, 0, 0, 0);   /* PR_SET_DUMPABLE 0 */
    char c = 'r'; unsigned char sink;
    call(1, ready, (i64)&c, 1, 0, 0);
    call(0, go, (i64)&sink, 1, 0, 0);
    done(0);
}
static void perm_target(const char *label, i64 pid) {
    char name[96]; u64 k = 0;
    while (label[k]) { name[k] = label[k]; k++; }
    const char *tails[3] = { ".attach", ".mem-rw", ".environ" };
    child = pid;
    char leaf[24];
    const char *files[3] = { "", "/mem", "/environ" };
    for (int t = 0; t < 3; t++) {
        u64 n = k; for (const char *s = tails[t]; *s; s++) name[n++] = *s; name[n] = 0;
        if (t == 0) {
            i64 ret = ptrace(ATTACH, 0, 0);
            dec(name, ret);
            if (ret == 0) {
                int st = 0; i64 got;
                do { got = call(61, pid, (i64)&st, WALL, 0, 0); } while (got == -4);
                hex("perm.attach.status", (unsigned)st);
                zero(&r, sizeof(r));
                dec("perm.attach.getregs", ptrace(GETREGS, 0, (u64)&r));
                dec("perm.attach.detach", ptrace(17, 0, 0));
            }
        } else {
            path(leaf, pid, 0, files[t]);
            i64 fd = call(2, (i64)leaf, t == 1 ? 2 : 0, 0, 0, 0);
            dec(name, fd < 0 ? fd : 0);
            if (fd >= 0) call(3, fd, 0, 0, 0, 0);
        }
    }
    child = 0;
}
static void perm_rows(void) {
    dec("perm.root", call(102, 0, 0, 0, 0, 0) == 0);
    if (call(102, 0, 0, 0, 0, 0) != 0) fail("perm.root");
    i64 pids[5]; int ready[2], go[2];
    ok("perm.pipe.ready", call(22, (i64)ready, 0, 0, 0, 0));
    ok("perm.pipe.go", call(22, (i64)go, 0, 0, 0, 0));
    for (int v = 1; v <= 4; v++) {
        pids[v] = call(57, 0, 0, 0, 0, 0);
        if (pids[v] == 0) { call(3, go[1], 0, 0, 0, 0); call(3, ready[0], 0, 0, 0, 0); perm_child(v, ready[1], go[0]); }
        if (pids[v] < 0) fail("perm.fork");
        char c = 0; i64 n;
        do { n = call(0, ready[0], (i64)&c, 1, 0, 0); } while (n == -4);
        if (n != 1) fail("perm.ready");
    }
    ok("perm.drop.gid", call(119, 1000, 1000, 1000, 0, 0));
    ok("perm.drop.uid", call(117, 1000, 1000, 1000, 0, 0));
    pids[0] = call(57, 0, 0, 0, 0, 0);
    if (pids[0] == 0) { call(3, go[1], 0, 0, 0, 0); call(3, ready[0], 0, 0, 0, 0); perm_child(0, ready[1], go[0]); }
    { char c = 0; i64 n; do { n = call(0, ready[0], (i64)&c, 1, 0, 0); } while (n == -4); if (n != 1) fail("perm.ready"); }
    perm_target("perm.control", pids[0]);
    perm_target("perm.uid-changed", pids[1]);
    perm_target("perm.same-uid-after-setuid", pids[2]);
    perm_target("perm.dumpable-reset", pids[3]);
    perm_target("perm.dumpable-off", pids[4]);
    call(3, go[1], 0, 0, 0, 0);
    for (int v = 0; v < 5; v++) {
        int st = 0; i64 got;
        do { got = call(61, pids[v], (i64)&st, WALL, 0, 0); } while (got == -4);
        dec("perm.exit.pid", got == pids[v]); hex("perm.exit.status", (unsigned)st);
    }
}
__attribute__((used, noreturn)) void trace_main(u64 *sp) {
    u64 argc = sp[0]; char **argv = (char **)(sp + 1);
    if (argc == 2 && equal(argv[1], "orphan-target")) done(23);
    if (argc == 2 && equal(argv[1], "role-fork")) role_fork();
    if (argc == 2 && equal(argv[1], "role-vfork")) role_vfork(argv[0]);
    if (argc == 2 && equal(argv[1], "role-clone")) role_clone();
    self_path = argv[0];
    if (argc == 2 && equal(argv[1], "role-group")) role_group();
    if (argc == 2 && equal(argv[1], "role-mem")) role_mem();
    if (argc == 2 && equal(argv[1], "role-exec-thread")) role_exec_thread();
    if (argc < 2 || argc > 3) { text("usage: trace TRACEE [core|syscall|exec|errors|stops|regs|step|notify|notify-syscall|exitkill|detach-exit|fork-event|vfork-event|vfork-order|clone-event|attach|seize|replace-signal|seize-fork|fault-handler|untraced-db|fault-segv|fault-ill|fault-fpe|fault-pass|group-exit|group-exit-event|exec-thread|tracer-thread|traceme-thread|blocked-read|blocked-sleep|blocked-futex|blocked-restart|blocked-eintr|memory|perm]\n"); done(2); }
    const char *mode = argc == 3 ? argv[2] : "core";
    if (controlled_mode(mode)) {
        controlled(mode); text("trace.complete\n"); done(0);
    }
    if (perm_mode(mode)) { perm_rows(); text("trace.complete\n"); done(0); }
    if (blocked_mode(mode)) {
        blocked(mode); text("trace.complete\n"); done(0);
    }
    if (thread_tracer_mode(mode)) {
        thread_tracers(mode); text("trace.complete\n"); done(0);
    }
    if (equal(mode, "exitkill") || equal(mode, "detach-exit")) {
        tracer_exit(argv[0], equal(mode, "exitkill"));
        text("trace.complete\n"); done(0);
    }
    if (!equal(mode, "core") && !equal(mode, "syscall") && !equal(mode, "exec") && !equal(mode, "errors") && !equal(mode, "stops") && !equal(mode, "regs") && !equal(mode, "step") && !equal(mode, "notify") && !equal(mode, "notify-syscall") && !event_mode(mode) && !fault_mode(mode) && !lifecycle_mode(mode) && !memory_mode(mode)) done(2);
    if (equal(mode, "notify") || equal(mode, "notify-syscall")) {
        struct { u64 handler, flags, restorer, mask; } action = {
            (u64)child_notice, 0x14000004, (u64)trace_restorer, 0
        };
        ok("notify.sigaction", call(13, 17, (i64)&action, 0, 8, 0));
    }
    child = call(57, 0, 0, 0, 0, 0);
    if (child < 0) { dec("fork", child); done(1); }
    if (child == 0) {
        i64 ret = call(101, TRACEME, 0, 0, 0, 0);
        if (ret) { dec("traceme", ret); done(111); }
        if (equal(mode, "exec") || equal(mode, "notify")) call(62, call(39, 0, 0, 0, 0, 0), 19, 0, 0, 0);
        char *av[] = { argv[1], 0, 0 }; char *ev[] = { 0 };
        if (event_mode(mode)) {
            av[0] = argv[0];
            av[1] = equal(mode, "fork-event") ? "role-fork" : equal(mode, "clone-event") ? "role-clone" : "role-vfork";
        }
        if (memory_mode(mode)) { av[0] = argv[0]; av[1] = "role-mem"; }
        if (lifecycle_mode(mode)) { av[0] = argv[0]; av[1] = equal(mode, "exec-thread") ? "role-exec-thread" : "role-group"; }
        ret = call(59, (i64)av[0], (i64)av, (i64)ev, 0, 0);
        dec("execve", ret); done(111);
    }
    waitid_peek();
    stopped("initial.status");
    if (equal(mode, "exec")) {
        ok("exec.options", ptrace(SETOPTIONS, 0, 0x10));
        resume(CONT, "event.exec.status");
        u64 message = 0;
        ok("geteventmsg.exec", ptrace(GETEVENTMSG, 0, (u64)&message));
        dec("event.exec.pid", message == (u64)child);
        getregs(); hex("event.exec.rip", r.rip);
        ok("exec.kill", ptrace(KILL, 0, 0));
        if (wait_child("kill.status") != 9) fail("kill.status");
    } else if (fault_mode(mode)) fault_rows(mode);
    else if (event_mode(mode)) child_events(mode);
    else if (lifecycle_mode(mode)) lifecycle(mode);
    else if (memory_mode(mode)) memory_rows();
    else if (equal(mode, "errors")) errors();
    else if (equal(mode, "syscall") || equal(mode, "notify-syscall")) syscall_rows(equal(mode, "notify-syscall"));
    else if (equal(mode, "stops")) stops();
    else if (equal(mode, "step")) steps();
    else if (equal(mode, "notify")) notifications();
    else if (equal(mode, "regs")) {
        registers();
        ok("regs.kill", ptrace(KILL, 0, 0));
        if (wait_child("kill.status") != 9) fail("kill.status");
    }
    else core();
    text("trace.complete\n"); done(0);
}
__asm__(".global _start\n_start:\nmov %rsp,%rdi\nand $-16,%rsp\ncall trace_main\nud2\n");
