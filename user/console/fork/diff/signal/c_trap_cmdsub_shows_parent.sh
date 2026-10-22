trap 'echo x' INT
x=$(trap); echo "$x" | sed 's/SIG//'
(trap) | sed 's/SIG//'
