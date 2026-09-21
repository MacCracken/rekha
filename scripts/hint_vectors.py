#!/usr/bin/env python3
"""Independent oracle for programs/hint_test.cyr's real-face constants (rekha 0.8.0).

Every number this prints is computed from fonts/LiberationSans-Regular.ttf by a decoder that
shares no code with src/hint.cyr:

  * the `fpgm` top level is walked here in Python — the instruction lengths, the FDEF/ENDF scan
    and the push stack are re-implemented, so "71 functions, these numbers, an empty stack" is
    not rekha agreeing with itself;
  * the control values are scaled with FreeType's own FT_DivFix / FT_MulFix arithmetic (round
    half AWAY FROM ZERO), which is what src/hint.cyr targets and NOT rekha's usual half-up;
  * the digests are the FNV-1a over the scaled arrays that programs/hint_test.cyr recomputes.

Needs fontTools only for the table decode. Run:  python3 scripts/hint_vectors.py
"""
import struct
import sys

from fontTools.ttLib import TTFont

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
M64 = 0xFFFFFFFFFFFFFFFF


def fnv_u32(h, v):
    """The 32-bit-wide feed programs/face_test.cyr uses, in 64-bit FNV-1a."""
    v &= M64
    for i in range(4):
        h = ((h ^ ((v >> (i * 8)) & 255)) * FNV_PRIME) & M64
    return h


def divfix(a, b):
    s = 1
    if a < 0:
        a, s = -a, -s
    if b < 0:
        b, s = -b, -s
    c = (a * 65536 + b // 2) // b
    return c if s > 0 else -c


def mulfix(a, b):
    s = 1
    if a < 0:
        a, s = -a, -s
    if b < 0:
        b, s = -b, -s
    c = (a * b + 0x8000) >> 16
    return c if s > 0 else -c


def ilen(code, ip):
    op = code[ip]
    if op == 0x40:
        return 2 + code[ip + 1]
    if op == 0x41:
        return 2 + code[ip + 1] * 2
    if 0xB0 <= op <= 0xB7:
        return 2 + (op - 0xB0)
    if 0xB8 <= op <= 0xBF:
        return 1 + (op - 0xB8 + 1) * 2
    return 1


def walk_fpgm(code):
    """The top level of a font program: pushes and FDEFs, nothing else."""
    stack, defs, ip = [], [], 0
    while ip < len(code):
        op = code[ip]
        if op == 0x40:
            stack += list(code[ip + 2 : ip + 2 + code[ip + 1]])
        elif op == 0x41:
            n = code[ip + 1]
            stack += [struct.unpack(">h", code[ip + 2 + 2 * k : ip + 4 + 2 * k])[0] for k in range(n)]
        elif 0xB0 <= op <= 0xB7:
            stack += list(code[ip + 1 : ip + 1 + op - 0xB0 + 1])
        elif 0xB8 <= op <= 0xBF:
            n = op - 0xB8 + 1
            stack += [struct.unpack(">h", code[ip + 1 + 2 * k : ip + 3 + 2 * k])[0] for k in range(n)]
        elif op == 0x2C:
            num = stack.pop()
            j = ip + 1
            while code[j] != 0x2D:
                j += ilen(code, j)
            defs.append((num, ip + 1, j))
            ip = j + 1
            continue
        else:
            raise SystemExit("unexpected top-level opcode 0x%02X at %d" % (op, ip))
        ip += ilen(code, ip)
    return defs, stack


def main(path="fonts/LiberationSans-Regular.ttf"):
    f = TTFont(path)
    upem = f["head"].unitsPerEm
    cvt = list(f["cvt "].values)
    mx = f["maxp"]
    defs, left = walk_fpgm(f["fpgm"].program.getBytecode())
    nums = sorted(d[0] for d in defs)

    print("face                 %s" % path)
    print("unitsPerEm           %d" % upem)
    print("cvt entries          %d" % len(cvt))
    print("fpgm bytes           %d" % len(f["fpgm"].program.getBytecode()))
    print("prep bytes           %d" % len(f["prep"].program.getBytecode()))
    print("maxStorage           %d" % mx.maxStorage)
    print("maxFunctionDefs      %d" % mx.maxFunctionDefs)
    print("maxInstructionDefs   %d" % mx.maxInstructionDefs)
    print("maxStackElements     %d" % mx.maxStackElements)
    print("maxSizeOfInstructions%d" % mx.maxSizeOfInstructions)
    print("maxTwilightPoints    %d" % mx.maxTwilightPoints)
    print()
    print("fpgm FDEFs           %d (stack left %d)" % (len(defs), len(left)))
    print("  numbers            %s" % nums)
    print("  undefined below max %s" % [i for i in range(max(nums) + 1) if i not in set(nums)])
    print()
    print("gasp                 %s" % dict(sorted(f["gasp"].gaspRange.items())))
    print()
    # src/hint.cyr's one allocation (0.8.1): a 648-byte header, the stack with FreeType 2.14.3's
    # margin (ref2143/ttobjs.c:1078), storage, the FDEF table at max(64, maxFunctionDefs) records
    # of 32 bytes (FreeType's floor), the IDEF table, the scaled cvt, the twilight
    # zone and the glyph zone at 48 bytes a point (orus / org / cur, x and y), the contour ends, and
    # one tag byte per point rounded up to 8. The glyph zone holds the larger of the simple and the
    # composite maxima plus the four phantom points.
    stk = mx.maxStackElements + max(mx.maxStackElements // 2, 128)
    fdn = max(64, mx.maxFunctionDefs)
    tz = mx.maxTwilightPoints
    gz = max(mx.maxPoints, mx.maxCompositePoints) + 4
    gc = max(mx.maxContours, mx.maxCompositeContours)
    tagb = (tz + gz + 7) & ~7
    ctx_bytes = (
        648
        + stk * 8
        + mx.maxStorage * 8
        + fdn * 32
        + mx.maxInstructionDefs * 32
        + len(cvt) * 8
        + tz * 48
        + gz * 48
        + gc * 8
        + tagb
    )
    print("hint context bytes   %d" % ctx_bytes)
    print()
    for ppem in (8, 12, 16, 24, 48, 100):
        sc = divfix(ppem * 64, upem)
        scaled = [mulfix(v, sc) for v in cvt]
        h = FNV_OFFSET
        for v in scaled:
            h = fnv_u32(h, v)
        print(
            "ppem %-4d scale %-8d cvt[0]=%-6d cvt[19]=%-5d cvt[323]=%-6d fnv=0x%016x"
            % (ppem, sc, scaled[0], scaled[19], scaled[323], h)
        )
    print()
    print("# where half-away-from-zero and rekha's usual half-up disagree, at ppem 12:")
    sc = divfix(12 * 64, upem)
    shown = 0
    for i, v in enumerate(cvt):
        prod = v * sc
        away = mulfix(v, sc)
        up = (prod + 0x8000) >> 16
        if away != up:
            print("  cvt[%d] = %d font units -> away %d, half-up %d" % (i, v, away, up))
            shown += 1
            if shown == 4:
                break


if __name__ == "__main__":
    main(*sys.argv[1:])
