trap 'echo parent' TERM
(/bin/sh -c 'kill -TERM $PPID'; echo in)
echo out=$?
