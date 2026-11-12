# px126 measurement variant (never merged): the walks unbounded, as raising SLOTS alone would leave them
# (every walk to SLOTS, the tick and every switch walking whatever the deadlines). python3 THIS CHECKOUT
import sys
p=sys.argv[1]+'/kernel/sched/sched.lu'
s=open(p).read()
old='''pub fn top() -> u64 {
    sv(S_TOP)
}'''
assert s.count(old)==1
s=s.replace(old,'''pub fn top() -> u64 {
    SLOTS // variant: the walks unbounded
}''')
old='''    if now < sv(S_WAKE_AT) {
        return
    }'''
assert s.count(old)==1
s=s.replace(old,'''    if now < sv(S_WAKE_AT) && now == 0xffffffffffffffff { // variant: never skips
        return
    }''')
open(p,'w').write(s)
