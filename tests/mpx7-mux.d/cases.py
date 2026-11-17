#!/usr/bin/env python3
"""tests/mpx7-mux.d/cases.py — px125: what the console draws for a
multiplexer's client (section B of the probe). The screen image plays
these with user/elf/vtcases.c (px59's player: a screen is cleared, its
bytes written, its name sent as an OSC string the serial log keeps, and
one key read once the suite has taken the screen), then runs
`muxprobe keys` (B5) and `muxprobe paint` (B7).

    cases.py RECORDS KEYS     the records vtcases plays and the steps
                              tools/ps2-session types
    cases.py --list           each case's name, kind and what xterm draws

Each SCREEN case is (name, bytes, rows): `rows` the top-left rows xterm
draws for the bytes from a blank screen with the cursor at home,
written from the XTerm Control Sequences document (docs/SOURCES.md)
and ECMA-48; tests/mpx7-mux.d/screen.py reads PAX's screen back cell by
cell and says whether it is xterm's. SGR and GLYPH cases are read cell by
cell instead (screen.py says what each drew). An ANSWER case is a query
whose answer vtcases prints at its end (`QUERY NAME hex...|none`).
"""
import struct
import sys

E = "\x1b"
CSI = E + "["
ST = E + "\\"


def lines(*rows):
    """Rows written from the top left: each then CR LF but the last."""
    return "\r\n".join(rows)


SCREEN = [
    # B1: the alternate screen, saving the cursor, regions, insert and delete, erase.
    ("b1-alt-on", "main" + CSI + "?1049h" + "alt", ["    alt"], CSI + "?1049l"),
    ("b1-alt-off", "main" + CSI + "?1049h" + "alt" + CSI + "?1049l" + "!", ["main!"]),
    ("b1-alt-47", "main" + CSI + "?47h" + "alt" + CSI + "?47l", ["main"], CSI + "?47l" + CSI + "?1049l"),
    ("b1-decsc", "abc" + E + "7" + CSI + "3;5H" + "X" + E + "8" + "d", ["abcd", "", "    X"]),
    ("b1-scosc", "abc" + CSI + "s" + CSI + "3;5H" + "X" + CSI + "u" + "d", ["abcd", "", "    X"]),
    ("b1-stbm", lines("1", "2", "3", "4", "5", "6") + CSI + "2;4r" + CSI + "4;1H" + "\n" + CSI + "r", ["1", "3", "4", "", "5", "6"]),
    ("b1-ri", lines("1", "2", "3", "4") + CSI + "2;3r" + CSI + "2;1H" + E + "M" + CSI + "r", ["1", "", "2", "4"]),
    ("b1-il", lines("1", "2", "3", "4") + CSI + "2;1H" + CSI + "L", ["1", "", "2", "3", "4"]),
    ("b1-dl", lines("1", "2", "3", "4") + CSI + "2;1H" + CSI + "M", ["1", "3", "4", ""]),
    ("b1-il-region", lines("1", "2", "3", "4", "5") + CSI + "2;4r" + CSI + "2;1H" + CSI + "L" + CSI + "r", ["1", "", "2", "3", "5"]),
    ("b1-ich", "abcdef" + CSI + "1;3H" + CSI + "2@", ["ab  cdef"]),
    ("b1-dch", "abcdef" + CSI + "1;3H" + CSI + "2P", ["abef"]),
    ("b1-ech", "abcdef" + CSI + "1;3H" + CSI + "2X", ["ab  ef"]),
    ("b1-el0", "abcdef" + CSI + "1;3H" + CSI + "K", ["ab"]),
    ("b1-el1", "abcdef" + CSI + "1;3H" + CSI + "1K", ["   def"]),
    ("b1-el2", "abcdef" + CSI + "1;3H" + CSI + "2K", [""]),
    ("b1-ed0", lines("aaaa", "bbbb", "cccc") + CSI + "2;3H" + CSI + "J", ["aaaa", "bb", ""]),
    ("b1-ed1", lines("aaaa", "bbbb", "cccc") + CSI + "2;3H" + CSI + "1J", ["", "   b", "cccc"]),
    ("b1-ed2", lines("aaaa", "bbbb", "cccc") + CSI + "2;3H" + CSI + "2J", ["", "", ""]),
    ("b1-su", lines("1", "2", "3") + CSI + "S", ["2", "3", ""]),
    ("b1-sd", lines("1", "2", "3") + CSI + "T", ["", "1", "2"]),
    ("b1-rep", "a" + CSI + "3b", ["aaaa"]),
    ("b1-irm", "abc" + CSI + "1;1H" + CSI + "4h" + "X" + CSI + "4l", ["Xabc"]),
    ("b1-decom", CSI + "3;5r" + CSI + "?6h" + CSI + "1;1H" + "X" + CSI + "?6l" + CSI + "r", ["", "", "X"]),
    ("b1-nowrap", CSI + "?7l" + "a" * 160 + "XYZ" + CSI + "?7h", ["a" * 159 + "Z", ""]),
    ("b1-wrap", "a" * 160 + "XYZ", ["a" * 160, "XYZ"]),
    ("b1-tab", "a\tb" + CSI + "2;1H" + "c" + CSI + "I" + "d", ["a       b", "c       d"]),
    ("b1-cup-home", "abc" + CSI + "H" + "X", ["Xbc"]),
    ("b1-cha-vpa", CSI + "5G" + "X" + CSI + "3d" + "Y", ["    X", "", "     Y"]),
]

# B2: one screen, a line a rendition: the label, then `X` in it.
SGR = [
    ("plain", "0"), ("bold", "1"), ("dim", "2"), ("italic", "3"), ("underline", "4"), ("curly", "4:3"),
    ("double-underline", "21"), ("blink", "5"), ("reverse", "7"), ("hidden", "8"), ("strike", "9"),
    ("overline", "53"), ("underline-colour", "4;58;5;1"), ("red", "31"), ("bright-red", "91"),
    ("red-bg", "41"), ("bold-red", "1;31"), ("bold-then-22", "1;22"), ("256-196", "38;5;196"),
    ("256-46", "38;5;46"), ("256-21", "38;5;21"), ("256-244", "38;5;244"), ("256-bg-22", "48;5;22"),
    ("rgb-orange", "38;2;255;128;0"), ("rgb-navy", "38;2;10;10;200"), ("rgb-bg-teal", "48;2;0;128;128"),
    ("rgb-colon", "38:2::255:128:0"), ("fg-default", "31;39"), ("reverse-off", "7;27"),
]

# B3: code points, a line each: the label, then the characters.
GLYPH = [
    ("box-light", [0x2500, 0x2502, 0x250C, 0x2510, 0x2514, 0x2518, 0x251C, 0x2524, 0x252C, 0x2534, 0x253C]),
    ("box-heavy", [0x2501, 0x2503, 0x250F, 0x2513, 0x2517, 0x251B, 0x2523, 0x252B, 0x2533, 0x253B, 0x254B]),
    ("box-double", [0x2550, 0x2551, 0x2554, 0x2557, 0x255A, 0x255D, 0x2560, 0x2563, 0x2566, 0x2569, 0x256C]),
    ("box-round", [0x256D, 0x256E, 0x256F, 0x2570, 0x2574, 0x2575, 0x2576, 0x2577]),
    ("box-all", list(range(0x2500, 0x2580))),
    ("block", list(range(0x2580, 0x25A0))),
    ("braille", list(range(0x2800, 0x2900, 9))),
    ("powerline", [0xE0A0, 0xE0A1, 0xE0A2, 0xE0B0, 0xE0B1, 0xE0B2, 0xE0B3]),
    ("latin1", [0xE9, 0xF1, 0xFC, 0xA9, 0xB0]),
    ("arrows", [0x2190, 0x2191, 0x2192, 0x2193]),
    ("unknown", [0x1F600, 0x2603, 0x4E2D]),
]

# B3's widths and B4's answers: queries, each answered (or not) at the end.
ANSWER = [
    ("width-ascii", "\r\n" + "ab" + CSI + "6n"),
    ("width-cjk", "\r\n" + "a中b" + CSI + "6n"),
    ("width-combining", "\r\n" + "éx" + CSI + "6n"),
    ("width-emoji", "\r\n" + "a\U0001F600b" + CSI + "6n"),
    ("da1", CSI + "c"),
    ("da2", CSI + ">c"),
    ("da3", CSI + "=c"),
    ("dsr5", CSI + "5n"),
    ("cpr", CSI + "H" + CSI + "6n"),
    ("decxcpr", CSI + "?6n"),
    ("decrqm-2004", CSI + "?2004$p"),
    ("decrqm-1049", CSI + "?1049$p"),
    ("decrqm-25", CSI + "?25$p"),
    ("decrqm-1006", CSI + "?1006$p"),
    ("decrqm-1004", CSI + "?1004$p"),
    ("decrqm-irm", CSI + "4$p"),
    ("xtversion", CSI + ">0q"),
    ("osc10", E + "]10;?" + "\x07"),
    ("kitty-keys", CSI + "?u"),
    ("decrqss-sgr", E + "P$qm" + ST),
    ("xtgettcap", E + "P+q544e" + ST),
]

# B4's cursor and B6's strings: screens read cell by cell.
SCREEN += [
    ("b4-cursor-shown", "ab", ["ab"]),
    ("b4-cursor-hidden", "ab" + CSI + "?25l", ["ab"]),
    ("b4-decscusr-bar", CSI + "?25h" + CSI + "5 q" + "ab", ["ab"]),
    ("b4-decscusr-reset", CSI + "0 q" + "ab", ["ab"]),
    ("b5-modes", CSI + "?2004h" + CSI + "?1004h" + "ab" + CSI + "?2004l" + CSI + "?1004l", ["ab"]),
    ("b6-osc0", "a" + E + "]0;a title" + "\x07" + "b", ["ab"]),
    ("b6-osc2-st", "a" + E + "]2;a title" + ST + "b", ["ab"]),
    ("b6-osc52", "a" + E + "]52;c;aGVsbG8gd2FycmVu" + "\x07" + "b", ["ab"]),
    ("b6-osc52-long", "a" + E + "]52;c;" + "QUFB" * 300 + "\x07" + "b", ["ab"]),
    ("b6-osc8", "a" + E + "]8;;https://example.org/" + ST + "link" + E + "]8;;" + ST + "b", ["alinkb"]),
    ("b6-osc-unknown", "a" + E + "]777;notify;x;y" + "\x07" + "b", ["ab"]),
    ("b6-dcs", "a" + E + "P1$r0m" + ST + "b", ["ab"]),
    ("b6-dcs-tcap", "a" + E + "P+q544e" + ST + "b", ["ab"]),
    ("b6-apc", "a" + E + "_Gf=24,s=1,v=1;AAAA" + ST + "b", ["ab"]),
    ("b6-pm", "a" + E + "^private" + ST + "b", ["ab"]),
    ("b6-sos", "a" + E + "Xstring" + ST + "b", ["ab"]),
]


def sgr_screen():
    out = []
    for label, ps in SGR:
        out.append("%-18s" % label + CSI + ps + "m" + "X" + CSI + "0m")
    return lines(*out)


def glyph_screen():
    out = []
    for label, cps in GLYPH:
        out.append("%-11s" % label + "".join(chr(c) for c in cps))
    return lines(*out)


KEYS = [
    # B5: what each key sends at the console, typed at the PS/2 keyboard.
    ("ctrl-space", "ctrl-spc"), ("ctrl-at", "ctrl-shift-2"), ("ctrl-2", "ctrl-2"), ("ctrl-a", "ctrl-a"),
    ("alt-a", "alt-a"), ("esc", "esc"), ("up", "up"), ("shift-up", "shift-up"), ("alt-up", "alt-up"),
    ("ctrl-up", "ctrl-up"), ("ctrl-left", "ctrl-left"), ("ctrl-shift-up", "ctrl-shift-up"), ("home", "home"),
    ("end", "end"), ("pgup", "pgup"), ("insert", "insert"), ("delete", "delete"), ("f1", "f1"),
    ("shift-f1", "shift-f1"), ("ctrl-f1", "ctrl-f1"), ("alt-f1", "alt-f1"), ("f5", "f5"), ("f12", "f12"),
    ("shift-tab", "shift-tab"), ("tab", "tab"), ("backspace", "backspace"), ("ctrl-backspace", "ctrl-backspace"),
    ("enter", "ret"),
]


def records():
    rec = bytearray()

    def add(kind, name, data):
        nonlocal rec
        b = data.encode("utf-8") if isinstance(data, str) else data
        rec += kind + name.encode() + b"\0" + struct.pack("<I", len(b)) + b

    for case in SCREEN:
        add(b"s", case[0], case[1])
        if len(case) > 3:
            add(b"e", "", case[3])
    add(b"s", "b2-sgr", sgr_screen())
    add(b"s", "b3-glyphs", glyph_screen())
    for name, data in ANSWER:
        add(b"a", name, data)
    return bytes(rec)


def steps():
    out = ["#!ps2-session", "prompt 1 vtcases: ready", "key ret"]
    for name in [c[0] for c in SCREEN] + ["b2-sgr", "b3-glyphs"]:
        out += ["prompt 1 \\x1b]px59;%s\\x07" % name, "dump %s 0.5" % name, "key ret"]
    out += ["prompt 1 vtcases: done", "prompt 1 keys: ready", "pause 1"]
    for _, key in KEYS:
        out += ["key %s" % key, "pause 0.3", "key z", "pause 0.3"]
    out += ["key shift-q", "prompt 1 keys: done", "prompt 1 paint: "]
    return out


def main(argv):
    if argv[1:] == ["--list"]:
        for c in SCREEN:
            print("screen %s %r" % (c[0], c[2]))
        print("screen b2-sgr (%d renditions)" % len(SGR))
        print("screen b3-glyphs (%d lines)" % len(GLYPH))
        for name, _ in ANSWER:
            print("answer %s" % name)
        for name, key in KEYS:
            print("key %s %s" % (name, key))
        return 0
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    rec = records()
    if len(rec) > 65536:
        sys.stderr.write("cases.py: %d bytes of records, more than vtcases reads\n" % len(rec))
        return 1
    open(argv[1], "wb").write(rec)
    open(argv[2], "w").write("\n".join(steps()) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
