#!/usr/bin/env python3
"""cff2_wide_diff.py — the CFF2 wide-`blend` differential against fontTools (rekha 0.5.0).

Builds a variable CFF2 in memory, writes it out, and hands THE SAME BYTES to fontTools and to
rekha, comparing every decoded point. Sweeps five region counts x five `wght` settings x four
glyph shapes.

    python3 scripts/cff2_wide_diff.py            # needs fontTools; exits non-zero on any mismatch

WHY THE FONT LOOKS LIKE THIS. One ItemVariationData over N IDENTICAL regions (start 0, peak +1,
end +1), so at the axis maximum every region scalar is exactly 1 and a blended value is its default
plus the SUM of its deltas. A `blend` of nb values over N regions needs nb + nb*N operands RESIDENT
when the operator runs, which is what rekha's 48-entry argument stack could not hold before 0.5.0 —
the CFF2 chapter specifies 513. Measured at the 0.4.12 ceiling, 60 of the 100 glyph instances below
came back EMPTY, the default location included.

⚠ NOT A CI GATE. fontTools is not a dependency of this repo, exactly as with
`scripts/cff_stdenc.py verify`. Unlike rekha's other differentials this one needs no font corpus —
it builds its own input — so it is committed and anyone with fontTools can re-run it.

⛔ It compiles and runs a throwaway Cyrius program (build/, gitignored) that reads the font and
prints rekha's points. Run it from the repository root.
"""

import struct, sys, subprocess, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "build")
NREG = 16


def t2num(v):
    """Type 2 charstring integer."""
    if -107 <= v <= 107:
        return bytes([v + 139])
    if 108 <= v <= 1131:
        w = v - 108
        return bytes([(w >> 8) + 247, w & 255])
    if -1131 <= v <= -108:
        u = -v - 108
        return bytes([(u >> 8) + 251, u & 255])
    return b"\x1c" + struct.pack(">h", v)


def cs(*items):
    out = b""
    for it in items:
        out += t2num(it) if isinstance(it, int) else it
    return out


OP_RMOVETO = b"\x15"
OP_RLINETO = b"\x05"
OP_BLEND = b"\x10"


OP_RRCURVETO = b"\x08"


def blend(defaults, k, delta=1):
    """nb defaults then nb*k deltas then the count: nb + nb*k + 1 operands resident."""
    b = cs(*defaults)
    for _ in defaults:
        b += cs(*([delta] * k))
    return b + cs(len(defaults)) + OP_BLEND


def glyphs_for(k):
    """Every shape a wide blend has to survive, at region count k."""
    g = []
    # 0: a blended rmoveto (2 + 2k + 1) then a blended rlineto pair (4 + 4k + 1)
    g.append(blend([100, 200], k) + OP_RMOVETO + blend([10, 0, 0, 10], k) + OP_RLINETO)
    # 1: the WIDEST blend 513 allows at this k, as a run of rlineto steps
    nb = min(30, (512 - 1) // (k + 1))
    nb = nb - (nb % 2)
    g.append(cs(0, 0) + OP_RMOVETO + blend([1] * nb, k) + OP_RLINETO)
    # 2: a blended CUBIC — rrcurveto, which is where CFF control points are flagged 2
    g.append(cs(0, 0) + OP_RMOVETO + blend([10, 20, 30, 40, 50, 60], k) + OP_RRCURVETO)
    # 3: no blend at all. ⛔ This glyph must be byte-identical at every location.
    g.append(cs(5, 5) + OP_RMOVETO + cs(20, 0, 0, 20) + OP_RLINETO)
    return g


def index32(objs):
    """CFF2 INDEX: u32 count, offSize, offsets, data."""
    if not objs:
        return struct.pack(">I", 0)
    total = 1 + sum(len(o) for o in objs)
    osz = 1 if total <= 255 else (2 if total <= 65535 else 4)
    out = struct.pack(">I", len(objs)) + bytes([osz])
    acc = 1
    for o in objs + [b""]:
        out += acc.to_bytes(osz, "big")
        acc += len(o)
    # the sentinel above already wrote the final offset; drop its double-count
    out = out[: 5 + (len(objs) + 1) * osz]
    return out + b"".join(objs)


def dop(v):
    return b"\x1d" + struct.pack(">I", v)


def vstore(nreg):
    ivd_off = 12
    ivd_len = 6 + nreg * 2
    rl_off = ivd_off + ivd_len
    body = struct.pack(">HIH", 1, rl_off, 1) + struct.pack(">I", ivd_off)
    assert len(body) == ivd_off
    body += struct.pack(">HHH", 0, 0, nreg) + b"".join(struct.pack(">H", i) for i in range(nreg))
    assert len(body) == rl_off
    body += struct.pack(">HH", 1, nreg)
    for _ in range(nreg):
        body += struct.pack(">HHH", 0, 16384, 16384)    # start 0, peak +1, end +1
    return struct.pack(">H", len(body)) + body


def build_cff2(charstrings):
    top_len = 6 + 7 + 6                                  # CharStrings, FDArray, vstore
    hdr = 5
    p = hdr + top_len
    gsubrs = struct.pack(">I", 0)
    p += len(gsubrs)
    cs_at = p
    cs_idx = index32(charstrings)
    p += len(cs_idx)
    priv_at = p                                          # empty Private DICT
    fd = dop(0) + dop(priv_at) + b"\x12"                 # Private (size 0, offset)
    fdarray_at = p
    fdarray = index32([fd])
    p += len(fdarray)
    vs_at = p
    vs = vstore(NREG)
    p += len(vs)
    top = dop(cs_at) + b"\x11" + dop(fdarray_at) + b"\x0c\x24" + dop(vs_at) + b"\x18"
    assert len(top) == top_len, (len(top), top_len)
    return bytes([2, 0, hdr]) + struct.pack(">H", top_len) + top + gsubrs + cs_idx + fdarray + vs


def sfnt(tables):
    tags = sorted(tables)
    n = len(tags)
    pow2 = 1
    sel = 0
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


def make_font():
    ng = len(glyphs_for(NREG))
    head = bytearray(54)
    struct.pack_into(">I", head, 0, 0x00010000)
    struct.pack_into(">H", head, 18, 1000)               # unitsPerEm
    struct.pack_into(">h", head, 50, 0)                  # indexToLocFormat
    maxp = struct.pack(">IH", 0x00005000, ng)
    hhea = bytearray(36)
    struct.pack_into(">I", hhea, 0, 0x00010000)
    struct.pack_into(">H", hhea, 34, ng)
    hmtx = b"".join(struct.pack(">Hh", 500 + i, 0) for i in range(ng))
    post = struct.pack(">IIhhI", 0x00030000, 0, 0, 0, 0) + b"\0" * 16
    fvar = struct.pack(">HHHHHHHH", 1, 0, 16, 2, 1, 20, 0, 0)
    fvar += struct.pack(">4siiiHH", b"wght", 100 << 16, 400 << 16, 900 << 16, 0, 256)
    cff2 = build_cff2(glyphs_for(NREG))
    return sfnt({
        "head": bytes(head), "maxp": maxp, "hhea": bytes(hhea), "hmtx": hmtx,
        "post": post, "fvar": fvar, "CFF2": cff2,
    })


LOCATIONS = [100, 400, 550, 700, 900]

DUMPER = r'''# GENERATED by scratchpad/wide_cff2.py — not part of the repo. Prints rekha's decoded points for
# every glyph at every axis setting, for the fontTools differential.
include "programs/prelude.cyr"

fn sp(): i64 { syscall(1, 1, " ", 1); return 0; }
fn nl(): i64 { syscall(1, 1, "\n", 1); return 0; }

fn main(): i64 {
    alloc_init();
    var cap = 1048576;
    var buf = alloc(cap);
    var n = file_read_all("__PATH__", buf, cap);
    if (n <= 0) { syscall(1, 2, "read failed\n", 12); return 1; }
    var f = rekha_font_open(buf, n);
    if (f == 0) { syscall(1, 2, "open failed\n", 12); return 1; }
    var locs: i64[__NLOC__];
__LOCS__
    var li = 0;
    while (li < __NLOC__) {
        rekha_var_set_axis(f, 0, load64(&locs + li * 8) * 65536);
        var g = 0;
        while (g < __NG__) {
            var o = rekha_load_glyph(f, g);
            var np = rekha_outline_n_points(o);
            syscall(1, 1, "G", 1); sp(); fmt_int(load64(&locs + li * 8)); sp();
            fmt_int(g); sp(); fmt_int(np); nl();
            var i = 0;
            while (i < np) {
                syscall(1, 1, "P", 1); sp(); fmt_int(i); sp();
                fmt_int(load64(rekha_outline_xs(o) + i * 8)); sp();
                fmt_int(load64(rekha_outline_ys(o) + i * 8)); nl();
                i = i + 1;
            }
            g = g + 1;
        }
        li = li + 1;
    }
    return 0;
}

var exit_code = main();
syscall(60, exit_code);
'''


def rekha_points(path, ng):
    src = DUMPER.replace("__PATH__", path).replace("__NLOC__", str(len(LOCATIONS)))
    src = src.replace("__NG__", str(ng))
    src = src.replace("__LOCS__", "\n".join(
        "    store64(&locs + %d, %d);" % (i * 8, w) for i, w in enumerate(LOCATIONS)))
    prog = os.path.join(REPO, "build", "wide_diff.cyr")
    open(prog, "w").write(src)
    r = subprocess.run(["cyrius", "build", "build/wide_diff.cyr", "build/wide_diff"],
                       cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("dumper build failed")
    r = subprocess.run([os.path.join(REPO, "build", "wide_diff")], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("dumper run failed")
    out, cur = {}, None
    for line in r.stdout.splitlines():
        f = line.split()
        if f[0] == "G":
            cur = (int(f[1]), int(f[2]))
            out[cur] = []
        elif f[0] == "P":
            out[cur].append((int(f[2]), int(f[3])))
    return out


def fonttools_points(path, ng):
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import RecordingPen
    out = {}
    for w in LOCATIONS:
        font = TTFont(path)
        gs = font.getGlyphSet(location={"wght": w})
        order = font.getGlyphOrder()
        for g in range(ng):
            pen = RecordingPen()
            gs[order[g]].draw(pen)
            pts = []
            for op, args in pen.value:
                for pt in args:
                    if isinstance(pt, tuple):
                        pts.append((round(pt[0]), round(pt[1])))
            out[(w, g)] = pts
    return out


def run_one(nreg):
    global NREG
    NREG = nreg
    data = make_font()
    path = os.path.join(OUT, "wide%d.otf" % nreg)
    open(path, "wb").write(data)
    ng = len(glyphs_for(nreg))
    ft = fonttools_points(path, ng)
    rk = rekha_points(path, ng)
    total = same = 0
    bad = []
    for key in sorted(ft):
        a, b = ft[key], rk.get(key, [])
        if len(a) != len(b):
            bad.append("%s: fontTools %d points, rekha %d" % (key, len(a), len(b)))
            continue
        for i, (p, q) in enumerate(zip(a, b)):
            total += 1
            if p == q:
                same += 1
            else:
                bad.append("wght %d gid %d point %d: fontTools %s rekha %s" % (key + (i, p, q)))
    print("  %2d regions: %4d points over %2d glyph instances, %4d identical%s"
          % (nreg, total, len(ft), same, "" if not bad else "   <-- MISMATCHES"))
    for b in bad[:6]:
        print("      MISMATCH", b)
    return total, same, len(ft), bad


def main():
    os.makedirs(OUT, exist_ok=True)
    print("CFF2 wide-blend differential vs fontTools, at wght", LOCATIONS)
    T = S = I = 0
    allbad = []
    for nreg in (2, 8, 16, 31, 63):
        t, sm, inst, bad = run_one(nreg)
        T += t; S += sm; I += inst; allbad += bad
    print("TOTAL: %d points over %d glyph instances, %d identical, %d mismatched"
          % (T, I, S, len(allbad)))
    return 0 if (not allbad and T) else 1


if __name__ == "__main__":
    sys.exit(main())
