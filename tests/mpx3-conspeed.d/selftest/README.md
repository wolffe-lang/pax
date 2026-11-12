# rows.py's selftest

Tables conspeed printed on the screen of tests/mpx3-conspeed's image (2560 x 1440, `fbwrite`, no
COM1, native tier), read off it by screen-run.py, under KVM and under TCG, on two hosts. rows.py
--selftest reads every `red-ACCEL[-HOST].txt` and `green-ACCEL[-HOST].txt` here, and needs at least
the four without a host:

- `red-kvm.txt`, `red-tcg.txt`: the trunk kernel the rows were written at (px129's base), UEFI, on
  a desktop i7-12700KF. They must fail: under KVM every row but C1 and yew's keypress is out of
  bounds, under TCG every row it does not SKIP but C1.
- `green-kvm.txt`, `green-tcg.txt`: px129's kernel (320 columns at 2560 pixels), UEFI, on the same
  host. They must pass every row they do not SKIP.
- `green-kvm-10870h.txt`: px129's kernel, BIOS, under KVM on a laptop i7-10870H, where a byte's
  parse costs about half as much again against the CPU's unit (screen text sha256 `c8f115c3…`). It
  must pass. The rows that bounded a test's raw figure in units failed it (C3's `sgr` 13.26 units
  against 11.5, C7's `cub` 4.52 against 4.3), which is why those rows now bound a test's drawing.

They are the rows' own proof that they can fail and can pass, as tests/expect-serial-selftest is
the harness's.
