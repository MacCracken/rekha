#!/usr/bin/env python3
"""Independent oracle for programs/hint_test.cyr's `prep` pins (rekha 0.8.1, group M).

A second TrueType `fpgm` + `prep` interpreter, pure Python 3 stdlib, written from FreeType
2.14.3's ttinterp.c / ttobjs.c / ttpload.c / ftcalc.c (classic v35 engine, non-pedantic,
grayscale, square pixels) and NOT from src/hint.cyr. Every number it prints is what that engine
leaves behind after the control-value program has run at a size, so "rekha's prep agrees with
rekha" is not what the suite pins:

  * the TTF is parsed with `struct` alone — no fontTools, no rekha;
  * the control values are scaled with FreeType's own FT_DivFix / FT_MulFix arithmetic (round
    half AWAY FROM ZERO), `cvt[i] = FT_MulFix(raw, FT_DivFix(ppem * 64, upem))`
    (ref2143/ttobjs.c:970 with ttpload.c:349's `raw * 64 / 64`);
  * the stack is `maxStackElements + max(maxStackElements / 2, 128)` deep (ttobjs.c:1078);
  * `fpgm` runs ONCE, at the first size asked for, with that size's real ppem and scale
    (ttobjs.c:891); every `prep` run starts from default GS, zeroed twilight org/cur, zeroed
    storage and an empty stack (ttobjs.c:951-960, ttinterp.c:7518-7531), and afterwards the
    size's GS is the defaults plus the ten fields `TT_Save_Context` keeps (ttinterp.c:329-338);
  * moves follow 2.14.3's `moveVector` (ttinterp.c:2238-2296, 1504-1540), ODD/EVEN test bit 6
    only (2567, 2581), MPS answers the ppem (2413), INSTCTRL binds only inside `prep` (4715),
    S45ROUND's default threshold is `period - 1` (2098), DELTAP/DELTAC clamp `nump`, pop every
    pair up front and return early when the ppem is outside the band (6308-6337);
  * FreeType's non-pedantic tolerance is copied — a short stack is zero-filled, a bad index is
    skipped or answers 0 — but EVERY such event is counted and printed, because rekha refuses
    where FreeType tolerates (design D1/D2): a non-zero count at a size is a refusal the
    release notes must state. A twilight index in [maxTwilightPoints, maxTwilightPoints + 4)
    is legal in FreeType (ttobjs.c:1094) and a refusal in rekha (D6); it is counted apart.

The digests are the FNV-1a that programs/hint_test.cyr recomputes: 64-bit FNV-1a fed the low 32
bits of every value, little-endian, in index order. Every post-prep cvt entry, storage slot and
twilight coordinate it prints for Liberation Sans at the six sizes, and four of the graphics-state
fields, are read back out of the installed libfreetype 2.14.3 by scripts/hint_prep_xcheck.py
(through scripts/ftshim.py, by replacing a glyph in memory with a program that copies that state
onto its points) and must match value for value — 2442 values, 0 mismatches when this was
written; rerun it whenever this file or the pins change. The suite pins the numbers as
"second-interpreter derived", and that script is what makes them FreeType's. Run:

  python3 scripts/hint_prep_vectors.py table              # the group-M pins, one line per ppem
  python3 scripts/hint_prep_vectors.py dump 12            # every cvt entry fresh vs post-prep,
                                                          # storage, twilight, GS at 12 ppem
  python3 scripts/hint_prep_vectors.py trace 12 [fpgm]    # one line per executed instruction:
                                                          # range:ip opcode mnemonic depth top-4

`--font PATH` points at another face (the synthetic builder's output, say), `--ppems 8,12`
changes the sizes; `fpgm` runs at the first ppem listed.
"""
import argparse
import struct
import sys
from collections import Counter

# ---------------------------------------------------------------------------------------------
# Fixed-point arithmetic, ref2143/ftcalc.c and ttinterp.c. FT_Long is 64-bit on the analysis
# platform; Python ints do not wrap, which is only observable for |values| >= 2^63 (never).
# ---------------------------------------------------------------------------------------------

M32 = 0xFFFFFFFF


def i32(v):
    """(FT_Int32) v — two's-complement truncation to 32 bits."""
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def u32(v):
    return v & M32


def i16(v):
    """(FT_Short) v."""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def u16(v):
    """(FT_UShort) v."""
    return v & 0xFFFF


def u64(v):
    """(FT_ULong) v — what BOUNDSL compares."""
    return v & 0xFFFFFFFFFFFFFFFF


def cdiv(a, b):
    """C `/` on signed operands: truncation toward zero."""
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def mulfix(a, b):
    """FT_MulFix_64 (ftcalc.h:90-100): (a*b + 0x8000 + (ab >> 63)) >> 16, half away from zero."""
    ab = a * b
    return (ab + 0x8000 + (-1 if ab < 0 else 0)) >> 16


def divfix(a, b):
    """FT_DivFix (ftcalc.c:232-250): magnitudes, ((a << 16) + b/2) / b, 0x7FFFFFFF on b == 0."""
    s = 1
    if a < 0:
        a, s = -a, -s
    if b < 0:
        b, s = -b, -s
    q = ((a << 16) + (b >> 1)) // b if b > 0 else 0x7FFFFFFF
    return -q if s < 0 else q


def muldiv(a, b, c):
    """FT_MulDiv (ftcalc.c:161-181): magnitudes, (a*b + c/2) / c, 0x7FFFFFFF on c == 0."""
    s = 1
    if a < 0:
        a, s = -a, -s
    if b < 0:
        b, s = -b, -s
    if c < 0:
        c, s = -c, -s
    d = (a * b + (c >> 1)) // c if c > 0 else 0x7FFFFFFF
    return -d if s < 0 else d


def muldiv_no_round(a, b, c):
    """FT_MulDiv_No_Round (ftcalc.c:186-206): what DIV uses — truncated, not rounded."""
    s = 1
    if a < 0:
        a, s = -a, -s
    if b < 0:
        b, s = -b, -s
    if c < 0:
        c, s = -c, -s
    d = (a * b) // c if c > 0 else 0x7FFFFFFF
    return -d if s < 0 else d


def mulfix14(a, b):
    """TT_MulFix14_64 (ttinterp.c:1039-1049)."""
    ab = a * b
    ab += 0x2000 + (-1 if ab < 0 else 0)
    return ab >> 14


def dotfix14(ax, ay, bx, by):
    """TT_DotFix14 (ttinterp.c:1189-1201)."""
    c = ax * bx + ay * by
    c += 0x2000 + (-1 if c < 0 else 0)
    return c >> 14


def pix_floor(x):
    return x & ~63


def pix_round(x):
    return pix_floor(x + 32)


def pix_ceil(x):
    return pix_floor(x + 63)


def msb(x):
    """FT_MSB for x > 0."""
    return x.bit_length() - 1


def normlen(vx, vy):
    """FT_Vector_NormLen (ref2143/ftcalc.c:786-874), verbatim: the inputs are truncated to
    FT_Int32, the length estimate is prenormalised into [2/3, 4/3] * 2^16 by a shift, then
    Newton iterations on the reciprocal length run until the correction stops being positive.
    Returns the 16.16 unit vector (x, y); the length itself is not needed here."""
    x_ = i32(vx)
    y_ = i32(vy)
    sx = 1
    sy = 1
    if x_ < 0:
        x = u32(-x_)
        sx = -1
    else:
        x = x_
    if y_ < 0:
        y = u32(-y_)
        sy = -1
    else:
        y = y_
    if x == 0:
        return (vx, sy * 0x10000 if y > 0 else vy)
    if y == 0:
        return (sx * 0x10000 if x > 0 else vx, vy)
    l = x + (y >> 1) if x > y else y + (x >> 1)
    shift = 31 - msb(l)
    shift -= 15 + (1 if l >= (0xAAAAAAAA >> shift) else 0)
    if shift > 0:
        x = u32(x << shift)
        y = u32(y << shift)
        l = x + (y >> 1) if x > y else y + (x >> 1)
    else:
        x >>= -shift
        y >>= -shift
        l >>= -shift
    b = i32(0x10000 - i32(l))
    x_ = i32(x)
    y_ = i32(y)
    while True:
        u = u32(x_ + ((x_ * b) >> 16))
        v = u32(y_ + ((y_ * b) >> 16))
        z = cdiv(-i32(u * u + v * v), 0x200)
        z = cdiv(i32(z * ((0x10000 + b) >> 8)), 0x10000)
        b = i32(b + z)
        if not z > 0:
            break
    return (-u if sx < 0 else u, -v if sy < 0 else v)


def normalize(vx, vy, current):
    """Normalize (ttinterp.c:2326-2349): (0,0) leaves the vector untouched; else NormLen then
    `/ 4` toward zero to F2Dot14."""
    if vx == 0 and vy == 0:
        return current
    rx, ry = normlen(vx, vy)
    return (i16(cdiv(rx, 4)), i16(cdiv(ry, 4)))


# ---------------------------------------------------------------------------------------------
# Opcode tables (ttinterp.c:407-706 Pop_Push_Count, 709-1006 opcode_name, 1009-1029 opcode_length)
# ---------------------------------------------------------------------------------------------

_PPC_TEXT = """
00 00 00 00 00 00 20 20 20 20 20 20 02 02 00 50
10 10 10 10 10 10 10 10 00 00 10 00 10 10 10 10
12 10 00 22 01 11 10 20 00 10 20 10 10 00 10 10
00 00 00 00 10 10 10 10 10 00 20 20 00 00 20 20
00 00 20 11 20 11 11 11 20 21 21 01 01 00 00 10
21 21 21 21 21 21 11 11 10 00 21 21 11 10 10 10
21 21 21 21 11 11 11 11 11 11 11 11 11 11 11 11
20 10 10 10 10 10 10 10 20 20 00 00 00 00 10 10
00 20 20 00 00 10 20 20 11 10 33 21 21 10 20 00
00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
01 02 03 04 05 06 07 08 01 02 03 04 05 06 07 08
10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10
10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10
20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20
20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20
"""
POP_PUSH = [(int(t[0]), int(t[1])) for t in _PPC_TEXT.split()]
assert len(POP_PUSH) == 256

_NAMES = (
    "SVTCA[y] SVTCA[x] SPVTCA[y] SPVTCA[x] SFVTCA[y] SFVTCA[x] SPVTL[||] SPVTL[+] SFVTL[||] "
    "SFVTL[+] SPVFS SFVFS GPV GFV SFVTPV ISECT "
    "SRP0 SRP1 SRP2 SZP0 SZP1 SZP2 SZPS SLOOP RTG RTHG SMD ELSE JMPR SCVTCI SSWCI SSW "
    "DUP POP CLEAR SWAP DEPTH CINDEX MINDEX ALIGNPTS INS_$28 UTP LOOPCALL CALL FDEF ENDF "
    "MDAP[] MDAP[rnd] "
    "IUP[y] IUP[x] SHP[rp2] SHP[rp1] SHC[rp2] SHC[rp1] SHZ[rp2] SHZ[rp1] SHPIX IP MSIRP[] "
    "MSIRP[rp0] ALIGNRP RTDG MIAP[] MIAP[rnd] "
    "NPUSHB NPUSHW WS RS WCVTP RCVT GC[curr] GC[orig] SCFS MD[curr] MD[orig] MPPEM MPS FLIPON "
    "FLIPOFF DEBUG "
    "LT LTEQ GT GTEQ EQ NEQ ODD EVEN IF EIF AND OR NOT DELTAP1 SDB SDS "
    "ADD SUB DIV MUL ABS NEG FLOOR CEILING ROUND[G] ROUND[B] ROUND[W] ROUND[] NROUND[G] "
    "NROUND[B] NROUND[W] NROUND[] "
    "WCVTF DELTAP2 DELTAP3 DELTAC1 DELTAC2 DELTAC3 SROUND S45ROUND JROT JROF ROFF INS_$7B RUTG "
    "RDTG SANGW AA "
    "FLIPPT FLIPRGON FLIPRGOFF INS_$83 INS_$84 SCANCTRL SDPVTL[||] SDPVTL[+] GETINFO IDEF ROLL "
    "MAX MIN SCANTYPE INSTCTRL INS_$8F"
).split()
_NAMES += ["INS_$%02X" % k for k in range(0x90, 0xB0)]
_NAMES += ["PUSHB[%d]" % k for k in range(8)] + ["PUSHW[%d]" % k for k in range(8)]
_MDRP_FLAGS = ["", "r", "m", "mr", "p", "pr", "pm", "pmr"]
_MDRP_TAIL = ["G", "B", "W", ""]
for _base, _mn in ((0xC0, "MDRP"), (0xE0, "MIRP")):
    for _k in range(32):
        _NAMES.append("%s[%s%s]" % (_mn, _MDRP_FLAGS[_k >> 2], _MDRP_TAIL[_k & 3]))
MNEMONIC = _NAMES
assert len(MNEMONIC) == 256

OPCODE_LENGTH = [1] * 256
OPCODE_LENGTH[0x40] = -1
OPCODE_LENGTH[0x41] = -2
for _k in range(8):
    OPCODE_LENGTH[0xB0 + _k] = 2 + _k
    OPCODE_LENGTH[0xB8 + _k] = 3 + 2 * _k

RANGE_FONT, RANGE_CVT, RANGE_GLYPH = 1, 2, 3
RANGE_NAME = {RANGE_FONT: "fpgm", RANGE_CVT: "prep", RANGE_GLYPH: "glyf"}

TOUCH_X, TOUCH_Y, ON_CURVE = 8, 16, 1
CALL_SIZE = 32                      # ttinterp.c:374
MAX_RUNNABLE_OPCODES = 1000000      # ftoption.h TT_CONFIG_OPTION_MAX_RUNNABLE_OPCODES

ROUND_OFF, ROUND_RTHG, ROUND_RTG, ROUND_RTDG, ROUND_RDTG, ROUND_RUTG = 5, 0, 1, 2, 3, 4
ROUND_SUPER, ROUND_SUPER45 = 6, 7


# ---------------------------------------------------------------------------------------------
# The face: `struct` only
# ---------------------------------------------------------------------------------------------


class Face:
    """The tables a hinting run reads, decoded from the sfnt directory by hand."""

    def __init__(self, data):
        self.data = data
        if len(data) < 12:
            raise SystemExit("not an sfnt: %d bytes" % len(data))
        n = struct.unpack(">H", data[4:6])[0]
        self.tables = {}
        for i in range(n):
            off = 12 + 16 * i
            tag = data[off : off + 4].decode("latin1")
            toff, tlen = struct.unpack(">II", data[off + 8 : off + 16])
            self.tables[tag] = data[toff : toff + tlen]
        head = self.tables.get("head")
        if head is None or len(head) < 54:
            raise SystemExit("no head table")
        self.flags = struct.unpack(">H", head[16:18])[0]
        self.upem = struct.unpack(">H", head[18:20])[0]
        mx = self.tables.get("maxp", b"")
        if len(mx) < 32 or struct.unpack(">I", mx[:4])[0] != 0x00010000:
            raise SystemExit("maxp is not version 1.0: no interpreter limits to size by")
        self.num_glyphs = struct.unpack(">H", mx[4:6])[0]
        (
            self.max_twilight,
            self.max_storage,
            self.max_fdefs,
            self.max_idefs,
            self.max_stack,
        ) = struct.unpack(">HHHHH", mx[16:26])
        cv = self.tables.get("cvt ", b"")
        # ttpload.c:349: FT_GET_SHORT() * 64, and ttobjs.c:970 divides by 64 again — the raw
        # signed 16-bit FUnit value is what gets scaled.
        self.cvt_raw = [struct.unpack(">h", cv[2 * i : 2 * i + 2])[0] for i in range(len(cv) // 2)]
        self.fpgm = self.tables.get("fpgm", b"")
        self.prep = self.tables.get("prep", b"")


# ---------------------------------------------------------------------------------------------
# Zones and the graphics state
# ---------------------------------------------------------------------------------------------


class Zone:
    """TT_GlyphZoneRec: org / cur / orus / tags / contours. Zone 1 stays empty in this script
    (prep and fpgm run with n_points = n_contours = 0, ttobjs.c:905-906, 986-987)."""

    def __init__(self, n, nc=0):
        self.n_points = n
        self.n_contours = nc
        self.org = [[0, 0] for _ in range(n)]
        self.cur = [[0, 0] for _ in range(n)]
        self.orus = [[0, 0] for _ in range(n)]
        self.tags = [0] * n
        self.contours = [0] * nc
        self.first_point = 0


class GS:
    """TT_GraphicsState with tt_default_graphics_state (ttinterp.c:106-114)."""

    SAVED = (
        "minimum_distance",
        "control_value_cutin",
        "single_width_cutin",
        "single_width_value",
        "delta_base",
        "delta_shift",
        "auto_flip",
        "instruct_control",
        "scan_control",
        "scan_type",
    )

    def __init__(self):
        self.rp0 = self.rp1 = self.rp2 = 0
        self.gep0 = self.gep1 = self.gep2 = 1
        self.dual = (0x4000, 0)
        self.proj = (0x4000, 0)
        self.free = (0x4000, 0)
        self.loop = 1
        self.round_state = ROUND_RTG
        self.compensation = [0, 0, 0, 0]
        self.minimum_distance = 64
        self.control_value_cutin = 68
        self.single_width_cutin = 0
        self.single_width_value = 0
        self.delta_base = 9
        self.delta_shift = 3
        self.auto_flip = 1
        self.instruct_control = 0
        self.scan_control = 0
        self.scan_type = 0

    def copy(self):
        g = GS()
        g.__dict__.update(self.__dict__)
        g.compensation = list(self.compensation)
        return g

    def saved_fields(self):
        return [(k, getattr(self, k)) for k in self.SAVED]


class TTError(Exception):
    """exc->error: FreeType aborts the run and remembers the code for the size."""


# ---------------------------------------------------------------------------------------------
# The machine
# ---------------------------------------------------------------------------------------------


class Interp:
    """One TT_ExecContext + TT_Size pair: created once per face (tt_size_init_bytecode), `fpgm`
    run once, `prep` run per size. State that FreeType keeps across runs is kept here across
    runs (FDefs/IDefs, cvt, storage, twilight tags, the exec GS); state it resets is reset."""

    def __init__(self, face, ppem):
        self.face = face
        self.cvt_size = len(face.cvt_raw)
        self.stack_size = face.max_stack + max(face.max_stack // 2, 128)   # ttobjs.c:1078
        self.store_size = face.max_storage
        self.max_fdefs = face.max_fdefs
        self.max_idefs = face.max_idefs
        self.fdefs = {}          # opc -> dict(range, start, end, active)
        self.idefs = {}
        self.num_fdefs = 0
        self.num_idefs = 0
        self.max_func = 0
        self.max_ins = 0
        self.stack = []
        self.storage = [0] * self.store_size
        self.cvt = [0] * self.cvt_size            # FT_NEW: zero until the first prep run
        self.twilight_alloc = face.max_twilight + 4   # ttobjs.c:1091-1094
        self.twilight = Zone(self.twilight_alloc)
        self.pts = Zone(0)
        self.size_gs = GS()                        # size->GS (ttobjs.c:1100)
        self.gs = GS()                             # exec->GS; see exec_gs_fresh
        self.exec_gs_fresh = False                 # exec->GS is FT_NEW zeros until a run copies
        #                                            size->GS into it (ttinterp.c:7518)
        self.period = self.phase = self.threshold = 0
        self.ranges = {}
        self.grayscale = 0                         # exec->grayscale: 0 in fpgm, 1 in prep
        self.fpgm_error = None
        self.fpgm_ppem = None
        self.set_size(ppem)
        self.round_func = ROUND_RTG
        self.compute_funcs()
        self.last_scanctrl = None
        self.run_context_empty()
        self.trace = None
        self.trace_out = sys.stdout

    def budget(self):
        """TT_Run_Context's LOOPCALL / backward-jump budget for a run with no glyph loaded
        (ttinterp.c:7478-7495)."""
        return min(300 + 22 * self.cvt_size, 100 * self.face.num_glyphs)

    # ---- size metrics (tt_size_reset, ttobjs.c:1237-1296)
    def set_size(self, ppem):
        self.ppem = ppem
        self.scale = divfix(ppem * 64, self.face.upem)

    # ---- bookkeeping of what rekha would refuse
    def tolerate(self, what):
        """A site where pedantic FreeType would raise and non-pedantic FreeType goes on."""
        self.tolerated[what] += 1
        if len(self.tolerated_detail) < 64:
            self.tolerated_detail.append(
                "%s:%d %s: %s" % (RANGE_NAME[self.cur_range], self.ip, MNEMONIC[self.opcode], what)
            )

    def bounds(self, idx, zone):
        """BOUNDS(x, zone.n_points) with the FT_UInt cast; also books D6's twilight+4 band."""
        j = u32(idx)
        if j >= zone.n_points:
            return True
        if zone is self.twilight and j >= self.face.max_twilight:
            self.d6_events += 1
        return False

    # ---- the projection / move machinery
    def compute_funcs(self):
        """Compute_Funcs (ttinterp.c:2238-2296)."""
        px, py = self.gs.proj
        fx, fy = self.gs.free
        fdp = (px * fx + py * fy + 0x2000) >> 14
        if fdp >= 0x3FFE:
            self.move_vec = (fx * 4, fy * 4)
        elif -0x400 < fdp < 0x400:
            self.move_vec = (0, 0)
        else:
            self.move_vec = (cdiv(fx * 0x10000, fdp), cdiv(fy * 0x10000, fdp))
        if fdp >= 0x3FFE and fx == 0x4000:
            self.move_axis = "x"
        elif fdp >= 0x3FFE and fy == 0x4000:
            self.move_axis = "y"
        else:
            self.move_axis = None
        self.f_dot_p = fdp

    def project(self, dx, dy):
        px, py = self.gs.proj
        if px == 0x4000:
            return dx
        if py == 0x4000:
            return dy
        return dotfix14(dx, dy, px, py)

    def dualproj(self, dx, dy):
        px, py = self.gs.dual
        if px == 0x4000:
            return dx
        if py == 0x4000:
            return dy
        return dotfix14(dx, dy, px, py)

    def move(self, zone, p, d):
        """func_move: Direct_Move_X / _Y / Direct_Move (ttinterp.c:1504-1627)."""
        if self.move_axis == "x":
            zone.cur[p][0] += d
            zone.tags[p] |= TOUCH_X
        elif self.move_axis == "y":
            zone.cur[p][1] += d
            zone.tags[p] |= TOUCH_Y
        else:
            vx, vy = self.move_vec
            if vx != 0:
                zone.cur[p][0] += mulfix(d, vx)
                zone.tags[p] |= TOUCH_X
            if vy != 0:
                zone.cur[p][1] += mulfix(d, vy)
                zone.tags[p] |= TOUCH_Y

    def move_orig(self, zone, p, d):
        """func_move_orig (ttinterp.c:1563-1661): the same on org, no touch bits."""
        if self.move_axis == "x":
            zone.org[p][0] += d
        elif self.move_axis == "y":
            zone.org[p][1] += d
        else:
            vx, vy = self.move_vec
            if vx != 0:
                zone.org[p][0] += mulfix(d, vx)
            if vy != 0:
                zone.org[p][1] += mulfix(d, vy)

    def move_zp2(self, p, dx, dy, touch):
        """Move_Zp2_Point (ttinterp.c:4965-4996): keyed on the FREEDOM vector, not moveVector."""
        z = self.zp2
        fx, fy = self.gs.free
        if fx != 0:
            z.cur[p][0] += dx
            if touch:
                z.tags[p] |= TOUCH_X
        if fy != 0:
            z.cur[p][1] += dy
            if touch:
                z.tags[p] |= TOUCH_Y

    # ---- rounding (ttinterp.c:1682-2108); compensation is 0 in every reachable call
    def round(self, d, comp=0):
        rs = self.round_func
        if rs == ROUND_OFF:
            return self.round_none(d, comp)
        if rs == ROUND_RTG:
            if d >= 0:
                v = pix_round(d + comp)
                return 0 if v < 0 else v
            v = -pix_round(comp - d)
            return 0 if v > 0 else v
        if rs == ROUND_RTHG:
            if d >= 0:
                v = pix_floor(d + comp) + 32
                return 32 if v < 0 else v
            v = -(pix_floor(comp - d) + 32)
            return -32 if v > 0 else v
        if rs == ROUND_RDTG:
            if d >= 0:
                v = pix_floor(d + comp)
                return 0 if v < 0 else v
            v = -pix_floor(comp - d)
            return 0 if v > 0 else v
        if rs == ROUND_RUTG:
            if d >= 0:
                v = pix_ceil(d + comp)
                return 0 if v < 0 else v
            v = -pix_ceil(comp - d)
            return 0 if v > 0 else v
        if rs == ROUND_RTDG:
            if d >= 0:
                v = (d + comp + 16) & ~31
                return 0 if v < 0 else v
            v = -((comp - d + 16) & ~31)
            return 0 if v > 0 else v
        if rs == ROUND_SUPER:
            if d >= 0:
                v = ((d + self.threshold - self.phase + comp) & -self.period) + self.phase
                return self.phase if v < 0 else v
            v = -((self.threshold - self.phase + comp - d) & -self.period) - self.phase
            return -self.phase if v > 0 else v
        if rs == ROUND_SUPER45:
            if d >= 0:
                v = cdiv(d + self.threshold - self.phase + comp, self.period) * self.period
                v += self.phase
                return self.phase if v < 0 else v
            v = -(cdiv(self.threshold - self.phase + comp - d, self.period) * self.period)
            v -= self.phase
            return -self.phase if v > 0 else v
        raise AssertionError("round state %r" % rs)

    @staticmethod
    def round_none(d, comp=0):
        if d >= 0:
            v = d + comp
            return 0 if v < 0 else v
        v = d - comp
        return 0 if v > 0 else v

    def set_super_round(self, grid, sel):
        """SetSuperRound (ttinterp.c:2056-2108)."""
        s = sel & 0xC0
        if s == 0:
            period = grid // 2
        elif s == 0x40:
            period = grid
        elif s == 0x80:
            period = grid * 2
        else:
            period = grid
        s = sel & 0x30
        if s == 0:
            phase = 0
        elif s == 0x10:
            phase = period // 4
        elif s == 0x20:
            phase = period // 2
        else:
            phase = period * 3 // 4
        if (sel & 0x0F) == 0:
            threshold = period - 1
        else:
            threshold = cdiv(((sel & 0x0F) - 4) * period, 8)
        self.period = period >> 8
        self.phase = phase >> 8
        self.threshold = threshold >> 8

    # ---- code ranges and the call stack
    def goto_range(self, rng, ip):
        """Ins_Goto_CodeRange (ttinterp.c:1394-1451)."""
        if rng < 1 or rng > 3:
            raise TTError("Bad_Argument")
        code = self.ranges.get(rng)
        if code is None:
            raise TTError("Invalid_CodeRange")
        if ip > len(code):
            raise TTError("Code_Overflow")
        self.code = code
        self.ip = ip
        self.length = 0
        self.cur_range = rng

    def skip_code(self):
        """SkipCode (ttinterp.c:3065-3088)."""
        self.ip += self.length
        if self.ip < len(self.code):
            self.opcode = self.code[self.ip]
            self.length = OPCODE_LENGTH[self.opcode]
            if self.length < 0:
                if self.ip + 1 >= len(self.code):
                    raise TTError("Code_Overflow")
                self.length = 2 - self.length * self.code[self.ip + 1]
            return
        raise TTError("Code_Overflow")

    def call_def(self, d, count):
        if len(self.call_stack) >= CALL_SIZE:
            raise TTError("Stack_Overflow")
        self.call_stack.append([self.cur_range, self.ip + 1, count, d])
        self.goto_range(d["range"], d["start"])

    def lookup_fdef(self, f):
        """Ins_CALL / Ins_LOOPCALL's lookup (ttinterp.c:3396-3428)."""
        f = u64(f)
        if f >= self.max_func + 1:
            raise TTError("Invalid_Reference")
        d = self.fdefs.get(f)
        if d is None or not d["active"]:
            raise TTError("Invalid_Reference")
        return d

    # ---- running a code range (TT_Run_Context, ttinterp.c:7435-7536 + TT_RunIns 6727-7416)
    def run_context(self, rng, code):
        self.ranges[rng] = code
        self.zp0 = self.zp1 = self.zp2 = self.pts
        cap = max(30, 2 * (self.pts.n_points + self.cvt_size))
        cap = min(cap, 0xFFFF)
        self.twilight.n_points = min(self.twilight_alloc, cap)
        self.loopcall_counter = 0
        self.neg_jump_counter = 0
        self.loopcall_counter_max = self.budget()
        self.neg_jump_counter_max = self.budget()
        self.gs = self.size_gs.copy()
        self.exec_gs_fresh = True
        self.round_func = ROUND_RTG
        self.compute_funcs()
        self.stack = []
        self.call_stack = []
        self.ini_range = rng
        self.code = code
        self.cur_range = rng
        self.ip = 0
        self.ins_count = 0
        self.calls = Counter()
        self.n_call = 0
        self.n_loopcall = 0
        self.census = Counter()
        self.tolerated = Counter()
        self.tolerated_detail = []
        self.d6_events = 0
        self.delta_skipped = 0
        self.notes = Counter()
        self.error = None
        try:
            self.run_ins()
        except TTError as e:
            self.error = str(e)
        return self.error

    def run_ins(self):
        st = self.stack
        while True:
            self.ins_count += 1
            if self.ins_count > MAX_RUNNABLE_OPCODES:
                raise TTError("Execution_Too_Long")
            op = self.code[self.ip]
            self.opcode = op
            self.length = 1
            self.census[op] += 1
            pops, pushes = POP_PUSH[op]
            if self.trace is not None:
                top4 = " ".join(str(v) for v in st[-1:-5:-1])
                self.trace_out.write(
                    "%s:%04d %02X %-12s %4d [%s]\n"
                    % (RANGE_NAME[self.cur_range], self.ip, op, MNEMONIC[op], len(st), top4)
                )
            if len(st) < pops:
                # TT_RunIns 6774-6789: the bottom `pops` slots become zeros, args = 0
                self.tolerate("Too_Few_Arguments (stack zero-filled)")
                st[:] = [0] * pops
            if len(st) - pops + pushes > self.stack_size:
                raise TTError("Stack_Overflow")
            try:
                self.dispatch(op, st)
            except TTError as e:
                if str(e) != "Invalid_Opcode":
                    raise
                d = self.idefs.get(op)
                if d is None or not d["active"]:
                    raise
                if len(self.call_stack) >= CALL_SIZE:
                    raise TTError("Invalid_Reference")
                self.call_stack.append([self.cur_range, self.ip + 1, 1, d])
                self.goto_range(d["range"], d["start"])
            self.ip += self.length
            if self.ip >= len(self.code):
                if self.call_stack:
                    raise TTError("Code_Overflow")
                return

    # ---- the dispatch (TT_RunIns's switch, ttinterp.c:6802-7340)
    def dispatch(self, op, st):
        pop = st.pop
        push = st.append
        gs = self.gs
        # -- vectors
        if op <= 0x05:
            aa = (op & 1) << 14
            bb = aa ^ 0x4000
            if op < 4:
                gs.proj = (aa, bb)
                gs.dual = (aa, bb)
            if (op & 2) == 0:
                gs.free = (aa, bb)
            self.compute_funcs()
        elif op in (0x06, 0x07, 0x08, 0x09):
            i1 = u16(pop())      # args[1], in zp2
            i2 = u16(pop())      # args[0], in zp1
            if self.bounds(i1, self.zp2) or self.bounds(i2, self.zp1):
                self.tolerate("Invalid_Reference (SxVTL point)")
                return
            a = self.zp1.cur[i2][0] - self.zp2.cur[i1][0]
            b = self.zp1.cur[i2][1] - self.zp2.cur[i1][1]
            o = op
            if a == 0 and b == 0:
                a = 0x4000
                o = 0
            if o & 1:
                a, b = -b, a
            if op <= 0x07:
                gs.proj = normalize(a, b, gs.proj)
                gs.dual = gs.proj
            else:
                gs.free = normalize(a, b, gs.free)
            self.compute_funcs()
        elif op == 0x0A:
            y = i16(pop())
            x = i16(pop())
            gs.proj = normalize(x, y, gs.proj)
            gs.dual = gs.proj
            self.compute_funcs()
        elif op == 0x0B:
            y = i16(pop())
            x = i16(pop())
            gs.free = normalize(x, y, gs.free)
            self.compute_funcs()
        elif op == 0x0C:
            st.extend(gs.proj)
        elif op == 0x0D:
            st.extend(gs.free)
        elif op == 0x0E:
            gs.free = gs.proj
            self.compute_funcs()
        elif op == 0x0F:
            self.ins_isect(st)
        # -- reference points, zones, loop, rounding, gs scalars
        elif op == 0x10:
            gs.rp0 = u16(pop())
        elif op == 0x11:
            gs.rp1 = u16(pop())
        elif op == 0x12:
            gs.rp2 = u16(pop())
        elif 0x13 <= op <= 0x16:
            z = i32(pop())
            if z not in (0, 1):
                self.tolerate("Invalid_Reference (SZP zone)")
                return
            zone = self.twilight if z == 0 else self.pts
            if op == 0x13 or op == 0x16:
                self.zp0 = zone
                gs.gep0 = z
            if op == 0x14 or op == 0x16:
                self.zp1 = zone
                gs.gep1 = z
            if op == 0x15 or op == 0x16:
                self.zp2 = zone
                gs.gep2 = z
        elif op == 0x17:
            v = pop()
            if v < 0:
                raise TTError("Bad_Argument")
            gs.loop = min(v, 0xFFFF)
        elif op == 0x18:
            gs.round_state = self.round_func = ROUND_RTG
        elif op == 0x19:
            gs.round_state = self.round_func = ROUND_RTHG
        elif op == 0x1A:
            gs.minimum_distance = pop()
        elif op == 0x1B:
            self.ins_else()
        elif op == 0x1C:
            self.jmpr(pop())
        elif op == 0x1D:
            gs.control_value_cutin = pop()
        elif op == 0x1E:
            gs.single_width_cutin = pop()
        elif op == 0x1F:
            gs.single_width_value = mulfix(pop(), self.scale)
        # -- stack
        elif op == 0x20:
            v = pop()
            push(v)
            push(v)
        elif op == 0x21:
            pop()
        elif op == 0x22:
            st.clear()
        elif op == 0x23:
            b = pop()
            a = pop()
            push(b)
            push(a)
        elif op == 0x24:
            push(len(st))
        elif op == 0x25:
            k = pop()
            if k <= 0 or k > len(st):
                self.tolerate("Invalid_Reference (CINDEX depth)")
                push(0)
            else:
                push(st[-k])
        elif op == 0x26:
            k = pop()
            if k <= 0 or k > len(st):
                self.tolerate("Invalid_Reference (MINDEX depth)")
            else:
                push(st.pop(-k))
        elif op == 0x27:
            self.ins_alignpts(st)
        elif op == 0x29:
            p = u16(pop())
            if self.bounds(p, self.zp0):
                self.tolerate("Invalid_Reference (UTP point)")
                return
            mask = 0xFF
            if gs.free[0] != 0:
                mask &= ~TOUCH_X
            if gs.free[1] != 0:
                mask &= ~TOUCH_Y
            self.zp0.tags[p] &= mask
        # -- functions and control flow
        elif op == 0x2A:
            f = pop()
            cnt = pop()
            d = self.lookup_fdef(f)
            if len(self.call_stack) >= CALL_SIZE:
                raise TTError("Stack_Overflow")
            self.n_loopcall += 1
            if cnt > 0:
                self.calls[u64(f)] += cnt
                self.call_def(d, i32(cnt))
                self.loopcall_counter += cnt
                if self.loopcall_counter > self.loopcall_counter_max:
                    raise TTError("Execution_Too_Long")
        elif op == 0x2B:
            f = pop()
            d = self.lookup_fdef(f)
            self.n_call += 1
            self.calls[u64(f)] += 1
            self.call_def(d, 1)
        elif op == 0x2C:
            self.ins_fdef(u64(pop()))
        elif op == 0x2D:
            self.ins_endf()
        elif op == 0x2E or op == 0x2F:
            self.ins_mdap(op, st)
        elif op == 0x30 or op == 0x31:
            # Ins_IUP (ttinterp.c:6182-6290) returns at once when pts.n_contours == 0, which
            # is always the case for a prep / fpgm run: zone 1 is empty here.
            if self.pts.n_contours != 0:
                raise AssertionError("IUP on a loaded glyph zone is 0.8.2's")
        elif op == 0x32 or op == 0x33:
            self.ins_shp(op, st)
        elif op == 0x34 or op == 0x35:
            self.ins_shc(op, st)
        elif op == 0x36 or op == 0x37:
            self.ins_shz(op, st)
        elif op == 0x38:
            self.ins_shpix(st)
        elif op == 0x39:
            self.ins_ip(st)
        elif op == 0x3A or op == 0x3B:
            self.ins_msirp(op, st)
        elif op == 0x3C:
            self.ins_alignrp(st)
        elif op == 0x3D:
            gs.round_state = self.round_func = ROUND_RTDG
        elif op == 0x3E or op == 0x3F:
            self.ins_miap(op, st)
        elif op == 0x40:
            self.ins_npush(st, 1)
        elif op == 0x41:
            self.ins_npush(st, 2)
        # -- storage, cvt
        elif op == 0x42:
            v = pop()
            i = pop()
            if u64(i) >= self.store_size:
                self.tolerate("Invalid_Reference (WS index)")
            else:
                self.storage[i] = v
        elif op == 0x43:
            i = pop()
            if u64(i) >= self.store_size:
                self.tolerate("Invalid_Reference (RS index)")
                push(0)
            else:
                push(self.storage[i])
        elif op == 0x44:
            v = pop()
            i = pop()
            if u64(i) >= self.cvt_size:
                self.tolerate("Invalid_Reference (WCVTP index)")
            else:
                self.cvt[i] = v
        elif op == 0x45:
            i = pop()
            if u64(i) >= self.cvt_size:
                self.tolerate("Invalid_Reference (RCVT index)")
                push(0)
            else:
                push(self.cvt[i])
        elif op == 0x46 or op == 0x47:
            i = pop()
            if u64(i) >= self.zp2.n_points:
                self.tolerate("Invalid_Reference (GC point)")
                push(0)
            else:
                self.bounds(i, self.zp2)
                if op & 1:
                    push(self.dualproj(self.zp2.org[i][0], self.zp2.org[i][1]))
                else:
                    push(self.project(self.zp2.cur[i][0], self.zp2.cur[i][1]))
        elif op == 0x48:
            v = pop()
            i = u16(pop())
            if self.bounds(i, self.zp2):
                self.tolerate("Invalid_Reference (SCFS point)")
                return
            k = self.project(self.zp2.cur[i][0], self.zp2.cur[i][1])
            self.move(self.zp2, i, v - k)
            if gs.gep2 == 0:
                self.zp2.org[i] = list(self.zp2.cur[i])
        elif op == 0x49 or op == 0x4A:
            self.ins_md(op, st)
        elif op == 0x4B or op == 0x4C:
            push(self.ppem)                     # MPS: v35 answers the ppem (ttinterp.c:2413)
        elif op == 0x4D:
            gs.auto_flip = 1
        elif op == 0x4E:
            gs.auto_flip = 0
        elif op == 0x4F:
            pop()
            raise TTError("Debug_OpCode")
        # -- comparison and logic
        elif op == 0x50:
            b = pop()
            a = pop()
            push(1 if a < b else 0)
        elif op == 0x51:
            b = pop()
            a = pop()
            push(1 if a <= b else 0)
        elif op == 0x52:
            b = pop()
            a = pop()
            push(1 if a > b else 0)
        elif op == 0x53:
            b = pop()
            a = pop()
            push(1 if a >= b else 0)
        elif op == 0x54:
            b = pop()
            a = pop()
            push(1 if a == b else 0)
        elif op == 0x55:
            b = pop()
            a = pop()
            push(1 if a != b else 0)
        elif op == 0x56:
            push(1 if (self.round(pop(), 0) & 64) == 64 else 0)
        elif op == 0x57:
            push(1 if (self.round(pop(), 0) & 64) == 0 else 0)
        elif op == 0x58:
            self.ins_if(pop())
        elif op == 0x59:
            pass
        elif op == 0x5A:
            b = pop()
            a = pop()
            push(1 if (a != 0 and b != 0) else 0)
        elif op == 0x5B:
            b = pop()
            a = pop()
            push(1 if (a != 0 or b != 0) else 0)
        elif op == 0x5C:
            push(1 if pop() == 0 else 0)
        elif op == 0x5D or op == 0x71 or op == 0x72:
            self.ins_deltap(op, st)
        elif op == 0x5E:
            gs.delta_base = u16(pop())
        elif op == 0x5F:
            v = pop()
            if u64(v) > 6:
                raise TTError("Bad_Argument")
            gs.delta_shift = u16(v)
        # -- arithmetic
        elif op == 0x60:
            b = pop()
            a = pop()
            push(a + b)
        elif op == 0x61:
            b = pop()
            a = pop()
            push(a - b)
        elif op == 0x62:
            b = pop()
            a = pop()
            if b == 0:
                raise TTError("Divide_By_Zero")
            push(muldiv_no_round(a, 64, b))
        elif op == 0x63:
            b = pop()
            a = pop()
            push(muldiv(a, b, 64))
        elif op == 0x64:
            push(abs(pop()))
        elif op == 0x65:
            push(-pop())
        elif op == 0x66:
            push(pix_floor(pop()))
        elif op == 0x67:
            push(pix_ceil(pop()))
        elif 0x68 <= op <= 0x6B:
            push(self.round(pop(), gs.compensation[op & 3]))
        elif 0x6C <= op <= 0x6F:
            push(self.round_none(pop(), gs.compensation[op & 3]))
        elif op == 0x70:
            v = pop()
            i = pop()
            if u64(i) >= self.cvt_size:
                self.tolerate("Invalid_Reference (WCVTF index)")
            else:
                self.cvt[i] = mulfix(v, self.scale)
        elif 0x73 <= op <= 0x75:
            self.ins_deltac(op, st)
        elif op == 0x76:
            self.set_super_round(0x4000, pop())
            gs.round_state = self.round_func = ROUND_SUPER
        elif op == 0x77:
            self.set_super_round(0x2D41, pop())
            gs.round_state = self.round_func = ROUND_SUPER45
        elif op == 0x78:
            e = pop()
            off = pop()
            if e != 0:
                self.jmpr(off)
        elif op == 0x79:
            e = pop()
            off = pop()
            if e == 0:
                self.jmpr(off)
        elif op == 0x7A:
            gs.round_state = self.round_func = ROUND_OFF
        elif op == 0x7C:
            gs.round_state = self.round_func = ROUND_RUTG
        elif op == 0x7D:
            gs.round_state = self.round_func = ROUND_RDTG
        elif op == 0x7E or op == 0x7F:
            pop()                               # SANGW / AA: no longer supported
        # -- flips, scan control, dual projection, misc
        elif op == 0x80:
            self.ins_flippt(st)
        elif op == 0x81 or op == 0x82:
            k = u16(pop())
            lo = u16(pop())
            if self.bounds(k, self.pts) or self.bounds(lo, self.pts):
                self.tolerate("Invalid_Reference (FLIPRG point)")
                return
            for i in range(lo, k + 1):
                if op == 0x81:
                    self.pts.tags[i] |= ON_CURVE
                else:
                    self.pts.tags[i] &= ~ON_CURVE
        elif op == 0x85:
            self.ins_scanctrl(pop())
        elif op == 0x86 or op == 0x87:
            self.ins_sdpvtl(op, st)
        elif op == 0x88:
            sel = pop()
            k = 0
            if sel & 1:
                k = 35
            if (sel & 32) and self.grayscale:
                k |= 1 << 12
            push(k)
        elif op == 0x89:
            self.ins_idef(pop())
        elif op == 0x8A:
            c = pop()
            b = pop()
            a = pop()
            push(b)
            push(c)
            push(a)
        elif op == 0x8B:
            b = pop()
            a = pop()
            push(max(a, b))
        elif op == 0x8C:
            b = pop()
            a = pop()
            push(min(a, b))
        elif op == 0x8D:
            v = pop()
            if v >= 0:
                gs.scan_type = i32(v) & 0xFFFF
        elif op == 0x8E:
            self.ins_instctrl(st)
        elif 0xB0 <= op <= 0xB7:
            self.ins_push(st, op - 0xB0 + 1, 1)
        elif 0xB8 <= op <= 0xBF:
            self.ins_push(st, op - 0xB8 + 1, 2)
        elif 0xC0 <= op <= 0xDF:
            self.ins_mdrp(op, st)
        elif op >= 0xE0:
            self.ins_mirp(op, st)
        else:
            # 0x28, 0x7B, 0x83, 0x84, 0x8F..0xAF: Ins_UNKNOWN — an IDEF or Invalid_Opcode
            raise TTError("Invalid_Opcode")

    # ---- control flow
    def ins_if(self, cond):
        if cond != 0:
            return
        n_ifs = 1
        while True:
            self.skip_code()
            if self.opcode == 0x58:
                n_ifs += 1
            elif self.opcode == 0x1B:
                if n_ifs == 1:
                    return
            elif self.opcode == 0x59:
                n_ifs -= 1
                if n_ifs == 0:
                    return

    def ins_else(self):
        n_ifs = 1
        while n_ifs != 0:
            self.skip_code()
            if self.opcode == 0x58:
                n_ifs += 1
            elif self.opcode == 0x59:
                n_ifs -= 1

    def jmpr(self, off):
        """Ins_JMPR (ttinterp.c:3187-3219); JROT/JROF land here with their offset."""
        if off == 0 and len(self.stack) == 0:
            raise TTError("Bad_Argument")
        self.ip += off
        if self.ip < 0 or (self.call_stack and self.ip > self.call_stack[-1][3]["end"]):
            raise TTError("Bad_Argument")
        self.length = 0
        if off < 0:
            self.neg_jump_counter += 1
            if self.neg_jump_counter > self.neg_jump_counter_max:
                raise TTError("Execution_Too_Long")

    def ins_fdef(self, n):
        """Ins_FDEF (ttinterp.c:3259-3341)."""
        if self.ini_range == RANGE_GLYPH:
            raise TTError("DEF_In_Glyf_Bytecode")
        d = self.fdefs.get(n)
        if d is None:
            if self.num_fdefs >= self.max_fdefs:
                raise TTError("Too_Many_Function_Defs")
            self.num_fdefs += 1
            d = {"range": 0, "start": 0, "end": 0, "active": False}
            self.fdefs[n] = d
        if n > 0xFFFF:
            raise TTError("Too_Many_Function_Defs")
        d["range"] = self.cur_range
        d["start"] = self.ip + 1
        d["active"] = True
        if n > self.max_func:
            self.max_func = n
        while True:
            self.skip_code()
            if self.opcode in (0x89, 0x2C):
                raise TTError("Nested_DEFS")
            if self.opcode == 0x2D:
                d["end"] = self.ip
                return

    def ins_idef(self, n):
        """Ins_IDEF (ttinterp.c:3549-3625)."""
        if self.ini_range == RANGE_GLYPH:
            raise TTError("DEF_In_Glyf_Bytecode")
        d = self.idefs.get(u64(n))
        if d is None:
            if self.num_idefs >= self.max_idefs:
                raise TTError("Too_Many_Instruction_Defs")
            self.num_idefs += 1
            d = {"range": 0, "start": 0, "end": 0, "active": False}
            self.idefs[u64(n)] = d
        if n < 0 or n > 0xFF:
            raise TTError("Too_Many_Instruction_Defs")
        d["range"] = self.cur_range
        d["start"] = self.ip + 1
        d["active"] = True
        if n > self.max_ins:
            self.max_ins = n
        while True:
            self.skip_code()
            if self.opcode in (0x89, 0x2C):
                raise TTError("Nested_DEFS")
            if self.opcode == 0x2D:
                d["end"] = self.ip
                return

    def ins_endf(self):
        """Ins_ENDF (ttinterp.c:3344-3385)."""
        if not self.call_stack:
            raise TTError("ENDF_In_Exec_Stream")
        frame = self.call_stack.pop()
        frame[2] -= 1
        if frame[2] > 0:
            self.call_stack.append(frame)
            self.ip = frame[3]["start"]
            self.length = 0
        else:
            self.goto_range(frame[0], frame[1])

    # ---- pushes (ttinterp.c:3635-3788)
    def ins_npush(self, st, width):
        code = self.code
        ip = self.ip + 1
        if ip >= len(code):
            raise TTError("Code_Overflow")
        n = code[ip]
        if ip + width * n >= len(code):
            raise TTError("Code_Overflow")
        if n >= self.stack_size + 1 - len(st):
            raise TTError("Stack_Overflow")
        self.push_bytes(st, ip + 1, n, width)
        self.ip = ip + width * n

    def ins_push(self, st, n, width):
        ip = self.ip
        if ip + width * n >= len(self.code):
            raise TTError("Code_Overflow")
        if n >= self.stack_size + 1 - len(st):
            raise TTError("Stack_Overflow")
        self.push_bytes(st, ip + 1, n, width)
        self.ip = ip + width * n

    def push_bytes(self, st, at, n, width):
        if width == 1:
            st.extend(self.code[at : at + n])
        else:
            st.extend(struct.unpack(">%dh" % n, self.code[at : at + 2 * n]))

    # ---- INSTCTRL / SCANCTRL
    def ins_instctrl(self, st):
        """Ins_INSTCTRL (ttinterp.c:4671-4730)."""
        k = u64(st.pop())
        lo = u64(st.pop())
        if k < 1 or k > 3:
            self.tolerate("Invalid_Reference (INSTCTRL selector)")
            return
        kf = 1 << (k - 1)
        if lo != 0 and lo != kf:
            self.tolerate("Invalid_Reference (INSTCTRL value)")
            return
        if self.ini_range == RANGE_CVT:
            self.gs.instruct_control = ((self.gs.instruct_control & ~kf) | lo) & 0xFF
        elif self.ini_range == RANGE_GLYPH and k == 3:
            pass                                # the v40 waiver; nothing in v35
        else:
            self.tolerate("Invalid_Reference (INSTCTRL outside prep)")

    def ins_scanctrl(self, v):
        """Ins_SCANCTRL (ttinterp.c:4733-4780): scan_control is a Bool decided by the ppem."""
        self.last_scanctrl = v
        a = v & 0xFF
        gs = self.gs
        if a == 0xFF:
            gs.scan_control = 1
            return
        if a == 0:
            gs.scan_control = 0
            return
        if (v & 0x100) and self.ppem <= a:
            gs.scan_control = 1
        # 0x200 / 0x400: rotated / stretched, never here
        if (v & 0x800) and self.ppem > a:
            gs.scan_control = 0
        # 0x1000 / 0x2000: rotated / stretched, never here

    # ---- DELTAP / DELTAC (ttinterp.c:6293-6465)
    def delta_pairs(self, st, op):
        nump = st.pop()
        if nump < 0 or nump > len(st) // 2:
            self.tolerate("Too_Few_Arguments (DELTA nump clamped)")
            nump = len(st) // 2
        pairs = []
        for _ in range(nump):
            a = st.pop()
            b = st.pop()
            pairs.append((a, b))
        p = self.ppem - self.gs.delta_base
        p -= {0x5D: 0, 0x71: 16, 0x72: 32, 0x73: 0, 0x74: 16, 0x75: 32}[op]
        if p & ~0xF:
            self.delta_skipped += 1              # pairs popped, nothing applied, no bounds checks
            return None, None
        return pairs, p << 4

    def ins_deltap(self, op, st):
        pairs, p = self.delta_pairs(st, op)
        if pairs is None:
            return
        f = 1 << (6 - self.gs.delta_shift)
        for a, b in pairs:
            a = u16(a)
            if self.bounds(a, self.zp0):
                self.tolerate("Invalid_Reference (DELTAP point)")
                continue
            if (b & 0xF0) == p:
                b = (b & 0xF) - 8
                if b >= 0:
                    b += 1
                self.move(self.zp0, a, b * f)

    def ins_deltac(self, op, st):
        pairs, p = self.delta_pairs(st, op)
        if pairs is None:
            return
        f = 1 << (6 - self.gs.delta_shift)
        for a, b in pairs:
            if u64(a) >= self.cvt_size:
                self.tolerate("Invalid_Reference (DELTAC cvt)")
                continue
            if (b & 0xF0) == p:
                b = (b & 0xF) - 8
                if b >= 0:
                    b += 1
                self.cvt[a] += b * f

    # ---- point instructions
    def ins_sdpvtl(self, op, st):
        """Ins_SDPVTL (ttinterp.c:4463-4543): dual from org, projection from cur, and the
        `opcode` variable zeroed by the first coincidence test stays zeroed for the second."""
        p1 = u16(st.pop())
        p2 = u16(st.pop())
        if self.bounds(p2, self.zp1) or self.bounds(p1, self.zp2):
            self.tolerate("Invalid_Reference (SDPVTL point)")
            return
        o = op
        a = self.zp1.org[p2][0] - self.zp2.org[p1][0]
        b = self.zp1.org[p2][1] - self.zp2.org[p1][1]
        if a == 0 and b == 0:
            a = 0x4000
            o = 0
        if o & 1:
            a, b = -b, a
        self.gs.dual = normalize(a, b, self.gs.dual)
        a = self.zp1.cur[p2][0] - self.zp2.cur[p1][0]
        b = self.zp1.cur[p2][1] - self.zp2.cur[p1][1]
        if a == 0 and b == 0:
            a = 0x4000
            o = 0
        if o & 1:
            a, b = -b, a
        self.gs.proj = normalize(a, b, self.gs.proj)
        self.compute_funcs()

    def ins_isect(self, st):
        """Ins_ISECT (ttinterp.c:5723-5822)."""
        b1 = u16(st.pop())
        b0 = u16(st.pop())
        a1 = u16(st.pop())
        a0 = u16(st.pop())
        pt = u16(st.pop())
        z0, z1, z2 = self.zp0, self.zp1, self.zp2
        if (
            self.bounds(b0, z0)
            or self.bounds(b1, z0)
            or self.bounds(a0, z1)
            or self.bounds(a1, z1)
            or self.bounds(pt, z2)
        ):
            self.tolerate("Invalid_Reference (ISECT point)")
            return
        dbx = z0.cur[b1][0] - z0.cur[b0][0]
        dby = z0.cur[b1][1] - z0.cur[b0][1]
        dax = z1.cur[a1][0] - z1.cur[a0][0]
        day = z1.cur[a1][1] - z1.cur[a0][1]
        dx = z0.cur[b0][0] - z1.cur[a0][0]
        dy = z0.cur[b0][1] - z1.cur[a0][1]
        discriminant = muldiv(dax, -dby, 0x40) + muldiv(day, dbx, 0x40)
        dotproduct = muldiv(dax, dbx, 0x40) + muldiv(day, dby, 0x40)
        if 19 * abs(discriminant) > abs(dotproduct):
            val = muldiv(dx, -dby, 0x40) + muldiv(dy, dbx, 0x40)
            rx = muldiv(val, dax, discriminant)
            ry = muldiv(val, day, discriminant)
            z2.cur[pt][0] = z1.cur[a0][0] + rx
            z2.cur[pt][1] = z1.cur[a0][1] + ry
        else:
            z2.cur[pt][0] = cdiv(z1.cur[a0][0] + z1.cur[a1][0] + z0.cur[b0][0] + z0.cur[b1][0], 4)
            z2.cur[pt][1] = cdiv(z1.cur[a0][1] + z1.cur[a1][1] + z0.cur[b0][1] + z0.cur[b1][1], 4)
        z2.tags[pt] |= TOUCH_X | TOUCH_Y

    def ins_alignpts(self, st):
        p2 = u16(st.pop())
        p1 = u16(st.pop())
        if self.bounds(p1, self.zp1) or self.bounds(p2, self.zp0):
            self.tolerate("Invalid_Reference (ALIGNPTS point)")
            return
        d = self.project(
            self.zp0.cur[p2][0] - self.zp1.cur[p1][0], self.zp0.cur[p2][1] - self.zp1.cur[p1][1]
        )
        d = cdiv(d, 2)
        self.move(self.zp1, p1, d)
        self.move(self.zp0, p2, -d)

    def ins_mdap(self, op, st):
        p = u16(st.pop())
        if self.bounds(p, self.zp0):
            self.tolerate("Invalid_Reference (MDAP point)")
            return
        if op & 1:
            cd = self.project(self.zp0.cur[p][0], self.zp0.cur[p][1])
            d = self.round(cd, 0) - cd
        else:
            d = 0
        self.move(self.zp0, p, d)
        self.gs.rp0 = p
        self.gs.rp1 = p

    def ins_miap(self, op, st):
        cvte = st.pop()
        p = u16(st.pop())
        gs = self.gs
        if self.bounds(p, self.zp0) or u64(cvte) >= self.cvt_size:
            self.tolerate("Invalid_Reference (MIAP point/cvt)")
        else:
            dist = self.cvt[cvte]
            z0 = self.zp0
            if gs.gep0 == 0:
                z0.org[p] = [mulfix14(dist, gs.free[0]), mulfix14(dist, gs.free[1])]
                z0.cur[p] = list(z0.org[p])
            od = self.project(z0.cur[p][0], z0.cur[p][1])
            if op & 1:
                if abs(dist - od) > gs.control_value_cutin:
                    dist = od
                dist = self.round(dist, 0)
            self.move(z0, p, dist - od)
        gs.rp0 = p
        gs.rp1 = p

    def orig_distance(self, z1, p, z0, r):
        """The MDRP / MD[orig] original distance: org + dual projection when either zone is
        twilight, else orus + dual projection scaled once (ttinterp.c:5421-5450)."""
        gs = self.gs
        if gs.gep0 == 0 or gs.gep1 == 0:
            return self.dualproj(z1.org[p][0] - z0.org[r][0], z1.org[p][1] - z0.org[r][1])
        d = self.dualproj(z1.orus[p][0] - z0.orus[r][0], z1.orus[p][1] - z0.orus[r][1])
        return mulfix(d, self.scale)

    def ins_mdrp(self, op, st):
        p = u16(st.pop())
        gs = self.gs
        z1, z0 = self.zp1, self.zp0
        if self.bounds(p, z1) or self.bounds(gs.rp0, z0):
            self.tolerate("Invalid_Reference (MDRP point/rp0)")
        else:
            r = gs.rp0
            od = self.orig_distance(z1, p, z0, r)
            swc, swv = gs.single_width_cutin, gs.single_width_value
            if swc > 0 and od < swv + swc and od > swv - swc:
                od = swv if od >= 0 else -swv
            comp = gs.compensation[op & 3]
            d = self.round(od, comp) if op & 4 else self.round_none(od, comp)
            if op & 8:
                md = gs.minimum_distance
                if od >= 0:
                    if d < md:
                        d = md
                elif d > -md:
                    d = -md
            cd = self.project(z1.cur[p][0] - z0.cur[r][0], z1.cur[p][1] - z0.cur[r][1])
            self.move(z1, p, d - cd)
        gs.rp1 = gs.rp0
        gs.rp2 = p
        if op & 16:
            gs.rp0 = p

    def ins_mirp(self, op, st):
        cvte = u64(st.pop() + 1)
        p = u16(st.pop())
        gs = self.gs
        z1, z0 = self.zp1, self.zp0
        if self.bounds(p, z1) or cvte >= self.cvt_size + 1 or self.bounds(gs.rp0, z0):
            self.tolerate("Invalid_Reference (MIRP point/cvt/rp0)")
        else:
            r = gs.rp0
            cvd = self.cvt[cvte - 1] if cvte else 0
            if abs(cvd - gs.single_width_value) < gs.single_width_cutin:
                cvd = gs.single_width_value if cvd >= 0 else -gs.single_width_value
            if gs.gep1 == 0:
                z1.org[p] = [
                    z0.org[r][0] + mulfix14(cvd, gs.free[0]),
                    z0.org[r][1] + mulfix14(cvd, gs.free[1]),
                ]
                z1.cur[p] = list(z1.org[p])
            od = self.dualproj(z1.org[p][0] - z0.org[r][0], z1.org[p][1] - z0.org[r][1])
            cd = self.project(z1.cur[p][0] - z0.cur[r][0], z1.cur[p][1] - z0.cur[r][1])
            if gs.auto_flip and (od ^ cvd) < 0:
                cvd = -cvd
            comp = gs.compensation[op & 3]
            if op & 4:
                if gs.gep0 == gs.gep1 and abs(cvd - od) > gs.control_value_cutin:
                    cvd = od
                d = self.round(cvd, comp)
            else:
                d = self.round_none(cvd, comp)
            if op & 8:
                md = gs.minimum_distance
                if od >= 0:
                    if d < md:
                        d = md
                elif d > -md:
                    d = -md
            self.move(z1, p, d - cd)
        gs.rp1 = gs.rp0
        gs.rp2 = p
        if op & 16:
            gs.rp0 = p

    def ins_msirp(self, op, st):
        d = st.pop()
        p = u16(st.pop())
        gs = self.gs
        z1, z0 = self.zp1, self.zp0
        if self.bounds(p, z1) or self.bounds(gs.rp0, z0):
            self.tolerate("Invalid_Reference (MSIRP point/rp0)")
            return
        r = gs.rp0
        if gs.gep1 == 0:
            z1.org[p] = list(z0.org[r])
            self.move_orig(z1, p, d)
            z1.cur[p] = list(z1.org[p])
        cd = self.project(z1.cur[p][0] - z0.cur[r][0], z1.cur[p][1] - z0.cur[r][1])
        self.move(z1, p, d - cd)
        gs.rp1 = gs.rp0
        gs.rp2 = p
        if op & 1:
            gs.rp0 = p

    def ins_alignrp(self, st):
        gs = self.gs
        loop = gs.loop
        if len(st) < loop:
            self.tolerate("Too_Few_Arguments (ALIGNRP loop)")
            gs.loop = 1
            return
        points = [st.pop() for _ in range(loop)]
        z1, z0 = self.zp1, self.zp0
        if self.bounds(gs.rp0, z0):
            self.tolerate("Invalid_Reference (ALIGNRP rp0; points popped)")
            gs.loop = 1
            return
        r = gs.rp0
        for p in points:
            p = u16(p)
            if self.bounds(p, z1):
                self.tolerate("Invalid_Reference (ALIGNRP point)")
                continue
            d = self.project(z1.cur[p][0] - z0.cur[r][0], z1.cur[p][1] - z0.cur[r][1])
            self.move(z1, p, -d)
        gs.loop = 1

    def ins_ip(self, st):
        """Ins_IP (ttinterp.c:5860-6010)."""
        gs = self.gs
        loop = gs.loop
        if len(st) < loop:
            self.tolerate("Too_Few_Arguments (IP loop)")
            gs.loop = 1
            return
        points = [st.pop() for _ in range(loop)]
        z0, z1, z2 = self.zp0, self.zp1, self.zp2
        if self.bounds(gs.rp1, z0):
            self.tolerate("Invalid_Reference (IP rp1; points popped)")
            gs.loop = 1
            return
        twilight = gs.gep0 == 0 or gs.gep1 == 0 or gs.gep2 == 0
        r1, r2 = gs.rp1, gs.rp2
        ob = z0.org[r1] if twilight else z0.orus[r1]
        cb = z0.cur[r1]
        if u32(r2) >= z1.n_points:
            # documented in both modes, no error even pedantic (5907-5911)
            self.notes["IP rp2 outside zp1: ranges 0"] += 1
            old_range = cur_range = 0
        else:
            self.bounds(r2, z1)
            src = z1.org[r2] if twilight else z1.orus[r2]
            old_range = self.dualproj(src[0] - ob[0], src[1] - ob[1])
            cur_range = self.project(z1.cur[r2][0] - cb[0], z1.cur[r2][1] - cb[1])
        for p in points:
            if u32(p) >= z2.n_points:
                self.tolerate("Invalid_Reference (IP point)")
                continue
            self.bounds(p, z2)
            src = z2.org[p] if twilight else z2.orus[p]
            od = self.dualproj(src[0] - ob[0], src[1] - ob[1])
            cd = self.project(z2.cur[p][0] - cb[0], z2.cur[p][1] - cb[1])
            if od:
                nd = muldiv(od, cur_range, old_range) if old_range else od
            else:
                nd = 0
            self.move(z2, u16(p), nd - cd)
        gs.loop = 1

    def displacement(self, op):
        """Compute_Point_Displacement (ttinterp.c:4922-4962)."""
        if op & 1:
            z, p = self.zp0, self.gs.rp1
        else:
            z, p = self.zp1, self.gs.rp2
        if self.bounds(p, z):
            self.tolerate("Invalid_Reference (SHx reference point)")
            return None
        d = self.project(z.cur[p][0] - z.org[p][0], z.cur[p][1] - z.org[p][1])
        return z, p, mulfix(d, self.move_vec[0]), mulfix(d, self.move_vec[1])

    def ins_shp(self, op, st):
        gs = self.gs
        loop = gs.loop
        if len(st) < loop:
            self.tolerate("Too_Few_Arguments (SHP loop)")
            gs.loop = 1
            return
        points = [st.pop() for _ in range(loop)]
        disp = self.displacement(op)
        if disp is None:
            return                              # points popped, GS.loop NOT reset (5026-5027)
        _, _, dx, dy = disp
        for p in points:
            p = u16(p)
            if self.bounds(p, self.zp2):
                self.tolerate("Invalid_Reference (SHP point)")
                continue
            self.move_zp2(p, dx, dy, True)
        gs.loop = 1

    def ins_shc(self, op, st):
        c = u16(st.pop())
        z2 = self.zp2
        nb = 1 if self.gs.gep2 == 0 else z2.n_contours
        if c >= nb:
            self.tolerate("Invalid_Reference (SHC contour)")
            return
        disp = self.displacement(op)
        if disp is None:
            return
        z, refp, dx, dy = disp
        start = 0 if c == 0 else z2.contours[c - 1] + 1 - z2.first_point
        limit = z2.n_points if self.gs.gep2 == 0 else z2.contours[c] + 1 - z2.first_point
        for i in range(start, limit):
            if z is not z2 or refp != i:
                self.move_zp2(i, dx, dy, True)

    def ins_shz(self, op, st):
        v = st.pop()
        if u32(v) >= 2:
            self.tolerate("Invalid_Reference (SHZ zone)")
            return
        disp = self.displacement(op)
        if disp is None:
            return
        z, refp, dx, dy = disp
        z2 = self.zp2
        if self.gs.gep2 == 0:
            limit = z2.n_points
        elif z2.n_contours > 0:
            limit = z2.contours[z2.n_contours - 1] + 1
        else:
            limit = 0
        for i in range(limit):
            if z is not z2 or refp != i:
                self.move_zp2(i, dx, dy, False)

    def ins_shpix(self, st):
        gs = self.gs
        loop = gs.loop
        amount = st.pop()
        if len(st) < loop:
            self.tolerate("Too_Few_Arguments (SHPIX loop)")
            gs.loop = 1
            return
        points = [st.pop() for _ in range(loop)]
        dx = mulfix14(amount, gs.free[0])
        dy = mulfix14(amount, gs.free[1])
        for p in points:
            p = u16(p)
            if self.bounds(p, self.zp2):
                self.tolerate("Invalid_Reference (SHPIX point)")
                continue
            self.move_zp2(p, dx, dy, True)
        gs.loop = 1

    def ins_flippt(self, st):
        gs = self.gs
        loop = gs.loop
        if len(st) < loop:
            self.tolerate("Too_Few_Arguments (FLIPPT loop)")
            gs.loop = 1
            return
        for _ in range(loop):
            p = u16(st.pop())
            if self.bounds(p, self.pts):
                self.tolerate("Invalid_Reference (FLIPPT point)")
                continue
            self.pts.tags[p] ^= ON_CURVE
        gs.loop = 1

    def ins_md(self, op, st):
        k = u16(st.pop())
        lo = u16(st.pop())
        z0, z1 = self.zp0, self.zp1
        if self.bounds(lo, z0) or self.bounds(k, z1):
            self.tolerate("Invalid_Reference (MD point)")
            st.append(0)
            return
        if op & 1:
            d = self.project(z0.cur[lo][0] - z1.cur[k][0], z0.cur[lo][1] - z1.cur[k][1])
        else:
            d = self.orig_distance(z0, lo, z1, k)
        st.append(d)

    # ---- the per-size lifecycle (ttobjs.c:883-1003)
    def run_fpgm(self):
        """tt_size_run_fpgm: once per size object, with the real metrics, GS = defaults."""
        self.fpgm_ppem = self.ppem
        self.grayscale = 0
        self.ranges.pop(RANGE_CVT, None)
        self.ranges.pop(RANGE_GLYPH, None)
        self.pts = Zone(0)
        if len(self.face.fpgm) > 0:
            err = self.run_context(RANGE_FONT, self.face.fpgm)
        else:
            self.run_context_empty()       # ttobjs.c:897-913: no run at all
            err = None
        self.fpgm_error = err
        if err is None:
            self.save_context()
        return err

    def run_prep(self):
        """tt_size_run_prep: default GS, twilight org/cur zeroed (tags stay), storage zeroed,
        cvt rescaled, then the program; on success the ten fields go to the size's GS."""
        self.size_gs = GS()
        for i in range(self.twilight_alloc):
            self.twilight.org[i] = [0, 0]
            self.twilight.cur[i] = [0, 0]
        self.storage = [0] * self.store_size
        self.fresh = [mulfix(v, self.scale) for v in self.face.cvt_raw]
        self.cvt = list(self.fresh)
        self.ranges.pop(RANGE_GLYPH, None)
        self.pts = Zone(0)
        self.grayscale = 1
        self.last_scanctrl = None
        if len(self.face.prep) > 0:
            err = self.run_context(RANGE_CVT, self.face.prep)
        else:
            # ttobjs.c:994-1000 (C2-verify M2): no run, and TT_Save_Context still copies the
            # ten fields from whatever exec->GS holds — fpgm's final GS, or FT_NEW zeros.
            self.run_context_empty()
            err = None
            if not self.exec_gs_fresh:
                self.gs = GS()
                for k in GS.SAVED:
                    setattr(self.gs, k, 0)
        self.prep_error = err
        if err is None:
            self.save_context()
        return err

    def run_context_empty(self):
        """The counters the table prints, for a run that never happens (no fpgm, no prep)."""
        self.ins_count = 0
        self.calls = Counter()
        self.n_call = self.n_loopcall = 0
        self.census = Counter()
        self.tolerated = Counter()
        self.tolerated_detail = []
        self.d6_events = 0
        self.delta_skipped = 0
        self.notes = Counter()
        self.stack = []
        self.error = None

    def save_context(self):
        """TT_Save_Context (ttinterp.c:323-341)."""
        for k in GS.SAVED:
            setattr(self.size_gs, k, getattr(self.gs, k))


# ---------------------------------------------------------------------------------------------
# Digests and reports
# ---------------------------------------------------------------------------------------------

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
M64 = 0xFFFFFFFFFFFFFFFF


def fnv_u32(h, v):
    """The 32-bit-wide feed programs/hint_test.cyr uses, in 64-bit FNV-1a."""
    v &= M64
    for i in range(4):
        h = ((h ^ ((v >> (i * 8)) & 255)) * FNV_PRIME) & M64
    return h


def digest(values):
    h = FNV_OFFSET
    for v in values:
        h = fnv_u32(h, v)
    return h


def twilight_values(it):
    n = it.face.max_twilight
    return [p[0] for p in it.twilight.cur[:n]] + [p[1] for p in it.twilight.cur[:n]]


def gs_line(gs):
    return (
        "mindist %d cvtcutin %d swcutin %d swvalue %d dbase %d dshift %d autoflip %d "
        "instctrl %d scanctrl %d scantype %d"
        % (
            gs.minimum_distance,
            gs.control_value_cutin,
            gs.single_width_cutin,
            gs.single_width_value,
            gs.delta_base,
            gs.delta_shift,
            gs.auto_flip,
            gs.instruct_control,
            gs.scan_control,
            gs.scan_type,
        )
    )


POINT_OPS = set(
    [0x0F, 0x27, 0x29, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39]
    + [0x3A, 0x3B, 0x3C, 0x3E, 0x3F, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x5D, 0x71, 0x72, 0x80, 0x81]
    + [0x82, 0x06, 0x07, 0x08, 0x09, 0x86, 0x87]
    + list(range(0xC0, 0x100))
)


def print_header(face, it, path, ppems):
    print("face                 %s" % path)
    print("reference            FreeType 2.14.3 classic (v35), non-pedantic, grayscale")
    print("unitsPerEm           %d" % face.upem)
    print("cvt entries          %d" % len(face.cvt_raw))
    print("fpgm bytes           %d" % len(face.fpgm))
    print("prep bytes           %d" % len(face.prep))
    print("maxStorage           %d" % face.max_storage)
    print("maxFunctionDefs      %d" % face.max_fdefs)
    print("maxInstructionDefs   %d" % face.max_idefs)
    print("maxStackElements     %d  -> stack slots %d" % (face.max_stack, it.stack_size))
    print(
        "maxTwilightPoints    %d  -> twilight points %d" % (face.max_twilight, it.twilight_alloc)
    )
    print("numGlyphs            %d  -> loop budget %d" % (face.num_glyphs, it.budget()))
    print()
    print(
        "fpgm at ppem %-4d    %s; %d instructions, %d FDEFs (numbers %s), %d IDEFs, stack left %d"
        % (
            it.fpgm_ppem,
            "absent" if not face.fpgm else "error " + it.fpgm_error if it.fpgm_error else "ok",
            it.ins_count,
            it.num_fdefs,
            compact(sorted(it.fdefs)) or "none",
            it.num_idefs,
            len(it.stack),
        )
    )
    if not face.prep:
        print(
            "  NO prep table: 2.14.3 still copies the ten fields from a STALE exec GS (fpgm's"
            " final GS, or zeros\n  when no fpgm ever ran) — C2-verify M2, an upstream defect;"
            " rekha answers the defaults (design D10)."
        )
    if it.tolerated:
        print("  fpgm tolerated      %s" % dict(it.tolerated))
    print("  fresh-scale digests (the group-C pins, scripts/hint_vectors.py):")
    for ppem in ppems:
        sc = divfix(ppem * 64, face.upem)
        h = digest(mulfix(v, sc) for v in face.cvt_raw)
        print("    ppem %-4d scale %-8d fnv=0x%016x" % (ppem, sc, h))
    print()


def compact(nums):
    """[0, 1, 2, 5, 7, 8] -> '0-2 5 7-8'."""
    out = []
    i = 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else "%d-%d" % (nums[i], nums[j]))
        i = j + 1
    return " ".join(out)


def cmd_table(face, path, ppems):
    it = Interp(face, ppems[0])
    it.run_fpgm()
    print_header(face, it, path, ppems)
    if it.fpgm_error:
        print("fpgm failed: FreeType fails every hinted load of this face (bytecode_ready)")
        return
    print(
        "ppem  scale   cvt-digest         storage-digest     twilight-digest    "
        "chg mov dep tol d6 dskip  ins  call lcall | the ten fields after prep"
    )
    print(
        "# chg: cvt entries prep changed vs the fresh scale; mov: twilight points with org or cur"
        " != 0; dep: residual stack depth;\n# tol: events FreeType tolerated (rekha refuses);"
        " d6: twilight indices in the +4 band (rekha refuses); dskip: DELTAP/DELTAC whose ppem"
        " was outside\n# the band (pairs popped, nothing applied); ins: instructions executed;"
        " call/lcall: CALL / LOOPCALL instructions executed"
    )
    call_sets = []
    for ppem in ppems:
        it.set_size(ppem)
        err = it.run_prep()
        changed = sum(1 for i in range(it.cvt_size) if it.cvt[i] != it.fresh[i])
        moved = sum(
            1
            for i in range(face.max_twilight)
            if it.twilight.cur[i] != [0, 0] or it.twilight.org[i] != [0, 0]
        )
        print(
            "%-4d %6d  0x%016x 0x%016x 0x%016x %3d %3d %3d %3d %2d %5d %4d %4d %4d | %s%s"
            % (
                ppem,
                it.scale,
                digest(it.cvt),
                digest(it.storage),
                digest(twilight_values(it)),
                changed,
                moved,
                len(it.stack),
                sum(it.tolerated.values()),
                it.d6_events,
                it.delta_skipped,
                it.ins_count,
                it.n_call,
                it.n_loopcall,
                gs_line(it.size_gs),
                "  ERROR %s (size GS stays default)" % err if err else "",
            )
        )
        if it.tolerated:
            for line in it.tolerated_detail:
                print("      tolerated: %s" % line)
        if it.notes:
            for k, v in sorted(it.notes.items()):
                print("      note: %s x%d" % (k, v))
        call_sets.append((ppem, dict(sorted(it.calls.items())), it.last_scanctrl, it.census))
    print()
    if all(cs[1] == call_sets[0][1] for cs in call_sets):
        print("functions CALLed (every ppem): %s" % fmt_calls(call_sets[0][1]))
    else:
        for ppem, calls, _, _ in call_sets:
            print("functions CALLed at %-4d %s" % (ppem, fmt_calls(calls)))
    pops = sorted(set(op for _, _, _, cen in call_sets for op in cen if op in POINT_OPS))
    print(
        "point instructions reached: %s"
        % (" ".join("%02X %s" % (op, MNEMONIC[op]) for op in pops) if pops else "none")
    )
    scans = sorted(set(cs[2] for cs in call_sets if cs[2] is not None))
    if scans:
        print(
            "SCANCTRL operand(s) seen: %s  (scan_control above is FreeType's Bool, not this word)"
            % ", ".join("%d (0x%X)" % (s, s) for s in scans)
        )
    print("scan_control / scan_type / instruct_control are the size GS after TT_Save_Context;")
    print("everything not listed (rp, gep, vectors, loop, round state) is at its default.")


def fmt_calls(calls):
    return " ".join("%dx%d" % (f, n) for f, n in calls.items()) if calls else "none"


def cmd_dump(face, path, ppems, ppem):
    it = Interp(face, ppems[0] if ppems else ppem)
    it.run_fpgm()
    print_header(face, it, path, [ppem])
    if it.fpgm_error:
        return
    it.set_size(ppem)
    err = it.run_prep()
    print(
        "prep at ppem %d: %s; %d instructions, stack left %d, tolerated %d, twilight+4 %d"
        % (
            ppem,
            "error " + err if err else "ok",
            it.ins_count,
            len(it.stack),
            sum(it.tolerated.values()),
            it.d6_events,
        )
    )
    for line in it.tolerated_detail:
        print("  tolerated: %s" % line)
    print()
    print("cvt   raw     fresh   post-prep  (delta)")
    for i in range(it.cvt_size):
        d = it.cvt[i] - it.fresh[i]
        delta = "%+d" % d if d else ""
        print("%4d %6d %8d %10d %s" % (i, face.cvt_raw[i], it.fresh[i], it.cvt[i], delta))
    print()
    print("storage (%d): %s" % (it.store_size, " ".join(str(v) for v in it.storage)))
    print()
    print(
        "twilight  org.x  org.y  cur.x  cur.y tags   (%d points, %d allocated)"
        % (face.max_twilight, it.twilight_alloc)
    )
    for i in range(it.twilight_alloc):
        o, c = it.twilight.org[i], it.twilight.cur[i]
        band = "  (+4 band)" if i >= face.max_twilight else ""
        t = it.twilight.tags[i]
        print("%8d %6d %6d %6d %6d %4d%s" % (i, o[0], o[1], c[0], c[1], t, band))
    print()
    print("size GS after prep:  %s" % gs_line(it.size_gs))
    g = it.gs
    print("exec GS at prep end: %s" % gs_line(g))
    rp_gep = (g.rp0, g.rp1, g.rp2, g.gep0, g.gep1, g.gep2, g.loop, g.round_state)
    print("  rp %d %d %d  gep %d %d %d  loop %d  round %d" % rp_gep)
    print("  proj %s  free %s  dual %s" % (g.proj, g.free, g.dual))
    print(
        "  moveVector %s  F_dot_P %d  period/phase/threshold %d/%d/%d"
        % (it.move_vec, it.f_dot_p, it.period, it.phase, it.threshold)
    )
    print("  residual stack: %s" % (it.stack if it.stack else "empty"))
    print(
        "digests: cvt 0x%016x storage 0x%016x twilight 0x%016x"
        % (digest(it.cvt), digest(it.storage), digest(twilight_values(it)))
    )


def cmd_trace(face, path, ppems, ppem, with_fpgm):
    it = Interp(face, ppems[0] if ppems else ppem)
    if with_fpgm:
        it.trace = True
        print("# fpgm at ppem %d" % it.ppem)
    it.run_fpgm()
    it.trace = None
    if it.fpgm_error:
        print("# fpgm error %s at %s:%d" % (it.fpgm_error, RANGE_NAME[it.cur_range], it.ip))
        return
    it.set_size(ppem)
    it.trace = True
    print(
        "# prep at ppem %d (scale %d): range:ip opcode mnemonic depth [top of stack first]"
        % (ppem, it.scale)
    )
    err = it.run_prep()
    it.trace = None
    print(
        "# end: %s; %d instructions, stack left %d, tolerated %d, twilight+4 %d"
        % (
            "error " + err if err else "ok",
            it.ins_count,
            len(it.stack),
            sum(it.tolerated.values()),
            it.d6_events,
        )
    )
    for line in it.tolerated_detail:
        print("# tolerated: %s" % line)
    print("# size GS: %s" % gs_line(it.size_gs))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["table", "dump", "trace"])
    ap.add_argument("ppem", nargs="?", type=int, help="the size for dump / trace")
    ap.add_argument("extra", nargs="?", help="'fpgm' after trace's ppem: trace fpgm too")
    ap.add_argument("--font", default="fonts/LiberationSans-Regular.ttf")
    ap.add_argument(
        "--ppems", default="8,12,16,24,48,100", help="table sizes; fpgm runs at the first"
    )
    a = ap.parse_args(argv)
    ppems = [int(p) for p in a.ppems.split(",") if p]
    face = Face(open(a.font, "rb").read())
    if a.mode == "table":
        cmd_table(face, a.font, ppems)
    elif a.mode == "dump":
        if a.ppem is None:
            ap.error("dump needs a ppem")
        cmd_dump(face, a.font, ppems, a.ppem)
    else:
        if a.ppem is None:
            ap.error("trace needs a ppem")
        cmd_trace(face, a.font, ppems, a.ppem, a.extra == "fpgm")


if __name__ == "__main__":
    main(sys.argv[1:])
