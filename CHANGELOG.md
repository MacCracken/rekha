# Changelog

All notable changes to rekha are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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

## [Unreleased]

## [0.3.7] - 2026-09-11

### Changed

- **Toolchain `6.5.41` → `6.6.2`.** No source change; the value form needed none.
  Build, tests, and any bench/fuzz/distlib target the repo ships re-verified at the new pin.
