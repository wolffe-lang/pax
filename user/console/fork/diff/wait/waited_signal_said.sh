# A job that a signal ends while `wait` waits for it: `wait` says so on
# standard error, and answers 128 + the signal (dash, black-box; the
# other half of pelt#47's row)
sh -c 'sleep 0.3; kill -TERM $$' & p=$!
wait $p; echo "seen ending: $?"
