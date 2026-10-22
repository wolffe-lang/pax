trap '' PIPE
{ sleep 1; echo x 2>/dev/null; echo "$?" > st; } | true
cat st
