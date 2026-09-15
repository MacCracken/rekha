# Changelog

All notable changes to rekha are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-09-15 — every Unicode cmap: formats 12 / 13 / 6 / 0, ranked selection, symbol faces

### Added — the cmap reads the whole Unicode range

- **Formats 12 (segmented coverage — U+0000..U+10FFFF), 13 (many-to-one), 6 (trimmed table) and 0
  (byte table)** beside format 4. Format 12 / 13 groups are binary-searched; an id past 0xFFFF has no
  glyph (glyph ids are u16) and maps to `.notdef`; a codepoint past U+10FFFF maps to `.notdef` even
  when a u32 group end reaches past it.
- **(3,0) SYMBOL faces map.** A symbol table is looked up at `cp` and, when that misses and
  `cp <= U+00FF`, at U+F000 + `cp` — symbol fonts keep their glyphs in the private-use F0xx block.
  (0.3.11 mapped nothing through a (3,0)-only cmap.)

### Changed — which subtable a font uses

- ⭐ **The best-RANKED valid subtable wins, not the last matching record.** Rank: (3,10) > (0,4) /
  (0,6) > a format 12 / 13 table under any other Unicode record > (3,1) > (0,3) > other (0,x) >
  (3,0); a later record wins a tie; (0,5) (Variation Sequences) and Macintosh (1,0) (Mac OS Roman, not
  Unicode) are never candidates. ⚠ Two consequences a consumer can observe: a (3,1) table now
  outranks a (0,3) table whatever the record order (0.3.11 took whichever came LAST), and a
  better-ranked record whose header or arrays do not fit the cmap extent is SKIPPED in favour of the
  next valid one (0.3.11 chose first and then found no usable subtable at all). Both follow what
  FreeType and HarfBuzz do. Every candidate is validated against the cmap table's DECLARED extent at
  `rekha_font_open`, as format 4 alone was in 0.3.11.
- **`RekhaFont` is 176 B** (was 160): the cmap cache holds the chosen table's entry count, format 6's
  firstCode, and its format + symbol flag. Paid once per `rekha_font_open`; every reader still
  allocates 0 B.
- ⚠ **~5 ns more per format-4 lookup.** MEASURED interleaved against 0.3.11, `bench_hotpath`,
  LiberationSans ASCII: `rekha_char_to_glyph` 29 -> 34 ns, `rekha_char_advance_px` 48 -> ~56 ns — the
  format dispatch. A format-4 fast path is in; inlining the lookup back into
  `rekha_char_to_glyph` did NOT recover it (measured, reverted). That is ~1 % of a 54-character label
  draw (~75 µs). Output is identical: the bench's result checksum over cp 32..255 is unchanged
  (`-6023123829465929365`).

### Verified

- **Real faces, against an independent reference.** A Python implementation of the selection rules
  and all five lookups, written from the spec, against `rekha_char_to_glyph` over EVERY codepoint
  U+0000..U+10FFFF, on 92 system `.ttf` faces (80 whose best map is format 12, 12 whose only map is
  format 4): **92 / 92 identical** (count of mapped codepoints and an FNV-1a digest of every
  (cp, gid) pair). On the 80 format-12 faces the BMP mapping is **identical to 0.3.11's** and every one
  of them gains codepoints past it — the Iosevka Nerd Fonts gain 9,442 (their plane-15 icons).
  LiberationSans still maps exactly 2,327 codepoints.
- **`programs/cmap_fmt_test.cyr`** (new, 90 checks): each format's mappings, range edges and a
  fits-exactly / one-byte-short pair on its arrays; every rank pair in BOTH record orders; symbol retry
  and its limits; supplementary codepoints through `rekha_char_to_sdpath` / the advance calls at 0 B;
  and a 600-group format-12 table whose lookup must equal a sequential reference on all 1,114,112
  codepoints, with and without the numGlyphs cap.
- **`hostile_test`** (540 checks): the A/B sentinel sweep now strides the supplementary planes, and
  formats 12 / 6 / 0 and a (3,0) table sit at EOF exactly long enough and one byte short — a fit
  check that reads one byte too far fails the differential itself (proven with three off-by-one
  mutants).
- **Mutation testing of the new cmap code:** 21 mutants. The first 16 left 5 alive — 3 real gaps
  (format 6's upper bound with a zero byte behind it, (0,5) / (1,0) only ever tested beside a better
  record, a u32 group end past U+10FFFF), now killed; 2 equivalent (`entryCount < 1` / `numGroups < 1`
  checks shadowed by the resolver's own `count > 0` gate), removed from the code.
- `cmap_ext_test` / `sfnt_edge_test` checks that pinned "last record wins", "a (3,0) table maps
  nothing" and "a cut header means no subtable" now pin the 0.4.0 behaviour, each with its reason in
  the comment.

### Dependencies — filed where the work is

- **sankoch:** `docs/development/proposals/2026-09-15-brotli-decoder-for-woff2.md` — a decode-only RFC
  7932 decoder as a `[lib.brotli]` profile for rekha's WOFF2 (roadmap Backlog note added).
  MEASURED on the embedded face: 410,820 B raw, 209,707 B WOFF1-style zlib, 169,278 B Brotli q11.
- **sadish:** two issues and one proposal, re-measured on sadish 0.6.0 — flatten keeps subdividing
  and allocating past `SD_FLATTEN_CAP` (50,200,616 B / 3,133,443 allocations for one flatten of
  4,096 curved quads, output silently truncated at 8,192 points); path construction stores through a
  refused `sd_alloc` (rc 139); and `sd_path_new_cap`, which would cut rekha's ASCII path arena
  433,648 -> 78,656 B. README's candidate list notes all three.
- README's roadmap is now an ordered v0.4.x ladder: WOFF 1.0, CFF outlines, WOFF2, the stdlib trim,
  adopting the sadish filings, then hinting.

## [0.3.11] - 2026-09-15 — hostile fonts: four overreads closed, fan-out bounded, the hot path cached

A full audit/hardening/optimization sweep. Eight independent audit lenses produced 88 raw findings
(59 after dedup, plus 3 from a completeness pass); every P0/P1 was reproduced with a running PoC
before it was fixed, and a second, fresh security review plus mutation testing ran against the
result. Public signatures are unchanged; the behaviour changes a consumer can observe are listed
under **Changed**.

### Security — out-of-bounds reads and unbounded work on untrusted font bytes

Every item below was reachable through `rekha_char_to_sdpath` (dhancha's per-glyph draw call) with a
crafted font that `rekha_font_open` accepts. Overreads on the bump allocator mostly land in mapped
memory, so they were PROVEN by a sentinel differential (the bytes past `len`, or an arena prefilled
A vs B — any output difference is a read outside the buffer) and then forced to fault at a guard page.

- ⛔ **Non-increasing `endPtsOfContours` → overread in `rekha_emit_contour`.** `rekha_load_simple`
  sized the point arrays from the LAST endPt only; an earlier one past it (`[65535, 2]` on a 3-point
  glyph) walked emit off xs / ys / on_curve. MEASURED: 59,417 verbs from 3 points; rc 139 at a
  guard page. Now: endPts must STRICTLY increase (checked again on the stored copy, after the
  allocation a hook could use to rewrite a shared buffer), and `rekha_outline_to_sdpath` stops at the
  first `end_pts` entry `< 0` or `>= n_points` whatever produced the outline.
- ⛔ **Composite merge past 4,096 points → `end_pts >= n_points`.** The merge clamped points at
  `REKHA_COMPOSITE_MAXP` but stored contour ends unclamped — from a fully VALID >4,096-point
  component. MEASURED: 16,381 verbs read from 4,096-entry buffers; rc 139. Now a merge over 4,096
  points or 128 contours is REJECTED (empty), never clamped.
- ⛔ **Composite fan-out: `sum N^L` bodies at ~70 KB each.** Nothing bounded total work across the
  depth-5 recursion. MEASURED: a 288-byte font whose glyph holds 4 self-references cost
  **96,733,552 B** in one `rekha_char_to_sdpath`; 6 self-references (~662 MB) faulted under a
  384 MB limit. ⚠ **Cycle detection alone does not fix it** — an ACYCLIC fan-out (glyph → 30× glyph
  → 30× glyph) amplifies the same way, which is why the fix is a budget. Now each
  `rekha_load_glyph` carries a stack context (0 B of heap): ≤ 64 glyph loads, ≤ 16,384 decoded points,
  depth ≤ 5, no gid repeated on its own component path; tripping any ABORTS the whole load (sticky —
  the result is EMPTY, never partial). MEASURED after: N = 1..8 self-references cost `8N + 96` B; the
  30×30 fan-out 11,184 B.
- ⛔ **`head` / `maxp` fields read past `len`.** `unitsPerEm` (+18), `indexToLocFormat` (+50) and
  `numGlyphs` (+4) were read after checking only that the table's declared span fit — a 0-length
  table at EOF read 16–48 B past the buffer (rc 139 at a guard page). Now `head` needs a declared
  length ≥ 54 B, `maxp` ≥ 6 B, `hhea` ≥ 36 B, or the table is treated as absent.
- ⛔ **Simple-glyph point count uncapped.** A ~530-byte glyph could declare 65,536 points via REPEAT
  flags: MEASURED 1,179,720 B per load. Now np > 4,096 is refused, and so is an np the remaining bytes
  could not encode as flags (2 bytes declare ≤ 256 points) — both before any allocation (48 B).
- ⚠ **Found by the second review, after the fixes above:** the endPts walk ran BEFORE the point cap
  and the budget, so a composite of 63 rejected 32,767-contour glyphs spent **9.6 ms** in one load.
  The O(1) gates and the budget charge now come first: MEASURED **10.5 µs**.

### Changed — hardening a consumer may observe

- **Tables obey an extent rule, checked once at open.** A table must start at/after the end of the
  directory and end inside `len` (a table overlapping the header/directory is absent). `cmap`
  records, the chosen format-4 subtable's header and all four segment arrays, and the glyphIdArray
  index are bounded by the `cmap` table's DECLARED length; `hmtx` reads by `hmtx`'s (a truncated
  `hmtx` now reads as advance 0 = unknown, never the next table's bytes); `loca` reads by `loca`'s and
  a glyph span by `glyf`'s (a last glyph overshooting `glyf` is refused, not clamped).
  `indexToLocFormat` other than 0 / 1 → no outline. Before, all of these were bounded by the FILE, so
  metrics and outlines could be decoded from a neighbouring table. Checked against 1,750 system
  `.ttf` files: 0 violate these rules.
- **`rekha_char_to_glyph` returns 0 for a mapped gid ≥ `maxp.numGlyphs`** (when maxp is present) — an
  id with no glyph behind it is `.notdef`, as FreeType maps it; `rekha_char_advance*` then report
  `.notdef`'s advance instead of the last hmetric's.
- **Every public reader returns 0 for a 0 font handle**; `rekha_font_open(0, n)` returns 0.
- **Composite decode is now spec-complete for positioning:** point matching (`ARGS_ARE_XY_VALUES`
  clear — unsigned point numbers; out-of-range → empty) was silently placed at (0, 0);
  `SCALED_COMPONENT_OFFSET` (0x800 without 0x1000) now scales the offset; the F2Dot14 transform
  ROUNDS, `sd_asr(v + 8192, 14)` (floor of v + ½), where 0.3.10 truncated toward zero. ⚠ Scaled or
  rotated components can move by up to 1 design unit: MEASURED old-vs-new over 71 system fonts
  (1,402,156 glyphs) — 69 identical, 53 composite glyphs in 2 fonts moved (contour/point/verb counts
  unchanged). LiberationSans is byte-identical (identity transforms only). A truncated LAST component
  record now yields an empty glyph (0.3.10 treated it as the end; FreeType rejects it).
- **`RekhaFont` is 160 B (was 40) and caches the table directory** — see Performance. ⚠ The buffer
  stays borrowed and the cache is a SNAPSHOT: mutating font bytes after `rekha_font_open` is
  unsupported (reads stay inside `len`; upem / numGlyphs / numberOfHMetrics / the cmap choice would
  describe the bytes as they were).
- **Allocation failure no longer faults inside rekha.** Every `sd_alloc` in the loaders is checked and
  0 propagates ("0 only on OOM"); `rekha_outline_to_sdpath(0, …)` returns an empty path. ⚠ sadish's
  `sd_path_new` / pushes still store through refused blocks, so a hook that can refuse must still
  fall back to the global allocator for a draw (MEASURED both ways; glyf.cyr head comment).
- **Removed (internal, unused downstream):** `rekha_px` / `rekha_py` (inlined), and the
  `RekhaPathVerb` enum — its QUADTO/CLOSE values disagreed with the sadish verb tags rekha actually
  emits. `rekha_load_glyph_d` takes a load context. `rekha_glyph_count` moved to sfnt.cyr (same
  signature).

### Added

- **`rekha_glyph_advance_px(font, gid, px)`** (what `rekha_char_advance_px` now wraps) so a consumer
  maps a codepoint ONCE and reuses the gid; **`rekha_glyph_advance_fx` / `rekha_char_advance_fx`**
  return the 16.16 advance. ⭐ Summing per-glyph-rounded pixel advances still drifts — MEASURED
  "ABABABABABAB" at 15 px: 78 px summed rounded vs 75 px from the 16.16 sum rounded once. The cmap.cyr
  comment that presented half-up rounding as the drift fix is corrected. All 0 B, 0 = unknown.
- **Ten new RUN suites (19 gating suites in all, each run under `CYRIUS_DCE=0` and `1`):**
  `hostile_test` (511 checks — a crafted corpus per audit class, an in-process A/B sentinel
  differential over every public entry point, and a 120-seed mutation loop over the embedded face;
  proven to fail against 12 deliberately broken copies of `src/`), `glyf_neg_test` (292 — one
  one-defect fixture per simple-glyph guard), `composite_flags_test` (262 — every component flag to
  hand-computed coordinates), `path_start_test` (247 — every contour-start branch, exact 16.16
  points), `extent_test` (325), `cmap_ext_test` (130 — incl. binary-search parity over all 65,536
  codepoints against a linear reference), `glyf_edge_test` / `sfnt_edge_test` (the gaps mutation
  testing found), `error_test`, and `dist_test`, which compiles the SHIPPED `dist/rekha.cyr` the
  consumer way (replacing the untested root `_distprobe.cyr`). `face_test` now loads and converts all
  2,620 glyphs of the embedded face under an arena hook and asserts exact totals (1,076 composites,
  5,288 contours, 71,785 points, 63,792 verbs, 2,327 mapped codepoints) at 0 B of global heap.
- **Mutation testing** of every new guard: 223 single-edit mutants over sfnt.cyr / cmap.cyr / glyf.cyr.
  The survivors that were real gaps (6 + 25) got the edge suites above, each verified to kill its
  mutant; the rest are equivalent mutants or guards no in-process test can observe (a 1-byte overread
  that changes no output). The reordered `rekha_load_simple` gates (Security, last item) were
  mutated again: the post-carve endPts re-checks survived until `glyf_edge_test` G14 rewrote the bytes
  from inside the allocation hook; the `nc > np` gate stays unkillable by an output check — removing
  it changes only the time a malformed glyph costs.
- **`programs/bench_hotpath.cyr`** — non-gating timings + arena bytes/op, with the result checksum
  (`-6023123829465929365` over cp 32..255, identical to 0.3.10's output).

### Performance — MEASURED, same machine, same session, median of 3 (bench_hotpath / audit bench)

The table directory used to be walked per call — `rekha_char_advance_px` walked it for head, cmap,
hhea and hmtx on every character, `rekha_char_to_sdpath` for cmap, maxp, loca, glyf and head. It is
now resolved once in `rekha_font_open`; cmap lookup takes segment 0 directly when it covers the
codepoint and binary-searches otherwise; each outline is ONE carved allocation; a composite is sized to
its children instead of fixed 4,096-point buffers; the span out-param moved to the stack; emit's
per-point helper calls are inlined.

| LiberationSans | 0.3.10 | 0.3.11 |
|---|---|---|
| `rekha_char_advance_px` | 787 ns | **48 ns** |
| `rekha_char_to_glyph` (ASCII) | 224 ns | **30 ns** |
| `rekha_glyf_span` | 785 ns | **36 ns** |
| `rekha_char_to_sdpath` (ASCII) | 2,473 ns | **1,398 ns** |
| `rekha_char_to_sdpath` (composite) | 5,473 ns | **3,231 ns** |
| 54-character label (advance + path per char) | 205,425 ns | **75,553 ns** |
| `rekha_font_open` (once per font) | 36 ns | ~1,500 ns |
| D2Coding (1,642 cmap segments), Hangul lookup | 7,686 ns | **85 ns** |

| bytes | 0.3.10 | 0.3.11 |
|---|---|---|
| 3-point simple outline (alloc_test) | 136 B | **112 B** |
| its `rekha_char_to_sdpath` | 4,328 B | **4,304 B** |
| one-component composite (alloc_test #51) | 70,856 B | **232 B** |
| `rekha_load_glyph` U+00C5 / U+00E9 | 71,632 / 71,464 B | **1,632 / 1,304 B** |
| Latin-1 U+00A0..00FF load pass | 4,237,264 B | **95,808 B** |
| `RekhaFont` (once) | 40 B | 160 B |

⚠ alloc_test check #51 used to assert the fixed-buffer waste EXISTED (`>= MAXP*17 + MAXC*8`); it is
now the exact composite cost, so a return to fixed buffers fails it by ~70 KB. The 0.3.10 table
above stays as it was measured. Output is unchanged on LiberationSans: every glyph's decoded points
and emitted 16.16 path match 0.3.10 and an independent spec-written Python reference (0 diff lines).

### CI, release, supply chain

- **Toolchain install pinned and verified** (`scripts/ci-install-cyrius.sh`, both workflows):
  `install.sh` is fetched from the `6.6.4` TAG (not `main`) and the release tarball is sha256-checked
  against hashes committed in the script (fails closed on a pin bump without a hash bump), under
  `set -euo pipefail`; the pin is parsed from `[package]` and must be `x.y.z`.
- **Permissions:** `contents: read` everywhere, `contents: write` only on the release job; every
  checkout `persist-credentials: false`; all actions pinned to full commit SHAs + `dependabot.yml`.
- **Build gate:** smoke and every `*_test.cyr` build AND run under `CYRIUS_DCE=0` and `1`; any
  `warning` / `undefined function` / `refusing to emit` line in a build log fails — 0.3.10's
  CHANGELOG described the green-build-that-faults and rekha's own CI never grepped for it.
- **Lock gate:** after `rm -rf lib && cyrius deps`, `cyrius.lock` must equal the committed file, and a
  live `path =` line in `cyrius.cyml` fails. **Dist gate:** `cyrius distlib --check` + no untracked
  `dist/` files; the release ships the COMMITTED bundle instead of regenerating it, and refuses a tag
  with no CHANGELOG section. **Lint gate** now fails on untracked deferrals and lint errors, not only
  `warn` lines.
- **Security scan** is an allowlist over every tracked `.cyr` / `.tcyr` (library code may only
  `syscall(1, 2, …)`; programs may also exit), and refuses process-spawn names, process/dlopen
  includes and inline `asm` (a working `asm` exit(7) passed the old scan).
- Job timeouts, `$RUNNER_TEMP` instead of `/tmp`, a dead cleanup step removed, prerelease comment
  corrected (every 0.x tag is a GitHub prerelease).

### Dependencies

- **`[deps.sadish]` drops `path = "../sadish"`.** It won over `tag` and skipped the commit pin, and
  its reason (0.5.5 not yet tagged) is gone — the tag is published (9760ead). `cyrius.lock` was
  regenerated from an EMPTY `lib/`: 110 → 23 entries plus the sadish `commit` pin; the 87 extra
  hashes were leftovers of a local full-snapshot `lib/` that no manifest asks for (and the source of
  the local "./lib/ shadows version-pinned" warning).

### Tooling

- `scripts/face2cyr.py` refuses short files, a directory past EOF, tables past EOF or over the
  directory, and a face with no format-4 Unicode cmap rekha can map (it used to accept one on which
  every codepoint is `.notdef`); writes atomically in UTF-8; escapes the file name in the generated
  string and comment. `fonts/face_data.cyr` regenerates byte-identically.

### Open items — where each one is tracked

- Glyphs over the load caps render EMPTY (a >4,096-point outline, a >128-contour composite, a
  composite needing >64 loads or >16,384 decoded points). No face checked exceeds them; LiberationSans
  peaks at 338 points (gid 2193).
- cmap formats 12 / 6 / 0 and `(3,0)` symbol fonts map nothing yet — first item of README's v0.4.0 line.
- Transform rounding is floor(v + ½) on the sum; FreeType rounds each product half away from zero,
  so exact negative halves can differ by 1 unit.
- **Filed in sadish (2026-09-15):** `sd_path_flatten` keeps subdividing and allocating after its
  8,192-point output is full and truncates silently — MEASURED on sadish 0.6.0: 12,386,304 B, 774,144
  allocations, ~47 ms for ONE `sd_canvas_fill_path` (64×64) of a glyph that fits every rekha cap
  (`sadish/docs/development/issues/2026-09-15-flatten-keeps-subdividing-and-allocating-after-the-output-cap-is-full.md`);
  `sd_path_new` / `sd_point_new` store through a refused `sd_alloc`
  (`…/issues/2026-09-15-path-construction-stores-through-a-refused-allocation.md`); and
  `sd_path_new_cap`, which would cut rekha's per-glyph path arena 5.5× on ASCII
  (`…/proposals/2026-09-15-path-capacity-for-known-size-paths.md`). rekha adopts each as it ships.
- `[deps].stdlib` still declares `io`, `vec`, `str`, `syscalls`, `assert`, `bench` that `src/` does not
  call. Trimming changes the `dist/rekha.deps` sidecar consumers resolve, so it goes out as its own
  release with the sidecar change called out — on README's v0.4.0 line.

## [0.3.10] - 2026-09-14 — rekha draws its memory from sadish's seam

### Changed — every allocation routes through `sd_alloc`; the draw stack has ONE knob

⭐⭐ **All 15 `alloc(` sites in `src/` — error.cyr 1, glyf.cyr 13, sfnt.cyr 1 — now call sadish's
`sd_alloc(n)`** (sadish 0.5.5's allocation seam: `sd_alloc_set(fp)` installs a hook and returns the
previous one, `sd_alloc_get()` reads it back, 0 = the global allocator). rekha adds no seam of its
own: it already hard-depends on sadish (`rekha_outline_to_sdpath` builds `SdPath`s), so the knob is
owned by the leaf, the way the fixed-point convention (16.16) already is. A consumer that scopes
`sd_alloc_set` around a text draw gets the **outlines, the paths and the coverage from the same
place**, and a per-frame arena reclaims all three at once.

**WHY.** `lib/alloc.cyr` is a bump allocator with **no `free()`**. dhancha's scalable text
(`dh_draw_text_ink`, `font != 0`) calls `rekha_char_to_sdpath` per glyph, per label, per frame, and
rekha drew its outline scratch — the 16-byte loca span, `end_pts`, `flags`, `on_curve`, `xs`, `ys`,
the 48-byte record, and for a composite (every accented letter in a real face) the 70,656 B of
merge buffers — from the global heap that no hook could reach. dhancha filed it (`2026-09-13-scalable-text-allocates-per-call-outside-the-frame-arena.md`);
crab's headline gate asserts a rendered frame costs the global heap **exactly 0 bytes** and cannot
adopt a proportional face until the whole draw stack can be pointed at its frame arena. sadish
0.5.5 is the rasterizer half of that fix; this is the outline half.

**MEASURED** (`alloc_used()` / `arena_used()` deltas, a 3-point triangle glyph, `'A'` via cmap,
sadish 0.5.5 vendored in both columns):

| call | 0.3.9, global heap | 0.3.9 under a sadish hook | 0.3.10 under the hook |
|---|---|---|---|
| `rekha_char_to_sdpath` | 4,328 B | **136 B leaked** on the global heap, 4,192 B on the arena | **0 B** global, 4,328 B on the arena |
| ...x 20 | 86,560 B | **2,720 B leaked** | **0 B** global, 86,560 B on the arena |
| `rekha_load_glyph` (simple) | 136 B | 136 B leaked, 0 on the arena | 0 B global, 136 B on the arena |
| `rekha_load_glyph` (composite of one) | 70,856 B | 70,856 B leaked | 0 B global, 70,856 B on the arena |
| `rekha_char_to_sdpath`, that composite | 75,048 B | **70,856 B leaked**, 4,192 B on the arena | 0 B global, 75,048 B on the arena |
| `rekha_font_open` | 40 B | 40 B leaked | 0 B global, 40 B on the arena |

The 4,328 B per glyph is 136 B of rekha (span 16 + end_pts 8 + flags 8 + on_curve 8 + xs 24 +
ys 24 + record 48) plus 4,192 B of sadish (`sd_path_new` 4,144 + 3 points x 16). Every byte
moved, none were added: the arena's high-water mark for twenty calls is exactly 20 x the global cost
0.3.9 paid, and after `arena_reset` twenty more calls land on the same mark.

⚠ **`rekha_font_open` lands in the hook too.** The 40-byte `RekhaFont` follows the seam like
everything else, which is why a consumer **opens fonts OUTSIDE a scoped hook** — a font opened under a
per-frame arena dies at that arena's reset. Reading a font costs nothing under any hook:
`rekha_char_to_glyph`, `rekha_advance_width`, `rekha_units_per_em`, `rekha_char_advance_px` allocate
0 B (asserted). ⛔ An outline or a path made under an arena hook must not be kept across that
arena's reset; that is the consumer's lifetime call, exactly as it is for sadish's own paths.
⛔ **The hook must not return 0.** `rekha_outline_empty` and `rekha_font_open` check their
allocation; the loaders store straight through theirs, as they always did with `alloc` — MEASURED
under a hook that returns 0: `rekha_font_open` returns 0 correctly, `rekha_char_to_sdpath` faults
(rc 139). A hook backed by an arena that can refuse falls back to the global allocator, as dhancha's
`dh_falloc` does, rather than returning 0. Said at the head of `src/glyf.cyr`.

⛔⛔ **FLOOR: sadish >= 0.5.5, HARD — AND BELOW IT THE BUILD MAY STILL GO GREEN.**
`sd_alloc` does not exist below 0.5.5, and MEASURED against a real 0.5.4 tree (a `git archive` of the
tag as the `path` dep): rekha's `path_test`, `glyf_test` and `smoke` **compile** — `warning: undefined
function 'sd_alloc'`, then `OK` — and the binary **dies at the first `rekha_font_open`**: `path_test`
and `glyf_test` exit 132 (SIGILL), the `CYRIUS_DCE=1` `path_test` exits 139 (SIGSEGV); only
`alloc_test` is refused (`error: refusing to emit binary with 2 reachable undefined function(s)`).
⚠ Which of the two a build gets is NOT "a direct call from the program vs one through the bundle"
(an earlier draft of this entry said so; it is wrong in both directions). cyrius 6.6.4 decides each
undefined NAME on its FIRST call site in code order: a first site inside a function DCE keeps live
refuses; a first site inside a dead function prints the warning, emits the binary, and every later
site of the same name — live or not — goes unexamined. MEASURED with a 4-line probe: a dead caller
of `missing_fn` listed before `main`'s own call → `OK (4456 bytes)`, rc 132; the same two fns with
`main` first → refused; a call three fns deep from `main` → refused. rekha's suites warn because the
first `sd_alloc(` in the fold is `rekha_err_new` (src/error.cyr), which no suite reaches — a copy of
`path_test` whose `main` calls `sd_alloc(16)` DIRECTLY still builds `OK (147320 bytes)` and exits 132.
A consumer whose first site is live is refused instead: crab, with no `sd_alloc*` call of its own,
against sadish 0.5.4 + dhancha 0.10.0 (`dh_draw_text_ink` is the first `sd_alloc_set(` site in its
fold, reachable from `main`) gets `refusing to emit binary with 2 reachable undefined function(s)`.
⇒ Either way the plain `warning: undefined function` line is printed; a consumer whose CI does not
grep build output for it can ship a green build that faults on its first glyph.
dhancha vendors the two bundles separately, so its `[deps.sadish]` tag must clear the same floor
when it takes this rekha — and its build gate should treat that warning as the error it is.
`[deps.sadish]` here moves `0.5.2` -> **`0.5.5`** and re-adds `path = "../sadish"` (the 0.5.5 tag
does not exist at the time of writing; ⛔ `path` WINS over `tag`, so a green build is not evidence
the tag resolves — re-verify with the `path` line disabled before moving the tag). `cyrius.lock`
loses the sadish `commit` line (a path dep pins no commit) and moves the `lib/sadish.cyr` hash;
nothing else in the lock changes.

**Proven by mutation** — `programs/alloc_test.cyr` (new, 67 numbered checks in groups A–D: the
no-hook baseline asserted > 0; twenty hooked calls cost the heap exactly 0 and the arena converges;
the outline record and all four buffers, the composite buffers and the font record lie inside the
arena's range; `sd_alloc_set(0)` restores and the next call is back on the heap at exactly the
group-A cost). Reverting one site at a time to `alloc(`:

| mutation | checks failed |
|---|---|
| glyf.cyr `rekha_load_simple` `xs` | **7** (#37, 38, 40, 41, 42, 46, 50) |
| glyf.cyr `rekha_load_glyph_d` `span` | **6** (#37, 38, 40, 41, 42, 50) |
| glyf.cyr `rekha_load_composite` `xs` | **3** (#50, 51, 53) |
| sfnt.cyr `rekha_font_open` `f` | **3** (#58, 59, 60) |

All **9** RUN suites pass (`sfnt meta glyf path cmap composite hmtx face alloc`); the eight
pre-existing ones are byte-for-byte unchanged in what they assert. `dist/rekha.cyr` 38,661 -> 40,750 B
(+2,089: the seam note in glyf.cyr and `sd_` on 15 call sites). The `CYRIUS_DCE=1` smoke binary
goes 16,208 -> 16,296 B, and **all +88 of it is the sadish 0.5.2 -> 0.5.5 bump** (0.3.9's sources
against the 0.5.5 bundle also build to 16,296; the non-DCE smoke is 143,272 B either way) — nothing
in rekha's change is reachable from the banner.

## [0.3.9] - 2026-09-14 — the literal defect is fixed upstream; the chunks stay

### Changed

- **Toolchain `6.6.3` → `6.6.4`**, moving with agnos 1.57.4 and kashi 1.0.8 (vendored `lib/` re-synced;
  `cyrius.lock` moves only for the six stdlib files 6.6.4 changed). All eight RUN suites pass.
- ✅ **The compiler defect 0.3.8 filed is FIXED in cyrius 6.6.4** — the lexer packed every string
  token as `(pool offset << 16) | length`, so a length ≥ 65,536 OR-ed into its own offset (the
  filing's "even length / alternate literal" narrative was the pool layout, not the mechanism);
  widened to `<< 32`. **Re-measured under 6.6.4:** the self-proving repro exits 0 and a SINGLE
  410,820-byte literal of this face compiles byte-exact (the same bisection that found it: 65,536,
  131,072 and 410,820 all OK). `scripts/face2cyr.py` and the generated header now record the defect
  as history rather than as a live constraint.
- ⚠ **The 4 KB chunks and `rekha_face_default_verify` stay.** A consumer that exposes bytes it has
  not hashed is trusting the compiler again; the boot-time verify that a chunked module makes cheap
  is what caught the last defect and is the only thing that would catch the next. `fonts/face_data.cyr`
  is byte-identical to 0.3.8 outside its header comment (regenerate-and-diff gate green).

## [0.3.8] - 2026-09-13 — the embedded default face: kernel support, half one

### Added — `fonts/face_data.cyr`, a freestanding data module carrying one TrueType face

⭐ **AGNOS had no proportional face a client could open, and the operator ruled rekha the
answer** (agnos issue `2026-09-13-no-proportional-face-on-the-target.md`, filed by crab). Stack-wide
there was no `.ttf` in any first-party repo; rekha parsed faces it never shipped. This is the
rekha half of the fix, shaped exactly like kashi's `src/font_data.cyr`: a **freestanding** module
(no stdlib, no heap, no syscalls — string literals, integer arithmetic, `load8`/`store8`) that a
freestanding kernel concatenates by path via `[deps.rekha] modules = ["fonts/face_data.cyr"]`.

- **The face is Liberation Sans Regular 2.1.5, embedded UNMODIFIED** (410,820 bytes, glyf outlines,
  format-4 BMP cmap — the two things `rekha_font_open` requires). `fonts/LiberationSans-Regular.ttf`
  is the source of truth and `fonts/LICENSE-LiberationFonts` (SIL OFL 1.1, Reserved Font Name
  *Liberation*) travels with it. ⚠ **Unmodified on purpose**: a subset is a Modified Version under
  the OFL and may not keep the Reserved Font Name, and no first-party subsetter exists; the full
  face costs a kernel ~410 KB of `.rodata` and a 2 MB page at boot, which agnos accepted.
- **API**: `rekha_face_default_len()` · `rekha_face_default_copy(dst, cap)` (→ length, or −1 when
  `cap` is short) · `rekha_face_default_verify(buf, len)` (FNV‑1a‑64 against the generator's hash of
  the source file → 1/0) · `rekha_face_default_name()`/`_name_len()` · per-chunk accessors.
- ⛔ **4096-byte chunks, and the reason is a compiler defect found while building this.** A cyrius
  6.6.3 string literal of EVEN length ≥ 65536 is emitted **shifted by one byte** (its first byte
  lost) on every alternate literal — `rc=0`, byte count intact, content wrong. Bisected over
  4096..131072 against an FNV‑1a of the file: odd lengths ≥ 65536 and every length < 65536 are
  byte-exact. Filed against cyrius; the generator stays far below the trap **and** the module carries
  the whole-face hash so a consumer verifies what it assembled rather than trusting the compiler.
  `programs/face_test.cyr` runs the same copy+verify path on the host, so the trap fails there before
  the bytes reach a target, and proves the verify is not vacuous (one flipped byte → 0).
- **`scripts/face2cyr.py`** (Python stdlib only — no fonttools) generates the module and refuses a
  CFF face or one missing `glyf`/`loca`/`cmap`/`hhea`/`hmtx`/`head`/`maxp`. CI regenerates into a
  temp file and requires a byte-identical match, so the data cannot drift from the `.ttf`.
- **Not in `[lib].modules`, not in `dist/rekha.cyr`, and outside `src/`**: 1.6 MB of generated
  literals must never ride into a consumer's bundle, and `cyrfmt` refuses files over 1028 KB.

### Changed

- **Toolchain `6.6.2` → `6.6.3`** (vendored `lib/` re-synced from the pin; `cyrius.lock` re-emitted in
  the sorted order 6.6.3 now writes — same entries, order only). All eight RUN suites pass, including
  the new `face_test`.

## [0.3.7] - 2026-09-11

### Changed

- **Toolchain `6.5.41` → `6.6.2`.** No source change; the value form needed none.
  Build, tests, and any bench/fuzz/distlib target the repo ships re-verified at the new pin.

## [0.3.6] - 2026-09-02 — horizontal metrics: hhea + hmtx

### Added — `rekha_advance_width`, and the reason the tags existed without it

⛔⛔ **`REKHA_TAG_HHEA` AND `REKHA_TAG_HMTX` HAVE BEEN DECLARED SINCE THE SFNT SCAFFOLD AND WERE
NEVER READ ONCE.** `grep` found both in the constant block and nowhere else — no reader, no test, no
consumer. A declared tag with no reader is a promise, not a feature, and downstream it cost real
behaviour: **dhancha hard-codes `advf = (h * 6) / 10`** — *"fixed advance ~0.6 em"* — because rekha
gave it nothing better to use. That renders a proportional face at monospace pitch: correct glyph
shapes at wrong positions, which reads as a rendering bug rather than a missing metric.

New, all in font **design units** (`unitsPerEm` space — rekha stays resolution-independent):

| | |
|---|---|
| `rekha_num_h_metrics(font)` | `hhea.numberOfHMetrics` |
| `rekha_ascender` / `rekha_descender` / `rekha_line_gap` | the three `hhea` line-box fields |
| `rekha_advance_width(font, gid)` | a glyph's advance |
| `rekha_char_advance(font, cp)` | codepoint -> advance, via `cmap` |
| `rekha_char_advance_px(font, cp, px_size)` | ...scaled to pixels, rounded half-up |

⛔⛔ **THE `hmtx` TAIL IS THE WHOLE SUBTLETY, AND IT IS WHAT THE TEST IS BUILT AROUND.** `hmtx` is
**two** arrays: `longHorMetric[numberOfHMetrics]` at 4 bytes each, then
`leftSideBearing[numGlyphs - numberOfHMetrics]` at 2 bytes each with **no advance of their own**.
Glyphs past `numberOfHMetrics` share the LAST long metric's advance — that is the format's
compression for a run of equal-width glyphs, not a defect. ⇒ A reader indexing `hmtx + gid * 4`
past that boundary walks into the bearing array and **returns a left side bearing as if it were a
width**. `programs/hmtx_test.cyr` plants exactly that: five glyphs, three long metrics, and two
tail bearings whose values (700, 900) are deliberately plausible widths. The naive reader returns
them and looks right until measured.
⚠ **Proven by mutation** — deleting the clamp fails the suite in **6** places.

⚠ **`descender` is returned SIGNED**, which is the only useful shape: it measures downward from the
baseline and is negative in every well-formed font, so `asc - desc + gap` is the line height with no
caller needing to know which way it points. Read as `u16` it comes back **65336** and every line-box
sum built on it is wrong by 65,536 design units.

⚠ **0 means UNKNOWN, never zero-width.** A font with no `hhea`/`hmtx` reports 0 and the consumer
must fall back to its own estimate; painting with 0 stacks every glyph on one x. `rekha_char_advance_px`
also returns 0 when `unitsPerEm` is 0, so a caller's fallback is one `== 0` test rather than two.

⭐ **The pixel helper rounds half-up rather than truncating**, because the scaling would otherwise be
written by every consumer and one of them would write it wrong: `adv * px / upem` truncating loses up
to a pixel per glyph and compounds — a 40-character run ends visibly left of where it should.

⚠ An unmapped codepoint resolves to `.notdef` (gid 0), whose advance is a real metric in most fonts,
so a run of missing glyphs still advances instead of collapsing onto one x.

### Changed — `cyrius = "6.5.27"` -> **6.5.41**

The stack moved and this repo had not. Every build was running with a drift warning against an
installed 6.5.41. ⚠ The pin selects the stdlib snapshot that compiles in, so this is not cosmetic.
`lib/` re-synced with `--full`, clearing the `./lib/ shadows version-pinned` warning; all seven test
programs and the smoke build re-run green after both changes.

## [0.3.5] - 2026-08-17 — toolchain pin to 6.5.27

### Changed — `cyrius = "6.5.5"` -> **6.5.27**

Stack-wide sweep so every repo in the desktop stack declares one toolchain. Pins had drifted across
three lines (6.5.5 / 6.5.20 / 6.5.21) while the installed wrapper was 6.5.27, so every build ran with
a drift warning and the declared graph did not describe what was actually compiled.

⚠ **THE ARTIFACT CHANGED, so this is not a cosmetic edit.** The build went `134712 -> 143128` bytes and the binary differs. The pin is not a comment: it selects the stdlib snapshot under `~/.cyrius/versions/<pin>/lib`, so moving it swaps the library code this repo compiles against.

⛔ **THE PIN IS NOT JUST DOCUMENTATION**, which is the half-truth that made this sweep's first
prediction wrong. `cycc` is the installed binary either way — but the **stdlib** resolves from
`~/.cyrius/versions/<pin>/lib`, so the pin decides which library sources compile in. Measured before
any other change: the pin bump ALONE moved these bytes.

⚠ The vendored `lib/` was then re-synced to the 6.5.27 bundled set, clearing the
`./lib/ shadows version-pinned` warning. Tests re-run green after both changes.

## [0.3.4] - 2026-08-02

### Changed — cyrius pin 6.4.71 -> 6.5.5, sadish dep 0.5.0 -> 0.5.1

Part of the whole-desktop-stack toolchain catch-up cut on this date. ⚠ The pin was documentation,
not enforcement: `cyrius build` compiles with the INSTALLED `cycc` and only warns on drift, so this
project was already being built by 6.5.5. The gap's load-bearing change is **6.5.1** making
overload-suffix arity a hard **error** where it used to warn.

### Verification

Host + `--agnos` builds green; **6 RUN tests** pass (`cmap`, `composite`, `glyf`, `meta`, `path`,
`sfnt`); `distlib` regenerated.

## [0.3.3] - 2026-07-23

### Changed — sadish 0.5.0 (real alpha channel) + dep refresh

Picks up sadish's additive alpha API (`sd_rgba` / `sd_alpha_of` / `sd_premul`). No behaviour change here:
sadish's legacy `0x00RRGGBB` colours still read back opaque, so glyph rasterisation is unaffected.

## [0.3.2] - 2026-07-23

### Changed — cyrius pin 6.4.25 → 6.4.71

Toolchain refresh across the draw stack. Materialised `lib/` re-synced (`cyrius lib sync --full`).
No source change; build + tests green at the new pin.

## [0.3.1] - 2026-07-08 — toolchain alignment

Pin/hygiene release — no code change; the TrueType/SFNT outline subsystem is
byte-identical to 0.3.0 (all RUN tests green).

### Changed

- **Cyrius pin `6.4.7` → `6.4.25`** — aligns rekha with the desktop stack
  (setu + dhancha pin `6.4.25`) instead of drifting behind. Builds + all 7 RUN
  tests (sfnt / glyf / cmap / path / composite / meta / smoke) pass.
- **`[deps.sadish]` → tag `0.4.1`; dev `path` override dropped** (tag-only for a
  reproducible pin). Pairs with sadish 0.4.1 — push sadish before rekha.

## [0.3.0] - 2026-07-05

Text, not just glyphs: cmap maps characters to glyph ids, and composite glyphs
(accented letters etc.) decode. 6 RUN tests.

### Added
- **cmap format 4** (`rekha_char_to_glyph`, `rekha_char_to_sdpath`) — Unicode
  BMP codepoint → glyph id via the segment-mapping subtable (platform 3/enc 1
  or platform 0): delta + idRangeOffset segments, gaps → .notdef, beyond-BMP →
  .notdef. `rekha_char_to_sdpath` is the one-call character → positioned sadish
  path. Bounds-checked. (`cmap_test`.)
- **Composite glyphs** — `rekha_load_glyph` now handles numberOfContours < 0:
  component records recursively load the referenced glyphs (depth-guarded),
  apply the F2Dot14 2×2 transform + x/y offset, and merge into one outline. The
  simple-glyph body split out to `rekha_load_simple`. (`composite_test`.)

### Deferred
- cmap formats 12 (full Unicode) / 6 / 0; point-matching composite args;
  OpenType/CFF (`OTTO`); WOFF/WOFF2; hinting.

## [0.2.0] - 2026-07-05

Real TrueType parsing, end to end: a font's bytes now become a filled glyph via
sadish. rekha is **sadish's first consumer** — the integration validated the
sadish API. 4 RUN tests (synthetic fonts + hand-built outlines).

### Added
- **SFNT table directory** (`rekha_find_table` / `rekha_find_table_len`) +
  hardened `rekha_font_open` — validates sfntVersion, bounds the directory, and
  bounds-checks every table span against the (untrusted) font length.
- **Font metadata** — `rekha_units_per_em`, `rekha_loca_format` (head),
  `rekha_glyph_count` (maxp).
- **loca → glyf span** (`rekha_glyf_span`) — glyph id to its byte range in the
  glyf table (short/long loca, empty-glyph + out-of-bounds aware).
- **glyf simple-glyph decode** (`rekha_load_glyph`) — numberOfContours,
  endPtsOfContours, the run-length flag array, and delta-encoded x/y coords →
  a `RekhaOutline` (contours + absolute points + on-curve flags). Every read
  bounds-checked; composite glyphs (numberOfContours < 0) deferred.
- **rekha → sadish seam** (`rekha_outline_to_sdpath`, `rekha_glyph_to_sdpath`) —
  walks each contour's on/off-curve run and converts TrueType quadratics into
  sadish `moveto`/`lineto`/`quadto`/`close` (implied on-curve midpoints between
  consecutive off-curve points; off-curve contour starts handled), y-flipped +
  scaled into sadish pixel space. **`sadish` is now wired as a dep** — rekha is
  its first real consumer.
- Tests: `sfnt_test` (directory + rejection), `meta_test` (head/maxp/loca
  spans), `glyf_test` (simple-glyph decode), `path_test` (glyph → sadish path →
  fill, plus off-curve verb-sequence checks).

### Deferred
- Composite glyphs, cmap (codepoint → glyph id), OpenType/CFF (`OTTO`) outlines,
  WOFF/WOFF2 (needs `sankoch` inflate + Brotli), and hinting.

## [0.1.0] - 2026-07-05

### Added
- Repo scaffolded: pure-Cyrius vector/outline font subsystem skeleton —
  `RekhaErr` codes, `RekhaFont`/`RekhaOutline` layouts, big-endian SFNT byte
  readers, and the `rekha_outline_to_path` sadish seam as stubs behind
  `# TODO(v0.2)` markers. Links clean via `programs/smoke.cyr`.
