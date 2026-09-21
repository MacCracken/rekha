#!/usr/bin/env python3
"""rekha's hinted outlines against FreeType's, glyph by glyph, point by point (rekha 0.8.2).

The dev-host differential for src/hint.cyr's glyph loader: every glyph of a face at every ppem,
rekha (through a committed dumper binary) versus the installed FreeType 2.14.x (through
scripts/ftshim.py: classic interpreter v35, grayscale, NO_AUTOHINT — the same oracle that
generated programs/hint_glyph_vectors.cyr and programs/hint_unit_vectors.cyr). Where the
committed modules pin 233 + 144 rows for CI, this script covers the other 2,300 glyphs of
Liberation Sans and any other hinted TrueType face on the host, and says WHICH point of WHICH
glyph disagrees, with the glyph's program disassembled and, for a composite, its component
records and whether each component agrees on its own.

    python3 scripts/hint_glyph_diff.py sweep [--font PATH] [--ppems 8,9,11,12,13,16,18,24,32,48]
            every glyph at every ppem; one summary line per ppem; exit 1 on any mismatch or
            refusal. --first N stops listing after N glyphs, --list prints headers only.
    python3 scripts/hint_glyph_diff.py diff <gid|char> <ppem> [--font PATH]
            one glyph, verbose: the full point table (FreeType, rekha, delta, tags), the
            program, the components each diffed as a glyph of their own.
    python3 scripts/hint_glyph_diff.py corpus [DIR|FILE ...] [--ppems 10,12,16]
            every .ttf with glyf + fpgm + prep under the directories (default: the host's font
            dirs) or named outright, one line per face: glyphs compared / agreeing / refused by
            rekha / mismatching / rejected by FreeType's own pedantic mode. Advisory: exit 0.
            --one-per-family keeps one face per family (the name before the first '-', the
            Regular where there is one): a host full of Nerd Fonts holds 150 Iosevka styles of
            57,000 glyphs each, and the styles differ in nothing the loader sees.
    python3 scripts/hint_glyph_diff.py mkdump <out> <ppem> <gid0> <gid1> [--font PATH]
            FreeType's numbers written in the DUMPER'S format (rekha-form tags): the reference
            of what a correct dumper prints for those glyphs, and the input of --dump-file.
    python3 scripts/hint_glyph_diff.py selftest
            the parser and the comparer on a dump generated from FreeType for two glyphs: a
            zero-mismatch run and, with one coordinate edited, a one-mismatch run.

    --dump-file PATH   (sweep / diff) read a saved dump instead of running the dumper binary
                       (every (gid, ppem) the mode needs must be in the file)
    --gids a,b,c       (sweep) only these glyphs — a partial dump, or one class of glyph
    --font PATH        the face (default fonts/LiberationSans-Regular.ttf); the dumper reads the
                       same file

THE DUMPER IS THROWAWAY, exactly as scripts/kern_diff.py's: the DUMPER template below, with
__FONT__ / __PPEM__ / __GID0__ / __GID1__ substituted, is written to build/hint_dump_<pid>.cyr,
built with `CYRIUS_DCE=1 cyrius build` into build/hint_dump_<pid> (one build per font, ppem and
gid range — a sweep of ten ppems is ten builds of ~0.5 s) and run; the pid in the name keeps two
invocations of this script from sharing one binary (both are removed when the script exits), and
run_dumper refuses a dump whose rows are not exactly the (gid, ppem) keys it asked for. Nothing
under programs/.
It reads the whole font file through the stdlib's `file_read_all(path, buf, cap)` (lib/io.cyr:502;
programs/ have no file reader of their own: programs/face_test.cyr uses the embedded
fonts/face_data.cyr), opens it with rekha_font_open, warms the hinting context ONCE at 64 ppem
(`rekha_hint_ctx(f, 64)`: fpgm runs at the first size a face is hinted at, exactly as this
oracle warms FreeType — hint_glyph_vectors.WARM_PPEM), then for every gid in [gid0, gid1) at
`ppem`: `cx = rekha_hint_ctx(f, ppem)`, `ok = rekha_hint_glyph(cx, gid)`, and prints on stdout,
per glyph:

    gid <g> ppem <p> status <1|0> err <code> <detail-or-> n <n> nc <nc> adv <F26Dot6> advpx <px>
    p <i> <x> <y> <tag>          one line per outline point i in 0..n-1 (phantoms excluded)
    c <end0> <end1> ...          one line: the contour ends (a bare `c` when nc is 0)

where status is rekha_hint_glyph's answer (0 = rekha REFUSED and zone 1 holds the unhinted
reload, whose points are still printed), err is rekha_hint_error(cx) (REKHA_OK 0) and detail
rekha_hint_error_detail(cx) or `-` when empty (the detail may contain spaces: the parser takes
the eight tokens `n .. advpx <px>` from the END of the line, so anything between the error code
and them is the detail), n / nc the view's point and contour counts, adv rekha_hint_advance(cx)
(cur[pp2].x - cur[pp1].x, F26Dot6, as the program left it), advpx rekha_hint_advance_px(cx)
(whole pixels, FreeType's slot rounding), x / y the view's cur in F26Dot6 AFTER the -pp1.x
translation (what rekha_hint_outline reports), tag rekha's tag byte — 1 ONCURVE | 2 TOUCHX |
4 TOUCHY (REKHA_TAG_*; the comparer maps FreeType's 1 / 8 / 16 the same way and drops FreeType's
scan bits, mask 0x19 as programs/hint_test.cyr's ft_tag does). Nothing else on stdout.
Exit 0 whenever the font opened. Every number in decimal, one space between tokens. `adv` is
read from the two phantom points through rekha_hint_point (the public surface has no raw
F26Dot6 advance — a consumer sees only the grid-fit one).

⛔ FreeType IS DRIVEN THE CONSUMER'S WAY — the size set ONCE per (face, ppem), then the glyphs
loaded in the DUMPER'S ORDER — so that the state one glyph program leaves for the next at a
fixed size (a WCVTF written through into the size's cvt, twilight points, INSTCTRL bit 2's
persistent defaults) is what rekha's context is compared against, exactly as the dumper's one
context sees it. Oracle.size(ppem) requests the size (a fresh `prep`) once before a range, and
Oracle.want then loads without re-requesting it (scripts/ftshim.py sets the size only when the
ppem changes). A sweep over a whole face is ONE dumper process per ppem and one size request
per ppem; with --gids each glyph is a dumper process of its own (fpgm at 64 ppem, prep at
`ppem`, the glyph), and the oracle re-requests the size before each glyph to match. Every
result of a ppem is classified before any is reported, because a mismatch report loads a
composite's components on the same face and would otherwise perturb the order. The PEDANTIC
face is separate and per-load: its size is re-requested before every pedantic load, so
"ft-pedantic-fails" means the glyph alone, on a fresh `prep`, fails FreeType's pedantic mode.

WHAT IS COMPARED per (gid, ppem), in this order — first failure names the class, all are listed:
  1. status: rekha refused / FreeType loaded ("refused"; FreeType's PEDANTIC load of the same
     glyph on a fresh face is ALSO tried, and a glyph FreeType itself rejects pedantic is classed
     "ft-pedantic-fails" — there rekha's refusal is 0.8.2's designed whole-load divergence from
     FreeType's default mode, which keeps the partial outline);
  2. point count and contour ends (a composite assembled wrong shows here first);
  3. advance: advpx * 64 against slot->advance.x (the grid-fit value);
  4. every point, x then y: FreeType's reported points against rekha's;
  5. every tag, masked.

NOT RUN IN CI. CI's Ubuntu ships FreeType 2.13.2, whose move arithmetic, ODD/EVEN, stack margin
and DELTAP pops differ from the 2.14.3 rekha targets (ftshim refuses it); this is a dev-host
tool, and its results go into the CHANGELOG as measurements. Python 3 stdlib + ftshim +
`cyrius` on PATH for the dumper build. Writes only under build/.
"""
import atexit
import glob
import os
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftshim  # noqa: E402
import hint_glyph_vectors as hg  # noqa: E402
import hint_unit_vectors as hu  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "build")
DUMPER_NAME = "hint_dump_%d" % os.getpid()  # two invocations never share a binary
DUMPER_SRC = os.path.join(OUT, DUMPER_NAME + ".cyr")
DUMPER_BIN = os.path.join(OUT, DUMPER_NAME)


def _drop_dumper():
    """The per-pid dumper goes at exit, so a hundred corpus runs do not leave a hundred binaries."""
    for path in (DUMPER_SRC, DUMPER_BIN):
        try:
            os.remove(path)
        except OSError:
            pass


atexit.register(_drop_dumper)

# The throwaway dumper (the docstring defines its output). A rekha program in the shape of
# programs/*_test.cyr: the prelude, the font through file_read_all, one context warmed at 64 ppem,
# then every glyph of [__GID0__, __GID1__) at __PPEM__ through rekha_hint_glyph and the readers.
DUMPER = r'''# GENERATED by scripts/hint_glyph_diff.py — throwaway, under build/.
include "programs/prelude.cyr"

fn out(s): i64 { syscall(1, 1, s, strlen(s)); return 0; }
fn outi(v): i64 { fmt_int(v); return 0; }

fn main(): i64 {
    alloc_init();
    var cap = 33554432;
    var buf = alloc(cap);
    var n = file_read_all("__FONT__", buf, cap);
    if (n <= 0) { syscall(1, 2, "read failed\n", 12); return 1; }
    var f = rekha_font_open(buf, n);
    if (f == 0) { syscall(1, 2, "open failed\n", 12); return 1; }
    var warm = rekha_hint_ctx(f, 64);
    if (warm == 0) { syscall(1, 2, "no hint context\n", 16); return 1; }
    var ppem = __PPEM__;
    var gid = __GID0__;
    while (gid < __GID1__) {
        var cx = rekha_hint_ctx(f, ppem);
        var ok = rekha_hint_glyph(cx, gid);
        var det = rekha_hint_error_detail(cx);
        if (det == 0) { det = "-"; }
        var o = rekha_hint_outline(cx);
        var np = 0;
        var nc = 0;
        if (o != 0) { np = rekha_outline_n_points(o); nc = rekha_outline_n_contours(o); }
        var adv = 0;
        if (o != 0) {
            adv = rekha_hint_point(cx, 1, np + 1, REKHA_PT_CURX) - rekha_hint_point(cx, 1, np, REKHA_PT_CURX);
        }
        out("gid "); outi(gid); out(" ppem "); outi(ppem); out(" status "); outi(ok);
        out(" err "); outi(rekha_hint_error(cx)); out(" "); out(det);
        out(" n "); outi(np); out(" nc "); outi(nc); out(" adv "); outi(adv);
        out(" advpx "); outi(rekha_hint_advance_px(cx)); out("\n");
        var i = 0;
        while (i < np) {
            out("p "); outi(i); out(" "); outi(load64(rekha_outline_xs(o) + i * 8));
            out(" "); outi(load64(rekha_outline_ys(o) + i * 8));
            out(" "); outi(rekha_hint_point(cx, 1, i, REKHA_PT_TAGS)); out("\n");
            i = i + 1;
        }
        out("c");
        var c = 0;
        while (c < nc) {
            out(" "); outi(load64(rekha_outline_end_pts(o) + c * 8));
            c = c + 1;
        }
        out("\n");
        gid = gid + 1;
    }
    return 0;
}
'''
DEFAULT_FONT = os.path.join(REPO, hg.FACE)
PPEMS = hg.PPEMS
CORPUS_PPEMS = (10, 12, 16)
DIRS = ["/usr/share/fonts", os.path.expanduser("~/.local/share/fonts"), os.path.expanduser("~/.fonts")]
WARM_PPEM = hg.WARM_PPEM


def ft_tag(t):
    """FreeType's tag byte to rekha's: 1 stays, 8 -> 2, 16 -> 4, everything else dropped."""
    r = t & 1
    if t & 8:
        r |= 2
    if t & 16:
        r |= 4
    return r


# ----------------------------------------------------------------------------------------------
# The dump: parse, and write (mkdump)
# ----------------------------------------------------------------------------------------------
class Row(object):
    """One glyph of a dump: what rekha said."""

    def __init__(self, gid, ppem, status, err, detail, n, nc, adv, advpx):
        self.gid, self.ppem, self.status, self.err, self.detail = gid, ppem, status, err, detail
        self.n, self.nc, self.adv, self.advpx = n, nc, adv, advpx
        self.points, self.tags, self.ends = [], [], []


def parse_dump(text):
    """{(gid, ppem): Row} from the dumper's stdout. Strict: a malformed line is an error that
    names it, never a silently skipped glyph."""
    rows, cur = {}, None
    for k, line in enumerate(text.split("\n"), 1):
        t = line.split()
        if not t:
            continue
        if t[0] == "gid":
            if len(t) < 15 or t[2] != "ppem" or t[4] != "status" or t[6] != "err":
                sys.exit("dump line %d: malformed header: %r" % (k, line))
            tail = t[-8:]
            if tail[0] != "n" or tail[2] != "nc" or tail[4] != "adv" or tail[6] != "advpx":
                sys.exit("dump line %d: malformed header tail: %r" % (k, line))
            detail = " ".join(t[8:-8])
            cur = Row(int(t[1]), int(t[3]), int(t[5]), int(t[7]), "" if detail == "-" else detail,
                      int(tail[1]), int(tail[3]), int(tail[5]), int(tail[7]))
            rows[(cur.gid, cur.ppem)] = cur
        elif t[0] == "p":
            if cur is None or len(t) != 5 or int(t[1]) != len(cur.points):
                sys.exit("dump line %d: unexpected point line: %r" % (k, line))
            cur.points.append((int(t[2]), int(t[3])))
            cur.tags.append(int(t[4]))
        elif t[0] == "c":
            if cur is None:
                sys.exit("dump line %d: contour line before any glyph" % k)
            cur.ends = [int(v) for v in t[1:]]
        else:
            sys.exit("dump line %d: unknown line: %r" % (k, line))
    for key, r in rows.items():
        if len(r.points) != r.n or len(r.ends) != r.nc:
            sys.exit("dump: gid %d ppem %d announces n %d nc %d but carries %d points, %d ends"
                     % (key[0], key[1], r.n, r.nc, len(r.points), len(r.ends)))
    return rows


def format_row(gid, ppem, status, err, detail, points, tags, ends, adv, advpx):
    """The dumper's format, for mkdump: FreeType's numbers as a correct dumper would print them."""
    L = ["gid %d ppem %d status %d err %d %s n %d nc %d adv %d advpx %d"
         % (gid, ppem, status, err, detail or "-", len(points), len(ends), adv, advpx)]
    for i, ((x, y), t) in enumerate(zip(points, tags)):
        L.append("p %d %d %d %d" % (i, x, y, t))
    L.append(("c " + " ".join(str(e) for e in ends)).rstrip())
    return "\n".join(L)


# ----------------------------------------------------------------------------------------------
# FreeType's side
# ----------------------------------------------------------------------------------------------
class Oracle(object):
    """One face through ftshim: a warmed default face, a warmed pedantic face, the raw glyf."""

    def __init__(self, path):
        self.path = path
        self.face = ftshim.load_face(path)
        self.strict = ftshim.load_face(path)
        self.num_glyphs = self.face.num_glyphs
        warm = self._first_hintable()
        ftshim.hinted(self.face, WARM_PPEM, warm)
        try:
            ftshim.hinted(self.strict, WARM_PPEM, warm, pedantic=True)
            self.prep_pedantic_ok = True
        except ftshim.FTError:
            self.prep_pedantic_ok = False  # fpgm/prep themselves fail pedantic: every row will
        self.gf = hg.Glyf(open(path, "rb").read())
        self._names = None

    def _first_hintable(self):
        for g in range(self.num_glyphs):
            try:
                ftshim.hinted(self.face, WARM_PPEM, g)
                return g
            except ftshim.FTError:
                continue
        return 0

    def size(self, ppem):
        """Request `ppem` on the default face — a fresh `prep` before the next hinted load — the
        way the dumper's one context enters a size. Once per dumper process; want() then loads
        glyph after glyph at that size without touching it, as the dumper does."""
        ftshim.set_size(self.face, ppem, force=True)

    def want(self, gid, ppem):
        """(points, tags-masked-to-rekha-form, ends, advance) or an FTError. No size request
        unless `ppem` is not the face's current size (a caller that skipped size())."""
        points, tags, ends, adv = ftshim.load_glyph(self.face, ppem, gid, 0)
        return points, [ft_tag(t) for t in tags], ends, adv

    def pedantic_ok(self, gid, ppem):
        """The glyph alone under FT_LOAD_PEDANTIC on the separate strict face, after a fresh
        size request: per load, so the answer is the glyph's own and not its predecessors'."""
        if not self.prep_pedantic_ok:
            return False
        try:
            ftshim.set_size(self.strict, ppem, force=True)
            ftshim.load_glyph(self.strict, ppem, gid, ftshim.FT_LOAD_PEDANTIC)
            return True
        except ftshim.FTError:
            return False

    def name(self, gid):
        """'U+00E9 é' for a glyph with a BMP code point, else ''."""
        if self._names is None:
            self._names = {}
            for cp in range(0x20, 0x10000):
                g = ftshim.char_index(self.face, cp)
                if g and g not in self._names:
                    self._names[g] = cp
        cp = self._names.get(gid)
        if cp is None:
            return ""
        ch = chr(cp)
        return "U+%04X %s" % (cp, repr(ch) if ch.isprintable() and not ch.isspace() else "")

    def kind(self, gid):
        return self.gf.kind(gid)

    def close(self):
        ftshim.done(self.face)
        ftshim.done(self.strict)


# ----------------------------------------------------------------------------------------------
# rekha's side
# ----------------------------------------------------------------------------------------------
def build_dumper(font, ppem, gid0, gid1):
    """Write build/hint_dump.cyr for this font, ppem and range, build it, answer the binary."""
    os.makedirs(OUT, exist_ok=True)
    src = (DUMPER.replace("__FONT__", os.path.abspath(font)).replace("__PPEM__", str(ppem))
           .replace("__GID0__", str(gid0)).replace("__GID1__", str(gid1)))
    open(DUMPER_SRC, "w").write(src)
    env = dict(os.environ, CYRIUS_DCE="1")
    r = subprocess.run(["cyrius", "build", "build/" + DUMPER_NAME + ".cyr", "build/" + DUMPER_NAME],
                       cwd=REPO, capture_output=True, text=True, env=env)
    bad = [l for l in (r.stdout + r.stderr).split("\n") if "warning" in l or "undefined function" in l]
    if r.returncode != 0 or bad or not os.path.exists(DUMPER_BIN):
        print(r.stdout, r.stderr)
        sys.exit("dumper build failed")
    subprocess.run(["git", "checkout", "cyrius.lock"], cwd=REPO, capture_output=True)
    return DUMPER_BIN


def run_dumper(font, ppem, gid0, gid1):
    """{(gid, ppem): Row} from one dumper build + run over [gid0, gid1) — exactly those keys, or
    the run stops naming the font, the ppem and the range (a binary another invocation wrote,
    or a dumper that stopped early, must never surface as a KeyError later)."""
    binary = build_dumper(font, ppem, gid0, gid1)
    r = subprocess.run([binary], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("dumper failed (rc %d) on %s ppem %d gids %d..%d:\n%s" % (r.returncode, font, ppem, gid0, gid1, r.stderr))
    rows = parse_dump(r.stdout)
    want = set((g, ppem) for g in range(gid0, gid1))
    got = set(rows)
    if got != want:
        missing, extra = sorted(want - got), sorted(got - want)
        sys.exit("dumper %s on %s ppem %d gids %d..%d answered the wrong rows: %d missing%s, %d extra%s"
                 % (binary, font, ppem, gid0, gid1, len(missing),
                    " (first %s)" % (missing[0],) if missing else "", len(extra),
                    " (first %s)" % (extra[0],) if extra else ""))
    return rows


class Dump(object):
    """rekha's rows, from a saved file (--dump-file) or from dumper runs on demand."""

    def __init__(self, font, dump_file=None):
        self.font = font
        self.rows = parse_dump(open(dump_file).read()) if dump_file else None
        self.fixed = dump_file is not None

    def get_range(self, ppem, gid0, gid1):
        if self.rows is None:
            self.rows = {}
        missing = [g for g in range(gid0, gid1) if (g, ppem) not in self.rows]
        if missing:
            if self.fixed:
                sys.exit("--dump-file lacks gid %d at %d ppem" % (missing[0], ppem))
            lo, hi = min(missing), max(missing) + 1
            self.rows.update(run_dumper(self.font, ppem, lo, hi))
        return {g: self.rows[(g, ppem)] for g in range(gid0, gid1)}

    def get(self, gid, ppem):
        return self.get_range(ppem, gid, gid + 1)[gid]


# ----------------------------------------------------------------------------------------------
# The comparison
# ----------------------------------------------------------------------------------------------
class Result(object):
    def __init__(self, gid, ppem):
        self.gid, self.ppem = gid, ppem
        self.cls = "agree"  # agree | refused | ft-pedantic-fails | count | advance | points | tags
        self.point_diffs = []  # (i, axis, got, want)
        self.tag_diffs = []  # (i, got, want)
        self.notes = []


def compare(oracle, row, gid, ppem):
    """Classify one (gid, ppem): rekha's row against FreeType's load."""
    res = Result(gid, ppem)
    try:
        points, tags, ends, adv = oracle.want(gid, ppem)
    except ftshim.FTError as e:
        res.cls = "ft-load-fails"
        res.notes.append("FreeType refused the load: %s" % e)
        return res
    if row.status != 1:
        res.cls = "ft-pedantic-fails" if not oracle.pedantic_ok(gid, ppem) else "refused"
        res.notes.append("rekha refused: error %d %s" % (row.err, row.detail or "-"))
        return res
    if row.n != len(points) or row.ends != list(ends):
        res.cls = "count"
        res.notes.append("points got %d want %d, ends got %s want %s" % (row.n, len(points), row.ends, list(ends)))
        return res
    if row.advpx * 64 != adv:
        res.cls = "advance"
        res.notes.append("advance got %d px (%d F26Dot6 raw) want %d F26Dot6 (%d px)" % (row.advpx, row.adv, adv, adv // 64))
    for i in range(len(points)):
        if row.points[i][0] != points[i][0]:
            res.point_diffs.append((i, "x", row.points[i][0], points[i][0]))
        if row.points[i][1] != points[i][1]:
            res.point_diffs.append((i, "y", row.points[i][1], points[i][1]))
        if row.tags[i] != tags[i]:
            res.tag_diffs.append((i, row.tags[i], tags[i]))
    if res.point_diffs and res.cls == "agree":
        res.cls = "points"
    if res.tag_diffs and res.cls == "agree":
        res.cls = "tags"
    return res


def listing(code):
    """The disassembly with the function number of each CALL guessed from the push before it."""
    toks = hu.disasm(code)
    out, last_push = [], None
    for t in toks:
        if t.startswith("PUSHB ") or t.startswith("PUSHW "):
            last_push = t.split()[1:]
            out.append(t)
        elif t == "CALL" and last_push:
            out.append("CALL(fn %s?)" % last_push[-1])
            last_push = last_push[:-1] or None
        else:
            out.append(t)
            if t not in ("SRP0", "SRP1", "SRP2", "SLOOP", "SZP0", "SZP1", "SZP2", "SZPS"):
                last_push = None
            elif last_push:
                last_push = last_push[:-1] or None
    return " ".join(out)


def sub_agree(oracle, dump, cg, ppem):
    """A component's own row against FreeType after a fresh size request (advisory)."""
    oracle.size(ppem)
    return compare(oracle, dump.get(cg, ppem), cg, ppem).cls == "agree"


def report(oracle, dump, res, verbose=False):
    """The MISMATCH block for one result (or the verbose table for `diff`)."""
    gid, ppem = res.gid, res.ppem
    kind = oracle.kind(gid)
    row = dump.get(gid, ppem)
    if kind == "composite":
        comps, n_ins, prog = oracle.gf.components(gid)
    else:
        comps, n_ins, prog = [], (oracle.gf.simple_n_ins(gid) if kind == "simple" else 0), (
            oracle.gf.simple_program(gid) if kind == "simple" else b"")
    head = "%s gid %d %s %s n_ins %d ppem %d: " % (
        "MISMATCH" if res.cls not in ("agree",) else "AGREE", gid, oracle.name(gid), kind, n_ins, ppem)
    if res.cls in ("refused", "ft-pedantic-fails", "ft-load-fails", "count"):
        head += res.cls + " — " + "; ".join(res.notes)
    else:
        head += "%d points differ, advance %s, tags %s" % (
            len(res.point_diffs), "DIFFERS" if any(n.startswith("advance") for n in res.notes) else "ok",
            "%d differ" % len(res.tag_diffs) if res.tag_diffs else "ok")
        if any(n.startswith("advance") for n in res.notes):
            head += " (%s)" % [n for n in res.notes if n.startswith("advance")][0]
    print(head)
    tags_by_i = {i: (g, w) for i, g, w in res.tag_diffs}
    for i, axis, got, want in res.point_diffs:
        extra = "     tag got %d want %d" % tags_by_i[i] if i in tags_by_i else ""
        print("    point %3d %s  got %6d want %6d delta %5d%s" % (i, axis, got, want, got - want, extra))
    seen = set(i for i, _, _, _ in res.point_diffs)
    for i, got, want in res.tag_diffs:
        if i not in seen:
            print("    point %3d tag got %d want %d" % (i, got, want))
    if verbose and res.cls not in ("refused", "ft-pedantic-fails", "ft-load-fails", "count"):
        points, tags, ends, adv = oracle.want(gid, ppem)
        raw, _, _ = ftshim.hinted(oracle.face, ppem, gid, hint=False)
        print("  contours %s, advance FreeType %d, rekha %d px (%d raw)" % (list(ends), adv, row.advpx, row.adv))
        print("  %4s %-14s %-14s %-14s %-12s %s" % ("i", "unhinted", "freetype", "rekha", "delta", "tags ft/rk"))
        for i in range(len(points)):
            d = (row.points[i][0] - points[i][0], row.points[i][1] - points[i][1])
            print("  %4d %-14s %-14s %-14s %-12s %d/%d%s" % (
                i, raw[i], points[i], row.points[i], d if d != (0, 0) else "", tags[i], row.tags[i],
                "  <--" if d != (0, 0) or tags[i] != row.tags[i] else ""))
    if prog:
        print("  program (%d B): %s" % (len(prog), listing(prog)))
    if comps:
        # advisory, after every glyph of the ppem was classified: each component on its own,
        # FreeType given a fresh `prep` before it (a component's own row in a whole-face dump
        # was loaded in gid order, which this cannot replay)
        for k, (flags, cg, a1, a2, m) in enumerate(comps):
            oracle.size(ppem)
            sub = compare(oracle, dump.get(cg, ppem), cg, ppem)
            verdict = "own hint agrees with FreeType" if sub.cls == "agree" else "own hint %s" % sub.cls
            off = "match (%d, %d)" % (a1, a2) if not flags & hg.ARGS_ARE_XY_VALUES else "(%d, %d)" % (a1, a2)
            mat = "" if m is None else " 2x2 %s" % (m,)
            print("  components: [%d] gid %d %s %s flags 0x%04x %s %s%s — %s" % (
                k, cg, oracle.name(cg), oracle.kind(cg), flags, hg.flag_names(flags), off, mat, verdict))
        if res.cls in ("points", "tags", "advance") and all(
                sub_agree(oracle, dump, cg, ppem) for _, cg, _, _, _ in comps):
            print("  every component agrees on its own: a composite-rule difference (offset rounding, the "
                  "USE_MY_METRICS phantoms, the untouch, the 1.0 scale of the composite program)")


# ----------------------------------------------------------------------------------------------
# Modes
# ----------------------------------------------------------------------------------------------
def opt(argv, name, default=None):
    if name in argv:
        k = argv.index(name)
        v = argv[k + 1]
        del argv[k : k + 2]
        return v
    return default


def flag(argv, name):
    if name in argv:
        argv.remove(name)
        return True
    return False


def parse_ppems(v, default):
    return tuple(int(x) for x in v.split(",")) if v else default


def sweep_face(oracle, dump, ppems, first=None, headers_only=False, quiet=False, gids=None):
    """The per-ppem summary over every glyph (or `gids`); returns (n_bad, counts per ppem).
    FreeType is loaded in the dumper's order: one size request per ppem and then every glyph in
    gid order for a whole face (one dumper process), a size request before each glyph with
    `gids` (a dumper process per glyph); every glyph is classified before any is reported."""
    totals, n_bad, listed = [], 0, 0
    for ppem in ppems:
        results = []
        if gids is None:
            rows = dump.get_range(ppem, 0, oracle.num_glyphs)
            oracle.size(ppem)
            for gid in range(oracle.num_glyphs):
                results.append(compare(oracle, rows[gid], gid, ppem))
        else:
            for gid in gids:
                row = dump.get(gid, ppem)
                oracle.size(ppem)
                results.append(compare(oracle, row, gid, ppem))
        c = {"agree": 0, "refused": 0, "ft-pedantic-fails": 0, "ft-load-fails": 0, "count": 0,
             "advance": 0, "points": 0, "tags": 0, "simple": 0, "composite": 0}
        for res in results:
            gid = res.gid
            c[res.cls] += 1
            if res.cls in ("count", "advance", "points", "tags", "refused"):
                n_bad += 1
                c[oracle.kind(gid) if oracle.kind(gid) in ("simple", "composite") else "simple"] += 1
                if not quiet and (first is None or listed < first):
                    if headers_only:
                        print("MISMATCH gid %d %s %s ppem %d: %s" % (gid, oracle.name(gid), oracle.kind(gid), ppem, res.cls))
                    else:
                        report(oracle, dump, res)
                    listed += 1
        differ = c["count"] + c["advance"] + c["points"] + c["tags"]
        print("ppem %2d: %d glyphs — %d agree, %d differ (%d simple, %d composite: %d count, %d advance, "
              "%d points, %d tags), %d refused, %d FreeType-pedantic-fails, %d FreeType-load-fails"
              % (ppem, len(results), c["agree"], differ, c["simple"], c["composite"], c["count"],
                 c["advance"], c["points"], c["tags"], c["refused"], c["ft-pedantic-fails"], c["ft-load-fails"]))
        totals.append(c)
    return n_bad, totals


def cmd_sweep(argv):
    font = opt(argv, "--font", DEFAULT_FONT)
    dump_file = opt(argv, "--dump-file")
    ppems = parse_ppems(opt(argv, "--ppems"), PPEMS)
    first = opt(argv, "--first")
    gids = opt(argv, "--gids")
    headers_only = flag(argv, "--list")
    oracle = Oracle(font)
    dump = Dump(font, dump_file)
    gid_list = [int(g) for g in gids.split(",")] if gids else None
    n_bad, _ = sweep_face(oracle, dump, ppems, int(first) if first else None, headers_only, gids=gid_list)
    print("FreeType %s (%s) v%d vs rekha (%s); %s; %d loads; exit %d" % (
        ftshim.version_string(), ftshim.library_path(), ftshim.INTERPRETER_VERSION,
        "dump file " + dump_file if dump_file else "build/" + DUMPER_NAME, font,
        (len(gid_list) if gid_list else oracle.num_glyphs) * len(ppems), 1 if n_bad else 0))
    oracle.close()
    return 1 if n_bad else 0


def cmd_diff(argv):
    font = opt(argv, "--font", DEFAULT_FONT)
    dump_file = opt(argv, "--dump-file")
    if len(argv) < 2:
        sys.exit("diff needs <gid|char> <ppem>")
    oracle = Oracle(font)
    tok, ppem = argv[0], int(argv[1])
    gid = int(tok) if tok.isdigit() else ftshim.char_index(oracle.face, tok)
    dump = Dump(font, dump_file)
    row = dump.get(gid, ppem)
    oracle.size(ppem)
    res = compare(oracle, row, gid, ppem)
    report(oracle, dump, res, verbose=True)
    oracle.close()
    return 0 if res.cls == "agree" else 1


def hinted_face(path):
    """True when the file is an sfnt with glyf, fpgm and prep (a hinted TrueType face)."""
    try:
        data = open(path, "rb").read(4096)
        if data[:4] not in (b"\x00\x01\x00\x00", b"true"):
            return False
        n = struct.unpack(">H", data[4:6])[0]
        tags = set(data[12 + 16 * i : 16 + 16 * i] for i in range(min(n, 64)))
        return {b"glyf", b"fpgm", b"prep"} <= tags
    except (OSError, struct.error):
        return False


def one_per_family(paths):
    """One face per family: the filename up to its first '-', the -Regular where there is one."""
    fam = {}
    for p in paths:
        name = os.path.splitext(os.path.basename(p))[0]
        key = name.split("-")[0]
        cur = fam.get(key)
        if cur is None or (name.endswith("-Regular") and not os.path.basename(cur).startswith(key + "-Regular.")):
            fam[key] = p
    return sorted(fam.values())


def cmd_corpus(argv):
    ppems = parse_ppems(opt(argv, "--ppems"), CORPUS_PPEMS)
    dedup = flag(argv, "--one-per-family")
    dirs = argv or DIRS
    paths = set()
    for d in dirs:
        if os.path.isfile(d):
            paths.add(d)
        else:
            paths |= set(glob.glob(os.path.join(d, "**", "*.ttf"), recursive=True))
    paths = sorted(p for p in paths if hinted_face(p))
    if dedup:
        paths = one_per_family(paths)
    print("# %d hinted TrueType faces under %s at ppems %s (advisory%s)" % (
        len(paths), " ".join(dirs), ",".join(str(p) for p in ppems), ", one per family" if dedup else ""))
    sys.stdout.flush()
    print("# %-60s %7s %7s %7s %7s %7s" % ("face", "loads", "agree", "refused", "differ", "ft-ped"))
    for path in paths:
        try:
            oracle = Oracle(path)
        except ftshim.FTError as e:
            print("# %-60s FreeType cannot open it: %s" % (path[-60:], e))
            continue
        dump = Dump(path)
        try:
            _, totals = sweep_face(oracle, dump, ppems, quiet=True)
        except SystemExit as e:
            print("# %-60s dumper failed: %s" % (path[-60:], e))
            oracle.close()
            continue
        agree = sum(c["agree"] for c in totals)
        refused = sum(c["refused"] for c in totals)
        differ = sum(c["count"] + c["advance"] + c["points"] + c["tags"] for c in totals)
        ped = sum(c["ft-pedantic-fails"] for c in totals)
        print("  %-60s %7d %7d %7d %7d %7d" % (path[-60:], oracle.num_glyphs * len(ppems), agree, refused, differ, ped))
        sys.stdout.flush()
        oracle.close()
    return 0


def mkdump_text(oracle, ppem, gid0, gid1):
    """FreeType's rows for [gid0, gid1) in the dumper's format, loaded as the dumper loads them:
    one size request, then the glyphs in order."""
    blocks = []
    oracle.size(ppem)
    for gid in range(gid0, gid1):
        try:
            points, tags, ends, adv = oracle.want(gid, ppem)
        except ftshim.FTError as e:
            blocks.append(format_row(gid, ppem, 0, 7, "FreeType: %s" % e, [], [], [], 0, 0))
            continue
        blocks.append(format_row(gid, ppem, 1, 0, "", points, tags, list(ends), adv, adv // 64))
    return "\n".join(blocks) + "\n"


def cmd_mkdump(argv):
    font = opt(argv, "--font", DEFAULT_FONT)
    if len(argv) < 4:
        sys.exit("mkdump needs <out> <ppem> <gid0> <gid1>")
    oracle = Oracle(font)
    out, ppem, gid0, gid1 = argv[0], int(argv[1]), int(argv[2]), int(argv[3])
    open(out, "w").write(mkdump_text(oracle, ppem, gid0, gid1))
    print("wrote %s: %d glyphs at %d ppem in the dumper's format (FreeType's numbers)" % (out, gid1 - gid0, ppem))
    oracle.close()
    return 0


def cmd_selftest(argv):
    """Two glyphs — 'H' (simple) and 'é' (composite, whose components e and acute are dumped
    too) at 12 ppem — from FreeType through the dumper format: parse and compare (0 mismatches),
    then one x edited by +3 (1 mismatch, reported with got/want/delta and the program)."""
    font = opt(argv, "--font", DEFAULT_FONT)
    oracle = Oracle(font)
    ppem = 12
    h, e_acute = ftshim.char_index(oracle.face, "H"), ftshim.char_index(oracle.face, "é")
    comps = [cg for _, cg, _, _, _ in oracle.gf.components(e_acute)[0]]
    text = "".join(mkdump_text(oracle, ppem, g, g + 1) for g in [h, e_acute] + comps)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "hint_selftest.dump")
    open(path, "w").write(text)
    rows = parse_dump(text)
    assert len(rows) == 2 + len(comps), len(rows)
    dump = Dump(font, path)
    oracle.size(ppem)
    res = [compare(oracle, dump.get(g, ppem), g, ppem) for g in (h, e_acute)]
    for r in res:
        assert r.cls == "agree", (r.gid, r.cls, r.notes)
    print("selftest 1: %d rows parsed, gid %d and gid %d agree with FreeType (0 mismatches)" % (len(rows), h, e_acute))
    for r in res:
        report(oracle, dump, r)
    # one coordinate edited: point 7 of é, x + 3; and a tag bit flipped on H's point 0
    lines = text.split("\n")
    hit = 0
    for k, line in enumerate(lines):
        if line.startswith("gid %d " % e_acute):
            t = lines[k + 1 + 7].split()
            assert t[0] == "p" and t[1] == "7"
            lines[k + 1 + 7] = "p 7 %d %s %s" % (int(t[2]) + 3, t[3], t[4])
            hit += 1
        if line.startswith("gid %d " % h):
            t = lines[k + 1].split()
            lines[k + 1] = "p 0 %s %s %d" % (t[2], t[3], int(t[4]) ^ 2)
            hit += 1
    assert hit == 2
    bad_path = os.path.join(OUT, "hint_selftest_bad.dump")
    open(bad_path, "w").write("\n".join(lines))
    dump2 = Dump(font, bad_path)
    oracle.size(ppem)
    r_e = compare(oracle, dump2.get(e_acute, ppem), e_acute, ppem)
    r_h = compare(oracle, dump2.get(h, ppem), h, ppem)
    assert r_e.cls == "points" and r_e.point_diffs == [(7, "x", r_e.point_diffs[0][3] + 3, r_e.point_diffs[0][3])], r_e.point_diffs
    assert r_h.cls == "tags" and len(r_h.tag_diffs) == 1 and r_h.tag_diffs[0][0] == 0, r_h.tag_diffs
    print("selftest 2: the edited dump — gid %d one point off by +3 in x, gid %d one tag bit flipped:" % (e_acute, h))
    report(oracle, dump2, r_e)
    report(oracle, dump2, r_h)
    print("selftest 3: the sweep summary over the edited dump's four glyphs (2 mismatches, exit 1):")
    n_bad, _ = sweep_face(oracle, dump2, (ppem,), headers_only=True, gids=[h, e_acute] + comps)
    assert n_bad == 2, n_bad
    n_ok, _ = sweep_face(oracle, dump, (ppem,), quiet=True, gids=[h, e_acute] + comps)
    assert n_ok == 0, n_ok
    print("selftest: ok (%s and %s kept under build/)" % (path, bad_path))
    oracle.close()
    return 0


def main():
    cmds = {"sweep": cmd_sweep, "diff": cmd_diff, "corpus": cmd_corpus, "mkdump": cmd_mkdump, "selftest": cmd_selftest}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        return 2
    return cmds[sys.argv[1]](sys.argv[2:]) or 0


if __name__ == "__main__":
    sys.exit(main())
