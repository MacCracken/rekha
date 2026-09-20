#!/usr/bin/env python3
"""metrics_var_diff.py — HVAR and MVAR against fontTools' own instancer (0.6.0, 0.6.1, 0.6.4).

Builds a two-axis variable font with HVAR (a DeltaSetIndexMap over two ItemVariationDatas) and
MVAR, writes it out, and hands THE SAME BYTES to both:

  * fontTools — `varLib.instancer.instantiateVariableFont` pins the axes and REWRITES hmtx from
    HVAR and hhea from MVAR, then drops both tables. So this is a genuine two-implementation
    comparison: fontTools applies the variation itself, it is not merely parsing.
  * rekha — `rekha_var_set_axis` then `rekha_advance_width` and the OS/2 accessors.

⛔ hhea AND OS/2 CARRY DIFFERENT NUMBERS HERE, DELIBERATELY. MVAR's `hasc` / `hdsc` / `hlgp` target
OS/2's sTypo trio, NOT hhea's ascender / descender / lineGap — MVAR has no tag for those at all.
rekha 0.6.0 put them on hhea and this script did not catch it, because its fixture set the two sets
EQUAL: every wrong answer was also a right one. It is also the case fontTools' own
`verticalMetricsKeptInSync` heuristic papers over, by copying an OS/2 change back to hhea when the
two started equal. With the two different, fontTools leaves hhea alone and so must rekha, and the
last three columns below check exactly that.

    python3 scripts/metrics_var_diff.py           # needs fontTools; non-zero on any mismatch

⚠ NOT A CI GATE: fontTools is not a dependency of this repo, as with `scripts/cff_stdenc.py
verify`. It needs no font corpus — it builds its own input — so it is committed and re-runnable.

⛔ Compiles and runs a throwaway Cyrius program under build/ (gitignored). Run from the repo root.
"""
import os
import struct
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "build")

NG = 8
UPEM = 1000
ADV = [500 + 37 * i for i in range(NG)]
ASC, DSC, LGP = 800, -200, 90               # hhea — has NO MVAR tag and must not move
TASC, TDSC, TLGP = 750, -250, 0             # OS/2 sTypo — deliberately not hhea's
WASC, WDSC = 900, 300                       # OS/2 usWin
XHGT, CPHT = 500, 700
STRS, STRO = 50, 260
SUB = [70, 65, 0, 75]                       # OS/2 ySubscript X/Y size, X/Y offset
SUP = [72, 68, 0, 480]                      # OS/2 ySuperscript X/Y size, X/Y offset
CRS, CRN, COF = 1, 0, 0                     # hhea caretSlopeRise / Run / Offset
UNDO, UNDS = -75, 50                        # post underlinePosition / underlineThickness

# Two axes, so every region scalar is a product of two tents rather than one.
AXES = [(b"wght", 100, 400, 900), (b"wdth", 50, 100, 200)]

# (wght peak triple, wdth peak triple) in F2Dot14, as (start, peak, end) per axis
REGIONS = [
    ((0, 16384, 16384), (0, 0, 0)),             # wght up; wdth unconstrained
    ((-16384, -16384, 0), (0, 0, 0)),           # wght down (F2Dot14 is SIGNED here)
    ((0, 0, 0), (0, 16384, 16384)),             # wdth up
    ((0, 16384, 16384), (0, 16384, 16384)),     # both up — the cross term
]

# The rekha accessor for each MVAR field, in the same keying as MVAR_FIELDS.
REKHA_ACCESSOR = {
    b"cpht": "rekha_cap_height",           b"hasc": "rekha_typo_ascender",
    b"hcla": "rekha_win_ascent",           b"hcld": "rekha_win_descent",
    b"hcof": "rekha_caret_offset",         b"hcrn": "rekha_caret_slope_run",
    b"hcrs": "rekha_caret_slope_rise",     b"hdsc": "rekha_typo_descender",
    b"hlgp": "rekha_typo_line_gap",        b"sbxo": "rekha_subscript_x_offset",
    b"sbxs": "rekha_subscript_x_size",     b"sbyo": "rekha_subscript_y_offset",
    b"sbys": "rekha_subscript_y_size",     b"spxo": "rekha_superscript_x_offset",
    b"spxs": "rekha_superscript_x_size",   b"spyo": "rekha_superscript_y_offset",
    b"spys": "rekha_superscript_y_size",   b"stro": "rekha_strikeout_position",
    b"strs": "rekha_strikeout_size",       b"undo": "rekha_underline_position",
    b"unds": "rekha_underline_thickness",  b"xhgt": "rekha_x_height",
}

LOCATIONS = [
    {"wght": 400, "wdth": 100},
    {"wght": 900, "wdth": 100},
    {"wght": 100, "wdth": 100},
    {"wght": 400, "wdth": 200},
    {"wght": 900, "wdth": 200},
    {"wght": 650, "wdth": 150},
    {"wght": 100, "wdth": 50},
    {"wght": 775, "wdth": 175},
]


def ivs(rows_per_data, long_words):
    """An ItemVariationStore: one region list, one ItemVariationData per entry of rows_per_data."""
    nreg = len(REGIONS)
    ivds = []
    for rows in rows_per_data:
        ric = nreg
        word = ric if long_words else 1
        wsz, ssz = (4, 2) if long_words else (2, 1)
        body = struct.pack(">HHH", len(rows), word | (0x8000 if long_words else 0), ric)
        body += b"".join(struct.pack(">H", i) for i in range(ric))
        for row in rows:
            for i, d in enumerate(row):
                if i < word:
                    body += struct.pack(">i", d) if wsz == 4 else struct.pack(">h", d)
                else:
                    body += struct.pack(">h", d) if ssz == 2 else struct.pack(">b", d)
        ivds.append(body)
    rlist = struct.pack(">HH", len(AXES), nreg)
    for reg in REGIONS:
        for tri in reg:
            rlist += struct.pack(">hhh", *tri)
    hdr = 8 + 4 * len(ivds)
    offs, at = [], hdr
    for b in ivds:
        offs.append(at)
        at += len(b)
    out = struct.pack(">HIH", 1, at, len(ivds)) + b"".join(struct.pack(">I", o) for o in offs)
    assert len(out) == hdr
    return out + b"".join(ivds) + rlist


def dsim(entries, inner_bits, esz):
    """DeltaSetIndexMap format 0."""
    ef = ((esz - 1) << 4) | (inner_bits - 1)
    out = struct.pack(">BBH", 0, ef, len(entries))
    for outer, inner in entries:
        out += ((outer << inner_bits) | inner).to_bytes(esz, "big")
    return out


# glyph i takes IVD (i % 2), row (i // 2)
HVAR_ROWS = [
    [[40, -20, 15, 7], [80, -30, 25, 11], [120, -40, 35, 13], [160, -50, 45, 17]],
    [[-40, 20, -15, -7], [-80, 30, -25, -11], [-120, 40, -35, -13], [-160, 50, -45, -17]],
]
HVAR_MAP = [(i % 2, i // 2) for i in range(NG)]

# ⭐ EVERY MVAR TAG rekha CAN LAND, and as of 0.6.4 that is all of them but the four `vhea` ones.
# Each entry is (tag, the fontTools object and attribute it targets, the deltas over the four
# regions). The records are SORTED BY TAG below, which the spec requires.
MVAR_FIELDS = [
    (b"cpht", "OS/2", "sCapHeight", [35, -12, 9, 4]),
    (b"hasc", "OS/2", "sTypoAscender", [30, -10, 12, 5]),
    (b"hcla", "OS/2", "usWinAscent", [40, -14, 11, 6]),
    (b"hcld", "OS/2", "usWinDescent", [15, -6, 5, 2]),
    (b"hcof", "hhea", "caretOffset", [3, -1, 2, 1]),
    (b"hcrn", "hhea", "caretSlopeRun", [7, -3, 4, 2]),
    (b"hcrs", "hhea", "caretSlopeRise", [2, -1, 1, 1]),
    (b"hdsc", "OS/2", "sTypoDescender", [-20, 8, -9, -4]),
    (b"hlgp", "OS/2", "sTypoLineGap", [10, -5, 6, 2]),
    (b"sbxo", "OS/2", "ySubscriptXOffset", [4, -2, 2, 1]),
    (b"sbxs", "OS/2", "ySubscriptXSize", [9, -4, 5, 2]),
    (b"sbyo", "OS/2", "ySubscriptYOffset", [6, -3, 3, 1]),
    (b"sbys", "OS/2", "ySubscriptYSize", [8, -3, 4, 2]),
    (b"spxo", "OS/2", "ySuperscriptXOffset", [5, -2, 3, 1]),
    (b"spxs", "OS/2", "ySuperscriptXSize", [11, -5, 6, 3]),
    (b"spyo", "OS/2", "ySuperscriptYOffset", [14, -6, 7, 3]),
    (b"spys", "OS/2", "ySuperscriptYSize", [13, -5, 7, 3]),
    (b"stro", "OS/2", "yStrikeoutPosition", [12, -4, 7, 3]),
    (b"strs", "OS/2", "yStrikeoutSize", [5, -2, 3, 1]),
    (b"undo", "post", "underlinePosition", [-9, 4, -5, -2]),
    (b"unds", "post", "underlineThickness", [6, -2, 3, 1]),
    (b"xhgt", "OS/2", "sxHeight", [25, -9, 8, 3]),
]
MVAR_FIELDS.sort(key=lambda e: e[0])
MVAR_TAGS = [e[0] for e in MVAR_FIELDS]
MVAR_ROWS = [[e[3] for e in MVAR_FIELDS]]


def build_hvar():
    m = dsim(HVAR_MAP, 4, 2)
    store = ivs(HVAR_ROWS, long_words=True)
    return struct.pack(">HHIIII", 1, 0, 20 + len(m), 20, 0, 0) + m + store


def build_mvar():
    store = ivs(MVAR_ROWS, long_words=False)
    recs = b"".join(struct.pack(">4sHH", t, 0, i) for i, t in enumerate(MVAR_TAGS))
    ivso = 12 + len(recs)
    return struct.pack(">HHHHHH", 1, 0, 0, 8, len(MVAR_TAGS), ivso) + recs + store


def build_fvar():
    out = struct.pack(">HHHHHHHH", 1, 0, 16, 2, len(AXES), 20, 0, 0)
    for i, (tag, lo, df, hi) in enumerate(AXES):
        out += struct.pack(">4siiiHH", tag, lo << 16, df << 16, hi << 16, 0, 256 + i)
    return out


def build_name():
    """A minimal name table — fontTools' instancer prunes unused names and wants one to prune.
    ⚠ rekha does not read `name` either (roadmap, 0.6.x); this is scaffolding for the reference."""
    recs = [(3, 1, 0x409, i, "R") for i in (1, 2, 256, 257)]
    hdr = struct.pack(">HHH", 0, len(recs), 6 + 12 * len(recs))
    data, body = b"", b""
    for pid, eid, lid, nid, txt in recs:
        enc = txt.encode("utf-16-be")
        hdr += struct.pack(">HHHHHH", pid, eid, lid, nid, len(enc), len(data))
        data += enc
    return hdr + data


def sfnt(tables):
    tags = sorted(tables)
    n = len(tags)
    pow2, sel = 1, 0
    while pow2 * 2 <= n:
        pow2 *= 2
        sel += 1
    out = struct.pack(">IHHHH", 0x00010000, n, pow2 * 16, sel, n * 16 - pow2 * 16)
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
    head = bytearray(54)
    struct.pack_into(">I", head, 0, 0x00010000)
    struct.pack_into(">H", head, 18, UPEM)
    struct.pack_into(">h", head, 50, 1)                 # long loca
    maxp = struct.pack(">IH", 0x00010000, NG) + b"\0" * 26
    hhea = bytearray(36)
    struct.pack_into(">I", hhea, 0, 0x00010000)
    struct.pack_into(">hhh", hhea, 4, ASC, DSC, LGP)
    struct.pack_into(">hhh", hhea, 18, CRS, CRN, COF)      # the caret, which DOES vary
    struct.pack_into(">H", hhea, 34, NG)
    post = struct.pack(">IIhhI", 0x00030000, 0, UNDO, UNDS, 0) + b"\0" * 16
    hmtx = b"".join(struct.pack(">Hh", a, 0) for a in ADV)
    loca = b"".join(struct.pack(">I", 0) for _ in range(NG + 1))
    # ⭐ OS/2 IS THE POINT OF THE FIXTURE as of 0.6.1: every MVAR tag but the caret ones lands on
    # one of its fields, and its sTypo trio is deliberately not hhea's so a wrong target shows.
    os2 = bytearray(96)
    struct.pack_into(">H", os2, 0, 4)
    struct.pack_into(">HH", os2, 4, 700, 3)                # usWeightClass / usWidthClass
    struct.pack_into(">hh", os2, 26, STRS, STRO)           # yStrikeout size / position
    struct.pack_into(">hhhh", os2, 10, SUB[0], SUB[1], SUB[2], SUB[3])
    struct.pack_into(">hhhh", os2, 18, SUP[0], SUP[1], SUP[2], SUP[3])
    struct.pack_into(">hhh", os2, 68, TASC, TDSC, TLGP)    # sTypoAscender / Descender / LineGap
    struct.pack_into(">HH", os2, 74, WASC, WDSC)           # usWinAscent / usWinDescent
    struct.pack_into(">hh", os2, 86, XHGT, CPHT)           # sxHeight / sCapHeight
    return sfnt({"head": bytes(head), "maxp": maxp, "hhea": bytes(hhea), "hmtx": hmtx,
                 "loca": loca, "glyf": b"", "post": post, "OS/2": bytes(os2),
                 "name": build_name(),
                 "fvar": build_fvar(), "HVAR": build_hvar(), "MVAR": build_mvar()})


DUMPER = r'''# GENERATED by scripts/metrics_var_diff.py — throwaway, under build/.
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
    var locs: i64[__NLOC2__];
__LOCS__
    var li = 0;
    while (li < __NLOC__) {
        rekha_var_set_axis(f, 0, load64(&locs + li * 16) * 65536);
        rekha_var_set_axis(f, 1, load64(&locs + li * 16 + 8) * 65536);
__FIELDS__
        fmt_int(rekha_ascender(f)); sp();
        fmt_int(rekha_descender(f)); sp();
        fmt_int(rekha_line_gap(f));
        var g = 0;
        while (g < __NG__) {
            sp(); fmt_int(rekha_advance_width(f, g));
            g = g + 1;
        }
        syscall(1, 1, "\n", 1);
        li = li + 1;
    }
    return 0;
}

var exit_code = main();
syscall(60, exit_code);
'''


def rekha_metrics(path):
    src = (DUMPER.replace("__PATH__", path)
           .replace("__NLOC2__", str(len(LOCATIONS) * 2))
           .replace("__NLOC__", str(len(LOCATIONS)))
           .replace("__NG__", str(NG))
           .replace("__FIELDS__", "\n".join(
               "        fmt_int(%s(f)); sp();" % REKHA_ACCESSOR[e[0]] for e in MVAR_FIELDS))
           .replace("__LOCS__", "\n".join(
               "    store64(&locs + %d, %d);\n    store64(&locs + %d, %d);"
               % (i * 16, loc["wght"], i * 16 + 8, loc["wdth"])
               for i, loc in enumerate(LOCATIONS))))
    open(os.path.join(OUT, "mv_diff.cyr"), "w").write(src)
    r = subprocess.run(["cyrius", "build", "build/mv_diff.cyr", "build/mv_diff"],
                       cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit("dumper build failed")
    r = subprocess.run([os.path.join(OUT, "mv_diff")], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("dumper run failed: " + r.stderr)
    return [[int(x) for x in line.split()] for line in r.stdout.strip().splitlines()]


def fonttools_metrics(path):
    """Two fontTools routes, because it uses two itself.

    MVAR — `instantiateVariableFont` pins the axes and REWRITES hhea from MVAR, then drops the
    table. That is fontTools applying the variation end to end.

    HVAR — the instancer does NOT go through HVAR for a `glyf` font: it bakes advances out of
    gvar's PHANTOM POINTS and treats HVAR as a lookaside to be dropped. This font has no gvar (it
    is a metrics fixture), so the instancer would report the unvaried advances and prove nothing.
    So the advance side uses fontTools' own `VarStoreInstancer` — the same store evaluator every
    other part of fontTools calls — over the same HVAR bytes, through the same DeltaSetIndexMap.
    """
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from fontTools.varLib.varStore import VarStoreInstancer
    from fontTools.varLib.models import normalizeLocation
    from fontTools.misc.roundTools import otRound

    base = TTFont(path)
    limits = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in base["fvar"].axes}
    hvar = base["HVAR"].table
    amap = hvar.AdvWidthMap
    order = base.getGlyphOrder()

    rows = []
    for loc in LOCATIONS:
        f = instancer.instantiateVariableFont(TTFont(path), loc, inplace=False,
                                              updateFontNames=False)
        h, o = f["hhea"], f["OS/2"]
        inst = VarStoreInstancer(hvar.VarStore, base["fvar"].axes, normalizeLocation(loc, limits))
        advances = []
        for g in range(NG):
            if amap is not None:
                varidx = amap.mapping[order[g]]
            else:
                varidx = g
            advances.append(ADV[g] + otRound(inst[varidx]))
        tabs = {"OS/2": o, "hhea": h, "post": f["post"]}
        # every varying field, in the order the dumper prints them, then the three hhea vertical
        # metrics that must NOT move, then the advances
        vals = [getattr(tabs[t], a) for _, t, a, _ in MVAR_FIELDS]
        rows.append(vals + [h.ascender, h.descender, h.lineGap] + advances)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "metvar.ttf")
    open(path, "wb").write(make_font())
    ft = fonttools_metrics(path)
    rk = rekha_metrics(path)
    print("HVAR / MVAR vs fontTools — %d locations x (%d MVAR fields + 3 unvarying hhea + %d "
          "advances)" % (len(LOCATIONS), len(MVAR_FIELDS), NG))
    total = same = 0
    bad = []
    for i, loc in enumerate(LOCATIONS):
        a, b = ft[i], rk[i] if i < len(rk) else []
        tag = "wght %-4d wdth %-4d" % (loc["wght"], loc["wdth"])
        if len(a) != len(b):
            bad.append("%s: fontTools %d values, rekha %d" % (tag, len(a), len(b)))
            continue
        n_ok = sum(1 for p, q in zip(a, b) if p == q)
        total += len(a)
        same += n_ok
        mark = "ok" if n_ok == len(a) else "MISMATCH"
        print("  %s  %2d/%2d  %s" % (tag, n_ok, len(a), mark))
        if n_ok != len(a):
            bad.append("%s: fontTools %s rekha %s" % (tag, a, b))
    print("%d of %d metric values identical" % (same, total))
    for b in bad[:8]:
        print("  ", b)
    return 0 if (not bad and total) else 1


if __name__ == "__main__":
    sys.exit(main())
