#!/usr/bin/env python3
"""ftshim — the installed libfreetype, through ctypes, pinned to the classic interpreter (rekha 0.8.1 and up).

⛔ THIS IS THE ONE WAY rekha's hinting suite reaches an interpreter it did not write. Every other
hinting oracle in scripts/ re-derives its numbers in Python from the same spec rekha read; this
module asks FreeType itself, the library the world's hinted fonts were drawn against, and hands
back exactly what a glyph slot holds after FT_Load_Glyph: the outline points in F26Dot6, the tag
bytes with their touch bits still set (FreeType only clears them for the renderer), and the
advance.

Three things are fixed here so no caller can get them wrong:

  * the CLASSIC interpreter (`GETINFO` 35), set twice on purpose — FREETYPE_PROPERTIES in the
    environment before the library is loaded, and FT_Property_Set on the library handle after —
    because the default since FreeType 2.7 is version 40, whose minimal subpixel hinting drops
    every horizontal move and would disagree with a CORRECT v35 implementation on most points;
  * FT_LOAD_NO_AUTOHINT on every load, because a font whose `fpgm`/`prep`/glyph programs are
    tiny (the synthetic unit-vector font is) trips FreeType's "this font is not really hinted"
    heuristic and gets autohinted instead — silently, with rc 0 and different points;
  * the version. rekha's reference is FreeType 2.14.x: 2.13.2 (what CI's Ubuntu ships) differs
    in the move arithmetic, the ODD/EVEN test, the stack margin and DELTAP's pop discipline, so
    a table generated against it would pin the wrong numbers. Any other major.minor refuses to
    run rather than produce a plausible-looking table.

No freetype-py, no fontTools: the struct layouts below are FreeType's public ABI (ftimage.h,
freetype.h), stable since 2.x, and were probed against the 2.14.3 on this host.

    import ftshim
    face = ftshim.load_face("fonts/LiberationSans-Regular.ttf")      # or the bytes of a font
    points, tags, advance = ftshim.hinted(face, 12, gid)              # v35, grayscale, NO_AUTOHINT
    points, tags, advance = ftshim.hinted(face, 12, gid, hint=False)  # the unhinted outline
    ftshim.hinted(face, 12, gid, pedantic=True)                       # raises FTError if any
                                                                      # instruction would have
                                                                      # been skipped silently
    ftshim.set_size(face, 12, force=True)                             # a fresh `prep` at 12

⛔ THE SIZE IS SET ONCE PER (FACE, PPEM), THE WAY A CONSUMER DRIVES FreeType. FT_Set_Pixel_Sizes
requests the size anew — tt_size_reset puts cvt_ready back to -1 (ref2143/ttobjs.c:1292) — and
the next hinted load then re-runs `prep`: the size's control values re-scaled from the font, the
storage area and the twilight zone zeroed, INSTCTRL's one-load state reset. A shim that set the
size before EVERY load would hand every glyph a prep-fresh interpreter and could never observe
what one glyph program leaves for the next at a fixed size — a WCVTF written through into the
size's cvt, a twilight point, INSTCTRL bit 2's persistent defaults — which rekha's context keeps
exactly as FreeType's size does. So load_glyph calls FT_Set_Pixel_Sizes only when `ppem` differs
from the face's last one (Face.ppem), and a caller that wants a fresh `prep` at the same size
says so with set_size(face, ppem, force=True). The generators' rows are unaffected either way:
scripts/hint_unit_vectors.py hints ONE glyph per fresh face, and scripts/hint_glyph_vectors.py
walks the ppems glyph by glyph, so consecutive loads there never share a size.
"""
import ctypes
import ctypes.util
import os
import sys

# Before the library is loaded: FreeType reads this at FT_Init_FreeType.
os.environ["FREETYPE_PROPERTIES"] = "truetype:interpreter-version=35"

REFERENCE = (2, 14)
INTERPRETER_VERSION = 35

FT_LOAD_NO_SCALE = 1 << 0
FT_LOAD_NO_HINTING = 1 << 1
FT_LOAD_NO_BITMAP = 1 << 3
FT_LOAD_PEDANTIC = 1 << 7
FT_LOAD_NO_RECURSE = 1 << 10
FT_LOAD_NO_AUTOHINT = 1 << 15

# FT_Glyph_Format tags (ftimage.h): what a slot holds after a load.
FT_GLYPH_FORMAT_COMPOSITE = 0x636F6D70  # 'comp'
FT_GLYPH_FORMAT_OUTLINE = 0x6F75746C  # 'outl'

# Tag bits on an outline point (ftimage.h). Touch bits are the interpreter's; HAS_SCANMODE is
# set on tags[0] together with scan_type << 5 after a glyph program ran.
TAG_ON_CURVE = 0x01
TAG_HAS_SCANMODE = 0x04
TAG_TOUCH_X = 0x08
TAG_TOUCH_Y = 0x10

FT_Library = ctypes.c_void_p
FT_Face = ctypes.c_void_p


class FTError(Exception):
    """A non-zero FT_Error from FT_Load_Glyph or the face constructor; `.rc` is the code."""

    def __init__(self, what, rc):
        Exception.__init__(self, "%s: FT_Error 0x%02x" % (what, rc))
        self.rc = rc


class FT_Generic(ctypes.Structure):
    _fields_ = [("data", ctypes.c_void_p), ("finalizer", ctypes.c_void_p)]


class FT_BBox(ctypes.Structure):
    _fields_ = [(n, ctypes.c_long) for n in ("xMin", "yMin", "xMax", "yMax")]


class FT_Vector(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class FT_FaceRec(ctypes.Structure):
    _fields_ = [
        ("num_faces", ctypes.c_long),
        ("face_index", ctypes.c_long),
        ("face_flags", ctypes.c_long),
        ("style_flags", ctypes.c_long),
        ("num_glyphs", ctypes.c_long),
        ("family_name", ctypes.c_char_p),
        ("style_name", ctypes.c_char_p),
        ("num_fixed_sizes", ctypes.c_int),
        ("available_sizes", ctypes.c_void_p),
        ("num_charmaps", ctypes.c_int),
        ("charmaps", ctypes.c_void_p),
        ("generic", FT_Generic),
        ("bbox", FT_BBox),
        ("units_per_EM", ctypes.c_ushort),
        ("ascender", ctypes.c_short),
        ("descender", ctypes.c_short),
        ("height", ctypes.c_short),
        ("max_advance_width", ctypes.c_short),
        ("max_advance_height", ctypes.c_short),
        ("underline_position", ctypes.c_short),
        ("underline_thickness", ctypes.c_short),
        ("glyph", ctypes.c_void_p),
        ("size", ctypes.c_void_p),
        ("charmap", ctypes.c_void_p),
    ]


class FT_Outline(ctypes.Structure):
    _fields_ = [
        ("n_contours", ctypes.c_short),
        ("n_points", ctypes.c_short),
        ("points", ctypes.POINTER(FT_Vector)),
        ("tags", ctypes.POINTER(ctypes.c_ubyte)),
        ("contours", ctypes.POINTER(ctypes.c_short)),
        ("flags", ctypes.c_int),
    ]


class FT_Glyph_Metrics(ctypes.Structure):
    _fields_ = [
        (n, ctypes.c_long)
        for n in (
            "width",
            "height",
            "horiBearingX",
            "horiBearingY",
            "horiAdvance",
            "vertBearingX",
            "vertBearingY",
            "vertAdvance",
        )
    ]


class FT_Bitmap(ctypes.Structure):
    _fields_ = [
        ("rows", ctypes.c_uint),
        ("width", ctypes.c_uint),
        ("pitch", ctypes.c_int),
        ("buffer", ctypes.c_void_p),
        ("num_grays", ctypes.c_ushort),
        ("pixel_mode", ctypes.c_ubyte),
        ("palette_mode", ctypes.c_ubyte),
        ("palette", ctypes.c_void_p),
    ]


class FT_GlyphSlotRec(ctypes.Structure):
    _fields_ = [
        ("library", ctypes.c_void_p),
        ("face", ctypes.c_void_p),
        ("next", ctypes.c_void_p),
        ("glyph_index", ctypes.c_uint),
        ("generic", FT_Generic),
        ("metrics", FT_Glyph_Metrics),
        ("linearHoriAdvance", ctypes.c_long),
        ("linearVertAdvance", ctypes.c_long),
        ("advance", FT_Vector),
        ("format", ctypes.c_int),
        ("bitmap", FT_Bitmap),
        ("bitmap_left", ctypes.c_int),
        ("bitmap_top", ctypes.c_int),
        ("outline", FT_Outline),
    ]


class Face(object):
    """An FT_Face plus whatever must outlive it: the memory buffer of a memory face — and the
    ppem its size was last requested at (None until set_size / load_glyph sets one)."""

    def __init__(self, handle, keep, name):
        self.handle = handle
        self._keep = keep
        self.name = name
        self.ppem = None

    @property
    def rec(self):
        return ctypes.cast(self.handle, ctypes.POINTER(FT_FaceRec)).contents

    @property
    def num_glyphs(self):
        return self.rec.num_glyphs

    @property
    def units_per_em(self):
        return self.rec.units_per_EM


def _bind():
    path = ctypes.util.find_library("freetype") or "libfreetype.so.6"
    lib = ctypes.CDLL(path)
    P = ctypes.POINTER
    lib.FT_Init_FreeType.argtypes = [P(FT_Library)]
    lib.FT_Library_Version.argtypes = [FT_Library, P(ctypes.c_int), P(ctypes.c_int), P(ctypes.c_int)]
    lib.FT_Property_Set.argtypes = [FT_Library, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p]
    lib.FT_New_Face.argtypes = [FT_Library, ctypes.c_char_p, ctypes.c_long, P(FT_Face)]
    lib.FT_New_Memory_Face.argtypes = [FT_Library, ctypes.c_char_p, ctypes.c_long, ctypes.c_long, P(FT_Face)]
    lib.FT_Done_Face.argtypes = [FT_Face]
    lib.FT_Set_Pixel_Sizes.argtypes = [FT_Face, ctypes.c_uint, ctypes.c_uint]
    lib.FT_Load_Glyph.argtypes = [FT_Face, ctypes.c_uint, ctypes.c_int32]
    lib.FT_Get_Char_Index.argtypes = [FT_Face, ctypes.c_ulong]
    lib.FT_Get_Char_Index.restype = ctypes.c_uint
    return path, lib


_PATH, _LIB = _bind()
_LIBRARY = FT_Library()


def _init():
    rc = _LIB.FT_Init_FreeType(ctypes.byref(_LIBRARY))
    if rc:
        sys.exit("ftshim: FT_Init_FreeType failed (0x%02x) on %s" % (rc, _PATH))
    v = version()
    if v[:2] != REFERENCE:
        sys.exit(
            "ftshim: %s is FreeType %d.%d.%d; rekha's reference is FreeType %d.%d.x and the "
            "move arithmetic, ODD/EVEN, the stack margin and DELTAP's pops differ across versions, "
            "so this oracle refuses to generate numbers against anything else." % ((_PATH,) + v + REFERENCE)
        )
    # After the load: the property is per library handle, the environment was for FT_Init.
    want = ctypes.c_uint(INTERPRETER_VERSION)
    rc = _LIB.FT_Property_Set(_LIBRARY, b"truetype", b"interpreter-version", ctypes.byref(want))
    if rc:
        sys.exit("ftshim: FT_Property_Set(truetype, interpreter-version, 35) failed (0x%02x)" % rc)


def version():
    """(major, minor, patch) of the loaded libfreetype."""
    a, b, c = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
    _LIB.FT_Library_Version(_LIBRARY, ctypes.byref(a), ctypes.byref(b), ctypes.byref(c))
    return (a.value, b.value, c.value)


def version_string():
    return "%d.%d.%d" % version()


def library_path():
    return _PATH


def load_face(source, index=0):
    """A Face from a path (str) or from font bytes; the bytes are copied and kept alive."""
    handle = FT_Face()
    if isinstance(source, (bytes, bytearray)):
        buf = ctypes.create_string_buffer(bytes(source), len(source))
        rc = _LIB.FT_New_Memory_Face(_LIBRARY, buf, len(source), index, ctypes.byref(handle))
        if rc:
            raise FTError("FT_New_Memory_Face(%d bytes)" % len(source), rc)
        return Face(handle, buf, "<%d bytes>" % len(source))
    rc = _LIB.FT_New_Face(_LIBRARY, source.encode(), index, ctypes.byref(handle))
    if rc:
        raise FTError("FT_New_Face(%s)" % source, rc)
    return Face(handle, None, source)


def done(face):
    if face.handle:
        _LIB.FT_Done_Face(face.handle)
        face.handle = None


def char_index(face, ch):
    return _LIB.FT_Get_Char_Index(face.handle, ord(ch) if isinstance(ch, str) else ch)


def set_size(face, ppem, force=False):
    """FT_Set_Pixel_Sizes(face, ppem) — only when `ppem` differs from the face's last size, or
    when `force` asks for the request anyway (a fresh `prep` before the next hinted load, the
    per-load pedantic check's shape). Raises FTError on rc != 0."""
    if face.ppem == ppem and not force:
        return
    rc = _LIB.FT_Set_Pixel_Sizes(face.handle, 0, ppem)
    if rc:
        raise FTError("FT_Set_Pixel_Sizes(%d)" % ppem, rc)
    face.ppem = ppem


def load_glyph(face, ppem, gid, flags):
    """set_size (FT_Set_Pixel_Sizes only when `ppem` is not the face's current size) + FT_Load_Glyph
    with exactly `flags` (NO_BITMAP | NO_AUTOHINT are always added). Returns (points, tags,
    contour_ends, advance_x); raises FTError on rc != 0."""
    set_size(face, ppem)
    rc = _LIB.FT_Load_Glyph(face.handle, gid, flags | FT_LOAD_NO_BITMAP | FT_LOAD_NO_AUTOHINT)
    if rc:
        raise FTError("FT_Load_Glyph(gid %d, ppem %d, flags 0x%x)" % (gid, ppem, flags), rc)
    slot = ctypes.cast(face.rec.glyph, ctypes.POINTER(FT_GlyphSlotRec)).contents
    o = slot.outline
    points = [(o.points[i].x, o.points[i].y) for i in range(o.n_points)]
    tags = [o.tags[i] for i in range(o.n_points)]
    ends = [o.contours[i] for i in range(o.n_contours)]
    return points, tags, ends, slot.advance.x


def hinted(face, ppem, gid, hint=True, pedantic=False):
    """(points, tags, advance) of glyph `gid` at `ppem`: hinted by the classic interpreter unless
    hint=False; with pedantic=True every instruction FreeType would otherwise skip silently
    (a bad point index, a short stack, a cvt index out of range) fails the load instead."""
    flags = 0
    if not hint:
        flags |= FT_LOAD_NO_HINTING
    if pedantic:
        flags |= FT_LOAD_PEDANTIC
    points, tags, _, advance = load_glyph(face, ppem, gid, flags)
    return points, tags, advance


def contours(face, ppem, gid):
    """The contour end indices of glyph `gid` (they do not change under hinting)."""
    return load_glyph(face, ppem, gid, FT_LOAD_NO_HINTING)[2]


def is_composite(face, gid):
    """FreeType's own answer: loaded with NO_RECURSE a composite glyph stays FT_GLYPH_FORMAT_COMPOSITE.
    NO_SCALE: no size is requested and no program runs, so the face's `prep` state is untouched."""
    rc = _LIB.FT_Load_Glyph(face.handle, gid, FT_LOAD_NO_SCALE | FT_LOAD_NO_RECURSE | FT_LOAD_NO_BITMAP)
    if rc:
        raise FTError("FT_Load_Glyph(gid %d, NO_RECURSE)" % gid, rc)
    slot = ctypes.cast(face.rec.glyph, ctypes.POINTER(FT_GlyphSlotRec)).contents
    return slot.format == FT_GLYPH_FORMAT_COMPOSITE


_init()


if __name__ == "__main__":
    print("FreeType %s at %s, interpreter-version %d" % (version_string(), _PATH, INTERPRETER_VERSION))
