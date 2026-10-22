# A job a signal ended long before `wait` asks for it: the shell reaped
# it as it went on (here as the next job started), so `wait` answers its
# status and says nothing on standard error; a job `wait` itself sees
# end by a signal is still said (dash, black-box; pelt#47)
sh -c 'kill -TERM $$' & p=$!
sleep 0.5
env true & q=$!
wait $q
wait $p; echo "long ended: $?"
