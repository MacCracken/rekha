# Characters and metrics

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

`rekha_char_to_glyph` is the `cmap` lookup — map a codepoint **once** and reuse the gid for
every advance, kern and path call. Horizontal metrics come from `hhea` / `hmtx` with the `HVAR`
delta applied; vertical from `vhea` / `vmtx` / `VORG` with `VVAR`; the line box a font
*intends* from `OS/2` and `post`, each taking its `MVAR` delta. The `_px` readers round half up
(`(v × px_size + upem/2) / upem`), the `_fx` readers answer 16.16.

Three vertical pairs exist — `hhea`'s ascender / descender / lineGap, `OS/2`'s sTypo trio and
its usWin pair — and rekha reports all three and chooses none: `rekha_use_typo_metrics` is the
font saying which it means, and the choice is the consumer's. A `0` from any metric reader is
*unknown*; `rekha_font_error` distinguishes it from a legal zero.

## Constants

### fsSelection bit 7


| name | value | meaning |
|---|---|---|
| `REKHA_OS2_USE_TYPO` | 128 |  |

## Functions

### `rekha_char_to_glyph(font, cp)`

```cyrius
fn rekha_char_to_glyph(font, cp): i64
```

Maps Unicode codepoint `cp` to a glyph id through the subtable chosen at open; returns 0 (.notdef) if the handle is 0, cp is outside 0..U+10FFFF (rekha_font_error = REKHA_ERR_OTHER, detail "codepoint"), there is no usable subtable (REKHA_ERR_NO_TABLE, "cmap"), or the mapped id is >= maxp.numGlyphs when maxp is present (REKHA_ERR_BAD_SFNT, "cmap glyph id"); an UNMAPPED character returns 0 with REKHA_OK — .notdef is the right answer, not an error. Clears the error on entry (after the 0-handle check), allocates 0 B. ⚠ Coverage follows the chosen table (format 4 / 6 / 0 cannot reach past U+FFFF / its range / U+00FF); a (3,0) SYMBOL table is retried at U+F000 + cp when cp <= U+00FF misses.

<!-- src/cmap.cyr:257 -->

### `rekha_char_advance(font, cp)`

```cyrius
fn rekha_char_advance(font, cp): i64
```

Advance width of codepoint `cp` in font DESIGN UNITS, = rekha_advance_width(font, rekha_char_to_glyph(font, cp)); 0 = unknown (and inherits rekha_char_to_glyph's error codes for a bad handle / codepoint / missing cmap). ⚠ An unmapped codepoint resolves to .notdef (gid 0), whose advance is a real metric in most fonts, so missing text still advances by the .notdef box rather than collapsing to zero. Allocates nothing.

<!-- src/cmap.cyr:314 -->

### `rekha_char_advance_px(font, cp, px_size)`

```cyrius
fn rekha_char_advance_px(font, cp, px_size): i64
```

Advance of `cp` in integer PIXELS at `px_size`, rounded half-up (nearest); = rekha_glyph_advance_px(font, rekha_char_to_glyph(font, cp), px_size). ⚠ Returns 0 when the metric is unknown OR `upem` is 0, so the caller's fallback is a single `== 0` test. ⛔ PER-GLYPH ROUNDING HALVES THE BIAS; IT DOES NOT STOP THE DRIFT — a run built by summing these integers accumulates up to half a pixel per glyph; exact run widths come from summing 16.16 advances (rekha_char_advance_fx) and rounding the pen ONCE. Allocates nothing.

<!-- src/cmap.cyr:330 -->

### `rekha_char_advance_fx(font, cp, px_size)`

```cyrius
fn rekha_char_advance_fx(font, cp, px_size): i64
```

Advance of `cp` at `px_size` as 16.16 fixed-point pixels; = rekha_glyph_advance_fx(font, rekha_char_to_glyph(font, cp), px_size). 0 = unknown. Allocates 0 B. Sum these and round the pen once for exact run widths (per rekha_char_advance_px's ⛔ note).

<!-- src/cmap.cyr:336 -->

### `rekha_os2_version(font)`

```cyrius
fn rekha_os2_version(font): i64
```

The OS/2 table's version number (u16 at +0), or -1 when the font has no OS/2 table (or the table is shorter than 78 bytes, or `font` is 0). This is the probe to call before trusting a 0 from any other OS/2 accessor. Does not allocate and sets no RekhaErrCode.

<!-- src/os2.cyr:85 -->

### `rekha_weight_class(font)`

```cyrius
fn rekha_weight_class(font): i64
```

usWeightClass, 1..1000 (400 = regular, 700 = bold); 0 when the font does not say. Not varied by MVAR. ⚠ This is the STATIC class — a variable font's `wght` axis (rekha_var_axis_tag / rekha_var_coord) is the live one and the two need not agree once an axis is set. No allocation, no RekhaErrCode.

<!-- src/os2.cyr:94 -->

### `rekha_width_class(font)`

```cyrius
fn rekha_width_class(font): i64
```

usWidthClass, 1..9 (5 = normal); 0 when the font does not say. Not varied by MVAR. No allocation, no RekhaErrCode.

<!-- src/os2.cyr:97 -->

### `rekha_fs_type(font)`

```cyrius
fn rekha_fs_type(font): i64
```

fsType, the embedding-permission bitfield as the font wrote it, or -1 when the font does not say (no OS/2, table too short, or `font` is 0) — note the sentinel here is -1, not 0. rekha neither enforces nor interprets it; a consumer that embeds fonts must. No allocation, no RekhaErrCode.

<!-- src/os2.cyr:101 -->

### `rekha_fs_selection(font)`

```cyrius
fn rekha_fs_selection(font): i64
```

fsSelection bitfield: bit 0 ITALIC, 5 BOLD, 6 REGULAR, 7 USE_TYPO_METRICS (mask REKHA_OS2_USE_TYPO = 128), 8 WWS, 9 OBLIQUE; -1 when the font does not say — the sentinel here is -1, not 0. No allocation, no RekhaErrCode.

<!-- src/os2.cyr:105 -->

### `rekha_use_typo_metrics(font)`

```cyrius
fn rekha_use_typo_metrics(font): i64
```

1 when fsSelection bit 7 (USE_TYPO_METRICS) is set — the font asking for its sTypo trio to be the line box — else 0, including when there is no OS/2 table to ask. ⛔ rekha reports the bit and picks none of the three vertical pairs: choosing is layout policy. No allocation, no RekhaErrCode.

<!-- src/os2.cyr:109 -->

### `rekha_typo_ascender(font)`

```cyrius
fn rekha_typo_ascender(font): i64
```

sTypoAscender (i16 at +68) in design units, plus its MVAR `hasc` delta at the current axis location. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:117 -->

### `rekha_typo_descender(font)`

```cyrius
fn rekha_typo_descender(font): i64
```

sTypoDescender (i16 at +70) in design units — NEGATIVE below the baseline — plus its MVAR `hdsc` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:118 -->

### `rekha_typo_line_gap(font)`

```cyrius
fn rekha_typo_line_gap(font): i64
```

sTypoLineGap (i16 at +72) in design units, plus its MVAR `hlgp` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:119 -->

### `rekha_win_ascent(font)`

```cyrius
fn rekha_win_ascent(font): i64
```

usWinAscent (u16 at +74) in design units, plus its MVAR `hcla` delta. ⚠ UNSIGNED. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:125 -->

### `rekha_win_descent(font)`

```cyrius
fn rekha_win_descent(font): i64
```

usWinDescent (u16 at +76) in design units, plus its MVAR `hcld` delta. ⚠ UNSIGNED and a POSITIVE distance below the baseline, where sTypoDescender is negative — not interchangeable; mixing them gives a line box off by twice the descent. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:126 -->

### `rekha_x_height(font)`

```cyrius
fn rekha_x_height(font): i64
```

sxHeight (i16 at +86, OS/2 version 2 and up) in design units, plus its MVAR `xhgt` delta. 0 when the table is older or shorter than the field. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:130 -->

### `rekha_cap_height(font)`

```cyrius
fn rekha_cap_height(font): i64
```

sCapHeight (i16 at +88, OS/2 version 2 and up) in design units, plus its MVAR `cpht` delta. 0 when the table is older or shorter than the field. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:131 -->

### `rekha_subscript_x_size(font)`

```cyrius
fn rekha_subscript_x_size(font): i64
```

ySubscriptXSize (i16 at +10) in design units, plus its MVAR `sbxs` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:137 -->

### `rekha_subscript_y_size(font)`

```cyrius
fn rekha_subscript_y_size(font): i64
```

ySubscriptYSize (i16 at +12) in design units, plus its MVAR `sbys` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:138 -->

### `rekha_subscript_x_offset(font)`

```cyrius
fn rekha_subscript_x_offset(font): i64
```

ySubscriptXOffset (i16 at +14) in design units from the baseline origin, plus its MVAR `sbxo` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:139 -->

### `rekha_subscript_y_offset(font)`

```cyrius
fn rekha_subscript_y_offset(font): i64
```

ySubscriptYOffset (i16 at +16) in design units, plus its MVAR `sbyo` delta. ⚠ Offsets are from the BASELINE, so a subscript's y offset is a positive distance DOWN — the sign convention is the field's. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:140 -->

### `rekha_superscript_x_size(font)`

```cyrius
fn rekha_superscript_x_size(font): i64
```

ySuperscriptXSize (i16 at +18) in design units, plus its MVAR `spxs` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:141 -->

### `rekha_superscript_y_size(font)`

```cyrius
fn rekha_superscript_y_size(font): i64
```

ySuperscriptYSize (i16 at +20) in design units, plus its MVAR `spys` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:142 -->

### `rekha_superscript_x_offset(font)`

```cyrius
fn rekha_superscript_x_offset(font): i64
```

ySuperscriptXOffset (i16 at +22) in design units from the baseline origin, plus its MVAR `spxo` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:143 -->

### `rekha_superscript_y_offset(font)`

```cyrius
fn rekha_superscript_y_offset(font): i64
```

ySuperscriptYOffset (i16 at +24) in design units, plus its MVAR `spyo` delta; a positive distance UP from the baseline. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:144 -->

### `rekha_strikeout_size(font)`

```cyrius
fn rekha_strikeout_size(font): i64
```

yStrikeoutSize (i16 at +26) — the strikeout rule's thickness in design units, plus its MVAR `strs` delta. Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:148 -->

### `rekha_strikeout_position(font)`

```cyrius
fn rekha_strikeout_position(font): i64
```

yStrikeoutPosition (i16 at +28) — the strikeout rule's position above the baseline in design units, plus its MVAR `stro` delta. The UNDERLINE pair is in `post` (rekha_underline_position / rekha_underline_thickness). Answers 0 when the font has no OS/2 table, the table is shorter than the field, or `font` is 0 — 0 is "the font did not say", not a measured zero; probe with rekha_os2_version (-1 = absent) before trusting a 0. Does not allocate and does not set a RekhaErrCode on the handle.

<!-- src/os2.cyr:149 -->

### `rekha_post_version(font)`

```cyrius
fn rekha_post_version(font): i64
```

Returns the post table's version as its raw 16.16 Fixed (0x00010000 for 1.0, 0x00020000 for 2.0, 0x00030000 for 3.0), or -1 when font is 0 or the font has no usable table (absent, or shorter than its 32-byte header). Does not allocate and does not set rekha_font_error. ⚠ The version tells a consumer whether glyph names would be present in the table, not whether rekha read any — glyph names are ⛔ not read.

<!-- src/post.cyr:46 -->

### `rekha_italic_angle(font)`

```cyrius
fn rekha_italic_angle(font): i64
```

Returns italicAngle as a signed 16.16 Fixed in DEGREES counter-clockwise from vertical, so an oblique face is NEGATIVE (the u32 field is sign-extended: values >= 0x80000000 have 0x100000000 subtracted). Returns 0 when font is 0 or there is no usable post table, which is also what an upright face says — probe with rekha_post_version to tell them apart. Does not allocate and sets no error code. ⚠ No MVAR tag exists for it: an italic angle does not vary.

<!-- src/post.cyr:56 -->

### `rekha_underline_position(font)`

```cyrius
fn rekha_underline_position(font): i64
```

Returns underlinePosition in design units: the TOP of the rule relative to the baseline, so normally NEGATIVE. Varies through MVAR's `undo` tag (the i16 field plus rekha_mvar_delta at the current axis position). Returns 0 when font is 0 or there is no usable post table; probe with rekha_post_version first. Does not allocate and sets no error code.

<!-- src/post.cyr:67 -->

### `rekha_underline_thickness(font)`

```cyrius
fn rekha_underline_thickness(font): i64
```

Returns underlineThickness in design units. Varies through MVAR's `unds` tag (the i16 field plus rekha_mvar_delta at the current axis position). Returns 0 when font is 0 or there is no usable post table; probe with rekha_post_version first. Does not allocate and sets no error code.

<!-- src/post.cyr:75 -->

### `rekha_is_fixed_pitch(font)`

```cyrius
fn rekha_is_fixed_pitch(font): i64
```

Returns 1 when every glyph has the same advance (post.isFixedPitch is non-zero), 0 when not, and -1 when font is 0 or there is no usable post table. ⚠ The field is a u32 and the spec only requires it to be non-zero for monospaced, so any non-zero value is collapsed to 1 rather than passed through. Does not allocate and sets no error code.

<!-- src/post.cyr:85 -->

### `rekha_num_h_metrics(font)`

```cyrius
fn rekha_num_h_metrics(font): i64
```

Answers hhea.numberOfHMetrics, how many glyphs carry their own long metric. Returns 0 when the handle is 0 or hhea is absent / shorter than its 36-byte fixed part, which callers must treat as 'no metrics'. Does not touch rekha_font_error.

<!-- src/sfnt.cyr:583 -->

### `rekha_ascender(font)`

```cyrius
fn rekha_ascender(font): i64
```

Answers hhea.ascender (i16 at hhea+4) in design units. Returns 0 for a 0 handle or an absent / short hhea (hhea_off is non-zero only when the table declares >= 36 B). Does not vary with axes (MVAR has no hhea ascender tag; the sTypo trio in OS/2 is what varies) and does not touch rekha_font_error.

<!-- src/sfnt.cyr:595 -->

### `rekha_descender(font)`

```cyrius
fn rekha_descender(font): i64
```

Answers hhea.descender (i16 at hhea+6) in design units, SIGNED: ⚠ negative in every well-formed font, deliberately, so `asc - desc + gap` is the line height. Returns 0 for a 0 handle or an absent / short hhea; does not vary with axes and does not touch rekha_font_error.

<!-- src/sfnt.cyr:603 -->

### `rekha_caret_slope_rise(font)`

```cyrius
fn rekha_caret_slope_rise(font): i64
```

Answers hhea.caretSlopeRise (i16 at hhea+18) plus the MVAR 'hcrs' delta at the current axis position, in design units. ⛔ Rise 1 with run 0 is upright: the pair is a vector, not an angle. Returns 0 for a 0 handle or an absent / short hhea; does not touch rekha_font_error. ⚠ This is hhea's caret, not post's italic angle; the two need not agree.

<!-- src/sfnt.cyr:616 -->

### `rekha_caret_slope_run(font)`

```cyrius
fn rekha_caret_slope_run(font): i64
```

Answers hhea.caretSlopeRun (i16 at hhea+20) plus the MVAR 'hcrn' delta, in design units; `run` is the component that carries the lean (0 = upright). Returns 0 for a 0 handle or an absent / short hhea; does not touch rekha_font_error.

<!-- src/sfnt.cyr:624 -->

### `rekha_caret_offset(font)`

```cyrius
fn rekha_caret_offset(font): i64
```

Answers hhea.caretOffset (i16 at hhea+22) plus the MVAR 'hcof' delta, in design units. Returns 0 for a 0 handle or an absent / short hhea; does not touch rekha_font_error.

<!-- src/sfnt.cyr:632 -->

### `rekha_line_gap(font)`

```cyrius
fn rekha_line_gap(font): i64
```

Answers hhea.lineGap (i16 at hhea+8) in design units. Returns 0 for a 0 handle or an absent / short hhea; does not vary with axes and does not touch rekha_font_error.

<!-- src/sfnt.cyr:640 -->

### `rekha_advance_width(font, gid)`

```cyrius
fn rekha_advance_width(font, gid): i64
```

Answers glyph `gid`'s advance width in DESIGN UNITS, plus the HVAR advance delta for the real gid at the current axis position; clears rekha_font_error on entry. Returns 0 with REKHA_ERR_OTHER "glyph id" for gid < 0, REKHA_ERR_NO_TABLE "hhea" when numberOfHMetrics is 0, REKHA_ERR_NO_TABLE "hmtx" when hmtx is absent, REKHA_ERR_TRUNCATED "hmtx" when the long metric lies past hmtx's DECLARED length; a 0 handle answers 0 with no code, and a legal zero-width advance answers 0 with REKHA_OK. ⛔ 0 is 'unknown', not 'zero-width': do not paint with it. ⛔ gid is clamped at numberOfHMetrics - 1 because the tail shares the last advance (the format, not a guess); a negative varied width is clamped to 0. Design units: scale by rekha_units_per_em or use rekha_glyph_advance_px / _fx.

<!-- src/sfnt.cyr:661 -->

### `rekha_left_side_bearing(font, gid)`

```cyrius
fn rekha_left_side_bearing(font, gid): i64
```

Answers glyph `gid`'s left side bearing in DESIGN UNITS plus the HVAR lsb-map delta (0.8.2); clears rekha_font_error on entry and refuses like rekha_advance_width: REKHA_ERR_OTHER "glyph id" for gid < 0, REKHA_ERR_NO_TABLE "hhea" / "hmtx", REKHA_ERR_TRUNCATED "hmtx" when the bearing lies past hmtx's declared length; a legal 0 answers REKHA_OK. ⛔ Tail rule is the format's: a gid at or past numberOfHMetrics reads `hmtx + numberOfHMetrics * 4 + (gid - numberOfHMetrics) * 2`. ⚠ The HINTED loader follows FreeType and does NOT apply the lsb delta (src/hint.cyr rekha_hint_hmetrics), so on a variation instance with an lsb map this metric and the hinted outline's origin differ by the delta (pinned in docs/development/roadmap.md).

<!-- src/sfnt.cyr:701 -->

### `rekha_glyph_advance_px(font, gid, px_size)`

```cyrius
fn rekha_glyph_advance_px(font, gid, px_size): i64
```

Answers glyph `gid`'s advance in whole PIXELS at `px_size`, rounded half-up: `(adv * px_size + upem / 2) / upem`. Returns 0 = unknown when upem <= 0 or the advance is <= 0; the advance path clears and may set rekha_font_error (via rekha_advance_width), but the upem <= 0 refusal returns before that and sets no code. Allocates 0 B. ⚠ Per-glyph rounded pixels drift when summed; accumulate rekha_glyph_advance_fx instead.

<!-- src/sfnt.cyr:719 -->

### `rekha_glyph_advance_fx(font, gid, px_size)`

```cyrius
fn rekha_glyph_advance_fx(font, gid, px_size): i64
```

Answers glyph `gid`'s advance at `px_size` as 16.16 fixed-point pixels: `(adv * px_size * 65536 + upem / 2) / upem`. Returns 0 = unknown when upem <= 0 or the advance is <= 0 (same code behaviour as rekha_glyph_advance_px). adv <= 65535, so the product fits i64 for any px_size below 2^31. Sum these into the pen and round once when placing a glyph; the run width is then exact to 1/65536 px per glyph. Allocates 0 B.

<!-- src/sfnt.cyr:733 -->

### `rekha_vhea_present(font)`

```cyrius
fn rekha_vhea_present(font): i64
```

Answers 1 when the font has a `vhea` directory entry of length >= 36 (recorded at open), else 0; 0 also for a null font. Sets no RekhaErrCode and allocates nothing. Ask this before trusting a 0 from rekha_vert_ascender / _descender / _line_gap / the caret trio / rekha_num_v_metrics, every one of which is a real value for some font.

<!-- src/vert.cyr:104 -->

### `rekha_vert_ascender(font)`

```cyrius
fn rekha_vert_ascender(font): i64
```

vhea.vertTypoAscender (offset 4) in design units plus the MVAR `vasc` delta at the current axis setting. Returns 0 when the font is null or has no vhea, which is indistinguishable from a real 0: probe rekha_vhea_present first. No RekhaErrCode is set; no allocation.

<!-- src/vert.cyr:111 -->

### `rekha_vert_descender(font)`

```cyrius
fn rekha_vert_descender(font): i64
```

vhea.vertTypoDescender (offset 6) in design units plus the MVAR `vdsc` delta. 0 for a null font or no vhea (a real 0 is possible; rekha_vhea_present disambiguates). No RekhaErrCode; no allocation.

<!-- src/vert.cyr:112 -->

### `rekha_vert_line_gap(font)`

```cyrius
fn rekha_vert_line_gap(font): i64
```

vhea.vertTypoLineGap (offset 8) in design units plus the MVAR `vlgp` delta. 0 for a null font or no vhea (a real 0 is common; rekha_vhea_present disambiguates). No RekhaErrCode; no allocation.

<!-- src/vert.cyr:113 -->

### `rekha_vert_caret_slope_rise(font)`

```cyrius
fn rekha_vert_caret_slope_rise(font): i64
```

vhea.caretSlopeRise (offset 18) in design units plus the MVAR `vcrs` delta. 0 for a null font or no vhea. No RekhaErrCode; no allocation.

<!-- src/vert.cyr:116 -->

### `rekha_vert_caret_slope_run(font)`

```cyrius
fn rekha_vert_caret_slope_run(font): i64
```

vhea.caretSlopeRun (offset 20) in design units plus the MVAR `vcrn` delta. 0 for a null font or no vhea (0 is also the real value for an upright caret; rekha_vhea_present disambiguates). No RekhaErrCode; no allocation.

<!-- src/vert.cyr:117 -->

### `rekha_vert_caret_offset(font)`

```cyrius
fn rekha_vert_caret_offset(font): i64
```

vhea.caretOffset (offset 22) in design units plus the MVAR `vcof` delta. 0 for a null font or no vhea (0 is the common real value; rekha_vhea_present disambiguates). No RekhaErrCode; no allocation.

<!-- src/vert.cyr:118 -->

### `rekha_num_v_metrics(font)`

```cyrius
fn rekha_num_v_metrics(font): i64
```

vhea.numOfLongVerMetrics (vhea offset 34, u16): how many glyphs carry their own advance height in vmtx. 0 when the font is null or has no vhea. ⚠ It reports vhea's count even when vmtx is absent or zero-length, in which case rekha_advance_height / rekha_top_side_bearing still answer 0 (hint_test checks vhea present, num_v_metrics 4, advance_height 0). No RekhaErrCode; no allocation.

<!-- src/vert.cyr:122 -->

### `rekha_advance_height(font, gid)`

```cyrius
fn rekha_advance_height(font, gid): i64
```

`gid`'s advance height in design units (vmtx advanceHeight u16 plus the VVAR advance-map delta, clamped so a negative result returns 0). Returns 0 when the font is null, gid < 0, there is no vhea, numOfLongVerMetrics is 0, vmtx is absent or zero-length, or the record lies past vmtx's length. ⚠ Like hmtx, a gid past numOfLongVerMetrics SHARES the last advance (the format's own rule) while VVAR's delta still applies to the real gid. No RekhaErrCode; no allocation.

<!-- src/vert.cyr:154 -->

### `rekha_top_side_bearing(font, gid)`

```cyrius
fn rekha_top_side_bearing(font, gid): i64
```

`gid`'s top side bearing in design units (i16 from vmtx's long record for gid < numOfLongVerMetrics, else from the bare i16 tail at nvm * 4 + (gid - nvm) * 2, plus the VVAR tsb-map delta). Returns 0 when the font is null, gid < 0, there is no vhea or vmtx, numOfLongVerMetrics is 0, or the 2-byte read would pass vmtx's length. ⛔ The tail past numOfLongVerMetrics is a BARE i16 array, not a continuation of the 4-byte records. No RekhaErrCode; no allocation.

<!-- src/vert.cyr:172 -->

### `rekha_vorg_present(font)`

```cyrius
fn rekha_vorg_present(font): i64
```

Answers 1 when the font carries a VORG table whose major version is 1 and length >= 8 (recorded at open), else 0; 0 for a null font. ⛔ rekha does NOT derive a vertical origin when the font states none, so this is the question to ask before rekha_vert_origin_y. No RekhaErrCode; no allocation.

<!-- src/vert.cyr:191 -->

### `rekha_vert_origin_y(font, gid)`

```cyrius
fn rekha_vert_origin_y(font, gid): i64
```

The y the pen sits at before drawing `gid` in a vertical run, in design units: VORG's per-glyph vertOriginY found by binary search over the sorted (glyphIndex, vertOriginY) records, else VORG's defaultVertOriginY, plus the VVAR vOrg-map delta. ⛔ Returns 0 when the font carries no VORG (rekha does NOT derive one from the bounding box and the top side bearing) or gid < 0; a 0 is also a legitimate origin, so ask rekha_vorg_present first. A record array that overruns the table falls back to the default. No RekhaErrCode; no allocation.

<!-- src/vert.cyr:201 -->

### `rekha_glyph_advance_height_px(font, gid, px_size)`

```cyrius
fn rekha_glyph_advance_height_px(font, gid, px_size): i64
```

`gid`'s advance height in whole pixels at `px_size`: (h * px_size + upem / 2) / upem, rounded half up, from rekha_advance_height and rekha_units_per_em. Returns 0 when unitsPerEm <= 0 or the design-unit advance height is <= 0 (so every refusal of rekha_advance_height propagates as 0). No RekhaErrCode; no allocation.

<!-- src/vert.cyr:234 -->

### `rekha_glyph_advance_height_fx(font, gid, px_size)`

```cyrius
fn rekha_glyph_advance_height_fx(font, gid, px_size): i64
```

`gid`'s advance height at `px_size` in 16.16 fixed point: (h * px_size * 65536 + upem / 2) / upem, rounded half up, from rekha_advance_height and rekha_units_per_em. Returns 0 when unitsPerEm <= 0 or the design-unit advance height is <= 0. No RekhaErrCode; no allocation.

<!-- src/vert.cyr:243 -->
