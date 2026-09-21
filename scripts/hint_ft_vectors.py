#!/usr/bin/env python3
"""FreeType's own hinted outlines of the embedded face, as the oracle for rekha's glyph zone (0.8.2).

⛔ THIS SCRIPT IS THE ONE PIECE OF EVIDENCE rekha CANNOT PRODUCE FOR ITSELF on a real font.
programs/hint_unit_vectors.cyr (scripts/hint_unit_vectors.py) pins every point instruction on a
synthetic glyph; this one runs Liberation Sans's actual glyph programs — fpgm, prep and all —
through the interpreter the world's hinted fonts were drawn against, and digests the result. Its
consumer is 0.8.2, the release that loads a glyph into zone 1 and answers a hinted outline; the
table it prints is transcribed into programs/hint_test.cyr then, the way face_test.cyr's constants
are, and not before.

FreeType is reached through scripts/ftshim.py: the CLASSIC interpreter (`GETINFO` 35), which is
what src/hint.cyr implements — the default since FreeType 2.7 is version 40, whose minimal
subpixel hinting suppresses every horizontal move (at 12 ppem it leaves the 'H' stem at x=420
where v35 puts it at 439) — and FT_LOAD_NO_AUTOHINT. The reference is FreeType 2.14.3; ftshim
refuses any other 2.x minor, because CI's Ubuntu ships 2.13.2 and its move arithmetic differs.

Every face is WARMED once at a throwaway ppem before anything is measured: FreeType runs `fpgm`
at the first size a face is hinted at, with that size's metrics (2.14.3, C2 B5), so a table whose
first row ran fpgm at 8 ppem would differ from one that started at 48 wherever fpgm asked MPPEM.
rekha does the same (D11: fpgm once, at the first size asked for); the consumer builds its first
context at WARM_PPEM before it compares anything.

No freetype-py, no fontTools. NOT run in CI. Modes:

    python3 scripts/hint_ft_vectors.py table            # the digests the suite will assert
    python3 scripts/hint_ft_vectors.py dump H 12        # every point, for debugging a mismatch
    python3 scripts/hint_ft_vectors.py sweep            # how much of the face hinting moves
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftshim  # noqa: E402

FACE = "fonts/LiberationSans-Regular.ttf"
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
M64 = 0xFFFFFFFFFFFFFFFF

# The characters the suite pins, chosen for what they exercise rather than for coverage:
# stems and a crossbar (H), a single stem (I l), curves (o e O), a diagonal (A W), a dot (i .),
# a descender (g j p), many points (m), and a digit with two counters (8).
CHARS = "HIloenAB08.,mWgjpi"
PPEMS = (8, 9, 11, 12, 13, 16, 18, 24, 32, 48)
WARM_PPEM = 64  # not in PPEMS: where fpgm runs, and where the consumer must start too
SWEEP_PPEM = 12


def fnv_u32(h, v):
    """The 32-bit-wide feed programs/face_test.cyr uses, in 64-bit FNV-1a."""
    v &= M64
    for i in range(4):
        h = ((h ^ ((v >> (i * 8)) & 255)) * FNV_PRIME) & M64
    return h


def digest(points):
    h = FNV_OFFSET
    for x, y in points:
        h = fnv_u32(h, x)
        h = fnv_u32(h, y)
    return h


def open_face():
    """The embedded face, warmed: its fpgm has run at WARM_PPEM before any row is measured."""
    face = ftshim.load_face(FACE)
    ftshim.hinted(face, WARM_PPEM, ftshim.char_index(face, "H"))
    return face


def cmd_dump(argv):
    ch = argv[0] if argv else "H"
    ppem = int(argv[1]) if len(argv) > 1 else 12
    face = open_face()
    gid = ftshim.char_index(face, ch)
    pts, tags, adv = ftshim.hinted(face, ppem, gid)
    raw, _, radv = ftshim.hinted(face, ppem, gid, hint=False)
    cts = ftshim.contours(face, ppem, gid)
    comp = " composite" if ftshim.is_composite(face, gid) else ""
    print(f"{ch!r} gid={gid}{comp} ppem={ppem} contours={cts} advance {radv} -> {adv} (26.6)")
    print(f"{'i':>4} {'on':>3} {'unhinted':>16} {'hinted':>16}   delta  tag")
    for i, (p, q) in enumerate(zip(raw, pts)):
        on = tags[i] & 1
        d = (q[0] - p[0], q[1] - p[1])
        mark = "   " if d == (0, 0) else " * "
        print(f"{i:>4} {on:>3} {str(p):>16} {str(q):>16}{mark}{str(d) if d != (0, 0) else '':<10} {tags[i]}")
    print(f"digest 0x{digest(pts):016x}")


def cmd_table(argv):
    face = open_face()
    print(f"# FreeType {ftshim.version_string()} interpreter-version {ftshim.INTERPRETER_VERSION}, {FACE}, "
          f"fpgm warmed at {WARM_PPEM} ppem")
    print(f"# {'ch':>3} {'gid':>5} {'ppem':>5} {'pts':>5} {'adv':>6}  digest")
    for ch in CHARS:
        gid = ftshim.char_index(face, ch)
        comp = "composite" if ftshim.is_composite(face, gid) else ""
        for ppem in PPEMS:
            pts, tags, adv = ftshim.hinted(face, ppem, gid)
            print(f"  {ch!r:>3} {gid:>5} {ppem:>5} {len(pts):>5} {adv:>6}  0x{digest(pts):016x} {comp}")


def cmd_sweep(argv):
    """How much of the face the oracle covers, split the way rekha will have to."""
    import collections

    face = open_face()
    n = face.num_glyphs
    kinds = collections.Counter()
    moved = 0
    for gid in range(n):
        try:
            pts, _, _ = ftshim.hinted(face, SWEEP_PPEM, gid)
            raw, _, _ = ftshim.hinted(face, SWEEP_PPEM, gid, hint=False)
        except ftshim.FTError:
            kinds["error"] += 1
            continue
        kinds["composite" if ftshim.is_composite(face, gid) else "simple"] += 1
        if pts != raw:
            moved += 1
    print(f"{FACE}: {dict(kinds)}, {moved} of {n} glyphs move under hinting at {SWEEP_PPEM} ppem")


def main():
    cmds = {"dump": cmd_dump, "table": cmd_table, "sweep": cmd_sweep}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        return 2
    return cmds[sys.argv[1]](sys.argv[2:]) or 0


if __name__ == "__main__":
    sys.exit(main())
