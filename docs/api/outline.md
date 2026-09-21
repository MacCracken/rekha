# Outlines and the sadish seam

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

`rekha_load_glyph(font, gid)` decodes a glyph — TrueType `glyf` (simple or composite, every
`gvar` delta applied at the current axis position) or CFF / CFF2 charstrings — into a
`RekhaOutline`: one allocation of the record plus its arrays, sized to the glyph, or the shared
**empty outline** (0 contours, 0 points) on any refusal, with the reason on the handle. The three
path emitters turn an outline into a positioned sadish `SdPath`; a refusal is an empty path.

## The `RekhaOutline` record

Six i64 slots, `REKHA_OUTLINE_SIZE` = 48 bytes, in this order: `n_contours`, `n_points`,
`end_pts` (a pointer to i64[n_contours], each the **last** point index of its contour, strictly
increasing and below `n_points`), `xs`, `ys` (pointers to i64[n_points], design units — F26Dot6
for a hinted view), `on_curve` (one byte per point: bit 0 on-curve, bit 1 a **cubic** control
from CFF; for a hinted view the `REKHA_TAG_*` bits). Read it through the six accessors. The
layout is frozen because a consumer may build one by hand to feed `rekha_outline_to_sdpath`.

### The size of the record


| name | value | meaning |
|---|---|---|
| `REKHA_OUTLINE_SIZE` | 48 |  |

## Functions

### `rekha_char_to_sdpath(font, cp, scale, ox, oy)`

```cyrius
fn rekha_char_to_sdpath(font, cp, scale, ox, oy): i64
```

Returns a sadish SdPath for codepoint `cp` scaled by `scale` and positioned at (`ox`, `oy`) via rekha_char_to_glyph then rekha_glyph_to_sdpath; an EMPTY path (not 0) for a character the font cannot draw is the contract every caller since 0.3.0 was written against. Allocates the path through sd_alloc (README: 20 calls under an arena hook cost the global heap exactly 0 bytes). ⚠ THE WRAPPER DOES NOT CLEAR the error itself; ⛔ if the cmap step refused (rekha_font_error != REKHA_OK) and the glyph step then reported REKHA_OK, it re-raises the first refusal's code and detail so the cmap reason survives the second call.

<!-- src/cmap.cyr:292 -->

### `rekha_outline_n_contours(o)`

```cyrius
fn rekha_outline_n_contours(o): i64
```

Number of closed contours in outline `o`; 0 = empty glyph (a space, or any refusal — rekha_font_error says which). A pure load of the i64 at o+0; allocates nothing.

<!-- src/glyf.cyr:77 -->

### `rekha_outline_n_points(o)`

```cyrius
fn rekha_outline_n_points(o): i64
```

Total point count across all contours — the length of the xs / ys / on_curve arrays. A pure load of the i64 at o+8; allocates nothing.

<!-- src/glyf.cyr:78 -->

### `rekha_outline_end_pts(o)`

```cyrius
fn rekha_outline_end_pts(o): i64
```

Pointer to i64[n_contours] holding the last-point index of each contour, or 0 for an empty outline. Loader guarantee: the entries STRICTLY increase and every one is < n_points, and the array is carved from the same sd_alloc block as the record. A pure load of the i64 at o+16; allocates nothing.

<!-- src/glyf.cyr:79 -->

### `rekha_outline_xs(o)`

```cyrius
fn rekha_outline_xs(o): i64
```

Pointer to i64[n_points] x coordinates in font design units (unitsPerEm space; the consumer scales), or 0 for an empty outline. A pure load of the i64 at o+24; allocates nothing.

<!-- src/glyf.cyr:80 -->

### `rekha_outline_ys(o)`

```cyrius
fn rekha_outline_ys(o): i64
```

Pointer to i64[n_points] y coordinates in font design units (y-up; rekha_outline_to_sdpath does the flip), or 0 for an empty outline. A pure load of the i64 at o+32; allocates nothing.

<!-- src/glyf.cyr:81 -->

### `rekha_outline_on_curve(o)`

```cyrius
fn rekha_outline_on_curve(o): i64
```

Pointer to u8[n_points] point flags: 1 = on-curve, 0 = quadratic control (glyf), 2 = cubic control (CFF / CFF2); or 0 for an empty outline. A pure load of the i64 at o+40; allocates nothing.

<!-- src/glyf.cyr:82 -->

### `rekha_load_glyph(font, gid)`

```cyrius
fn rekha_load_glyph(font, gid): i64
```

Loads glyph `gid` into a fresh RekhaOutline in design units — glyf simple or composite, or CFF / CFF2 charstrings when the face is an 'OTTO' whose CFF resolved (font+176 != 0) — with gvar deltas applied at the current axis location. Clears rekha_font_error on entry; returns an EMPTY outline (n_contours 0) for a space, a malformed glyph, an out-of-range gid or a tripped cap, and REKHA_OK then means the blank was real — otherwise rekha_font_error carries REKHA_ERR_TRUNCATED / REKHA_ERR_BAD_GLYF from the decoders, or REKHA_ERR_OOM with detail "point cap" / "contour cap" / "glyph load cap" for the caps REKHA_COMPOSITE_MAXP 4096, REKHA_COMPOSITE_MAXC 128, REKHA_COMPOSITE_MAXDEPTH 5, REKHA_GLYPH_MAXLOADS 64, REKHA_GLYPH_MAXPOINTS_TOTAL 16384 (an abort is sticky and never partial). Returns 0 ONLY on OOM (REKHA_ERR_OOM "outline"); allocates one sd_alloc block per decoded glyph (a composite also its children and an n-slot pointer array), so ⛔ an outline made under an arena hook must not be kept across that arena's reset, and ⚠ fonts are opened OUTSIDE a scoped hook.

<!-- src/glyf.cyr:608 -->

### `rekha_outline_to_sdpath(outline, scale, ox, oy)`

```cyrius
fn rekha_outline_to_sdpath(outline, scale, ox, oy): i64
```

Walks a RekhaOutline and returns a fresh sadish SdPath mapped by sd_x = ox + design_x * scale, sd_y = oy - design_y * scale (y-flipped), with `scale` in 16.16 px per design unit and (ox, oy) in 16.16 px; quadratic controls become quadto with implied midpoints, cubic-flagged pairs become cubicto. Returns an EMPTY path for a 0-contour or 0 outline; returns 0 when the path allocation or a growth mid-build is refused (never a silently truncated path) — it has no font argument so it sets no RekhaErrCode itself, rekha_glyph_to_sdpath records REKHA_ERR_OOM "sdpath" on its behalf. Allocates the path once through sd_alloc, opened by sd_path_new_cap at exactly the outline's verb and point counts (sadish >= 0.7.2); contours stop at the first end_pts entry that is negative or >= n_points, and ⚠ a hand-built outline must really hold n_points entries in xs / ys / on_curve and n_contours in end_pts because the seam cannot see an allocation's size.

<!-- src/glyf.cyr:803 -->

### `rekha_glyph_to_sdpath(font, gid, scale, ox, oy)`

```cyrius
fn rekha_glyph_to_sdpath(font, gid, scale, ox, oy): i64
```

rekha_load_glyph then rekha_outline_to_sdpath in one call: a positioned SdPath for glyph `gid` at `scale` (16.16 px per design unit) and 16.16 pixel offset (ox, oy). Returns an EMPTY path when the glyph loads empty (rekha_font_error says whether the blank was real); returns 0 when the outline load or the path allocation is refused — the load's own code stands, and only a path allocation that fails after a good outline sets REKHA_ERR_OOM "sdpath" (and only when rekha_font_error is still REKHA_OK). Allocates the outline block(s) and the path through sd_alloc; the same arena-lifetime ⛔ as rekha_load_glyph applies.

<!-- src/glyf.cyr:856 -->
