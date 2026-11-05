set pagination off
set confirm off
break add
run
next
step
print c
print counter
info registers rip
x/4xb &counter
finish
continue
delete
continue
