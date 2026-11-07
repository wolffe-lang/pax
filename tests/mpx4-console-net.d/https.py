#!/usr/bin/env python3
"""tests/mpx4-console-net.d/https.py — the console's https row (px105, R-px105-2 B).

    https.py --work DIR --den BIN --den-src DIR --indir BIN --elf KERNEL.elf
             --tier T --leg L --accel A --mac MAC --log SERIAL.log

den at the https pin (tests/mpx4-console-net.d/den-https.pin, built by
tools/mkden) clones over https at PAX's console from a TLS fixture on this
host's loopback, which the guest reaches through QEMU's user network at
10.0.2.2, as den's own smart-HTTP rows hold den to git:

  - the fixture is den's (its tools/http-git-test.py `Server` at that pin,
    loaded from DIR, never copied): OpenSSL's s_server as the TLS
    terminator in front of git's http-backend, both black boxes;
  - its PKI is made here as den's rows make theirs (a CA, a leaf for the
    name the guest dials), the leaf's name the address itself, `DNS:10.0.2.2`
    (wolf-std's client matches dNSName only, and PAX has no resolver);
  - the repository is git's: two commits on main;
  - the image: /bin/den, /bin/indir (a run-list line in a directory),
    /etc/den/ca.der (den's --tls-roots), /etc/pax-net `dhcp`, and the run
    list, written once the fixture's port is known:
        /bin/den clone -q --tls-roots=/etc/den/ca.der https://10.0.2.2:<port>/remote.git /c
        /bin/indir /c /bin/den log --oneline --no-decorate
        /bin/indir /c /bin/den fsck --full
  - booted on QEMU's igb with the user network.

Rows (printed as the suite prints them):
  H1 the clone: den's first run ends `exit_group 0`, before it the lease;
  H2 its log is git's `log --oneline` of the repository, line for line
     (`--no-decorate`: den decorates at a terminal by default, as git does);
  H3 `fsck --full` ends `exit_group 0` and prints nothing;
  H4 the fixture saw protocol v2: discovery (`info/refs?service=
     git-upload-pack`, `Git-Protocol: version=2`) and a fetch POST, and
     no error of its own.
Exit 0 when every row held, 1 otherwise, 2 on a setup error.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
GUEST_HOST = "10.0.2.2"


def say(line):
    print("mpx4-console-net: " + line, file=sys.stderr, flush=True)


def main():
    a = argparse.ArgumentParser()
    for k in ("work", "den", "den-src", "indir", "elf", "tier", "leg", "accel", "mac", "log"):
        a.add_argument("--" + k, required=True)
    args = a.parse_args()
    L = "%s %s https" % (args.tier, args.leg)
    work = Path(args.work)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    log = Path(args.log)
    for p in (log, Path(str(log) + ".verdict"), Path(str(log) + ".norm")):
        if p.exists():
            p.unlink()

    spec = importlib.util.spec_from_file_location("den_http_git", Path(args.den_src) / "tools/http-git-test.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)

    git = shutil.which("git")
    if not git:
        say("FAIL H0 %s: no git for the fixture" % L)
        return 2
    env = dict(PATH="/usr/bin:/bin", HOME=str(work / "home"), LC_ALL="C", TZ="UTC0", GIT_CONFIG_NOSYSTEM="1",
               GIT_TERMINAL_PROMPT="0", GIT_AUTHOR_NAME="PAX Tester", GIT_AUTHOR_EMAIL="pax@example.invalid",
               GIT_COMMITTER_NAME="PAX Tester", GIT_COMMITTER_EMAIL="pax@example.invalid",
               GIT_AUTHOR_DATE="1700000000 +0000", GIT_COMMITTER_DATE="1700000000 +0000")
    (work / "home").mkdir()

    def run(argv, cwd=None, data=b"", own=False):
        # The fixture's commands get its pinned environment; PAX's own tools
        # (own=True) the suite's, PAX_CACHE and the rest.
        r = subprocess.run([str(x) for x in argv], cwd=cwd, env=None if own else env, input=data,
                           capture_output=True, timeout=120)
        if r.returncode:
            raise RuntimeError("%s: exit %d: %s" % (" ".join(map(str, argv[:3])), r.returncode, r.stderr.decode(errors="replace")[-300:]))
        return r.stdout

    # The PKI, as den's rows make theirs, for the address the guest dials.
    pki = work / "pki"
    pki.mkdir()
    ossl = lambda *x: run(["/usr/bin/openssl", *x])
    ossl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", "2",
         "-subj", "/CN=PAX console https fixture root", "-addext", "basicConstraints=critical,CA:TRUE",
         "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-keyout", pki / "ca.key", "-out", pki / "ca.pem")
    ossl("x509", "-in", pki / "ca.pem", "-outform", "DER", "-out", pki / "ca.der")
    (pki / "leaf.cnf").write_text("basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\n"
                                  "extendedKeyUsage=serverAuth\nsubjectAltName=DNS:%s\n" % GUEST_HOST)
    ossl("req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=" + GUEST_HOST,
         "-keyout", pki / "leaf.key", "-out", pki / "leaf.csr")
    ossl("x509", "-req", "-in", pki / "leaf.csr", "-CA", pki / "ca.pem", "-CAkey", pki / "ca.key",
         "-CAcreateserial", "-days", "1", "-sha256", "-extfile", pki / "leaf.cnf", "-out", pki / "leaf.pem")

    # The repository: two commits on main, served bare.
    src = work / "src"
    run([git, "init", "-q", "-b", "main", src])
    (src / "file").write_text("first\n")
    run([git, "add", "file"], src)
    run([git, "commit", "-q", "-m", "base"], src)
    (src / "file").write_text("first\nsecond\n")
    run([git, "commit", "-q", "-a", "-m", "forward"], src)
    root = work / "root"
    root.mkdir()
    run([git, "clone", "-q", "--bare", src, root / "remote.git"])
    want_log = run([git, "log", "--oneline"], src).decode().splitlines()

    server = fixture.Server(root, git, env, "tls", pki, None, lambda data: None)
    try:
        url = "https://%s:%d/remote.git" % (GUEST_HOST, server.port)
        (work / "run").write_text("/bin/den clone -q --tls-roots=/etc/den/ca.der %s /c\n"
                                  "/bin/indir /c /bin/den log --oneline --no-decorate\n"
                                  "/bin/indir /c /bin/den fsck --full\n" % url)
        (work / "pax-net").write_text("dhcp\n")
        run([ROOT / "tools/mkinitramfs", work / "https.cpio", "/bin/den=" + args.den, "/bin/indir=" + args.indir,
             "/etc/den/ca.der=%s" % (pki / "ca.der"), "/etc/pax-run=%s" % (work / "run"),
             "/etc/pax-net=%s" % (work / "pax-net"), "/tmp/:1777"], own=True)
        run([ROOT / "tools/mkimage", "--conf", ROOT / "boot/limine-initramfs.conf", "--add", work / "https.cpio",
             "initramfs.cpio", args.elf, work / "https.iso"], own=True)
        with open(str(log) + ".verdict", "wb") as v:
            hrc = subprocess.run([str(ROOT / "tools/qemu-halt"), "--firmware", args.leg, "--serial", str(log),
                                  "--timeout", "300", "--accel", args.accel, "--elf", args.elf, "--marker", "halt|PANIC .*",
                                  "--qemu", "-netdev", "--qemu", "user,id=n0,ipv6=off",
                                  "--qemu", "-device", "--qemu", "igb,netdev=n0,mac=" + args.mac,
                                  str(work / "https.iso")], stdout=v, stderr=subprocess.STDOUT).returncode
    finally:
        try:
            server.close()
        except Exception as e:
            server.errors.append("close: %s" % e)

    raw = log.read_bytes() if log.exists() else b""
    norm = re.sub(rb"\x1b\[[0-9;?=<>]*[A-Za-z]", b"", raw).replace(b"\r", b"").decode("latin-1")
    Path(str(log) + ".norm").write_text(norm)
    lines = norm.splitlines()
    fail = 0

    def row(name, ok, what):
        nonlocal fail
        say(("PASS %s %s: %s" if ok else "FAIL %s %s: %s") % (name, L, what))
        fail |= not ok

    def section(k):
        # The lines of run k: after `run k:`, up to the next `run ` or the frames line.
        out, on = [], False
        for line in lines:
            if line.startswith("run %d: " % k):
                on = True
                continue
            if on and (re.match(r"^run [0-9]+: |^run: [0-9]+ commands$|^user: frames free ", line)):
                break
            if on:
                out.append(line)
        return out

    def exit_of(sec):
        for line in sec:
            m = re.match(r"^user: den pid [0-9]+ exit_group ([0-9]+) ", line)
            if m:
                return int(m.group(1))
        return None

    lease = next((k for k, l in enumerate(lines) if re.match(r"^dhcp: \+[0-9.]+ s bound 10\.0\.2\.15 ", l)), None)
    first = next((k for k, l in enumerate(lines) if l.startswith("run 1: ")), None)
    c1 = section(1)
    st1 = exit_of(c1)
    row("H1", lease is not None and first is not None and lease < first and st1 == 0,
        "the lease before run 1, den clone over https from %s exit %s%s" % (
            GUEST_HOST, st1, "" if st1 == 0 else "; " + " | ".join(l for l in c1 if not l.startswith("user: "))[:300]))
    got_log = [l for l in section(2) if not l.startswith("user: ")]
    row("H2", got_log == want_log and exit_of(section(2)) == 0,
        "den log --oneline %s git's %s" % ("is" if got_log == want_log else "is not", want_log if got_log == want_log else (got_log, want_log)))
    c3 = section(3)
    row("H3", exit_of(c3) == 0 and not [l for l in c3 if not l.startswith("user: ")],
        "den fsck --full exit %s, %d lines" % (exit_of(c3), len([l for l in c3 if not l.startswith("user: ")])))
    reqs = server.requests
    v2 = any(r["path"] == "/remote.git/info/refs" and r["query"] == "service=git-upload-pack" and r["protocol"] == "version=2" for r in reqs)
    fetch = any(r["path"] == "/remote.git/git-upload-pack" and r["command_fetch"] for r in reqs)
    row("H4", v2 and fetch and not server.errors,
        "%d requests: v2 discovery %s, fetch %s; fixture errors %s" % (len(reqs), v2, fetch, server.errors or "none"))
    ok = hrc == 0 and "\nhalt\n" in "\n" + norm + "\n" and "PANIC" not in norm
    row("H5", ok, "qemu-halt %d; %s" % (hrc, "halted" if ok else "not halted"))
    return 1 if fail else 0


try:
    sys.exit(main())
except Exception as e:
    # A setup that failed is the row's failure by name, never a traceback.
    say("FAIL H1 https: the row could not be set up: %s: %s" % (type(e).__name__, str(e)[-300:]))
    sys.exit(1)
