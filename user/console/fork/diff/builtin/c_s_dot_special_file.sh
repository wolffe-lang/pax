# `.` reads commands from any readable file the name resolves to, not
# only a regular one (XCU 2.15 dot): /dev/null is an empty script.
. /dev/null
echo "dev null: $?"
mkfifo pipe
(echo 'echo "from the fifo"' >pipe &)
. ./pipe
echo "fifo: $?"
