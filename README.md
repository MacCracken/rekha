# rekha

Version: 0.3.1

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
    delta-encoded coords → `RekhaOutline`); every read bounds-checked.
  - **sadish seam** — `rekha_outline_to_sdpath` / `rekha_glyph_to_sdpath`
    convert TrueType quadratic contours (implied midpoints, off-curve
    starts) into a sadish `SdPath`, y-flipped + scaled to pixel space.
    **`sadish` is wired as a dependency; rekha is its first consumer.**
- **v0.3.0 — text (shipped).** Characters → glyphs, and composite glyphs:
  - **cmap format 4** — `rekha_char_to_glyph` (Unicode BMP codepoint → glyph
    id) + `rekha_char_to_sdpath` (one call: character → positioned sadish path).
  - **Composite glyphs** — `rekha_load_glyph` decodes numberOfContours < 0
    (recursive component load, F2Dot14 transform + offset, merged outline).
- **v0.4.0 / staged — next:** cmap formats 12 (full Unicode) / 6 / 0,
  OpenType/CFF (`OTTO`) outlines, WOFF/WOFF2 (needs `sankoch` inflate +
  Brotli), and hinting.

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

## Consumers

rekha has no live consumer yet; downstream repos pull `dist/rekha.cyr` via
a `[deps.rekha]` git-tag entry. Its intended consumers are the AGNOS
text/typography path — the `dhancha` UI toolkit, a terminal, document /
UI text — anywhere scalable glyphs are needed.

## Dependencies

- **sadish** — the 2D vector-fill core rekha emits glyph paths into (the
  rasterize target). Wired via `[deps.sadish]` (local path override
  `../sadish` for cross-repo dev; git tag as the published pin).
- **Cyrius stdlib** — `string`, `fmt`, `alloc`, `io`, `vec`, `str`,
  `syscalls`, `assert`, `bench`. Resolved by `cyrius deps` into `lib/`.
- No inflate/thread deps yet — SFNT tables are read raw (uncompressed).
  WOFF/WOFF2 (which need `sankoch`) are a later scope.

The toolchain pin is `cyrius = "6.4.7"`.

## Quick Start

```bash
cyrius deps                                          # resolve stdlib + sadish into lib/
cyrius build programs/smoke.cyr build/rekha-smoke    # link-check
./build/rekha-smoke                                  # prints the banner

# RUN tests (each self-checks and exits non-zero on failure)
for t in sfnt meta glyf path cmap composite; do
  cyrius build "programs/${t}_test.cyr" "build/${t}_test" && "./build/${t}_test"
done
```

## License

GPL-3.0-only.
