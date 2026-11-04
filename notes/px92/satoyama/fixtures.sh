#!/usr/bin/env bash
# px92: rec.sh's step 5, and run alone on a take's outputs: the two PAX sessions tests/mpx5-wolf
# cuts from the serial log (pb/mpx5-wolf-native-bios-{root,pax}.session) become test_rows.py's
# fixtures. The suite hands W1 and W2 serial_norm of the .session (.session.cmp), but with no
# Linux side W1 continues before it writes one, so this checks the identity instead:
# serial_norm(.session) is the .session, byte for byte, and rows.py passes on each fixture.
#   fixtures.sh RUN CHECKOUT
set -euo pipefail
R=$1 C=$2
# shellcheck source=/dev/null
. "$C/tools/lib.sh"
mkdir -p "$R/fixtures"
for pair in "root root" "pax user"; do
    read -r n f <<< "$pair"
    s=$R/pb/mpx5-wolf-native-bios-$n.session
    out=$R/fixtures/wolf-pax-$f.tty
    serial_norm "$s" | cmp - "$s"
    echo "PASS $n: serial_norm(.session) == .session (the suite's .cmp form)"
    cp "$s" "$out"
    python3 -I "$C/tests/mpx5-wolf.d/rows.py" "$out" "$n"
done
wc -l "$R"/fixtures/*.tty
sha256sum "$R"/fixtures/*.tty
