( sleep 1; echo slow ) & ( echo fast ) & wait
{ sleep 1; : > a-done; } & { [ -f a-done ] || echo b-ran-first; } ; wait
