# Which subshells list the shell's jobs (dash, black-box; XCU `jobs`,
# 2.13): one simple command forked as a substitution or a pipeline
# stage lists them; a parenthesized subshell, and a pipeline inside a
# substitution, start with none; and in no subshell is one a job to
# wait for or signal by its job id
sleep 1 & x=$(jobs); echo "cmdsub-jobs: [$x]"
( jobs ) | sed 's/^/subshell-jobs: /'
jobs | sed 's/^/stage-jobs: /'
y=$(jobs -p | wc -l | tr -d ' '); echo "cmdsub-pipeline-count: $y"
( wait %1 2>/dev/null; echo "sub-wait-%1=$?" )
( kill -0 %1 2>/dev/null && echo "sub-kill: ok" || echo "sub-kill: refused" )
wait
