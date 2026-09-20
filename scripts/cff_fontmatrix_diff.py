#!/usr/bin/env python3
"""cff_fontmatrix_diff.py — is rekha's FontMatrix the one fontTools reads? (rekha 0.5.1)

Builds a CFF font per matrix, writes it out, and hands THE SAME BYTES to fontTools and to rekha.

    python3 scripts/cff_fontmatrix_diff.py        # needs fontTools; non-zero on any mismatch

WHAT IS COMPARED, AND WHAT THE REFERENCE ACTUALLY IS. fontTools parses the Top DICT and exposes
`cff[0].FontMatrix` as six floats; that parse — of the DICT **real-number** format, two nibbles a
byte with its own '.', 'E', 'E-' and '-' codes — is the risky half and the half fontTools is the
reference for. What fontTools does NOT do is apply the matrix: its CFF glyph set returns raw
charstring coordinates. So the affine fold is rekha's own, and this script models it (round
a x upem x 65536, accumulate at 32.32, round once, half up) to turn fontTools' matrix into the
points rekha must produce.

⭐ rekha is never asked for its matrix — there is no accessor and this does not add one. The test
glyph draws (0, 0), (1000, 0), (0, 1000), so the three decoded points ARE the matrix: p0 gives the
translation and p1, p2 give the two columns.

⚠ NOT A CI GATE: fontTools is not a dependency of this repo, as with `scripts/cff_stdenc.py
verify`. It needs no font corpus — it builds its own input — so it is committed and re-runnable.

⛔ Compiles and runs a throwaway Cyrius program under build/ (gitignored). Run from the repo root.
"""
import os
import struct
import subprocess
import sys
from decimal import Decimal, ROUND_HALF_UP

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "build")

# (label, [a, b, c, d, e, f] as written into the DICT, unitsPerEm)
CASES = [
    ("identity, dot form",      ["0.001", "0", "0", "0.001", "0", "0"], 1000),
    ("identity, exponent form", ["1E-3", "0", "0", "1E-3", "0", "0"], 1000),
    ("half scale",              ["0.0005", "0", "0", "0.0005", "0", "0"], 1000),
    ("1/1024, many digits",     ["0.0009765625", "0", "0", "0.0009765625", "0", "0"], 1024),
    ("negative d",              ["0.001", "0", "0", "-0.001", "0", "0"], 1000),
    ("skew c",                  ["0.001", "0", "0.0005", "0.001", "0", "0"], 1000),
    ("skew b, exponent",        ["1E-3", "2.5E-4", "0", "1E-3", "0", "0"], 1000),
    ("translation",             ["0.001", "0", "0", "0.001", "0.05", "-0.02"], 1000),
    ("upem 2048, matched",      ["0.00048828125", "0", "0", "0.00048828125", "0", "0"], 2048),
    ("upem 2048, 1/1000",       ["0.001", "0", "0", "0.001", "0", "0"], 2048),
    ("rotation-ish",            ["0.000866", "0.0005", "-0.0005", "0.000866", "0", "0"], 1000),
    ("tiny, 9 digits",          ["0.000999999", "0", "0", "0.001000001", "0", "0"], 1000),
]


def nibbles(text):
    """A DICT real: byte 30, then two nibbles a byte, terminated by f."""
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == ".":
            out.append(0xA)
        elif c == "E":
            if i + 1 < len(text) and text[i + 1] == "-":
                out.append(0xC)
                i += 1
            else:
                out.append(0xB)
        elif c == "-":
            out.append(0xE)
        else:
            out.append(int(c))
        i += 1
    out.append(0xF)
    if len(out) % 2:
        out.append(0xF)
    return b"\x1e" + bytes(out[i] * 16 + out[i + 1] for i in range(0, len(out), 2))


def t2num(v):
    if -107 <= v <= 107:
        return bytes([v + 139])
    if 108 <= v <= 1131:
        w = v - 108
        return bytes([(w >> 8) + 247, w & 255])
    if -1131 <= v <= -108:
        u = -v - 108
        return bytes([(u >> 8) + 251, u & 255])
    return b"\x1c" + struct.pack(">h", v)


def dop(v):
    return b"\x1d" + struct.pack(">I", v)


def index16(objs):
    """A CFF 1.0 INDEX: u16 count, offSize, offsets, data."""
    if not objs:
        return struct.pack(">H", 0)
    total = 1 + sum(len(o) for o in objs)
    osz = 1 if total <= 255 else (2 if total <= 65535 else 4)
    out = struct.pack(">H", len(objs)) + bytes([osz])
    acc = 1
    for o in objs + [b""]:
        out += acc.to_bytes(osz, "big")
        acc += len(o)
    out = out[: 3 + (len(objs) + 1) * osz]
    return out + b"".join(objs)


# 0 0 rmoveto  1000 0 rlineto  -1000 1000 rlineto  endchar
PROBE = (t2num(0) + t2num(0) + b"\x15"
         + t2num(1000) + t2num(0) + b"\x05"
         + t2num(-1000) + t2num(1000) + b"\x05"
         + b"\x0e")


def build_cff(matrix):
    fm = b"".join(nibbles(m) for m in matrix) + b"\x0c\x07"
    top_len = len(fm) + 6 + 11                       # FontMatrix, CharStrings, Private
    hdr = b"\x01\x00\x04\x04"
    name = index16([b"T"])
    strings = index16([])
    gsubrs = index16([])
    charstrings = index16([PROBE, PROBE])
    priv = dop(0) + b"\x14"                          # defaultWidthX 0
    # positions depend on the Top DICT INDEX, whose object length is known
    top_idx_len = len(index16([b"\0" * top_len]))
    at = len(hdr) + len(name) + top_idx_len + len(strings) + len(gsubrs)
    cs_at = at
    priv_at = cs_at + len(charstrings)
    top = fm + dop(cs_at) + b"\x11" + dop(len(priv)) + dop(priv_at) + b"\x12"
    assert len(top) == top_len, (len(top), top_len)
    return hdr + name + index16([top]) + strings + gsubrs + charstrings + priv


def sfnt(tables):
    tags = sorted(tables)
    n = len(tags)
    pow2, sel = 1, 0
    while pow2 * 2 <= n:
        pow2 *= 2
        sel += 1
    out = struct.pack(">4sHHHH", b"OTTO", n, pow2 * 16, sel, n * 16 - pow2 * 16)
    at = 12 + n * 16
    body = b""
    for t in tags:
        d = tables[t]
        out += struct.pack(">4sIII", t.encode(), 0, at, len(d))
        pad = (-len(d)) % 4
        body += d + b"\0" * pad
        at += len(d) + pad
    return out + body


def make_font(matrix, upem):
    ng = 2
    head = bytearray(54)
    struct.pack_into(">I", head, 0, 0x00010000)
    struct.pack_into(">H", head, 18, upem)
    maxp = struct.pack(">IH", 0x00005000, ng)
    hhea = bytearray(36)
    struct.pack_into(">I", hhea, 0, 0x00010000)
    struct.pack_into(">H", hhea, 34, ng)
    hmtx = b"".join(struct.pack(">Hh", 500, 0) for _ in range(ng))
    return sfnt({"head": bytes(head), "maxp": maxp, "hhea": bytes(hhea), "hmtx": hmtx,
                 "CFF ": build_cff(matrix)})


def half_up(x):
    return int(Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def expected_points(ft_matrix, upem):
    """fontTools' parsed matrix, folded and rounded the way rekha does."""
    m = [half_up(Decimal(repr(v)) * upem * 65536) for v in ft_matrix]
    out = []
    for x, y in ((0, 0), (1000, 0), (0, 1000)):
        fx, fy = x * 65536, y * 65536
        ox = half_up(Decimal(m[0] * fx + m[2] * fy + (m[4] << 16)) / Decimal(1 << 32))
        oy = half_up(Decimal(m[1] * fx + m[3] * fy + (m[5] << 16)) / Decimal(1 << 32))
        out.append((ox, oy))
    return out


DUMPER = r'''# GENERATED by scripts/cff_fontmatrix_diff.py — throwaway, under build/.
include "programs/prelude.cyr"

fn sp(): i64 { syscall(1, 1, " ", 1); return 0; }

fn main(): i64 {
    alloc_init();
    var cap = 65536;
    var buf = alloc(cap);
    var n = file_read_all("__PATH__", buf, cap);
    if (n <= 0) { syscall(1, 2, "read failed\n", 12); return 1; }
    var f = rekha_font_open(buf, n);
    if (f == 0) { syscall(1, 2, "open failed\n", 12); return 1; }
    var o = rekha_load_glyph(f, 0);
    var np = rekha_outline_n_points(o);
    fmt_int(np);
    var i = 0;
    while (i < np) {
        sp(); fmt_int(load64(rekha_outline_xs(o) + i * 8));
        sp(); fmt_int(load64(rekha_outline_ys(o) + i * 8));
        i = i + 1;
    }
    syscall(1, 1, "\n", 1);
    return 0;
}

var exit_code = main();
syscall(60, exit_code);
'''


def rekha_points(path):
    prog = os.path.join(OUT, "fm_diff.cyr")
    open(prog, "w").write(DUMPER.replace("__PATH__", path))
    r = subprocess.run(["cyrius", "build", "build/fm_diff.cyr", "build/fm_diff"],
                       cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("dumper build failed")
    r = subprocess.run([os.path.join(OUT, "fm_diff")], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("dumper run failed: " + r.stderr)
    f = r.stdout.split()
    n = int(f[0])
    return [(int(f[1 + 2 * i]), int(f[2 + 2 * i])) for i in range(n)]


def main():
    from fontTools.ttLib import TTFont
    os.makedirs(OUT, exist_ok=True)
    print("CFF FontMatrix differential vs fontTools")
    bad = 0
    for label, matrix, upem in CASES:
        path = os.path.join(OUT, "fm.otf")
        open(path, "wb").write(make_font(matrix, upem))
        ft = list(TTFont(path)["CFF "].cff[0].FontMatrix)
        want = expected_points(ft, upem)
        got = rekha_points(path)
        ok = got == want
        print("  %-24s upem %-5d fontTools %-42s %s"
              % (label, upem, "[" + ", ".join("%g" % v for v in ft) + "]",
                 "ok" if ok else "MISMATCH"))
        if not ok:
            print("      want %s" % (want,))
            print("      got  %s" % (got,))
            bad += 1
    print("%d of %d matrices agree" % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
