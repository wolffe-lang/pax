# rows.py's selftest

Tables conspeed printed on the screen of tests/mpx3-conspeed's image (2560 x 1440, `fbwrite`, no
COM1, UEFI, native tier), read off it by screen-run.py, on one host, under KVM and under TCG:

- `red-kvm.txt`, `red-tcg.txt`: the trunk kernel the rows were written at (px129's base). They
  must fail: under KVM every row but C1 and yew's keypress is out of bounds, under TCG every row
  it does not SKIP but C1.
- `green-kvm.txt`, `green-tcg.txt`: px129's kernel (320 columns at 2560 pixels). They must pass every row
  they do not SKIP.

They are the rows' own proof that they can fail and can pass, as tests/expect-serial-selftest is
the harness's.
