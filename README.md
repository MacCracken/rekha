# rekha

Version: 0.4.2

**rekha** (रेखा — Sanskrit/Hindi: *line / outline / contour / stroke*) is
a pure-Cyrius vector/outline font subsystem for AGNOS. It parses
TrueType/OpenType (SFNT) font containers and decodes glyph outlines,
emitting them as **paths** (line / quadratic-Bézier verbs) into the
`sadish` 2D vector core, which rasterizes them.

rekha does **not** bundle its own Bézier rasterizer — it produces the
glyph-outline path; `sadish` fills it. The two form a clean seam: rekha
owns *what the glyph is* (SFNT tables → outlines), sadish owns *how it
becomes pixels* (fill → coverage). rekha is pure CPU Cyrius: no GPU, no C
shim, no external binaries.

## Scope

- **v0.1.0 — scaffold.** Buildable compiling skeleton (error codes, struct
  layouts, SFNT byte readers, stub bodies). Superseded below.
- **v0.2.0 — real TrueType, end to end (shipped).** Font bytes → filled
  glyph, RUN-tested:
  - **SFNT container** — `rekha_font_open` (validated) + `rekha_find_table`
    (bounds-checked table directory).
  - **Metadata** — `rekha_units_per_em`, `rekha_loca_format`,
    `rekha_glyph_count`.
  - **loca → glyf** — `rekha_glyf_span` (glyph id → its glyf byte range).
  - **glyf decode** — `rekha_load_glyph` (contours, run-length flags,
    delta-encoded coords → `RekhaOutline`); reads bounded by the file (tightened
    to each table's own extent in 0.3.11).
  - **sadish seam** — `rekha_outline_to_sdpath` / `rekha_glyph_to_sdpath`
    convert TrueType quadratic contours (implied midpoints, off-curve
    starts) into a sadish `SdPath`, y-flipped + scaled to pixel space.
    **`sadish` is wired as a dependency; rekha is its first consumer.**
- **v0.3.0 — text (shipped).** Characters → glyphs, and composite glyphs:
  - **cmap format 4** — `rekha_char_to_glyph` (Unicode BMP codepoint → glyph
    id) + `rekha_char_to_sdpath` (one call: character → positioned sadish path).
  - **Composite glyphs** — `rekha_load_glyph` decodes numberOfContours < 0
    (recursive component load, F2Dot14 transform + offset, merged outline).
- **v0.3.6 — horizontal metrics (shipped).** `hhea`/`hmtx`: `rekha_advance_width`,
  `rekha_char_advance` / `rekha_char_advance_px` (rounded half-up), the `hhea`
  line-box fields; the `hmtx` left-side-bearing tail handled.
- **v0.3.10 — one allocation knob (shipped).** Every byte rekha allocates goes
  through sadish's seam (`sd_alloc`, sadish >= 0.5.5), so a consumer that scopes
  `sd_alloc_set` around a text draw gets the outlines, the paths and the coverage
  from the same arena: 20 `rekha_char_to_sdpath` calls under an arena hook cost
  the global heap **exactly 0 bytes** (MEASURED; 4,328 B each on the arena).
  ⚠ Open fonts OUTSIDE a scoped hook — `rekha_font_open` follows the seam too.
- **v0.3.11 — hardened against hostile fonts, and faster (shipped).** An
  audit found four out-of-bounds reads reachable from `rekha_char_to_sdpath`
  with crafted bytes, plus composite fan-out that could demand gigabytes;
  all are fixed and each has a regression suite. The invariant now enforced:
  every table lies after the directory and inside the file, a fixed field is
  read only when its table's DECLARED length covers it, variable arrays stay
  inside their own table, and every outline's `end_pts` strictly increase and
  stay `< n_points`. Load caps (not read from the font): 4,096 points / 128
  contours per outline, 64 glyph loads and 16,384 decoded points per
  `rekha_load_glyph`, nesting depth 5, no component cycles — tripping one
  yields an EMPTY glyph, never a partial one. Table offsets are cached at open
  (`RekhaFont` 40 → 160 B, once): a 54-character label draws **2.7× faster**
  (205 → 76 µs MEASURED) and an accented composite loads in 1.6 KB instead of
  71.6 KB. Composite point matching and scaled component offsets now decode;
  new `rekha_glyph_advance_px` / `_fx` and `rekha_char_advance_fx` (16.16).
  ⚠ The font buffer is borrowed and its metadata snapshotted at open — do not
  mutate it afterwards.
- **v0.4.0 — every Unicode cmap (shipped).** `rekha_char_to_glyph` reads formats 4, **12**
  (the whole Unicode range), **13**, **6** and **0**; the best-ranked valid subtable wins —
  (3,10) > (0,4)/(0,6) > a wide table under any other Unicode record > (3,1) > (0,3) > other (0,x)
  > (3,0) — and a broken record is skipped instead of blanking the map. (3,0) **symbol** faces map,
  with U+00xx retried at U+F0xx. MEASURED on 92 system faces against an independent reference: every
  codepoint U+0000..U+10FFFF identical; the 80 with a format-12 map keep 0.3.11's BMP mapping exactly
  and gain the planes past it (Iosevka Nerd Fonts: 9,442 icon codepoints).
- **v0.4.1 — WOFF 1.0 (shipped).** `rekha_font_open_woff` / `rekha_font_open_any` open a `.woff`
  (the W3C WOFF 1.0 container: per-table zlib) by rebuilding its SFNT into one `sd_alloc` and opening
  that; `rekha_woff_sfnt_size` validates without inflating, `rekha_woff_decode` rebuilds into a
  caller's buffer. Every declared size is checked before anything is allocated or inflated (tag
  order, table extents, DEFLATE's 1,032:1 ratio, the exact totalSfntSize, no stream shared between
  entries) and each table must inflate to exactly its origLength. **Opt-in:** it lives in
  `dist/rekha-woff.cyr` (`[lib.woff]`), which a WOFF consumer takes instead of `dist/rekha.cyr` and
  pairs with sankoch (the stdlib `sankoch` leaf + `sync`); the base bundle never requires sankoch.
  MEASURED: all 29 real `.woff` files on the dev host (Lato, Roboto Slab, KaTeX, FontAwesome, Qt
  icons) rebuild byte-identical to an independent Python/zlib decoder and open.
- **v0.4.2 — CFF outlines: OpenType `OTTO` faces (shipped).** `rekha_font_open` accepts the `OTTO`
  sfntVersion and resolves the `CFF ` table; `rekha_load_glyph` runs the glyph's **Type 2 charstring**
  (all the drawing, hint, subroutine and flex operators, name-keyed and **CID-keyed** fonts) into the
  same `RekhaOutline` glyf produces, with **cubic** control points flagged 2 — so
  `rekha_char_to_sdpath` draws an OTTO face through `sd_path_cubicto` with no consumer change. One
  decode is bounded: 65,536 operators, nesting 10, a 48-argument stack, 4,096 points. MEASURED against
  an independent reference on **all 405 CFF faces of the dev host — 5,093,070 glyphs, 415,584,832
  points, identical**. ⚠ Accented glyphs built with `seac`, CFF2 and TrueType Collections are on the
  list below; a WOFF wrapping an OTTO face now works end to end.
- **v0.4.x line — next, in order:**
  1. ~~cmap formats 12 / 6 / 0 + symbol fonts~~ — shipped in 0.4.0, above.
  2. ~~WOFF 1.0~~ — shipped in 0.4.1, above.
  3. ~~OpenType/CFF (`OTTO`) outlines~~ — shipped in 0.4.2, above.
  4. **WOFF2** — the container, the glyf/loca and hmtx transforms, tested on
     transformed-but-uncompressed tables; the Brotli stream decodes through sankoch's requested
     `[lib.brotli]` (`sankoch/docs/development/proposals/2026-09-15-brotli-decoder-for-woff2.md`).
  5. **`[deps].stdlib` trim** — to what `src/` calls; released on its own, since it changes the
     `dist/rekha.deps` sidecar consumers resolve.
  6. **Adopt the sadish filings as they ship** — bounded flatten, checked path allocation,
     `sd_path_new_cap` sized from the outline (5.5× less path arena on ASCII, MEASURED).
  7. **CFF `seac`** — the accented glyphs old CFF faces build from a base + an accent (none of the 405
     surveyed faces use it; they are EMPTY today), which needs the charset and standard-encoding
     lookup.
  8. **TrueType Collections (`ttcf`)** and **CFF2** — a `.ttc` carries several faces in one file
     (CJK faces ship this way) and CFF2 is the variable-font charstring format.
- **after 0.4.x:** TrueType hinting (the `fpgm`/`prep`/glyph bytecode interpreter) for small
  sizes.

## Place in the stack

rekha is a **system library** in the Sanskrit/Hindi naming lane. It is the
*outline* half of a sibling font pair with `kashi` (काशि):

- **kashi** — **bitmap** glyph sources: PSF1/PSF2, VGA-ROM 8x16 / CGA 8x8,
  hand-drawn. Fixed-resolution; a freestanding kernel can embed it.
- **rekha** — **outline / Bézier** glyph sources: TrueType/OpenType.
  Scalable, resolution-independent; for high-DPI and arbitrary point sizes.

```
  font bytes ─▶ rekha (SFNT tables → glyph outlines → sadish paths)
                  │
                  ▼
                sadish (fill → coverage) ─▶ pixels
```

## The embedded default face

rekha ships one face as **data**, so a target with no font on disk still has
something to open: `fonts/face_data.cyr` is a freestanding module (no stdlib)
generated from `fonts/LiberationSans-Regular.ttf` (SIL OFL 1.1, unmodified;
licence in `fonts/LICENSE-LiberationFonts`). A kernel consumes it by path —

```toml
[deps.rekha]
path    = "../rekha"
modules = ["fonts/face_data.cyr"]
```

— copies it into one contiguous buffer with `rekha_face_default_copy(dst, cap)`
and **must** check `rekha_face_default_verify(buf, len)` before exposing it
(the 0.3.8 changelog records the compiler defect that check caught — fixed
in cyrius 6.6.4 — and 0.3.9 why the check stays). Regenerate with `python3 scripts/face2cyr.py fonts/<face>.ttf
fonts/face_data.cyr`; `programs/face_test.cyr` is the RUN proof.

## Consumers

**agnos** (1.57.2) is the first live consumer — of the *data* half: the
kernel folds `fonts/face_data.cyr` into its build and serves the face
read-only at `/fonts/default.ttf` (see *The embedded default face* above).
Downstream repos pull the *parser* half, `dist/rekha.cyr`, via a
`[deps.rekha]` git-tag entry; its intended consumers are the AGNOS
text/typography path — the `dhancha` UI toolkit, `crab`, a terminal,
document / UI text — anywhere scalable glyphs are needed.

## Dependencies

- **sadish** — the 2D vector-fill core rekha emits glyph paths into (the
  rasterize target), AND the allocation seam rekha draws from (`sd_alloc`).
  ⛔ Floor **0.5.5**: `sd_alloc` does not exist below it — the build may
  still compile (`warning: undefined function 'sd_alloc'`, printed either way)
  and fault at the first `rekha_font_open`, or be refused outright, depending
  on where the first call site sits (CHANGELOG 0.3.10). Wired via
  `[deps.sadish]` (`tag = "0.5.5"`, commit-pinned in `cyrius.lock`; for
  cross-repo dev add `path = "../sadish"` in an UNCOMMITTED copy — `path`
  wins over `tag`, skips the pin, and CI refuses a committed `path` line).
  A consumer vendoring `dist/rekha.cyr` next to its own `dist/sadish.cyr`
  must clear the same floor.
- **Cyrius stdlib** — `string`, `fmt`, `alloc`, `io`, `vec`, `str`,
  `syscalls`, `assert`, `bench`. Resolved by `cyrius deps` into `lib/`.
- **sankoch** — only for WOFF, and only through `dist/rekha-woff.cyr`: `zlib_decompress_capped`
  (sankoch >= 2.7.13; the cyrius 6.6.4 stdlib ships 2.7.15). A consumer includes `lib/sync.cyr` and
  `lib/sankoch.cyr` before the bundle. ⚠ sankoch's lean `[lib.zlib]` profile does not link on its own
  today (filed: `sankoch/docs/development/issues/2026-09-15-profile-bundles-call-sankoch-reset-tables-outside-their-closure.md`).
  WOFF2's Brotli decoder is requested from sankoch (see the v0.4.x line). `dist/rekha.cyr` needs no
  sankoch.

The toolchain pin is `cyrius = "6.6.4"`.

## Quick Start

```bash
cyrius deps                                          # resolve stdlib + sadish into lib/
cyrius build programs/smoke.cyr build/rekha-smoke    # link-check
./build/rekha-smoke                                  # prints the banner

# RUN tests (each self-checks and exits non-zero on failure; CI runs them all
# under CYRIUS_DCE=0 and 1 and fails on any build-log warning)
for t in programs/*_test.cyr; do
  n=$(basename "$t" .cyr)
  cyrius build "$t" "build/$n" && "./build/$n" || break
done

# hot-path timings (visibility only; not a gate)
cyrius build programs/bench_hotpath.cyr build/bench_hotpath && ./build/bench_hotpath
```

## License

GPL-3.0-only.
