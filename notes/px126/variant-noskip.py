# px126 measurement variant (never merged): the walks to the high water, but the tick and every switch
# walking whatever the deadlines (no S_WAKE_AT skip). Applied to a checkout: python3 THIS CHECKOUT
import sys
p=sys.argv[1]+'/kernel/sched/sched.lu'
s=open(p).read()
old='''    if now < sv(S_WAKE_AT) {
        return
    }'''
assert s.count(old)==1
s=s.replace(old,'''    if now < sv(S_WAKE_AT) && now == 0xffffffffffffffff { // variant: never skips
        return
    }''')
open(p,'w').write(s)
