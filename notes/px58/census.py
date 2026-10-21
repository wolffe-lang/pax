#!/usr/bin/env python3
# px58: the census of what yew asks of Linux, read from `strace -f -n -v
# -xx -s N` traces (strace(1)'s output, black-box): every system call by
# name and number with counts, every ioctl request with counts, the
# termios states set (strace's own decoding), the window size asked, the
# opens of /dev/tty, the signals caught, ignored and defaulted, and the
# escape sequences written to the terminal, classified by name
# (ECMA-48's and the DEC private modes' names, console_codes(4)).
#
#   census.py OUT.txt TRACE...
#
# A process is the guard when it execve'd with `--guard` (yew's terminal
# guard sibling, ruling #93 R1 interim B); the editor otherwise.
import collections
import re
import sys

LINE = re.compile(r"^(\d+)\s+\[\s*(\d+)\]\s+([a-z0-9_]+)\((.*)$")
RESUMED = re.compile(r"^(\d+)\s+(?:\[\s*\d+\]\s+)?<\.\.\. ([a-z0-9_]+) resumed>(.*)$")


def unescape(s):
    # strace -xx: every byte as \xNN; with -s large enough, whole.
    out = bytearray()
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            c = s[i + 1]
            if c == "x":
                out.append(int(s[i + 2:i + 4], 16))
                i += 4
                continue
            m = {"n": 10, "r": 13, "t": 9, "\\": 92, '"': 34, "e": 27, "f": 12, "v": 11, "a": 7, "b": 8}
            if c in m:
                out.append(m[c])
                i += 2
                continue
        out += s[i].encode()
        i += 1
    return bytes(out)


DEC = {"1049": "alternate screen (?1049)", "47": "alternate screen (?47)", "1047": "alternate screen (?1047)",
       "25": "cursor visibility (DECTCEM ?25)", "2004": "bracketed paste (?2004)", "1000": "mouse X11 (?1000)",
       "1002": "mouse button-event (?1002)", "1003": "mouse any-event (?1003)", "1006": "mouse SGR encoding (?1006)",
       "1004": "focus events (?1004)", "2026": "synchronized output (?2026)", "7": "autowrap (DECAWM ?7)",
       "1": "cursor keys (DECCKM ?1)", "12": "cursor blink (?12)", "1005": "mouse UTF-8 (?1005)", "1015": "mouse urxvt (?1015)"}
CSI_FINAL = {"H": "cursor position (CUP)", "f": "cursor position (HVP)", "A": "cursor up (CUU)", "B": "cursor down (CUD)",
             "C": "cursor forward (CUF)", "D": "cursor back (CUB)", "E": "cursor next line (CNL)", "F": "cursor previous line (CPL)",
             "G": "cursor column (CHA)", "d": "cursor row (VPA)", "J": "erase in display (ED)", "K": "erase in line (EL)",
             "X": "erase characters (ECH)", "@": "insert characters (ICH)", "P": "delete characters (DCH)", "L": "insert lines (IL)",
             "M": "delete lines (DL)", "S": "scroll up (SU)", "T": "scroll down (SD)", "r": "scroll region (DECSTBM)",
             "m": "SGR", "n": "device status report (DSR)", "c": "device attributes query (DA1)", "s": "save cursor (SCOSC)",
             "u": "restore cursor (SCORC)", "t": "window operations (XTWINOPS)", "b": "repeat (REP)", "Z": "back tab (CBT)",
             "I": "forward tab (CHT)", "g": "tab clear (TBC)"}


def classify(data, classes, sgr):
    i, n = 0, len(data)
    text = 0
    while i < n:
        b = data[i]
        if b == 0x1b and i + 1 < n:
            c = data[i + 1]
            if c == 0x5b:  # CSI
                j = i + 2
                while j < n and 0x30 <= data[j] <= 0x3f:
                    j += 1
                k = j
                while k < n and 0x20 <= data[k] <= 0x2f:
                    k += 1
                if k >= n:
                    classes["CSI cut short"] += 1
                    break
                params = data[i + 2:j].decode("latin-1")
                inter = data[j:k].decode("latin-1")
                final = chr(data[k])
                priv = params[:1] if params[:1] in "?<=>" else ""
                body = params[1:] if priv else params
                if priv == "?" and final in "hl" and not inter:
                    for p in body.split(";"):
                        name = DEC.get(p, "DEC private mode ?%s" % p)
                        classes["%s %s" % (name, "set (h)" if final == "h" else "reset (l)")] += 1
                elif priv == "?" and final == "p" and inter == "$":
                    classes["DEC mode query (DECRQM ?%s $p)" % body] += 1
                elif priv == "?" and final == "u":
                    classes["kitty keyboard query (CSI ? u)"] += 1
                elif priv == ">" and final == "u":
                    classes["kitty keyboard push (CSI > %s u)" % body] += 1
                elif priv == "<" and final == "u":
                    classes["kitty keyboard pop (CSI < u)"] += 1
                elif final == "q" and inter == " ":
                    classes["cursor shape (DECSCUSR %s SP q)" % (body or "0")] += 1
                elif final == "m" and not priv and not inter:
                    classes["SGR"] += 1
                    ps = body.split(";") if body else ["0"]
                    q = 0
                    while q < len(ps):
                        p = ps[q] or "0"
                        if p in ("38", "48", "58") and q + 1 < len(ps):
                            if ps[q + 1] == "5":
                                sgr["%s;5;n" % p] += 1
                                q += 3
                                continue
                            if ps[q + 1] == "2":
                                sgr["%s;2;r;g;b" % p] += 1
                                q += 5
                                continue
                        sgr[p] += 1
                        q += 1
                elif not priv and not inter and final in CSI_FINAL:
                    nm = CSI_FINAL[final]
                    if final in "JK":
                        nm = "%s %s" % (nm, body or "0")
                    classes[nm] += 1
                else:
                    classes["CSI %s%s%s (other)" % (priv, inter, final)] += 1
                i = k + 1
                continue
            if c == 0x5d:  # OSC
                j = i + 2
                while j < n and data[j] not in (7, 0x1b):
                    j += 1
                num = data[i + 2:j].split(b";")[0].decode("latin-1")
                classes["OSC %s" % num] += 1
                i = j + (1 if j < n and data[j] == 7 else 2)
                continue
            names = {0x37: "save cursor (DECSC, ESC 7)", 0x38: "restore cursor (DECRC, ESC 8)", 0x3d: "keypad application (DECKPAM)",
                     0x3e: "keypad numeric (DECKPNM)", 0x63: "reset (RIS)", 0x4d: "reverse index (RI)", 0x50: "DCS", 0x5c: "string terminator (ST)"}
            classes[names.get(c, "ESC %s" % chr(c))] += 1
            i += 2
            continue
        if b < 0x20 or b == 0x7f:
            classes[{13: "CR", 10: "LF", 8: "BS", 9: "TAB", 7: "BEL"}.get(b, "C0 0x%02x" % b)] += 1
        else:
            text += 1
        i += 1
    return text


def main(argv):
    out = argv[1]
    calls = {"editor": collections.Counter(), "guard": collections.Counter()}
    errs = collections.Counter()
    ioctls = collections.Counter()
    termios = collections.Counter()
    winsz = collections.Counter()
    sigs = collections.Counter()
    opens = collections.Counter()
    classes = collections.Counter()
    sgr = collections.Counter()
    text = 0
    procs = 0
    for path in argv[2:]:
        guards = set()
        writes = collections.defaultdict(bytearray)
        for line in open(path, errors="replace"):
            m = LINE.match(line)
            if not m:
                continue
            pid, nr, name, rest = m.groups()
            if name == "execve" and b"--guard" in unescape(rest):
                guards.add(pid)
            role = "guard" if pid in guards else "editor"
            calls[role]["%s %s" % (name, nr)] += 1
            em = re.search(r"= -1 (E[A-Z0-9]+)", rest)
            if em:
                errs["%s %s %s" % (role, name, em.group(1))] += 1
            if name == "ioctl":
                req = rest.split(",")[1].strip() if "," in rest else "?"
                req = req.split(" <")[0]
                ioctls["%s %s" % (role, req)] += 1
                if req in ("TCSETS", "TCSETSW", "TCSETSF"):
                    st = re.search(r"\{(c_iflag=.*?c_lflag=[^,]*), .*?\[VTIME\]=(\w+), \[VMIN\]=(\w+)", rest)
                    termios["%s %s %s VMIN %d VTIME %d" % (role, req, st.group(1), int(st.group(3), 0), int(st.group(2), 0)) if st else "%s %s ?" % (role, req)] += 1
                if req == "TIOCGWINSZ":
                    ws = re.search(r"\{(ws_row=\d+, ws_col=\d+)", rest)
                    winsz["%s %s" % (role, ws.group(1) if ws else rest.strip()[:60])] += 1
            if name in ("openat", "open") and b'"/dev/tty"' in unescape(rest):
                opens["%s /dev/tty" % role] += 1
            if name == "rt_sigaction":
                sm = re.match(r"(SIG[A-Z0-9+]+|\d+), (\{[^}]*\}|NULL)", rest)
                if sm and sm.group(2) != "NULL":
                    h = re.search(r"sa_handler=([^,}]+)", sm.group(2))
                    hv = h.group(1) if h else "?"
                    kind = "default" if hv == "SIG_DFL" else ("ignored" if hv == "SIG_IGN" else "caught")
                    if "SA_ONSTACK" in sm.group(2) and kind == "caught":
                        kind = "caught (on the alternate stack)"
                    sigs["%s %s %s" % (role, sm.group(1), kind)] += 1
            if name == "write" and re.match(r"[12], ", rest):
                dm = re.match(r'([12]), "((?:[^"\\]|\\.)*)"', rest)
                if dm:
                    writes[pid] += unescape(dm.group(2))
        procs += len(writes)
        for pid, data in writes.items():
            text += classify(bytes(data), classes, sgr)
    names = collections.Counter()
    with open(out, "w") as f:
        f.write("traces: %d\n" % (len(argv) - 2))
        for role in ("editor", "guard"):
            f.write("\n%s calls: %d by name\n" % (role, len(calls[role])))
            for k, v in sorted(calls[role].items(), key=lambda kv: int(kv[0].split()[1])):
                f.write("  %s %d\n" % (k, v))
        f.write("\nfailures (name, errno, count)\n")
        for k, v in sorted(errs.items()):
            f.write("  %s %d\n" % (k, v))
        f.write("\nioctls (role, request, count)\n")
        for k, v in sorted(ioctls.items()):
            f.write("  %s %d\n" % (k, v))
        f.write("\ntermios set (role, request, state, count)\n")
        for k, v in sorted(termios.items(), key=lambda kv: -kv[1]):
            f.write("  %s: %d\n" % (k, v))
        f.write("\nwindow size asked (role, answer, count)\n")
        for k, v in sorted(winsz.items()):
            f.write("  %s %d\n" % (k, v))
        f.write("\n/dev/tty opened: %s\n" % (dict(opens) or "never"))
        f.write("\nsignals (role, signal, disposition, count)\n")
        for k, v in sorted(sigs.items()):
            f.write("  %s %d\n" % (k, v))
        f.write("\nescape classes written to the terminal (%d bytes of text besides)\n" % text)
        for k, v in sorted(classes.items(), key=lambda kv: -kv[1]):
            f.write("  %s %d\n" % (k, v))
        f.write("\nSGR parameters\n")
        for k, v in sorted(sgr.items(), key=lambda kv: -kv[1]):
            f.write("  %s %d\n" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
