#!/usr/bin/env python3
"""tests/mpx5-bore.d/fixture.py DIR — px65: the files bu31's text tools
read in tests/mpx5-bore's text session, generated (the same bytes every
run): written into DIR, which the image carries as /usr/share/bore and
the container's root as the same path. Prints one line per file: name,
bytes, sha256. rows.py reads FILES from here, so the witness and the
image are one set of bytes."""
import hashlib
import os
import sys

FILES = {
    # base64 and base32: a short line, every byte value (the alphabet's
    # last two characters and padding), and encoded forms to decode.
    "hello.txt": b"hello\n",
    "bytes.dat": bytes(range(256)),
    "b64.txt": b"aGVsbG8sIHdv\ncmxkCg==\n",
    "b32.txt": b"NBSWY3DPFQQH\nO33SNRSAU===\n",
    "bad.txt": b"aGVsbG8K!!\n",
    # comm: two sorted lists sharing two lines, and one out of order.
    "c1.txt": b"apple\nbanana\ncherry\ndate\n",
    "c2.txt": b"banana\ncherry\negg\nfig\n",
    "cu.txt": b"cherry\napple\n",
    # join: on the first field, blank-separated; on chosen fields with
    # `:`; case folded; a header line each.
    "j1.txt": b"1 alice\n2 bob\n3 carol\n",
    "j2.txt": b"1 paris\n3 rome\n4 oslo\n",
    "p1.txt": b"alice:1\nbob:2\ncarol:3\n",
    "p2.txt": b"1:red\n3:blue\n",
    "u1.txt": b"A one\nb two\n",
    "u2.txt": b"a uno\nB dos\n",
    "h1.txt": b"id name\n1 alice\n2 bob\n",
    "h2.txt": b"id city\n1 paris\n2 rome\n",
    # tsort: a DAG of pairs, a cycle, an odd token count.
    "ts.txt": b"shirt tie\ntie jacket\nshirt jacket\nsocks shoes\npants shoes\n",
    "tcyc.txt": b"a b\nb a\n",
    "todd.txt": b"a b c\n",
    # shuf: ten lines to permute.
    "lines.txt": b"".join(b"%d\n" % k for k in range(1, 11)),
}


def main():
    if len(sys.argv) != 2:
        print("usage: fixture.py DIR", file=sys.stderr)
        return 2
    d = sys.argv[1]
    os.makedirs(d, exist_ok=True)
    for name in sorted(FILES):
        data = FILES[name]
        with open(os.path.join(d, name), "wb") as f:
            f.write(data)
        print("%s %d %s" % (name, len(data), hashlib.sha256(data).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
