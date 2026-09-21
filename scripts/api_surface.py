#!/usr/bin/env python3
"""rekha's API-surface gate (0.9.0, the freeze).

    python3 scripts/api_surface.py --check     # CI: exit 1 on any violation, listing each
    python3 scripts/api_surface.py --update    # rewrite docs/api/surface.txt, then --check

The public surface IS what the compiler enforces: every `public fn` / `public var` in src/, in a
bundle that begins with `private` (src/freeze.cyr, the first [lib] module). This script pins the
conventions AROUND that declaration, none of which the compiler checks:

  1. spelling — `public fn name(` / `public var NAME` on the item's own line (the textual
     `cyrius api-surface` scanner and the compiler agree only on that form); never `pub`, never
     `public` alone on a line, never `private fn`, one name per `public var`;
  2. governance — every public item sits under a `# @public` doc comment (the nearest column-0
     comment block above it, no blank line between; a RUN of `public fn` one-liners with no blank
     lines between them shares one block), and every `# @public` block governs a public item;
  3. src/freeze.cyr holds one code line, `private`; it is FIRST in both module lists of
     cyrius.cyml; src/lib.cyr does not include it; no other src module says `private`;
  4. the dist bundles begin with `private` and carry exactly the src surface (`dist/rekha.cyr`
     without the woff modules, `dist/rekha-woff.cyr` with them);
  5. docs/api/*.md documents every surface name exactly once — a fn as a `### `name(` heading,
     a constant or enum member as a `### `NAME`` heading or the first cell of a table row — and
     documents nothing that is not on the surface;
  6. docs/api/surface.txt (module::name/arity, module::NAME = value) equals the computed surface.

fonts/face_data.cyr is generated (scripts/face2cyr.py), consumed by path and never through a
bundle; every fn in it is public by construction and listed under `face_data::`.
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURFACE_TXT = os.path.join(ROOT, "docs", "api", "surface.txt")
FREEZE = "src/freeze.cyr"

RE_FN = re.compile(r"^(public )?fn ([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)")
RE_VAR = re.compile(r"^(public )?var ([A-Za-z_][A-Za-z0-9_]*)\s*(=\s*([^;#]*?)\s*;)?")
RE_ENUM_MEMBER = re.compile(r"^\s+([A-Z][A-Z0-9_]*)\s*=\s*([^;]+);")
RE_HEADING_FN = re.compile(r"^###\s+`([A-Za-z_][A-Za-z0-9_]*)\(")
RE_HEADING_CONST = re.compile(r"^###\s+`([A-Z][A-Z0-9_]*)`")
RE_ROW_CONST = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]*)`\s*\|")


class Item:
    def __init__(self, module, kind, name, arity=None, value=None, line=0, public=False):
        self.module, self.kind, self.name = module, kind, name
        self.arity, self.value, self.line, self.public = arity, value, line, public

    def bare(self):
        return self.key().split("::", 1)[1]

    def key(self):
        if self.kind == "fn":
            return "%s::%s/%d" % (self.module, self.name, self.arity)
        if self.kind == "var":
            return "%s::%s = %s" % (self.module, self.name, self.value)
        return "%s::%s = %s (enum)" % (self.module, self.name, self.value)


def module_name(path):
    return os.path.splitext(os.path.basename(path))[0]


def arity_of(params):
    params = params.strip()
    return 0 if params == "" else len([p for p in params.split(",") if p.strip() != ""])


def scan(path, problems, want_governance=True):
    """Return (items, has_private): every fn / var / enum member in `path`, with visibility."""
    mod = module_name(path)
    items = []
    has_private = False
    gov = None           # the governing comment block: dict(tagged, line, used) or None
    in_run = False       # inside a run of one-liner public fns sharing `gov`
    in_body = False      # inside a multi-line fn body
    in_enum = False
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for i, raw in enumerate(lines):
        n = i + 1
        line = raw.rstrip("\r")
        if in_enum:
            m = RE_ENUM_MEMBER.match(line)
            if m:
                items.append(Item(mod, "enum", m.group(1), value=m.group(2).strip(), line=n, public=True))
            if line.startswith("}"):
                in_enum = False
            continue
        if in_body:
            if line.startswith("}"):
                in_body = False
                in_run = False
                gov = None
            continue
        if line == "":
            gov = None
            in_run = False
            continue
        if line.startswith("#"):
            if in_run:
                # a comment inside a run does not start a new block unless it is tagged
                if re.match(r"^#\s*@public\b", line):
                    gov = {"tagged": True, "line": n, "used": False}
                    in_run = False
                continue
            if gov is None or gov.get("closed"):
                gov = {"tagged": False, "line": n, "used": False}
            if re.match(r"^#\s*@public\b", line):
                gov["tagged"] = True
            if re.search(r"@internal\b", line) and not line.startswith("# @internal"):
                pass
            continue
        # a code line at column 0
        if gov is not None and not gov.get("closed"):
            gov["closed"] = True
        if line.startswith("private") and (line == "private" or line == "private;"):
            has_private = True
            continue
        if re.match(r"^private\b", line):
            problems.append("%s:%d: `%s` — `private` must be alone on its line" % (path, n, line))
            has_private = True
            continue
        if re.match(r"^pub\b", line) and not line.startswith("public"):
            problems.append("%s:%d: `pub` is not the spelling the freeze uses; write `public`" % (path, n))
            continue
        if line == "public" or line == "public;":
            problems.append("%s:%d: `public` alone on a line; put it on the item's line" % (path, n))
            continue
        m = RE_FN.match(line)
        if m:
            pub = m.group(1) is not None
            it = Item(mod, "fn", m.group(2), arity=arity_of(m.group(3)), line=n, public=pub)
            items.append(it)
            one_liner = line.rstrip().endswith("}")
            if want_governance:
                if pub:
                    if gov is None or not gov["tagged"]:
                        problems.append("%s:%d: public fn %s is not governed by a `# @public` comment" % (path, n, it.name))
                    else:
                        gov["used"] = True
                else:
                    if gov is not None and gov["tagged"] and not in_run:
                        problems.append("%s:%d: a `# @public` comment (line %d) governs the INTERNAL fn %s" % (path, n, gov["line"], it.name))
            if one_liner:
                in_run = True
            else:
                in_body = True
                in_run = False
            continue
        m = RE_VAR.match(line)
        if m:
            pub = m.group(1) is not None
            if "," in (m.group(4) or "") and "(" not in (m.group(4) or ""):
                problems.append("%s:%d: one name per `var` line" % (path, n))
            it = Item(mod, "var", m.group(2), value=(m.group(4) or "").strip(), line=n, public=pub)
            items.append(it)
            if want_governance:
                if pub:
                    if gov is None or not gov["tagged"]:
                        problems.append("%s:%d: public var %s is not governed by a `# @public` comment" % (path, n, it.name))
                    else:
                        gov["used"] = True
                elif gov is not None and gov["tagged"] and not in_run:
                    problems.append("%s:%d: a `# @public` comment (line %d) governs the INTERNAL var %s" % (path, n, gov["line"], it.name))
            in_run = True   # constants come in runs under one comment too
            continue
        if line.startswith("enum "):
            in_enum = True
            in_run = False
            gov = None
            continue
        # any other code line (include, struct, `}` …) ends a run
        in_run = False
        gov = None
    # orphan check needs a second pass: blocks that were tagged and never used
    if want_governance:
        for prob in orphan_blocks(path, lines):
            problems.append(prob)
    return items, has_private


def orphan_blocks(path, lines):
    """Every `# @public` block must be followed (no blank line) by a public item or a run that
    holds one. Reports blocks that govern nothing public."""
    out = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].startswith("#") and re.match(r"^#\s*@public\b", lines[i]):
            start = i
            while i < n and lines[i].startswith("#"):
                i += 1
            # what follows the block, until a blank line or a multi-line fn ends
            governed_public = False
            j = i
            while j < n:
                l = lines[j]
                if l == "":
                    break
                if l.startswith("#"):
                    j += 1
                    continue
                if l.startswith("public fn") or l.startswith("public var"):
                    governed_public = True
                    break
                if l.startswith("fn ") or l.startswith("var "):
                    if l.rstrip().endswith("}") or l.startswith("var "):
                        j += 1
                        continue
                    break
                break
            if not governed_public:
                out.append("%s:%d: `# @public` comment governs no public item (orphan)" % (path, start + 1))
        else:
            i += 1
    return out


def cyml_modules(section):
    text = open(os.path.join(ROOT, "cyrius.cyml"), encoding="utf-8").read()
    m = re.search(r"^\[%s\]\s*\n((?:.*\n)*?)modules\s*=\s*\[(.*?)\]" % re.escape(section), text, re.M | re.S)
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(2))


def compute(problems):
    """The surface from src/ (+ fonts/face_data.cyr): list of Items with public=True, and the
    woff-only module names."""
    lib = cyml_modules("lib")
    woff = cyml_modules("lib.woff")
    if not lib or not woff:
        problems.append("cyrius.cyml: could not read [lib].modules / [lib.woff].modules")
    if lib[:1] != [FREEZE]:
        problems.append("cyrius.cyml: [lib].modules must begin with %s (is %s)" % (FREEZE, lib[:1]))
    if woff[:1] != [FREEZE]:
        problems.append("cyrius.cyml: [lib.woff].modules must begin with %s (is %s)" % (FREEZE, woff[:1]))
    woff_only = sorted(set(module_name(m) for m in woff) - set(module_name(m) for m in lib))
    surface = []
    src_files = sorted(glob.glob(os.path.join(ROOT, "src", "*.cyr")))
    for path in src_files:
        rel = os.path.relpath(path, ROOT)
        items, has_private = scan(path, problems)
        if rel == FREEZE:
            code = [l for l in open(path, encoding="utf-8").read().split("\n") if l != "" and not l.startswith("#")]
            if code != ["private"]:
                problems.append("%s: must hold exactly one code line, `private` (holds %r)" % (rel, code))
            if items:
                problems.append("%s: must define nothing" % rel)
            continue
        if has_private:
            problems.append("%s: says `private`; only %s may" % (rel, FREEZE))
        if rel == "src/lib.cyr":
            if "freeze.cyr" in open(path, encoding="utf-8").read():
                problems.append("src/lib.cyr must not include %s (the src chain stays open to the tests)" % FREEZE)
            continue
        surface.extend([it for it in items if it.public])
    if not os.path.exists(os.path.join(ROOT, FREEZE)):
        problems.append("%s is missing" % FREEZE)
    face = os.path.join(ROOT, "fonts", "face_data.cyr")
    if os.path.exists(face):
        items, _ = scan(face, problems, want_governance=False)
        for it in items:
            if it.kind == "fn":
                it.public = True
                it.module = "face_data"
                surface.append(it)
    else:
        problems.append("fonts/face_data.cyr is missing")
    return surface, woff_only


def check_dist(surface, woff_only, problems):
    for rel, exclude in (("dist/rekha.cyr", set(woff_only)), ("dist/rekha-woff.cyr", set())):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            problems.append("%s is missing" % rel)
            continue
        lines = open(path, encoding="utf-8").read().split("\n")
        first = next((l for l in lines if l != "" and not l.startswith("#")), None)
        if first != "private":
            problems.append("%s: first code line must be `private` (is %r)" % (rel, first))
        want = set(it.bare() for it in surface if it.module != "face_data" and it.module not in exclude)
        items, _ = scan(path, [], want_governance=False)
        got = set(it.bare() for it in items if it.public and it.kind != "enum")
        want_ne = set(k for k in want if "(enum)" not in k)
        for k in sorted(want_ne - got):
            problems.append("%s: missing public item %s (stale dist? run `cyrius distlib --all`)" % (rel, k))
        for k in sorted(got - want_ne):
            problems.append("%s: public item %s is not in src/ (stale dist?)" % (rel, k))


def check_docs(surface, problems):
    pages = sorted(glob.glob(os.path.join(ROOT, "docs", "api", "*.md")))
    if not pages:
        problems.append("docs/api/*.md: no pages")
        return
    seen = {}
    for page in pages:
        rel = os.path.relpath(page, ROOT)
        for i, line in enumerate(open(page, encoding="utf-8").read().split("\n")):
            m = RE_HEADING_FN.match(line)
            if m:
                seen.setdefault(m.group(1), []).append("%s:%d" % (rel, i + 1))
                continue
            m = RE_HEADING_CONST.match(line) or RE_ROW_CONST.match(line)
            if m:
                seen.setdefault(m.group(1), []).append("%s:%d" % (rel, i + 1))
    names = {}
    for it in surface:
        names.setdefault(it.name, it)
    for name, it in sorted(names.items()):
        where = seen.get(name, [])
        if len(where) == 0:
            problems.append("docs/api: %s %s (%s:%d) is not documented" % (it.kind, name, it.module, it.line))
        elif len(where) > 1:
            problems.append("docs/api: %s documented %d times: %s" % (name, len(where), ", ".join(where)))
    for name, where in sorted(seen.items()):
        if name not in names and (name.startswith("rekha_") or name.startswith("REKHA_")):
            problems.append("docs/api: %s is documented at %s but is not public" % (name, where[0]))


def surface_text(surface):
    keys = sorted(it.key() for it in surface)
    fns = sum(1 for it in surface if it.kind == "fn")
    vars_ = sum(1 for it in surface if it.kind == "var")
    enums = sum(1 for it in surface if it.kind == "enum")
    head = [
        "# rekha public API surface — generated by scripts/api_surface.py --update; CI checks it.",
        "# %d functions, %d constants, %d enum members. module::name/arity, module::NAME = value."
        % (fns, vars_, enums),
    ]
    return "\n".join(head + keys) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--list", action="store_true", help="print the surface and exit")
    a = ap.parse_args()
    problems = []
    surface, woff_only = compute(problems)
    if a.list:
        sys.stdout.write(surface_text(surface))
        return 0
    text = surface_text(surface)
    if a.update:
        os.makedirs(os.path.dirname(SURFACE_TXT), exist_ok=True)
        with open(SURFACE_TXT, "w", encoding="utf-8") as f:
            f.write(text)
        print("api-surface: wrote %s" % os.path.relpath(SURFACE_TXT, ROOT))
    check_dist(surface, woff_only, problems)
    check_docs(surface, problems)
    if not os.path.exists(SURFACE_TXT):
        problems.append("docs/api/surface.txt is missing (run --update)")
    elif open(SURFACE_TXT, encoding="utf-8").read() != text:
        problems.append("docs/api/surface.txt is stale (run --update and commit it)")
    fns = sum(1 for it in surface if it.kind == "fn" and it.module != "face_data")
    face = sum(1 for it in surface if it.module == "face_data")
    vars_ = sum(1 for it in surface if it.kind == "var")
    enums = sum(1 for it in surface if it.kind == "enum")
    for p in problems:
        print("api-surface: FAIL " + p)
    print("api-surface: %d public fns in src, %d in fonts/face_data.cyr, %d constants, %d enum members; %d problem(s)"
          % (fns, face, vars_, enums, len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
