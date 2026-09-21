#!/usr/bin/env python3
"""Cross-check of scripts/hint_prep_vectors.py against libfreetype itself (rekha 0.8.1, group M).

    python3 scripts/hint_prep_xcheck.py        # from the repo root; prints one line per ppem, then
                                               # "<n> values compared, <m> mismatches"; exit 1 on any

WHAT THIS PROVES. programs/hint_test.cyr's group M pins what Liberation Sans's `fpgm` + `prep`
leave behind at six sizes — every control value, every storage slot, every twilight coordinate
and the graphics-state fields a glyph program inherits — from scripts/hint_prep_vectors.py, a
second interpreter written from the FreeType sources and NOT from src/hint.cyr. Two interpreters
written from the same sources can still share a misreading, so this script asks FreeType. It
loads fonts/LiberationSans-Regular.ttf through scripts/ftshim.py (FreeType 2.14.x, classic
interpreter v35, NO_AUTOHINT), REPLACES one simple glyph in memory with a degenerate 48-point
outline whose glyph program copies interpreter state onto its points — RCVT / RS / GC on the
twilight zone, then SCFS along x — and reads FT_Load_Glyph's outline back: the x of point k IS
cvt[base + k], storage[base + k], or twilight k's coordinate as FreeType holds them after ITS
fpgm and prep ran at that size. Four graphics-state fields are read the same way through their
observable effects: the control-value cut-in through MIAP[1] on a cvt entry written 100 away
from the point, the minimum distance through MDRP[01000] from a point to itself, the scan type
through the scan-mode bits FreeType writes into tags[0], and scan control through the
FT_OUTLINE_SMART_DROPOUTS flag it sets on the outline. Every value the second interpreter holds
after its own prep run at the same size must equal FreeType's, value for value: that is what
makes group M's "second-interpreter derived" pins FreeType's numbers by transitivity, and it is
the provenance programs/hint_test.cyr's header and hint_prep_vectors.py's docstring cite.

Only glyph bytes change; the font's fpgm, prep, cvt and maxp are untouched, so the fpgm and prep
FreeType runs are the real ones. FreeType ignores table checksums, which is why the copy needs no
checksum fix-up.

NOT RUN IN CI. CI's Ubuntu ships FreeType 2.13.2, which ftshim refuses (its prep arithmetic
differs from the 2.14.x rekha targets); run this by hand on a 2.14.x host whenever
hint_prep_vectors.py or the pins change. Python 3 stdlib only.
"""
import ctypes
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ftshim  # noqa: E402
import hint_prep_vectors as hp  # noqa: E402

FONT = os.path.join(HERE, "..", "fonts", "LiberationSans-Regular.ttf")
PPEMS = [8, 12, 16, 24, 48, 100]
NPTS = 48  # points in the replacement glyph: one batch of cvt / storage / twilight values
FT_OUTLINE_SMART_DROPOUTS = 0x10  # ftimage.h; set by TT_Hint_Glyph when scan control is on


# ----------------------------------------------------------------------------------------------
# The font: find a simple glyph with room for the program, and replace it
# ----------------------------------------------------------------------------------------------
def tables(data):
    n = struct.unpack(">H", data[4:6])[0]
    t = {}
    for i in range(n):
        off = 12 + 16 * i
        tag = data[off : off + 4].decode("latin1")
        toff, tlen = struct.unpack(">II", data[off + 8 : off + 16])
        t[tag] = (toff, tlen)
    return t


def pick_glyph(data, t):
    """The first simple glyph whose glyf record is at least 700 bytes: enough room for the
    longest program here. Answers (gid, offset of its record, the record's length, its lsb)."""
    head = data[t["head"][0] : t["head"][0] + 54]
    fmt = struct.unpack(">h", head[50:52])[0]
    loca_off = t["loca"][0]
    n = struct.unpack(">H", data[t["maxp"][0] + 4 : t["maxp"][0] + 6])[0]
    if fmt == 0:
        offs = [2 * v for v in struct.unpack(">%dH" % (n + 1), data[loca_off : loca_off + 2 * (n + 1)])]
    else:
        offs = list(struct.unpack(">%dI" % (n + 1), data[loca_off : loca_off + 4 * (n + 1)]))
    glyf = t["glyf"][0]
    nhm = struct.unpack(">H", data[t["hhea"][0] + 34 : t["hhea"][0] + 36])[0]
    hmtx = t["hmtx"][0]
    for g in range(n):
        ln = offs[g + 1] - offs[g]
        if ln < 700:
            continue
        nc = struct.unpack(">h", data[glyf + offs[g] : glyf + offs[g] + 2])[0]
        if nc <= 0:
            continue
        k = min(g, nhm - 1)
        lsb = struct.unpack(">h", data[hmtx + 4 * k + 2 : hmtx + 4 * k + 4])[0]
        return g, glyf + offs[g], ln, lsb
    sys.exit("no simple glyph with 700 bytes of room in %s" % FONT)


def glyph_bytes(xmin, instr, room):
    """A one-contour glyph of NPTS points, all at (0, 0) as a single repeated-flag run (flag 0x39:
    on-curve, x and y 'same', repeat NPTS - 1 more times), carrying `instr`, padded to `room`."""
    hdr = struct.pack(">hhhhh", 1, xmin, 0, xmin + 100, 100)
    body = hdr + struct.pack(">H", NPTS - 1) + struct.pack(">H", len(instr)) + instr + bytes([0x39, NPTS - 1])
    assert len(body) <= room, (len(body), room)
    return body + bytes(room - len(body))


# ----------------------------------------------------------------------------------------------
# The probe programs (raw opcodes: 0x01 SVTCA[x], 0x00 SVTCA[y], 0x45 RCVT, 0x43 RS, 0x48 SCFS,
# 0x46 GC[0], 0x15 SZP2, 0x23 SWAP, 0x44 WCVTP, 0x3F MIAP[1], 0x10 SRP0, 0xC8 MDRP[01000])
# ----------------------------------------------------------------------------------------------
def pushb(*vals):
    assert 1 <= len(vals) <= 8 and all(0 <= v < 256 for v in vals)
    return bytes([0xB0 + len(vals) - 1]) + bytes(vals)


def pushw(*vals):
    return bytes([0xB8 + len(vals) - 1]) + b"".join(struct.pack(">h", v) for v in vals)


def prog_cvt(base, count):
    """point k <- RCVT (base + k), along x."""
    p = b"\x01"
    for k in range(count):
        p += pushb(k) + pushw(base + k) + b"\x45\x48"
    return p


def prog_storage(base, count):
    """point k <- RS (base + k), along x."""
    p = b"\x01"
    for k in range(count):
        p += pushb(k, base + k) + b"\x43\x48"
    return p


def prog_twilight(n):
    """point i <- twilight i's x (GC[0] with zp2 = 0, SCFS with zp2 = 1), point n + i <- its y."""
    p = b""
    for axis, op in ((0, b"\x01"), (1, b"\x00")):
        p += op
        for i in range(n):
            k = axis * n + i
            p += pushb(0) + b"\x15" + pushb(i) + b"\x46" + pushb(1) + b"\x15" + pushb(k) + b"\x23\x48"
    return p


def prog_gs():
    """WCVTP 200 <- 100 then MIAP[1] point 0 with cvt 200: 128 when the cut-in is >= 100, else 0
    (the point sits at 0). WCVTP 200 <- 60 then MIAP[1] point 1: 64 either way, a control. SRP0 5,
    MDRP[01000] point 6: a zero distance lifted to the minimum distance."""
    return (b"\x01" + pushb(200, 100) + b"\x44" + pushb(0, 200) + b"\x3F"
            + pushb(200, 60) + b"\x44" + pushb(1, 200) + b"\x3F"
            + pushb(5) + b"\x10" + pushb(6) + b"\xC8")


# ----------------------------------------------------------------------------------------------
# FreeType's side
# ----------------------------------------------------------------------------------------------
def load_patched(data, goff, room, lsb, ppem, gid, instr):
    """FT_Load_Glyph of the replaced glyph on a fresh memory face: (points, tags, outline flags)."""
    buf = data[:goff] + glyph_bytes(lsb, instr, room) + data[goff + room :]
    face = ftshim.load_face(buf)
    try:
        points, tags, _, _ = ftshim.load_glyph(face, ppem, gid, 0)
        slot = ctypes.cast(face.rec.glyph, ctypes.POINTER(ftshim.FT_GlyphSlotRec)).contents
        flags = slot.outline.flags
    finally:
        ftshim.done(face)
    assert len(points) == NPTS, len(points)
    return points, tags, flags


def main():
    data = open(FONT, "rb").read()
    t = tables(data)
    gid, goff, room, lsb = pick_glyph(data, t)
    face = hp.Face(data)
    it = hp.Interp(face, PPEMS[0])
    it.run_fpgm()
    compared = mismatches = 0

    def run(ppem, instr):
        return load_patched(data, goff, room, lsb, ppem, gid, instr)

    for ppem in PPEMS:
        it.set_size(ppem)
        err = it.run_prep()
        assert err is None, "hint_prep_vectors: prep failed at %d ppem: %s" % (ppem, err)
        got_cvt = []
        for base in range(0, it.cvt_size, NPTS):
            cnt = min(NPTS, it.cvt_size - base)
            pts, _, _ = run(ppem, prog_cvt(base, cnt))
            got_cvt += [pts[k][0] for k in range(cnt)]
        got_st = []
        for base in range(0, it.store_size, NPTS):
            cnt = min(NPTS, it.store_size - base)
            pts, _, _ = run(ppem, prog_storage(base, cnt))
            got_st += [pts[k][0] for k in range(cnt)]
        n = face.max_twilight
        assert 2 * n <= NPTS, n
        pts, _, _ = run(ppem, prog_twilight(n))
        got_tw = [pts[k][0] for k in range(n)] + [pts[n + k][1] for k in range(n)]
        pts, tags, flags = run(ppem, prog_gs())
        exp_tw = hp.twilight_values(it)
        gs = it.size_gs
        d_cvt = [i for i in range(it.cvt_size) if got_cvt[i] != it.cvt[i]]
        d_st = [i for i in range(it.store_size) if got_st[i] != it.storage[i]]
        d_tw = [i for i in range(2 * n) if got_tw[i] != exp_tw[i]]
        cutin_ok = pts[0][0] == (128 if gs.control_value_cutin >= 100 else 0) and pts[1][0] == 64
        mind_ok = pts[6][0] == gs.minimum_distance
        scan_ok = ((tags[0] >> 5) & 7) == gs.scan_type and bool(tags[0] & 4)
        smart = bool(flags & FT_OUTLINE_SMART_DROPOUTS)
        sc_ok = smart == (gs.scan_control == 1 and gs.scan_type == 5)
        compared += it.cvt_size + it.store_size + 2 * n + 4
        bad = len(d_cvt) + len(d_st) + len(d_tw) + (not cutin_ok) + (not mind_ok) + (not scan_ok) + (not sc_ok)
        mismatches += bad
        print("ppem %-4d cvt %s  storage %s  twilight %s  cutin(%d) %s  mindist(%d) %s  scantype(%d) %s  "
              "scancontrol(%d) %s  ft cvt digest 0x%016x"
              % (ppem,
                 "OK" if not d_cvt else "DIFF %s" % d_cvt[:10],
                 "OK" if not d_st else "DIFF %s" % d_st[:10],
                 "OK" if not d_tw else "DIFF %s" % d_tw[:10],
                 gs.control_value_cutin, "OK" if cutin_ok else "DIFF %s" % pts[:2],
                 gs.minimum_distance, "OK" if mind_ok else "DIFF %d" % pts[6][0],
                 gs.scan_type, "OK" if scan_ok else "DIFF tags0=%d" % tags[0],
                 gs.scan_control, "OK" if sc_ok else "DIFF flags=%d" % flags,
                 hp.digest(got_cvt)))
    print("glyph %d of %s replaced (%d bytes of room, lsb %d); FreeType %s"
          % (gid, os.path.relpath(FONT), room, lsb, ftshim.version_string()))
    print("%d values compared, %d mismatches" % (compared, mismatches))
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
