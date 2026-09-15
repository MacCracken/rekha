# rekha

Version: 0.4.0

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
- **v0.4.x line — next, in order:**
  1. ~~cmap formats 12 / 6 / 0 + symbol fonts~~ — shipped in 0.4.0, above.
  2. **WOFF 1.0** — per-table zlib through sankoch's `[lib.zlib]` profile
     (`zlib_decompress_capped`, sankoch >= 2.7.13), output sized from the WOFF directory and capped.
  3. **OpenType/CFF (`OTTO`) outlines** — Type 2 charstrings (subroutines, CID-keyed FDSelect) emitted
     as cubic Béziers through `sd_path_cubicto`, under the same load budget as glyf.
  4. **WOFF2** — the container, the glyf/loca and hmtx transforms, tested on
     transformed-but-uncompressed tables; the Brotli stream decodes through sankoch's requested
     `[lib.brotli]` (`sankoch/docs/development/proposals/2026-09-15-brotli-decoder-for-woff2.md`).
  5. **`[deps].stdlib` trim** — to what `src/` calls; released on its own, since it changes the
     `dist/rekha.deps` sidecar consumers resolve.
  6. **Adopt the sadish filings as they ship** — bounded flatten, checked path allocation,
     `sd_path_new_cap` sized from the outline (5.5× less path arena on ASCII, MEASURED).
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
- **sankoch** arrives with WOFF 1.0 (`[lib.zlib]`) and WOFF2 (`[lib.brotli]`, requested —
  see the v0.4.x line). Until then SFNT tables are read raw (uncompressed).

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
