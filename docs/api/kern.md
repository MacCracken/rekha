# Kerning

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

`rekha_kern_pair(font, left, right)` answers the pair adjustment in design units from `GPOS`
pair positioning when the font has it — the union of every `kern` feature's lookups, at the
default axis location — and from the legacy `kern` table (format 0) otherwise;
`rekha_kern_source` says which. The two table-specific readers are there for a consumer that
wants one source only. `rekha_char_kern` is the codepoint form; `rekha_kern_pair_px` the
pixel form, rounded half up.

## Functions

### `rekha_gpos_kern_present(font)`

```cyrius
fn rekha_gpos_kern_present(font): i64
```

Answers 1 when the font carries a version-1 GPOS table with at least one `kern` FeatureRecord whose lookups resolve (any lookup type — a feature whose lookups are all types rekha skips still answers 1, per programs/gpos_test.cyr:578), else 0; 0 for a null handle. The first call lazily resolves the lookups into one sd_alloc of REKHA_GPOS_MAXLOOKUP x 8 = 512 bytes and writes the handle (+592/+600), so it is not thread-safe across a shared handle. It never sets a RekhaErrCode: rekha_font_error is untouched by anything in gpos.cyr.

<!-- src/gpos.cyr:303 -->

### `rekha_gpos_kern_pair(font, l, r)`

```cyrius
fn rekha_gpos_kern_pair(font, l, r): i64
```

The first glyph's XAdvance adjustment for glyph pair (l, r) from GPOS alone, in design (font) units, usually negative. Returns 0 — with NO RekhaErrCode recorded — for a null font, l or r < 0 or > 65535, no GPOS, no `kern` feature, or a pair no PairPos matches, so 0 is indistinguishable from a real kern of zero except via rekha_gpos_kern_present / rekha_kern_source. ⛔ Lookups ACCUMULATE (the sum over every deduplicated `kern`-feature lookup) while within one lookup the FIRST subtable that matches wins; only lookup type 2 (or 9 wrapping a 2) is consulted; Device / VariationIndex deltas are ignored so a variable font answers its default instance; the first query allocates 512 bytes via rekha_gpos_lookups.

<!-- src/gpos.cyr:314 -->

### `rekha_kern_present(font)`

```cyrius
fn rekha_kern_present(font): i64
```

Returns 1 when the handle resolved a legacy `kern` table rekha can walk (Microsoft version 0 or Apple 0x00010000), else 0; a 0 handle returns 0. Allocates nothing and records no RekhaErrCode. ⚠ 0 does NOT mean the font has no kerning — a modern face keeps it in GPOS; `rekha_kern_source` is the question to ask.

<!-- src/kern.cyr:75 -->

### `rekha_kern_table_pair(font, l, r)`

```cyrius
fn rekha_kern_table_pair(font, l, r): i64
```

The adjustment for glyph pair (l, r) from the legacy `kern` table ALONE, in design units, usually negative. Returns 0 when the font has no `kern`, when l or r is < 0 or > 65535, when the pair is not in the table, or when every subtable that could carry it is one rekha skips (format != 0, non-HORIZONTAL, CROSS_STREAM, MINIMUM); OVERRIDE subtables replace the accumulated total, others add. The walk is capped at REKHA_KERN_MAXSUB (256) subtables; allocates nothing and records no RekhaErrCode. ⚠ `rekha_kern_pair` is the one to call: since 0.6.6 it prefers GPOS.

<!-- src/kern.cyr:116 -->

### `rekha_kern_source(font)`

```cyrius
fn rekha_kern_source(font): i64
```

Answers where the font keeps its kerning: 0 neither, 1 the legacy `kern` table, 2 GPOS; a 0 handle returns 0. ⛔ NOT BOTH: GPOS wins when a face carries both, because such a face usually says the same thing twice and adding them would double every pair. Allocates nothing directly (the GPOS presence probe it calls resolves GPOS kern lookups lazily on first query) and records no RekhaErrCode.

<!-- src/kern.cyr:193 -->

### `rekha_kern_pair(font, l, r)`

```cyrius
fn rekha_kern_pair(font, l, r): i64
```

THE kerning adjustment for glyph pair (l, r) in design units, from wherever the font keeps it: GPOS when the font has a `kern` feature there (since 0.6.6), the legacy table otherwise; `rekha_kern_source` says which answered. Returns 0 for a 0 handle, an out-of-range gid (< 0 or > 65535), an absent pair, or a font with neither table; records no RekhaErrCode. Allocates nothing itself; the first GPOS query on a handle resolves its kern lookups lazily into one sd_alloc.

<!-- src/kern.cyr:203 -->

### `rekha_kern_pair_px(font, l, r, px_size)`

```cyrius
fn rekha_kern_pair_px(font, l, r, px_size): i64
```

The same adjustment as rekha_kern_pair scaled to whole pixels at `px_size`: floor((v * px_size + upem / 2) / upem), i.e. rounded HALF UP as every other rounding in rekha is. ⚠ Half up, not half away from zero: -1.5 px comes back -1. Returns 0 when units-per-em is <= 0 (including a 0 handle) or when the design-unit adjustment is 0; allocates nothing and records no RekhaErrCode.

<!-- src/kern.cyr:210 -->

### `rekha_char_kern(font, cp1, cp2)`

```cyrius
fn rekha_char_kern(font, cp1, cp2): i64
```

The kerning adjustment between two CHARACTERS (codepoints cp1, cp2) in design units, mapped through cmap then answered by rekha_kern_pair. Returns 0 when either codepoint maps to gid 0 (unmapped, or no usable cmap) or the handle is 0; allocates nothing and records no RekhaErrCode.

<!-- src/kern.cyr:220 -->
