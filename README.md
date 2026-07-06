# rekha

Version: 0.1.0

**rekha** (रेखा — Sanskrit/Hindi: *line / outline / contour / stroke*) is
a pure-Cyrius vector/outline font subsystem for AGNOS. It parses
TrueType/OpenType (SFNT) font containers and loads glyph outlines,
emitting resolution-independent **paths** (line / quadratic-Bézier verbs)
for the `sadish` 2D vector core to rasterize.

rekha does **not** bundle its own Bézier rasterizer — it produces the
glyph-outline path stream; `sadish` fills it. The two form a clean seam:
rekha owns *what the glyph is* (SFNT tables → outlines), sadish owns
*how it becomes pixels* (fill → coverage).

## Scope

- **v0.1.0 — scaffold.** A buildable compiling skeleton: real error
  codes + real struct layouts + real fn signatures with stub bodies and
  `# TODO(v0.2)` markers where the parse/decode algorithms land. It
  compiles and links clean (`programs/smoke.cyr`); it does not yet
  decode a real font. The shape is in place: big-endian SFNT byte
  readers (`rekha_rd_u16` / `rekha_rd_u32` / `rekha_rd_i16`), the
  `RekhaFont` SFNT handle + `rekha_font_open` / `rekha_find_table`, the
  `RekhaOutline` record + `rekha_load_glyph`, and the
  `rekha_outline_to_path` seam that will emit sadish path verbs.
- **v0.2.0 — real SFNT + glyf.** Locate head / cmap / glyf / loca / hhea
  / maxp; decode a simple TrueType glyph (contours, run-length flags,
  delta-encoded coords) into a `RekhaOutline`; walk on-curve/off-curve
  point runs into quadto/lineto/close verbs; wire `sadish` as the
  rasterize target. Composite glyphs + cmap character mapping follow.
- **Staged (tracked, not silently dropped):** OpenType/CFF (`OTTO`)
  outlines; WOFF/WOFF2 (needs `sankoch` inflate + Brotli); hinting.

## Place in the stack

rekha is a **system library** in the Sanskrit/Hindi naming lane. It sits
alongside `kashi` (काशि) as the *outline* half of a sibling font pair:

- **kashi** — **bitmap** glyph sources: PSF1/PSF2, VGA-ROM 8x16 / CGA
  8x8, hand-drawn. Fixed-resolution; a freestanding kernel can embed it.
- **rekha** — **outline / Bézier** glyph sources: TrueType/OpenType.
  Scalable, resolution-independent; for high-DPI and arbitrary point
  sizes where a bitmap font can't follow.

rekha reads font bytes → emits outline paths; **sadish** rasterizes those
paths → coverage/pixels. rekha is pure CPU Cyrius: no GPU, no C shim, no
external binaries.

## Consumers

- **sadish** — the 2D vector-fill core; the rasterize target for the
  path stream `rekha_outline_to_path` emits. Deferred cross-dep: not
  wired at scaffold. When the path seam lands its real body (v0.2), add
  `[deps.sadish] path = "../sadish"` to `cyrius.cyml`.
- Downstream: the AGNOS text/typography path (compositor + terminal +
  UI) that needs scalable glyphs, via sadish.

Consumers pull `dist/rekha.cyr` via a `[deps.rekha]` entry at a git tag.

## Dependencies

- **Cyrius stdlib** — `string`, `fmt`, `alloc`, `io`, `vec`, `str`,
  `syscalls`, `assert`, `bench`. Resolved by `cyrius deps` into `lib/`.
- No inflate/thread deps at v0.1.0 — SFNT tables are read raw
  (uncompressed). WOFF/WOFF2 (which need `sankoch`) are a later scope.

The toolchain pin is `cyrius = "6.4.7"`.

## Quick Start

```bash
cyrius deps                                          # resolve stdlib into lib/
cyrius build programs/smoke.cyr build/rekha-smoke    # link-check
./build/rekha-smoke                                  # prints the banner
```

## License

GPL-3.0-only.
