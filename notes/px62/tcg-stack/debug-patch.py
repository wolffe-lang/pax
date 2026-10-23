# px62 debug only, applied to a copy of a tree (never to the repository): log each fork's frames and time, and every system call of a pid >= 56 that took over 20M TSC cycles.
import sys
p = sys.argv[1] + '/kernel/user/user.lu'
s = open(p).read()
old = "    sched.syscall_begins() // px26: whatever wait the last call was in is over\n"
assert s.count(old) == 1
s = s.replace(old, old)
old = 'pub fn syscall(f: u64) -> u64 {'
assert s.count(old) == 1
s = s.replace(old, '''extern "c" fn pax_rdtsc() -> u64

fn dbg_tsc() -> u64 {
    // # Safety: RDTSC.
    unsafe { pax_rdtsc() }
}

pub fn syscall(f: u64) -> u64 {
    let t0 = dbg_tsc()
    let dnr = word(f, W_RAX)
    let dp = sched.self_pid()
    let fr0 = frames.free_count()
    let r = syscall_body(f)
    let dt = dbg_tsc() - t0
    if dnr == 56 && dp >= 56 {
        log.put("dbg clone pid ")
        log.dec(dp as int)
        log.put(" frames ")
        log.dec((fr0 - frames.free_count()) as int)
        log.put(" dtms ")
        log.dec((dt / 1000000) as int)
        log.end()
    }
    if dp >= 56 && dt > 20000000 {
        log.put("dbg slow pid ")
        log.dec(dp as int)
        log.put(" nr ")
        log.dec(dnr as int)
        log.put(" dtms ")
        log.dec((dt / 1000000) as int)
        log.end()
    }
    r
}

fn syscall_body(f: u64) -> u64 {''', 1)
open(p, 'w').write(s)
print("patched", p)
