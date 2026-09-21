# Variations

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

A variable font's axes (`fvar`, normalised through `avar`) are set per handle:
`rekha_var_set_axis` / `rekha_var_set_instance` / `rekha_var_reset` change what every later
`rekha_load_glyph`, advance and metric reader answers for that font, and mark a cached hint
context stale (call `rekha_hint_ctx` again — [`hint.md`](hint.md) rule 2). The first setter
allocates the coordinate and region-scalar arrays on the seam; setters are not per-glyph calls.
Coordinates are 16.16 **user** units on the way in and normalised 16.16 (−1.0 … 1.0) from
`rekha_var_coord`. The three delta readers expose what `HVAR` / `MVAR` add, for a consumer
applying a metric of its own.

## Functions

### `rekha_hvar_advance_delta(font, gid)`

```cyrius
fn rekha_hvar_advance_delta(font, gid): i64
```

Answers how much glyph `gid`'s advance width moves at the current axis setting, in design units (not 16.16), summed over every region and rounded HALF UP once. Returns 0 when `font` is 0, `gid` < 0, the font has no HVAR, no axis is set (rekha_var_live == 0), or the store/map refuses (major version != 1, indices out of range, wordDeltaCount > regionIndexCount, a delta beyond REKHA_VAR_MAXDELTA = 1048576 design units) — the advance then stays at its DEFAULT, never half-varied; it never sets a RekhaErrCode and 0 is indistinguishable from a true zero delta. Does not allocate (stack arrays only); scalars are computed on demand, not cached. An absent advance map means the glyph id IS the inner index.

<!-- src/hvar.cyr:240 -->

### `rekha_hvar_lsb_delta(font, gid)`

```cyrius
fn rekha_hvar_lsb_delta(font, gid): i64
```

Answers how much glyph `gid`'s left side bearing moves at the current axis setting, in design units, via the lsb DeltaSetIndexMap at HVAR+12. ⛔ THE TWO MAPS DEFAULT DIFFERENTLY: an absent (NULL) lsb map answers 0, never an implicit row, whereas an absent advance map means the gid is the inner index. Returns 0 likewise when `font` is 0, `gid` < 0, the font has no HVAR, no axis is set, or the table refuses; never sets a RekhaErrCode; does not allocate. ⚠ rekha_left_side_bearing (src/sfnt.cyr) applies this delta but the HINTED loader's left phantom (rekha_hint_hmetrics) does not, following FreeType 2.14.3 (ref2143/ttdriver.c:559) — on a variation instance with an lsb map the two differ by the delta; pinned in docs/development/roadmap.md.

<!-- src/hvar.cyr:272 -->

### `rekha_mvar_delta(font, tag)`

```cyrius
fn rekha_mvar_delta(font, tag): i64
```

Answers how much the font-wide metric named by the four-byte `tag` (e.g. REKHA_MVAR_HASC = 0x68617363 'hasc') moves at the current axis setting, in design units, by a linear scan of MVAR's ValueRecords. Returns 0 when `font` is 0, there is no MVAR, no axis is set, the tag is absent, valueRecordSize < 8, the record array runs past the table, the store offset is < 12, or the ItemVariationStore refuses; never sets a RekhaErrCode (0 is also a legal delta); does not allocate. Tags rekha has no reader for are SKIPPED, not refused; hhea's ascender/descender/lineGap have no MVAR tag and do not move.

<!-- src/hvar.cyr:293 -->

### `rekha_var_axis_count(font)`

```cyrius
fn rekha_var_axis_count(font): i64
```

Number of fvar axes the font declares. Returns 0 for a null font, a font with no fvar, or an fvar the resolver refused (majorVersion != 1, axisCount < 1 or > 64, axisSize < 20, or axis records past the table end). Never records a RekhaErrCode (rekha_var_resolve never fails an open); no allocation.

<!-- src/var.cyr:70 -->

### `rekha_var_axis_tag(font, i)`

```cyrius
fn rekha_var_axis_tag(font, i): i64
```

Axis i's four-byte tag as a big-endian u32 (e.g. 'wght'), read at record offset 0. Returns 0 for a null font or an index outside [0, rekha_var_axis_count). No allocation, no RekhaErrCode.

<!-- src/var.cyr:84 -->

### `rekha_var_axis_name_id(font, i)`

```cyrius
fn rekha_var_axis_name_id(font, i): i64
```

The axisNameID of axis i (u16 at record offset 18), to pass to rekha_name_utf8 for the label text. Returns 0 when the font has no such axis (null font or bad index). No allocation, no RekhaErrCode.

<!-- src/var.cyr:104 -->

### `rekha_var_axis_min(font, i)`

```cyrius
fn rekha_var_axis_min(font, i): i64
```

Axis i's minValue as a signed 16.16 user value (fvar Fixed at record offset 4, sign-extended from the u32 read: v >= 0x80000000 -> v - 0x100000000). Returns 0 for a bad index or null font. No allocation, no RekhaErrCode.

<!-- src/var.cyr:111 -->

### `rekha_var_axis_default(font, i)`

```cyrius
fn rekha_var_axis_default(font, i): i64
```

Axis i's defaultValue as a signed 16.16 user value (fvar Fixed at record offset 8, sign-extended). Returns 0 for a bad index or null font. No allocation, no RekhaErrCode.

<!-- src/var.cyr:112 -->

### `rekha_var_axis_max(font, i)`

```cyrius
fn rekha_var_axis_max(font, i): i64
```

Axis i's maxValue as a signed 16.16 user value (fvar Fixed at record offset 12, sign-extended). Returns 0 for a bad index or null font. No allocation, no RekhaErrCode.

<!-- src/var.cyr:113 -->

### `rekha_var_instance_count(font)`

```cyrius
fn rekha_var_instance_count(font): i64
```

Number of fvar named instances the font ships. Returns 0 for a null font, no instances, or an instance array the resolver refused (instanceCount > 4096, instanceSize other than axisCount x 4 + 4 or axisCount x 4 + 6, or records past the table end); a refused instance array loses only the instances, the axes stay. No allocation, no RekhaErrCode.

<!-- src/var.cyr:275 -->

### `rekha_var_instance_name_id(font, i)`

```cyrius
fn rekha_var_instance_name_id(font, i): i64
```

Instance i's subfamilyNameID (u16 at record offset 0), to pass to rekha_name_utf8. Returns 0 when there is no such instance. No allocation, no RekhaErrCode.

<!-- src/var.cyr:290 -->

### `rekha_var_instance_ps_name_id(font, i)`

```cyrius
fn rekha_var_instance_ps_name_id(font, i): i64
```

Instance i's postScriptNameID (u16 at record offset 4 + axisCount x 4). Returns 0 when there is no such instance or when instanceSize != axisCount x 4 + 6 — ⚠ the field is OPTIONAL and its presence is told by instanceSize alone. No allocation, no RekhaErrCode.

<!-- src/var.cyr:299 -->

### `rekha_var_instance_flags(font, i)`

```cyrius
fn rekha_var_instance_flags(font, i): i64
```

Instance i's flags u16 (record offset 2); every bit is reserved as of OpenType 1.9. Returns 0 when there is no such instance. No allocation, no RekhaErrCode.

<!-- src/var.cyr:308 -->

### `rekha_var_instance_coord(font, i, a)`

```cyrius
fn rekha_var_instance_coord(font, i, a): i64
```

Instance i's coordinate on axis a as a signed 16.16 USER value (record offset 4 + a x 4, sign-extended from the u32). Returns 0 when either index is out of range — ⚠ 0 is a real coordinate on most axes, so check rekha_var_instance_count and rekha_var_axis_count first. No allocation, no RekhaErrCode.

<!-- src/var.cyr:316 -->

### `rekha_var_set_instance(font, i)`

```cyrius
fn rekha_var_set_instance(font, i): i64
```

Puts every axis at instance i's user coordinates through rekha_var_set_axis, so the next rekha_load_glyph draws that style. Returns 1, or 0 when there is no such instance (or a rekha_var_set_axis call fails). ⛔ It sets EVERY axis, including ones the instance leaves at default — a named instance is a whole location. Allocates on first use exactly as rekha_var_set_axis does and marks a cached hint context stale; no RekhaErrCode.

<!-- src/var.cyr:329 -->

### `rekha_var_coord(font, i)`

```cyrius
fn rekha_var_coord(font, i): i64
```

The normalized 16.16 coordinate axis i currently sits at (after avar), in [-65536, 65536]; 0 at the default location and until rekha_var_set_axis moves it. Returns 0 for a null font, an index outside [0, rekha_var_axis_count), or before the coordinate array exists — 0 is indistinguishable from 'at default'. No allocation, no RekhaErrCode.

<!-- src/var.cyr:343 -->

### `rekha_var_set_axis(font, i, value)`

```cyrius
fn rekha_var_set_axis(font, i, value): i64
```

Puts axis i at value (16.16 USER units, the scale fvar's min / default / max use), normalizes it, applies avar, rebuilds every region scalar, and marks a cached rekha_hint_ctx stale via a forward call to rekha_hint_axes_changed so the next rekha_hint_ctx re-runs prep. Returns 1 on success, 0 for a null font, a font with no axes, a bad index, or an allocation failure; no RekhaErrCode. ⚠ ALLOCATION: the coordinate array (REKHA_VAR_MAXAXES * 8 = 512 bytes) and the scalar array (REKHA_VAR_MAXREGION * 8 = 32768 bytes) are allocated on the first call, reused after, and never freed. ⚠ It changes what EVERY later rekha_load_glyph returns for this font and is not cheap enough for a per-glyph call: set the axes once, then draw.

<!-- src/var.cyr:362 -->

### `rekha_var_reset(font)`

```cyrius
fn rekha_var_reset(font): i64
```

Puts every axis back at its default: zeroes all REKHA_VAR_MAXAXES coordinate slots if the array exists, sets the region-scalar count (font+328) to 0, and marks a cached hint context stale as rekha_var_set_axis does. Returns 1 when the font has axes, 0 for a null font or one with no axes. Does not allocate or free; no RekhaErrCode.

<!-- src/var.cyr:404 -->
