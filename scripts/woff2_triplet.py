#!/usr/bin/env python3
"""woff2_triplet.py — the W3C "Triplet Encoding" table, and what rekha checks itself against.

    python3 scripts/woff2_triplet.py emit   [out.cyr]   # write programs/woff2_vectors.cyr
    python3 scripts/woff2_triplet.py verify <spec.html> # re-extract the table from the spec and diff

WHY THIS EXISTS. src/woff2.cyr decodes a point's (dx, dy) with ARITHMETIC — six ranges of `i`, a
base, a nibble split and two signs — where the spec gives a 128-row table (WOFF File Format 2.0,
subclause 5.2). That is a deliberate trade: no 128-entry literal in the library, at the cost of a
closed form that could be subtly wrong in a way no round trip would catch, because the test
encoder and the decoder would share the mistake.

So the table below is the spec's, transcribed, and this script does two things with it:

  `verify` re-extracts the table from a local copy of the W3C HTML and requires a byte-equal match,
  so the transcription can be re-audited against the source whenever the spec moves.

  `emit` writes programs/woff2_vectors.cyr — the expected (dx, dy) for every one of the 128 indices
  under two fixed coordinate-byte patterns, computed FROM THE TABLE and from nothing in rekha. CI
  requires the committed file to equal a fresh emit, exactly as it does for fonts/face_data.cyr.

THE TABLE. Columns: index, byte count (the flag byte included), x bits, y bits, delta x, delta y,
x sign, y sign. The spec prints it with blank cells inheriting downwards; it is written out in full
here. 'N/A' means the coordinate is not encoded at all and is zero.
"""
import sys

SPEC_TABLE = """\
0	2	0	8	N/A	0	N/A	-
1	2	0	8	N/A	0	N/A	+
2	2	0	8	N/A	256	N/A	-
3	2	0	8	N/A	256	N/A	+
4	2	0	8	N/A	512	N/A	-
5	2	0	8	N/A	512	N/A	+
6	2	0	8	N/A	768	N/A	-
7	2	0	8	N/A	768	N/A	+
8	2	0	8	N/A	1024	N/A	-
9	2	0	8	N/A	1024	N/A	+
10	2	8	0	0	N/A	-	N/A
11	2	8	0	0	N/A	+	N/A
12	2	8	0	256	N/A	-	N/A
13	2	8	0	256	N/A	+	N/A
14	2	8	0	512	N/A	-	N/A
15	2	8	0	512	N/A	+	N/A
16	2	8	0	768	N/A	-	N/A
17	2	8	0	768	N/A	+	N/A
18	2	8	0	1024	N/A	-	N/A
19	2	8	0	1024	N/A	+	N/A
20	2	4	4	1	1	-	-
21	2	4	4	1	1	+	-
22	2	4	4	1	1	-	+
23	2	4	4	1	1	+	+
24	2	4	4	1	17	-	-
25	2	4	4	1	17	+	-
26	2	4	4	1	17	-	+
27	2	4	4	1	17	+	+
28	2	4	4	1	33	-	-
29	2	4	4	1	33	+	-
30	2	4	4	1	33	-	+
31	2	4	4	1	33	+	+
32	2	4	4	1	49	-	-
33	2	4	4	1	49	+	-
34	2	4	4	1	49	-	+
35	2	4	4	1	49	+	+
36	2	4	4	17	1	-	-
37	2	4	4	17	1	+	-
38	2	4	4	17	1	-	+
39	2	4	4	17	1	+	+
40	2	4	4	17	17	-	-
41	2	4	4	17	17	+	-
42	2	4	4	17	17	-	+
43	2	4	4	17	17	+	+
44	2	4	4	17	33	-	-
45	2	4	4	17	33	+	-
46	2	4	4	17	33	-	+
47	2	4	4	17	33	+	+
48	2	4	4	17	49	-	-
49	2	4	4	17	49	+	-
50	2	4	4	17	49	-	+
51	2	4	4	17	49	+	+
52	2	4	4	33	1	-	-
53	2	4	4	33	1	+	-
54	2	4	4	33	1	-	+
55	2	4	4	33	1	+	+
56	2	4	4	33	17	-	-
57	2	4	4	33	17	+	-
58	2	4	4	33	17	-	+
59	2	4	4	33	17	+	+
60	2	4	4	33	33	-	-
61	2	4	4	33	33	+	-
62	2	4	4	33	33	-	+
63	2	4	4	33	33	+	+
64	2	4	4	33	49	-	-
65	2	4	4	33	49	+	-
66	2	4	4	33	49	-	+
67	2	4	4	33	49	+	+
68	2	4	4	49	1	-	-
69	2	4	4	49	1	+	-
70	2	4	4	49	1	-	+
71	2	4	4	49	1	+	+
72	2	4	4	49	17	-	-
73	2	4	4	49	17	+	-
74	2	4	4	49	17	-	+
75	2	4	4	49	17	+	+
76	2	4	4	49	33	-	-
77	2	4	4	49	33	+	-
78	2	4	4	49	33	-	+
79	2	4	4	49	33	+	+
80	2	4	4	49	49	-	-
81	2	4	4	49	49	+	-
82	2	4	4	49	49	-	+
83	2	4	4	49	49	+	+
84	3	8	8	1	1	-	-
85	3	8	8	1	1	+	-
86	3	8	8	1	1	-	+
87	3	8	8	1	1	+	+
88	3	8	8	1	257	-	-
89	3	8	8	1	257	+	-
90	3	8	8	1	257	-	+
91	3	8	8	1	257	+	+
92	3	8	8	1	513	-	-
93	3	8	8	1	513	+	-
94	3	8	8	1	513	-	+
95	3	8	8	1	513	+	+
96	3	8	8	257	1	-	-
97	3	8	8	257	1	+	-
98	3	8	8	257	1	-	+
99	3	8	8	257	1	+	+
100	3	8	8	257	257	-	-
101	3	8	8	257	257	+	-
102	3	8	8	257	257	-	+
103	3	8	8	257	257	+	+
104	3	8	8	257	513	-	-
105	3	8	8	257	513	+	-
106	3	8	8	257	513	-	+
107	3	8	8	257	513	+	+
108	3	8	8	513	1	-	-
109	3	8	8	513	1	+	-
110	3	8	8	513	1	-	+
111	3	8	8	513	1	+	+
112	3	8	8	513	257	-	-
113	3	8	8	513	257	+	-
114	3	8	8	513	257	-	+
115	3	8	8	513	257	+	+
116	3	8	8	513	513	-	-
117	3	8	8	513	513	+	-
118	3	8	8	513	513	-	+
119	3	8	8	513	513	+	+
120	4	12	12	0	0	-	-
121	4	12	12	0	0	+	-
122	4	12	12	0	0	-	+
123	4	12	12	0	0	+	+
124	5	16	16	0	0	-	-
125	5	16	16	0	0	+	-
126	5	16	16	0	0	-	+
127	5	16	16	0	0	+	+"""


def rows():
    out = []
    for line in SPEC_TABLE.strip().split("\n"):
        f = line.split("\t")
        assert len(f) == 8, line
        idx, nb, xb, yb, dx, dy, xs, ys = f
        num = lambda v: 0 if v in ("N/A", "") else int(v)
        sgn = lambda v: 0 if v in ("N/A", "") else (1 if v == "+" else -1)
        out.append((int(idx), num(nb), num(xb), num(yb), num(dx), num(dy), sgn(xs), sgn(ys)))
    assert len(out) == 128, len(out)
    assert [r[0] for r in out] == list(range(128))
    return out


def decode(row, data):
    """(dx, dy) for one row given its coordinate bytes, straight from the table's own columns."""
    _, nb, xb, yb, dx0, dy0, xs, ys = row
    need = nb - 1
    assert len(data) == need, (row, data)
    if xb == 0 and yb == 8:
        vx, vy = 0, data[0]
    elif xb == 8 and yb == 0:
        vx, vy = data[0], 0
    elif xb == 4 and yb == 4:
        vx, vy = data[0] >> 4, data[0] & 15
    elif xb == 8 and yb == 8:
        vx, vy = data[0], data[1]
    elif xb == 12 and yb == 12:
        vx = (data[0] << 4) | (data[1] >> 4)
        vy = ((data[1] & 15) << 8) | data[2]
    elif xb == 16 and yb == 16:
        vx = (data[0] << 8) | data[1]
        vy = (data[2] << 8) | data[3]
    else:
        raise AssertionError(row)
    x = (dx0 + vx) * (xs if xs else 0)
    y = (dy0 + vy) * (ys if ys else 0)
    return x, y


# The two coordinate-byte patterns the emitted vectors use. All-zero pins each row's BASE; the
# ascending one pins the nibble packing, the byte order and both signs.
PATTERNS = [lambda n: [0] * n, lambda n: [(0x12 + 0x37 * k) & 255 for k in range(n)]]


def emit(path):
    tab = rows()
    lines = []
    for pi, pat in enumerate(PATTERNS):
        for row in tab:
            data = pat(row[1] - 1)
            x, y = decode(row, data)
            lines.append((row[0], pi, row[1] - 1, data, x, y))
    body = []
    for idx, pi, nb, data, x, y in lines:
        d = (data + [0, 0, 0, 0])[:4]
        body.append(
            "    w2tv(p, %d, %d, %d, %d, %d, %d, %d, %d, %d);"
            % (idx, pi, nb, d[0], d[1], d[2], d[3], x, y)
        )
    src = [
        "# programs/woff2_vectors.cyr — GENERATED by scripts/woff2_triplet.py from the W3C",
        "# \"Triplet Encoding\" table (WOFF File Format 2.0, subclause 5.2). DO NOT EDIT.",
        "#",
        "# One row per (spec index, coordinate-byte pattern): the index, the pattern number, how many",
        "# coordinate bytes it consumes, those bytes, and the dx / dy the SPEC says they decode to.",
        "# Nothing here is derived from src/woff2.cyr — that is the point. CI requires this file to",
        "# equal a fresh `python3 scripts/woff2_triplet.py emit`.",
        "",
        "var REKHA_W2_NVEC = %d;" % len(lines),
        "",
        "fn w2tv(p, idx, pat, nb, b0, b1, b2, b3, x, y): i64 {",
        "    var q = p + (idx * 2 + pat) * 64;",
        "    store64(q, idx);",
        "    store64(q + 8, nb);",
        "    store64(q + 16, b0);",
        "    store64(q + 24, b1);",
        "    store64(q + 32, b2);",
        "    store64(q + 40, b3);",
        "    store64(q + 48, x);",
        "    store64(q + 56, y);",
        "    return 0;",
        "}",
        "",
        "# Fill `p` with REKHA_W2_NVEC vectors of 64 bytes each, at (index * 2 + pattern).",
        "fn w2_vectors_fill(p): i64 {",
    ]
    src += body
    src += ["    return 0;", "}", ""]
    open(path, "w").write("\n".join(src))
    print("wrote %s (%d vectors)" % (path, len(lines)))


def verify(html_path):
    import re, html as H
    s = open(html_path, encoding="utf-8", errors="replace").read()
    m = re.search(r"<table[^>]*>(?:(?!</table>).)*?Triplet Encoding.*?</table>", s, re.S)
    assert m, "no Triplet Encoding table in %s" % html_path
    got, prev = [], [None] * 8
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S):
        cells = [
            re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", c))).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        ]
        if not cells or not re.fullmatch(r"\d+", cells[0]):
            continue
        cells += [""] * (8 - len(cells))
        cur = [cells[i] if (i == 0 or cells[i] != "") else prev[i] for i in range(8)]
        prev = cur
        got.append("\t".join(cur))
    want = SPEC_TABLE.strip().split("\n")
    if got != want:
        for i, (a, b) in enumerate(zip(want, got)):
            if a != b:
                print("row %d: embedded %r != spec %r" % (i, a, b))
        print("MISMATCH (%d embedded rows, %d spec rows)" % (len(want), len(got)))
        return 1
    print("the embedded table matches %s exactly: all %d rows" % (html_path, len(got)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "emit":
        emit(sys.argv[2] if len(sys.argv) > 2 else "programs/woff2_vectors.cyr")
    elif len(sys.argv) == 3 and sys.argv[1] == "verify":
        sys.exit(verify(sys.argv[2]))
    else:
        print(__doc__)
        sys.exit(2)
