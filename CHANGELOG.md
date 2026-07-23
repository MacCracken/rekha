# Changelog

All notable changes to rekha are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
