/* px102: Linux ABI measurement and PAX's red-first tracing witness.
 * No libc, headers or debugger implementation. Sources: ptrace(2),
 * wait(2), proc_pid_mem(5), proc_pid_status(5), x86-64 psABI A.2.1;
 * register layout/offsets already measured by notes/px102/gdb/.
 *
 * Usage: trace /absolute/path/to/tracee [core|syscall|exec|errors|stops|regs|step|notify|notify-syscall|exitkill|detach-exit|fork-event|vfork-event|vfork-order|clone-event]
 * Each invocation owns exactly one child. The tracee is ET_EXEC at fixed
 * text/data addresses, checked by tools/mktrace. Only pids and descriptors
 * are normalized: report equality to the child's pid and an open's success.
 * The notify mode also compares si_uid with the caller's getuid().
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
static void trace_status(void) {
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
    ok("event.options", ptrace(SETOPTIONS, 0, vf ? 0x34 : clone ? 8 : 2));
    resume(CONT, "event.parent.status");
    u64 target = 0;
    ok("event.child.message", ptrace(GETEVENTMSG, 0, (u64)&target));
    dec("event.child.valid", target != 0 && target != (u64)child);
    if (!target || target == (u64)child) fail("event.child.pid");
    if (wait_other(target, "event.child.initial") != 0x137f) fail("event.child.initial");
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
__attribute__((used, noreturn)) void trace_main(u64 *sp) {
    u64 argc = sp[0]; char **argv = (char **)(sp + 1);
    if (argc == 2 && equal(argv[1], "orphan-target")) done(23);
    if (argc == 2 && equal(argv[1], "role-fork")) role_fork();
    if (argc == 2 && equal(argv[1], "role-vfork")) role_vfork(argv[0]);
    if (argc == 2 && equal(argv[1], "role-clone")) role_clone();
    if (argc < 2 || argc > 3) { text("usage: trace TRACEE [core|syscall|exec|errors|stops|regs|step|notify|notify-syscall|exitkill|detach-exit|fork-event|vfork-event|vfork-order|clone-event]\n"); done(2); }
    const char *mode = argc == 3 ? argv[2] : "core";
    if (equal(mode, "exitkill") || equal(mode, "detach-exit")) {
        tracer_exit(argv[0], equal(mode, "exitkill"));
        text("trace.complete\n"); done(0);
    }
    if (!equal(mode, "core") && !equal(mode, "syscall") && !equal(mode, "exec") && !equal(mode, "errors") && !equal(mode, "stops") && !equal(mode, "regs") && !equal(mode, "step") && !equal(mode, "notify") && !equal(mode, "notify-syscall") && !event_mode(mode)) done(2);
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
    } else if (event_mode(mode)) child_events(mode);
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
