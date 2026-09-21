# Changelog

All notable changes to rekha are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.7.0] - 2026-09-20 — `RekhaErr` gets a producer

`src/error.cyr` has declared "@public — stable API surface for rekha error handling" since 0.1.0
and **nothing in rekha ever produced one**. Every failure collapsed to a sentinel:
`rekha_advance_width` returned 0 for "no hhea", "hmtx truncated" and "this glyph is genuinely
zero-width" alike, and its own comment said so. rekha's rule, written in `src/sfnt.cyr` about two
tags it declared and never read, is that **a declared name with no reader is a promise and not a
feature**. This release is the reader.

⛔ **THE VALUE rekha RETURNS DOES NOT MOVE.** An empty outline for a refused glyph, a 0 advance, an
empty path — every one is what it was, because every caller since 0.2.0 was written against them.
What is new is that `rekha_font_error` says which.

### The three ambiguities this exists for

| the sentinel | what it meant | what tells them apart now |
|---|---|---|
| an EMPTY outline from `rekha_load_glyph` | a space, **or** any refusal there is | `REKHA_OK` means the blank was real |
| a 0 from `rekha_advance_width` | a legal zero-width metric, **or** no hhea, **or** hmtx truncated | `REKHA_ERR_NO_TABLE` / `_TRUNCATED` |
| a 0 from `rekha_char_to_glyph` | the drawable `.notdef` box, **or** this font has no cmap | `REKHA_ERR_NO_TABLE`, detail `"cmap"` |

### Found while wiring it: the ambiguity was one level below where it was being looked for

⭐ `rekha_glyf_span`'s own 0 meant **both** "the glyph is empty (e.g. space)" and "loca is lying" —
its doc comment listed the two in the same bullet list. Wiring the LOADER alone therefore reported
every space as a malformed glyph. The empty case is now silent and every other 0 says why, which
also fixes the public `rekha_glyf_span` for anyone calling it directly.

### Added

`rekha_font_error(font)`, `rekha_font_error_detail(font)` — a short **static** cstring naming the
table or field, never allocated and never owned by the caller — and `rekha_font_error_clear`.
Plus `rekha_font_open_why(buf, len, err_out)` and `rekha_font_open_index_why(...)`, because an open
fails **before there is a handle**, which is the whole failure; they take a caller-supplied i64
slot (or 0 to ignore) and set it on success as well.

Reporting today: the two `_why` opens, `rekha_glyf_span`, `rekha_load_glyph`,
`rekha_glyph_to_sdpath`, `rekha_char_to_glyph`, `rekha_char_to_sdpath` and `rekha_advance_width`.
⚠ **Not yet**: the WOFF and WOFF2 opens, and the CFF interpreter's own refusals. The metadata
readers already answer through a `_present` probe and do not need one. Both gaps are pinned.

### Removed — the 16-byte `RekhaErr` record, and its four helpers

⛔ `rekha_err_new` called `sd_alloc(16)`, so **constructing an out-of-memory error allocated**. An
error path that can fail the same way as the thing it reports is not an error path. Nothing
produced one, and rekha now reports a code and a detail pointer straight out of the handle with no
record to build and no byte allocated — `programs/error_test.cyr` group H pins that at zero.
Removing published names is exactly what a pre-freeze release is for.

### ⛔ Per handle, not a global, and the reason is not taste

**Cyrius 6.6.6 has no thread-local storage and `lib/thread.cyr` exposes no thread id**, so a
per-thread slot could not even be keyed: a global last-error would be **unfixable**, and calling it
thread-safe would be the promise-that-is-not-a-feature this release exists to delete. rekha also
has no mutable module-level state anywhere in `src/` — every `var` in the library is a constant —
and a diagnostic is a poor reason to be the first.

⚠ **ONE HANDLE, ONE THREAD** is a new obligation and is stated rather than glossed: share the
borrowed font bytes, open a handle per thread, which costs `REKHA_FONT_SIZE` and not the file.
⚠ The handle was already written by readers (GPOS resolves its lookups lazily, `rekha_var_set_axis`
writes the coordinates); 0.7.0 adds to that, it does not introduce it.

⚠ **The contract is "ask immediately after the sentinel."** Every call that can set a code clears it
first, so a code describes the LAST call — but a reader that cannot refuse, like
`rekha_units_per_em`, does not clear, so a question asked after one of those still reports what came
before. That is a contract, not a guarantee, and it is written in the source rather than left to be
discovered.

`REKHA_FONT_SIZE` **672 -> 688**. ⇒ `programs/error_test.cyr` rewritten, **88 checks**: the
vocabulary including every byte-value's name, a clean font that stays quiet, six open refusals
through the `_why` slot, a blank glyph against a refused one, three advance failures told apart,
`.notdef` against a missing cmap, the wrapper that must not lose the first reason, and a loop
proving the whole mechanism allocates nothing.

## [0.6.7] - 2026-09-20 — vertical metrics, and the close of 0.6.x

`vhea`, `vmtx`, `VORG` and `VVAR`: everything rekha knows about laying a line of text DOWN the page
instead of across it. A CJK face set vertically needs a per-glyph advance HEIGHT, a vertical line
box, a top side bearing and a vertical origin, and none of it is derivable from the horizontal
metrics. **This is the last item of the 0.6.x milestone.**

⭐ **AND IT CLOSES MVAR.** `vasc`, `vdsc`, `vlgp`, `vcrs`, `vcrn` and `vcof` were the last tags with
nowhere to land, so **every one of MVAR's 28 tags now lands on the field the spec names** —
re-measured against fontTools' instancer on the same bytes, two axes, eight locations:

| | fields | identical |
|---|---:|---|
| **0.6.7** | **28 MVAR + 3 unvarying hhea + 8 advances** | **312 of 312** |
| 0.6.4 | 22 MVAR + 3 + 8 | 264 of 264 |

⚠ **0.6.4 said there were four `vhea` tags left. There are six** — it counted the line box and
missed the caret. This is the correction; the live comment that said it is fixed too.

### Added — `src/vert.cyr`

`rekha_vhea_present`, `rekha_vert_ascender` / `_descender` / `_line_gap`,
`rekha_vert_caret_slope_rise` / `_run` / `_offset`, `rekha_num_v_metrics`,
`rekha_advance_height` (+ `_px`, `_fx`), `rekha_top_side_bearing`, `rekha_vorg_present`,
`rekha_vert_origin_y`.

- ⛔ **A glyph's vertical origin is NOT its top side bearing.** `VORG` gives the origin outright and
  is what a CFF face carries; a TrueType face usually has none, and the convention is to derive one
  from the bounding box and the bearing. **rekha does not derive it.** `rekha_vorg_present` says
  whether the font stated one, and the reader answers only when it did — guessing here would put
  every glyph of a vertical run at a plausible wrong height.
- ⛔ **`vmtx`'s tail is a BARE i16 array**, not a continuation of its 4-byte records. Reading it
  with the wrong stride hands back another glyph's advance as a bearing. The fixture has six glyphs
  and four long metrics so the tail is exercised rather than assumed.
- **VVAR** varies the advance height, the top side bearing and the vertical origin, through
  `src/hvar.cyr`'s `rekha_ivs_delta` and `rekha_dsim` — the same readers HVAR uses, already
  verified at 264/264 against fontTools. ⛔ Its four maps are **separate**, and the suite gives the
  advance map and the vertical-origin map deliberately different targets, so a reader that used one
  map's offset for the other metric returns a plausible number that is simply the wrong one.
- ⚠ **Horizontal is still the default and the tested path.** rekha names horizontal metrics as its
  shipped scope (0.3.6) and no AGNOS consumer lays out vertical text today. This is here because it
  is metrics, because it is what the last MVAR tags needed, and because a CJK consumer that arrives
  should not find the table unread. ⛔ It is not a vertical LAYOUT engine: rekha reports the numbers.

`REKHA_FONT_SIZE` **608 -> 672**. ⇒ new `programs/vert_test.cyr`, **89 checks**: the line box and
caret, advances including the shared tail past `numOfLongVerMetrics`, bearings in both regions of
`vmtx`, VORG's per-glyph entries and its default, VVAR's three metrics with the maps kept apart, a
vhea below its header, a VORG and a VVAR version rekha refuses, and a bit-flip sweep over all four
tables.

### 0.6.x closed

Twenty-one tables resolved, from `head` to `VVAR`. The milestone opened with "the tables rekha
transports and never reads"; what is left of that list is nothing. Next is 0.7.x — `RekhaErr`,
which is published and produced by nothing.

## [0.6.6] - 2026-09-20 — GPOS: where a modern font actually keeps its kerning

0.6.5 read the legacy `kern` table and said plainly that a face with GPOS alone is normal and got
0 for one. This is that face. **`rekha_kern_pair` now prefers GPOS**, and `rekha_kern_source` says
which of the two answered.

⭐ **CHECKED AGAINST fontTools ON 60 REAL FONTS** — `scripts/gpos_kern_diff.py`, which for each
font picks a glyph sample from the PairPos coverages **plus glyphs that are in none of them**, and
asks both implementations for **every ordered pair** of that sample:

| | |
|---|---|
| fonts | **60** |
| pairs compared | **264,964 — all identical** |
| of those, carrying a non-zero kern | 41,749; the rest prove the misses |
| subtables exercised | 93 PairPos format 1, **213 format 2**, 6 behind an extension lookup |

⚠ **What fontTools is the reference for.** It DECOMPILES GPOS — Coverage, ClassDef, PairPos,
ValueRecords with their bitfield sizing — and that decompiler is a thorough, independent
implementation of the byte-level parse. It does not decide which lookups a `(left, right)` query
should consult, so the feature-union / dedup / accumulate rule is rekha's in both columns.
⛔ A **dev-host** differential, like `scripts/kern_diff.py`: it reads the machine's fonts.

### Added — `src/gpos.cyr`

`rekha_gpos_kern_present`, `rekha_gpos_kern_pair`; and in `src/kern.cyr`, `rekha_kern_source` and
the renamed `rekha_kern_table_pair` for the legacy table alone.

- **PairPos formats 1 and 2**, **Coverage** formats 1 and 2, **ClassDef** formats 1 and 2, and the
  **extension** wrapper (lookup type 9) large fonts use to reach past a 16-bit offset. Both the
  format 1 PairSet and the coverage and class ranges are binary-searched.
- ⛔ **A VALUE RECORD HAS NO FIXED SIZE.** `valueFormat` is a bitfield and the record holds one i16
  per set bit, in bit order, so XAdvance sits at `2 x popcount(valueFormat & 3)` and is absent when
  its own bit is clear. Reading it at a fixed offset is how a font with Y placement gets its
  kerning read out of the wrong field — group D builds exactly that font.
- ⛔ **Lookups ACCUMULATE; within one lookup the FIRST matching subtable wins** and the rest are
  not consulted. Backwards either way drops a font's kerning or applies it twice.
- ⛔ **The `kern` feature's lookups are DEDUPLICATED.** Two scripts normally carry two
  FeatureRecords pointing at the same lookups, and not deduplicating doubles every kern in the
  font.
- ⛔ **Class 0 is a real class** — "everything not listed" — with its own row and column in a
  format 2 grid, so an unlisted glyph is class 0 and not a miss.
- ⛔ **GPOS beats the legacy table, never both.** A face carrying both usually says the same thing
  twice, for shapers that read only one; adding them would double every pair. HarfBuzz does the
  same.

### What rekha deliberately does not do here

- ⛔ **The script and language walk.** rekha scans the FeatureList for every `kern` feature and
  takes the UNION of their lookups. Doing it properly needs a script and a language on the API, and
  rekha's kerning question is `(left, right)` with no run and no language around it. The suite
  fills the ScriptList with garbage to prove rekha never reads it.
- **`lookupFlag`'s ignore bits.** They say which glyphs a SHAPER skips while walking a run; a
  pairwise query has no run to skip in.
- **Device tables and VariationIndex values**, so a GPOS kern does not follow the axes. The
  ItemVariationStore reader for it already exists (`src/hvar.cyr`); GDEF is what is missing, and
  the roadmap pins it.
- ⛔ **Pair positioning and nothing else.** Mark attachment, cursive joining and contextual chains
  are a positioning engine over a glyph run and belong to a shaping library — a committed non-goal.
  Other lookup types are skipped, not refused: a font is normal for having them.

⚠ **ALLOCATION.** The lookups are resolved ONCE, on the first query, into one `sd_alloc` — the lazy
shape `rekha_var_set_axis` and gvar's scratch already use — so `rekha_font_open` still costs exactly
`REKHA_FONT_SIZE` and a font nobody asks about kerning never pays.

`REKHA_FONT_SIZE` **568 -> 608**. ⇒ new `programs/gpos_test.cyr`, **157 checks** on the things a
corpus cannot isolate: two `kern` features aimed at one lookup, a valueFormat that puts XAdvance
third, two subtables in one lookup where only the first may apply, a GPOS and a legacy table that
disagree, a garbage ScriptList, a lookup type that must be skipped, and a bit-flip sweep over the
whole table that runs 64 pair queries per mutant.

## [0.6.5] - 2026-09-20 — `kern`: pairs stop being placed at their raw advance

rekha owns advance widths, so rekha is what decides inter-glyph spacing — and through 0.6.4 every
pair was placed at its raw advance. This is the first half of fixing that: the legacy `kern` table,
a sorted array of (left glyph, right glyph, adjustment) and nothing more.

⚠ **The other half is GPOS, and it is where a modern font keeps its kerning.** A face with both is
common; a face with GPOS alone is normal. `rekha_kern_pair` answers 0 for such a font, which is the
unkerned spacing rekha has always given and not a wrong number. It is the next roadmap item.

⭐ **CHECKED AGAINST fontTools ON EVERY `kern` FONT ON THE DEV HOST** —
`scripts/kern_diff.py`, 2,155 font files scanned:

| | |
|---|---|
| fonts with a `kern` table | **16** (GNU FreeFont, Liberation) |
| pairs compared | **163,183 — all identical** |
| pairs fontTools says are ABSENT, probed | **8,000 — all correctly 0** |
| fonts with a single applicable subtable | 11 of 16, where the comparison is parse against parse with no rule in between |

⚠ **What fontTools is the reference for.** It PARSES the table — the subtable walk, the endianness,
the pair array — and that is the half this settles. It does not decide what to do with several
subtables, so the accumulate / override / skip rule is rekha's in both columns and the script models
it. FreeSerif carries **five** applicable subtables, so the accumulate path is exercised on real
fonts and not only on a fixture. ⛔ This is a **dev-host** differential, like rekha's CFF and WOFF2
corpus sweeps: it reads the machine's installed fonts and cannot run in CI.

### Added — `src/kern.cyr`

`rekha_kern_present`, `rekha_kern_pair`, `rekha_kern_pair_px`, `rekha_char_kern`.

- ⛔ **Two incompatible tables share the tag**, and telling them apart is the first thing this does.
  Microsoft's is version **0**: a u16 version, a u16 count, subtables with a u16 length and a u16
  coverage. Apple's is version **0x00010000**: a Fixed version, a u32 count, subtables with a u32
  length, a coverage BYTE and a separate format byte — and its coverage reads the other way round,
  with a SET bit meaning vertical. Reading one as the other does not fail; it walks into the middle
  of a pair array and returns a number.
- ⭐ **The sort is the lookup.** The array is ordered by the pair packed as `(left << 16) | right`,
  so a binary search finds one in log2(nPairs) reads — a dozen for a 4,000-pair table. The
  `searchRange` fields a font supplies are ignored: they are a font's arithmetic about rekha's
  array, and rekha can do its own.
- **OVERRIDE is honoured** — such a subtable replaces what earlier ones accumulated — and only when
  the pair is actually in it. An absent pair overrides nothing.
- ⚠ `rekha_kern_pair_px` rounds **half up, not half away from zero**: -1.5 px comes back -1, which
  is what every other rounding in rekha does. The division is written so it never divides a
  negative, and so does not depend on which way the language truncates.

### Skipped, subtable by subtable, rather than refusing the table

- ⛔ **MINIMUM subtables.** That coverage bit means the value is a FLOOR on the pair's spacing, not
  an adjustment to it, and adding it as though it were an adjustment is how a minimum becomes a
  visible gap.
- Anything not horizontal, anything CROSS_STREAM (which moves text off the baseline), and any
  format but 0 — format 2's two-dimensional class array is not read, and a font carrying one
  alongside a format 0 still kerns from the format 0.

### Refused

A version that is neither form; a header or subtable outside the table; ⛔ **a subtable shorter than
its own header**, which is checked before the step rather than after, because a zero-length one
would walk the loop forever; and a pair array that does not fit. The subtable walk is capped at 256
however many the font declares.

`REKHA_FONT_SIZE` **552 -> 568**. ⇒ new `programs/kern_test.cyr`, **78 checks** including a
**200-pair binary search with every other key deliberately absent** (400 lookups), both table
forms built from the same pairs, accumulation and override across two subtables, five skips, four
refusals, and a bit-flip sweep that requires the walk to terminate.

## [0.6.4] - 2026-09-20 — `post`, and every MVAR tag lands

`OS/2` gives the strikeout pair (0.6.1). `post` gives the **underline** pair, and it is the only
place a font says where to draw a rule under its text — a consumer that has one and invents the
other draws two rules of different weights.

⭐ **AND `unds` / `undo` WERE THE LAST TWO MVAR TAGS WITH NOWHERE TO LAND.** Closing them turned
this release into a completeness claim, so it takes in the eleven other tags whose fields rekha
simply had no accessor for: OS/2's eight sub- and superscript fields and hhea's three caret ones.
**Every tag in MVAR that names a table rekha reads now lands on it.** What is left of MVAR is the
four `vhea` tags, which are the vertical-metrics item.

⭐ **CHECKED AGAINST fontTools' INSTANCER, SAME BYTES, EVERY TAG** —
`scripts/metrics_var_diff.py`, now **22 MVAR fields** plus three hhea fields that must not move and
eight advances, over two axes and eight locations:

| | metric values | identical |
|---|---:|---|
| **0.6.4** | 264 | **264** |

### Added — `src/post.cyr`

`rekha_post_version`, `rekha_italic_angle`, `rekha_underline_position` (+ `undo`),
`rekha_underline_thickness` (+ `unds`), `rekha_is_fixed_pitch`.

- ⚠ **The header is 32 bytes in EVERY version** and carries all of it; the versions differ only in
  what follows. So a 2.0 table and a 3.0 table answer identically here, and
  `rekha_post_version` tells a consumer whether glyph names would be there — not whether rekha read
  any.
- ⛔ **Glyph names are not read, and that is a scoping decision.** They serve tooling — PDF export,
  a debugger naming the glyph that failed — and nothing rekha draws depends on one. Carrying them
  means carrying the 258-name Macintosh standard order as data, a table the size of everything else
  in that file put together. `docs/development/roadmap.md` pins it.
- ⚠ `italicAngle` is in **degrees counter-clockwise from vertical**, so an oblique face is
  NEGATIVE, and it has no MVAR tag: an italic angle does not vary.
- ⚠ `isFixedPitch` is a u32 the spec only requires to be non-zero, so any non-zero value is 1 here
  rather than passed through. -1 when the font does not say.

### Added — the eleven fields that completed MVAR

- **`OS/2`**: `rekha_subscript_x_size` / `_y_size` / `_x_offset` / `_y_offset` and the four
  `rekha_superscript_*` twins. A renderer with no real superscript glyphs scales and shifts by
  these rather than guessing a fraction of the em. ⚠ The offsets are from the BASELINE, so a
  subscript's y offset is a positive distance DOWN.
- **`hhea`**: `rekha_caret_slope_rise` / `_run` / `_offset` — the **only** thing in hhea that MVAR
  has a tag for, which is what made 0.6.0's mistake findable. ⛔ A rise of 1 and a run of 0 is
  upright: the caret is a vector, not an angle. ⚠ `rekha_italic_angle` says the same thing in
  degrees, does not vary, and need not agree.

`REKHA_FONT_SIZE` **536 -> 552**.

⇒ `programs/os2_test.cyr` **85 -> 141 checks** and is now the whole metrics-metadata suite: its
MVAR store carries all 22 tags in the sorted order the spec requires, two new groups cover `post`
(both versions, absent, and a table below its 32-byte header) and the static sub/superscript boxes
and caret, and the bit-flip sweep takes in `post` as well.

## [0.6.3] - 2026-09-20 — named instances and `STAT`: a font menu, at last

An axis is a continuum. A **named instance** is a point on it the designer blessed and gave a name
to — "Regular", "Bold Condensed". A font menu lists those, not axis values, and until now rekha
could report that a font has a `wght` axis running 100 to 900 without being able to say it ships a
style called "Bold" at 700. `STAT` is the other half: it says 700 is *called* Bold, that `wght`
sorts before `wdth`, and that "Regular" is a name to be **elided** rather than printed.

This closes the last of the 0.6.x metadata items but one, and it is the **largest single API
addition rekha has made** — twenty public functions, because these two tables are the font-menu
surface and nothing smaller answers the question.

### Added — named instances, in `src/var.cyr`

`rekha_var_instance_count`, `_name_id`, `_ps_name_id`, `_flags`, `_coord`, and
**`rekha_var_set_instance`** — the one call that turns a menu choice into a drawn font. Every
coordinate is a USER value, the same units `rekha_var_set_axis` takes, and the name id goes
straight to `rekha_name_utf8` (0.6.2).

- ⭐ **The instance array has no offset field of its own.** It begins at
  `axesArrayOffset + axisCount x axisSize` and nothing in the header says so.
- ⛔ **`instanceSize` is the only thing that says whether a record carries a `postScriptNameID`.**
  The spec allows exactly two strides — `axisCount x 4 + 4` without it and `+ 6` with — and rekha
  walks neither anything else, because guessing the stride is guessing every coordinate after the
  first. A refused array loses only the instances; the **axes are untouched**.
- ⛔ **`rekha_var_set_instance` sets EVERY axis**, including the ones the instance leaves at their
  defaults. Applying half an instance over a previous setting would draw a style the font does not
  ship — selecting "Bold" after "Bold Condensed" has to put the width back.

### Added — `src/stat.cyr`

`rekha_stat_present`, `_fallback_name_id`, `_axis_count` / `_axis_tag` / `_axis_name_id` /
`_axis_ordering`, `_value_count` / `_value_format` / `_value_flags` / `_value_name_id` /
`_value_pairs` / `_value_axis` / `_value_value` / `_value_min` / `_value_max` / `_value_linked`.

- ⭐ **All four axis-value formats are read through ONE pair API.** `rekha_stat_value_pairs` is 1
  for formats 1, 2 and 3 and format 4's own `axisCount`, and `_value_axis` / `_value_value` take a
  pair index — so a consumer walks every format the same way and never branches on the format to
  reach the numbers. The format is still reported, because 2 and 3 carry fields the others do not.
- ⛔ **rekha reads STAT and does not synthesize a style name.** Choosing which values apply,
  ordering them by `axisOrdering`, dropping the elidable ones and joining the rest is a
  family-naming POLICY with real disagreement in it — the same reason `rekha_use_typo_metrics`
  reports a bit instead of picking a line box. Every field the policy needs is here.
- ⛔ **A zero offset is the spec's "no entry here"**, not an entry at the start of the array.
- ⚠ An `axisIndex` is **not** clamped against `designAxisCount`: it is reported as written, so a
  consumer cross-referencing STAT's axes can see an out-of-range one instead of having it quietly
  turned into axis 0. Every BYTE read is inside the table; only the meaning is left alone.
- ⚠ `elidedFallbackNameID` is a minorVersion 1 field and a 1.0 table has none, which is 0 here.

`REKHA_FONT_SIZE` **496 -> 536**.

### Refused

A `STAT` majorVersion other than 1, a header that does not fit, a `designAxisSize` below 8, an axis
array or axis-value offset array outside the table, an axis value format past 4, and a format 4
whose record array does not fit. On the `fvar` side: a stride the spec does not allow, and an
`instanceCount` the table's own declared length does not cover — the array is not walked at all
rather than walked as far as it goes, because a short read there is a coordinate taken from
whatever follows `fvar`.

⇒ new `programs/stat_test.cyr`, **127 checks**: four instances with and without their PostScript
name ids, selection and re-selection across two axes, three instance refusals that leave the axes
working, STAT's design axes and its version-1.0 fallback, **one axis value of each of the four
formats plus a zero offset**, four STAT refusals, and a sweep that flips every bit of `fvar` and
`STAT` and requires every accessor to stay in range.

## [0.6.2] - 2026-09-20 — `name`: what a font is called, and labels for its axes

rekha is the only SFNT parser in the AGNOS stack, and until now nothing here could ask a face its
name. A font picker had a list of files. `rekha_var_axis_count` could say a font has two axes
without being able to say either one is called "Weight" — the record's `axisNameID` was parsed past
and never resolved, which is the gap this closes.

### Added — `src/name.cyr`

⭐ **WHAT COMES BACK IS UTF-8, IN THE CALLER'S BUFFER.** A name is stored as UTF-16BE or as
Macintosh Roman, and neither is something a consumer should have to know. rekha decodes and writes
into a buffer the caller owns — the same shape as `rekha_woff_decode` — so a name query **allocates
nothing**. `dst == 0` sizes it; a `cap` below the size writes nothing at all and still returns the
size, so the two-call idiom is safe. ⛔ Half a name is worse than no name, and a truncated UTF-8
string can end inside a character.

- `rekha_name_utf8(font, name_id, dst, cap)` — the best record for an id, ranked.
- `rekha_name_count`, `rekha_name_at_utf8`, and `rekha_name_platform_at` / `_encoding_at` /
  `_language_at` / `_id_at`, for a consumer that wants another language and will walk the table.
- Sixteen named ids (`REKHA_NAME_FAMILY`, `_SUBFAMILY`, `_POSTSCRIPT`, `_LICENSE`, …); every other
  id is still readable by number.
- `rekha_var_axis_name_id(font, i)` in `src/var.cyr`, which feeds straight into `rekha_name_utf8`.
- `rekha_mac_roman_cp(b)`, public because the table is worth being able to check.
- `REKHA_FONT_SIZE` **464 -> 496**.

⛔ **WHICH RECORD WINS IS RANKED, NOT LAST-ONE-SEEN.** A font carries the same id several times
over — Windows English, Unicode, Macintosh Roman — and the last is no more the intended one than
the first. The order is Windows/BMP/English, the other Windows encodings in English, any Windows
record, the Unicode platform, Macintosh Roman in English, then any Macintosh Roman. A platform or
encoding rekha cannot decode is **not a candidate at all**, rather than a candidate that later
fails, so a readable record behind it still wins. Same shape as cmap's subtable ranking (0.4.0) and
for the same reason.

### Added — the Macintosh Roman table, generated

⭐ A `name` record on platform 1 encoding 0 is **Mac OS Roman**, not Latin-1 and not Unicode: its
high half is 128 fixed entries that nothing derives, and one wrong entry is one wrong character in
a font's name — the quietest failure in the table. So it is **generated**, by
`scripts/mac_roman.py`, from **Python's own `mac_roman` codec**: the script prints the hex chunks
`src/name.cyr` carries and emits `programs/mac_roman_vectors.cyr`, the independent half that
`programs/name_test.cyr` drives the decoder with. CI regenerates and compares the vectors, the
third gate of that shape after the WOFF2 triplet table and CFF Standard Encoding.

⚠ Stored as hex, four digits an entry, rather than as the characters themselves — which would put
a non-breaking space and a set of curly quotes into a Cyrius literal, invisible to a reader and at
the mercy of the formatter.

### Refused — 0 bytes, and the name is simply absent

A `name` format past 1; a header, record array or string outside the table; a UTF-16BE string with
an **odd byte length**, an unpaired high surrogate, or a low surrogate first; an empty string; any
platform / encoding pair rekha does not decode.

⚠ **Nothing here caps what a font may declare**, because nothing is allocated: a 65,535-byte name
costs the caller exactly the buffer it chooses to pass.

⇒ new `programs/name_test.cyr`, **101 checks**: the record accessors, the ranking across four
platforms in a deliberately unhelpful order, UTF-16 past ASCII including a surrogate pair,
**every one of the 128 Macintosh Roman bytes** through the whole decoder with the UTF-8 decoded
back by the suite's own decoder rather than compared against rekha's encoder, the buffer contract,
ten refusals, the fvar axis labels, and a sweep that flips every bit of the table and requires a
name never to report more than it writes nor write past its cap.

## [0.6.1] - 2026-09-20 — `OS/2`: the metrics a font intends, and the MVAR targets 0.6.0 got wrong

`hhea` says how tall a font's glyphs are. **`OS/2` says how the designer meant them to be set** —
which vertical pair to build a line box from, where the x-height and cap-height sit, how bold and
how wide the face is, where a strikeout goes. Nothing in the AGNOS stack could read any of it.

### Fixed — 0.6.0 put MVAR's `hasc` / `hdsc` / `hlgp` on the wrong table

⛔ **They target `OS/2`'s sTypo trio, not `hhea`'s ascender, descender and lineGap.** MVAR has no
tag for hhea's vertical metrics at all — only for its three *caret* fields. 0.6.0 added those
deltas to hhea, so on a variable font `rekha_ascender` moved when it should not have and
`sTypoAscender` did not move when it should have.

⚠ **The differential should have caught it and could not.** `scripts/metrics_var_diff.py`'s fixture
set OS/2's sTypo trio EQUAL to hhea's, so every wrong answer was also a right one — and it is the
same case fontTools' `verticalMetricsKeptInSync` heuristic papers over, by copying an OS/2 change
back to hhea when the two started equal. A fixture that cannot tell two behaviours apart is not a
test of either. The fixture now carries hhea 800 / -200 / 90 against sTypo 750 / -250 / 0, and the
suites do the same.

⚠ **rekha does not copy that heuristic.** fontTools propagates because "it is common in fonts to
have the hhea metrics be equal for compat reasons" — a guess about intent. rekha reports what the
tables say: hhea has no MVAR tag, so `rekha_ascender` does not move at any axis setting. A consumer
that wants the varying line box reads the typo metrics, which is what `rekha_use_typo_metrics`
exists to tell it.

⭐ **RE-MEASURED ON THE STRENGTHENED HARNESS**, same bytes to fontTools and rekha, eight locations
over two axes x (nine OS/2 fields + three hhea fields + eight advances):

| | metric values | identical |
|---|---:|---|
| **0.6.1** | 160 | **160** |
| 0.6.0, same harness | 160 | 68 — nine columns of zeros where OS/2 was unread, and hhea moving where it must not |

### Added — `src/os2.cyr`

`rekha_os2_version` (**-1 when the table is absent**, and the probe to use before trusting a 0 from
anything else), `rekha_weight_class`, `rekha_width_class`, `rekha_fs_type`, `rekha_fs_selection`,
`rekha_use_typo_metrics`, `rekha_typo_ascender` / `_descender` / `_line_gap`, `rekha_win_ascent` /
`_descent`, `rekha_x_height`, `rekha_cap_height`, `rekha_strikeout_size` / `_position`.

- ⭐ **Every one of them varies.** Each field MVAR has a tag for takes its delta here — `hasc`,
  `hdsc`, `hlgp`, `hcla`, `hcld`, `xhgt`, `cpht`, `strs`, `stro` — so a variable font's x-height
  moves with its weight.
- ⛔ **Which vertical pair to use is the CONSUMER'S call.** A face carries three: hhea's, OS/2's
  sTypo trio, and OS/2's usWin pair. `fsSelection` bit 7 is the font saying "use sTypo". rekha
  reports the bit and all three pairs and picks none: choosing is layout policy and rekha is a
  parser.
- ⚠ **Gated on the DECLARED LENGTH, not the version number**, because the two are allowed to
  disagree and the length is what bounds the bytes. A table declaring version 4 in 80 bytes answers
  for `usWinDescent` and returns 0 for `sxHeight`, rather than reading its neighbour. Below the
  78-byte minimum nothing is cached at all.
- ⚠ **0 means "the font did not say"** for every metric, which is indistinguishable from a font
  that says zero — hence the version probe. `fsType` and `fsSelection` return **-1** instead,
  because 0 is meaningful for both.
- ⚠ `rekha_weight_class` is the STATIC class; a variable font's `wght` axis is the live one and the
  two need not agree once an axis is set.
- `REKHA_FONT_SIZE` **448 -> 464**.

⇒ new `programs/os2_test.cyr`, **85 checks**: a full version 4 table, an absent one, versions 0 and
1, a version and a length that disagree, a table under the minimum, every MVAR delta landing on the
field the spec names, and a sweep that flips every bit of OS/2 and MVAR and requires hhea to be
untouchable from there. `programs/hvar_test.cyr` 169 -> **159 checks**: its group E asserted the old
wrong behaviour and now asserts that the store resolves every tag while hhea stands still.

## [0.6.0] - 2026-09-20 — `HVAR` / `MVAR`: the advance follows the axes

0.4.11 and 0.4.12 made a glyph's **outline** follow the axes, for CFF2 and for TrueType. Its
**advance** did not: `rekha_advance_width` read `hmtx` in design units and consulted no variation
store, so a bold instance drew bold letters at regular spacing. This is that store, and with it the
line box — `rekha_ascender` / `_descender` / `_line_gap` now move too. First item of the 0.6.x
milestone, *the font's own answers*.

⭐ **CHECKED AGAINST fontTools, SAME BYTES, BEFORE AND AFTER** — `scripts/metrics_var_diff.py`, a
**two-axis** font (`wght` x `wdth`) over four regions including a cross-term one, eight glyphs
through a DeltaSetIndexMap spanning two ItemVariationDatas, and LONG_WORDS delta rows:

| | locations | metric values | result |
|---|---:|---:|---|
| **0.6.0** | 8 | **88** | all identical |
| 0.5.1, same harness | 8 | 88 | 11 identical — only the default location, where nothing varies |

⚠ **fontTools is used two ways here, because it uses two itself.** For MVAR,
`instantiateVariableFont` pins the axes and rewrites `hhea` end to end. For HVAR it does **not**:
on a `glyf` font the instancer bakes advances out of gvar's PHANTOM POINTS and treats HVAR as a
lookaside to drop, so on this gvar-less metrics fixture it would have reported the unvaried
advances and proved nothing. The advance side therefore goes through fontTools' own
`VarStoreInstancer` — the store evaluator the rest of fontTools calls — over the same HVAR bytes
and the same index map. Both routes are named in the script.

### Added — `src/hvar.cyr`

- **HVAR**: the ItemVariationStore, the advance DeltaSetIndexMap (**formats 0 and 1**, any entry
  size, any inner-bit split), and the delta sum. ⛔ An index past `mapCount` takes the LAST entry —
  the spec's rule, not a clamp of convenience: a font maps its first N glyphs and lets the tail
  share.
- **MVAR**: the ValueRecord array and the three tags the line box is made of — `hasc`, `hdsc`,
  `hlgp`. ⚠ A tag rekha has no reader for is **skipped, not refused**: MVAR is a bag of metrics and
  most of them belong to tables rekha does not read yet.
- ⛔ **LONG_WORDS.** Bit 15 of `wordDeltaCount` makes the first N deltas four bytes and the rest
  two, instead of two and one. Reading a long row as a short one does not fail — it returns other
  numbers — so it is decoded, and group D of the suite is built on it.
- ⭐ **The region machinery is `var.cyr`'s, unchanged.** `rekha_var_region_scalar` already turns a
  region into a 16.16 scalar at the current setting; this module is only the other half. The
  scalars are computed **on demand** rather than cached the way CFF2's are: an advance query
  touches one delta row, so a per-store array would cost more than it saves and would need a second
  allocation at open. When no axis is set the cost is one load and a compare — `rekha_var_live` is
  checked first and an unvaried font never reaches the store.
- `REKHA_FONT_SIZE` **416 -> 448** for the two tables and their extents.

### Fixed — a metric a hostile store could take to 10^12

⭐ **Found by `programs/hvar_test.cyr`'s bit-flip sweep, before any font did it.** Nothing in the
format bounds a delta: LONG_WORDS makes each one a signed 32-bit value and `regionIndexCount` is a
u16, so a crafted store can ask for `2^31 x 65535` — which overflows the 16.16 accumulator and,
short of that, hands a consumer an advance of **8.8e12** to lay text out with. A real delta is a
fraction of an em. `REKHA_VAR_MAXDELTA` is 2^20 design units, checked on the accumulator **every
iteration** so the refusal lands before the wrap, and a refusal leaves the metric at its default.

### Refused, each leaving the metric at its DEFAULT and never half-varied

A major version other than 1 (either table); a header, store, map or delta row outside its table; a
region index past the region list; an outer index past `itemVariationDataCount` or an inner index
past `itemCount`; `wordDeltaCount` greater than `regionIndexCount`; a DeltaSetIndexMap with a
reserved `entryFormat` bit or `mapCount` 0; an MVAR `valueRecordSize` below 8.

⚠ **HVAR's lsb and rsb maps are read past, not read.** rekha publishes no side-bearing accessor for
them to vary, and a glyph's real bearing already follows its outline, which does vary. Pinned in
`docs/development/roadmap.md`.
⚠ **Phantom-point advances are still not applied.** A TrueType variable font with `gvar` and no
HVAR varies its advances through the four phantom points `gvar` carries per glyph, which rekha
decodes and discards. Honouring them would put a full glyph decode behind the advance query that
0.3.11 measured at 47 ns, so it is its own item rather than a line here.

⇒ new `programs/hvar_test.cyr`, **169 checks**: the default instance, advances with and without a
map, both map formats, the shared tail, LONG_WORDS, the line box, nine refusals, and a sweep that
flips **every bit of both tables** and requires every metric to come back at its varied value or
its default and nothing between.

## [0.5.1] - 2026-09-20 — `FontMatrix`: charstring units are not always design units

The last of the five conformance items, and **0.5.x closes with it**. Through 0.5.0 rekha never
read Top DICT `12 7`: the DICT walker skipped the real-number operand format outright, and every
CFF and CFF2 glyph was decoded as though one charstring unit were one design unit. That holds for
all 405 CFF faces surveyed, every one of which carries `FontMatrix = 1 / unitsPerEm` — it is an
assumption, not a guarantee, and a face that says otherwise **rendered at the wrong scale with no
refusal**, which is a worse failure than an empty glyph.

⭐ **CHECKED AGAINST fontTools ON TWELVE MATRICES**, the same bytes to both — `scripts/cff_fontmatrix_diff.py`:

| | matrices agreeing |
|---|---|
| **0.5.1** | **12 of 12** |
| 0.5.0, same harness | 5 of 12 — the other seven silently drew at the wrong scale or orientation |

⚠ **What fontTools is the reference FOR.** It parses the Top DICT and exposes `FontMatrix` as six
floats; that parse — of a format that is two nibbles a byte with its own `.`, `E`, `E-` and `-`
codes — is the risky half and the half it settles. What fontTools does **not** do is apply the
matrix: its CFF glyph set returns raw charstring coordinates. The fold is rekha's own and the
script models it. rekha is never asked for its matrix and no accessor was added for the test: the
probe glyph draws (0, 0), (1000, 0), (0, 1000), so its three decoded points **are** the matrix.

### Added — `src/cff.cyr` reads and applies `FontMatrix`

- The **real-number operand format**, which the DICT walker had only ever skipped over.
- ⭐ **What is cached is not the matrix.** rekha keeps `M x unitsPerEm` in 16.16: the transform from
  charstring units straight to the design units the rest of rekha already works in, so the sadish
  seam's single divide by `upem` remains the only other scaling step. Precision is why — 0.001 in
  16.16 is 65.536, which rounds to 66, **a 0.7% error before a single point is placed**; 0.001 x
  1000 is exactly 1.0. For every font that agrees with its own `head` the product IS 1.0, the
  transform is recorded as off, and the point store pays nothing.
- Applied in the point store at 32.32 and rounded **once**, half up, exactly as the untouched path
  does. CFF2 gets it through the same code.
- ⛔ **ABSENT MEANS 0.001, NOT "the same units as head".** That is the CFF default and what FreeType
  derives its own upem from. The two agree exactly when `unitsPerEm` is 1000, which is what an
  OpenType CFF face carries; they differ only on a face already contradicting itself, and rekha
  follows the spec rather than siding with `head`. At upem 2048 with no `FontMatrix`, a 100-unit
  step is now 205 design units and was 100.
- `REKHA_FONT_SIZE` **360 -> 416** for the flag and the six entries. `programs/extent_test.cyr`'s
  literal gate is the place that makes that a decision.

### Refused rather than approximated

Each loses the CFF table, so the glyphs come back EMPTY — never a wrong scale. `head` is a
different table and still reads, which is how these are told from a broken font.

- an arity other than six; a scale past +-64 or a translation past +-16384 em; a real rekha cannot
  represent; the reserved nibble `d`; a real with no terminator before the DICT ends;
- ⛔ **a CID font whose FDArray Font DICT carries its own `FontMatrix`.** TN 5176 has that one and
  the Top DICT's **multiply**, so honouring only one would scale that subfont wrong — the exact
  failure this release exists to end. No surveyed face carries one; the day one does, rekha says so
  by drawing nothing. The same CID font without it still draws, which `programs/cff_test.cyr` group
  K checks immediately afterwards so the refusal cannot quietly widen.

### Fixed — while writing the walker

The operand counter was capped at six alongside the six-slot ring, so a **seven**-operand
`FontMatrix` read as a six-operand one and silently used the last six. Caught by group K, which
checks both arities; the ring stays capped and the count no longer is.

⇒ `programs/cff_test.cyr` **697 -> 785 checks**: both encodings of the identity, half scale, a
negative `d`, a skew, a translation in em units, the 0.001 default at upem 2048, and seven
refusals.

## [0.5.0] - 2026-09-20 — conformance: the stack CFF2 asks for, and the target rekha is named for

The 0.4.x line added formats. 0.5.x fixes the places rekha was **wrong or unproven** on a font it
already claimed to read — the milestone the roadmap cleanup opened, and the reason it is a minor
bump rather than another patch. Four of its five items land here; `FontMatrix` is 0.5.1.

⭐ **THE HEADLINE, AND IT IS A BEFORE AND AFTER.** A variable CFF2 built in Python, read from the
SAME BYTES by fontTools 4.65.0 and by rekha, swept over five region counts (2, 8, 16, 31, 63) x
five `wght` settings x four glyph shapes:

| | glyph instances | points | result |
|---|---:|---:|---|
| **0.5.0** | 100 | **550** | all identical |
| 0.4.12's ceiling, same harness | 100 | 125 of 550 ever produced | **60 instances came back EMPTY** |

The harness is committed as **`scripts/cff2_wide_diff.py`** — unlike rekha's other differentials it
needs no font corpus, only fontTools, because it builds its own input. It is not a CI gate, for the
same reason `scripts/cff_stdenc.py verify` is not: fontTools is not a dependency of this repo.

⛔ **And the blank glyphs include the DEFAULT location.** The overflow happens while operands are
being PUSHED, before any scalar arithmetic, so a consumer that never touched an axis still got
nothing. That is worse than the roadmap stated.

### Fixed — CFF2 charstrings ran on CFF's argument stack

`REKHA_CFF_MAXSTACK = 48` was one constant for both dialects. A CFF2 `blend` of `nb` values over
`k` regions needs `nb + nb x k` operands **resident** when the operator runs, so 48 capped a
conformant font at `floor(48 / (k + 1))` blended values — 3 at 15 regions, 2 at 23. The CFF2
chapter says **513**, and overflowing was not graceful: the push guard sets `RC_BAD`, so the glyph
came back EMPTY rather than at its default.

- The ceiling is now per-run state (`RC_SMAX`), set from the dialect: `REKHA_CFF_MAXSTACK` 48 for
  CFF, new `REKHA_CFF2_MAXSTACK` 513 for CFF2. ⛔ **CFF stays at 48** — that is the format's own
  limit and a CFF pushing a 49th operand is malformed. `programs/cff_test.cyr`'s B2 pins it.
- One `i64[513]` argument stack (4,104 B of frame, once per `rekha_cff_load`, not per point).
- ⚠ **Why no suite caught it:** every CFF2 fixture rekha had was two regions wide and one.
  `programs/cff2_test.cyr` gains **group W** — a 16-region store whose tents are identical, so at
  the axis maximum every scalar is 1 and a blended value is exactly its default plus the SUM of its
  deltas. It drives a 69-operand blend, the 511-operand one that 513 just allows, and a 545-operand
  one that must still be refused.

### Fixed — a wrong syscall number shipped in both bundles

`src/error.cyr`'s `rekha_err_print_name` wrote to fd 2 through the literal x86_64 write number,
`syscall(1, 2, ...)`. On aarch64 `write` is **64** and **1 is `io_destroy`**. It was the only
syscall in library code, and it shipped in `dist/rekha.cyr` and `dist/rekha-woff.cyr`.

- ⭐ **Removed rather than repaired.** Taking the stdlib's dispatched `SYS_WRITE` would add the
  `syscalls` leaf to `dist/rekha.deps` — a tax on every consumer for a debug helper nothing calls,
  one release after 0.4.4 and 0.4.5 spent two releases cutting that list to ONE. A pure parser that
  makes **no syscall at all** is the better invariant, and CI now gates exactly that: the security
  scan's library allowlist went from "may write to fd 2" to "must make none".
- `rekha_err_name` is unchanged and still returns the cstring; a caller that wants it on a fd uses
  its own I/O, which is what `programs/error_test.cyr` now does.
- ⛔ **This is a removal from a declared public surface.** rekha has not frozen its API (that is
  0.9.0) and nothing consumed this, but it is called out rather than slipped in.

### Added — CI builds for aarch64 and AGNOS

rekha's first line calls it "a subsystem for AGNOS" and nothing had ever built it for AGNOS or for
aarch64: all three CI jobs are one x86_64 host, and `scripts/ci-install-cyrius.sh` has committed an
aarch64 tarball hash since 0.4.5 without ever using it. A **cross-target link-check** step now
builds `programs/smoke.cyr` — which links the whole include chain — under `--aarch64` and
`--agnos`, failing on a build error or any warning. Same shape as sadish's own step, which is where
it came from. ⚠ Link-check only: the binaries are not run, there being no such host here, and
`programs/` keeps its raw write/exit numbers deliberately.

### Fixed — an `avar` 2.0 table was dropped whole, segment maps included

The version gate took `majorVersion == 1` only. avar 2.0 keeps 1.0's `axisSegmentMaps` unchanged
and in the same place — its additions sit AFTER them — so rekha was discarding mapping it already
knew how to apply, and such an axis landed UNMAPPED rather than merely un-refined. Version 2 is now
accepted for its segment maps. ⛔ Its variation store is still not applied: that needs a
`DeltaSetIndexMap` reader rekha does not have. A 2.0 font that does all its work in the store
carries identity segment maps and is unaffected either way, which is what makes this the safe
subset.

### Fixed — `rekha_fx_div` truncated where `rekha_fx_mul` rounds

⭐ **Found by the differential above, and not one of the five.** The two 16.16 primitives sitting
next to each other disagreed: `rekha_fx_mul` rounds half up, `rekha_fx_div` truncated. Every caller
divides one interval by another to get a ratio in [0, 1] — axis **normalization**, the `avar`
segment walk, and a region's **tent scalar** — so all three were biased low by up to one ulp.

⚠ One ulp of scalar is enough to move a point. MEASURED on the 31-region font at `wght` 550, where
the exact coordinate is **51.5**: rekha normalized 150 / 500 to 19660 (0.2999878) instead of 19661
(0.3000031) and rounded the point DOWN to 51 where fontTools gave 52. 19661 is also simply the
closer of the two to 0.3. `programs/cff2_test.cyr` pins the normalized value directly.

### Removed — the `tests/tcyr` tier that never existed

`ls -d tests` fails and `git ls-files | grep '^tests/'` returns nothing, yet three CI steps globbed
it — including one named *Test (native tcyr suites)* that looped over an empty glob and could not
fail. ⚠ **Coverage was never absent**: the 25 `programs/*_test.cyr` RUN suites gate the library
under `CYRIUS_DCE=0` and `1`. What was wrong is a step advertising a tier the repo does not have.
The globs and the step are gone; if a `.tcyr` tier is ever added, the step comes back with it.

### Fixed — `programs/cff2_test.cyr`'s INDEX writer

Not library code, and worth recording because it looked exactly like a library bug. `idx32`
hardcoded `offSize = 1` with the note *"every object here is small"*, which held until group W's
charstrings — a 30-value blend over 16 regions is 510 operands, ~517 bytes — overflowed a one-byte
offset and handed rekha an INDEX whose objects overlapped. The glyph came back empty and read as a
refusal. offSize is now computed. `pt()` is bounds-checked too: the first run of group W under the
old ceiling died of SIGSEGV walking past an empty outline instead of printing which check failed.

### Filed

- `cyrius/docs/development/proposals/2026-09-20-coverage-should-accept-run-programs-as-a-corpus.md`
- `cyrius/docs/development/proposals/2026-09-20-fuzz-poison-should-follow-a-custom-allocator-seam.md`

Both from the roadmap cleanup that preceded this release; both had lived only as a CI comment.

## [0.4.12] - 2026-09-20 — `gvar`: instancing for TrueType outlines

The other half of variable fonts. 0.4.11 gave CFF2 outlines their axes; `gvar` does the same for
TrueType, and it is its own release because it is its own format: where a CFF2 charstring carries
its deltas inline and names every value it blends, a `gvar` tuple carries them **out of line**,
**packed**, and may name only SOME of a glyph's points — the rest are inferred by interpolating
between their touched neighbours around the contour. Roadmap v0.4.x item 12. The axis machinery
(`fvar`, `avar`, the region scalars) is 0.4.11's and is shared unchanged.

⭐ **CHECKED AGAINST fontTools' OWN GLYPH SET, POINT FOR POINT:**

| | instances | points | result |
|---|---:|---:|---|
| simple glyphs, four weights, incl. a sparse tuple only IUP can complete | 20 | 508 | all identical |
| composite glyphs, three weights | 9 | 519 | all identical |

⚠ **One ±1 disagreement turned out to be the reference, not rekha**, and is worth recording because
the next person will hit it: Python's `round()` is banker's rounding and fontTools' own `otRound` is
half-up, so a first pass at the comparison script reported a one-unit difference on every delta that
landed exactly on .5. rekha rounds half up, which is what fontTools does internally.

### Added — `src/gvar.cyr`

- The table, its per-glyph offsets (**16-bit offsets are stored HALVED**), the tuple headers with
  their shared / embedded / intermediate peaks, and the two packed formats: packed point numbers
  (run-length, byte or word, cumulative) and packed deltas (with a zero-run that carries no bytes
  at all).
- ⭐ **IUP, per contour and per tuple.** A tuple that names only some points has the rest inferred
  BEFORE its deltas are scaled in, not after the tuples are summed. ⛔ A contour the tuple names
  nothing in keeps ZERO deltas — it does not inherit its neighbour's, which is what makes the
  difference between one contour moving and the whole glyph moving.
- ⛔ **The equal-coordinate case in IUP is a rule, not a rounding worry**: when an untouched point's
  two touched neighbours sit at the same coordinate, it takes their shared delta if they agree and
  **nothing** if they disagree.
- ⭐ **Composites vary too**, through their component offsets: each component counts as one point,
  and the delta goes on the STORED offset — before `SCALED_COMPONENT_OFFSET` scales it, since the
  other order would scale the variation as well as the placement.
- ⚠ Every glyph has four phantom points past its real ones and a tuple's deltas cover them. rekha
  decodes them (a tuple naming them must still be read to the end) and applies only the real points:
  phantom deltas are METRICS variations, now roadmap item 13.
- `rekha_var_axis_factor` was factored out of 0.4.11's region scalar and is now shared — the tent is
  the same shape for a CFF2 region and a `gvar` tuple, and only the source of the three coordinates
  differs. ⚠ Without an intermediate region a tuple's tent is `(min(peak, 0), peak, max(peak, 0))`.

### Fixed — the default that made every full-glyph tuple silently do nothing

⛔ A tuple with no private point numbers falls back to the glyph's SHARED point numbers; when the
glyph declares none either, the spec says the tuple provides deltas for **every** point. The first
cut defaulted that to "names nothing", so every tuple in a font without shared point numbers decoded
cleanly and applied zero deltas — no refusal, no warning, just an outline that never moved. Caught
by `programs/gvar_test.cyr` group B, whose font is exactly that shape.

### Added — `programs/gvar_test.cyr` (207 checks)

A TrueType font built in code — head / maxp / hhea / hmtx / loca / glyf / fvar / gvar — with one
two-contour glyph and three tuples chosen so each drives a different part of the decoder: a
shared-tuple tuple naming all points, a private-point tuple naming two points of ONE contour, and an
intermediate-region tuple whose tent is not derived from its peak. Every expected coordinate is
worked out from those tents and deltas by hand.

Group C is the one to read: the sparse tuple names points 0 and 2 of contour 0 with opposite deltas,
so points 1 and 3 must take an endpoint's delta whole (they sit at the extremes of their
neighbours' coordinates, not between them) — and **contour 1 must not move at all**. Group E is the
refusals, each leaving the outline exactly as stored; group F a guard differential, a truncation
sweep and a **bit-flip sweep over every byte of the `gvar` table**.

⚠ Two builder bugs found while writing it, both mine and both in the fixture: `loca` needs
`numGlyphs + 1` entries, not `numGlyphs`, and the glyph record is 56 bytes rather than the 48 first
written down. `REKHA_FONT_SIZE` **336 → 360**.

## [0.4.11] - 2026-09-20 — variable-font instancing, for CFF2

`rekha_var_set_axis(font, i, value)` puts axis `i` at a user value and every later
`rekha_load_glyph` draws the font there. Roadmap v0.4.x item 11, the CFF2 half.

0.4.9 decoded a CFF2 at its **default** location, and the reason it could ignore the deltas
entirely is the reason this release is small: at the default every region's scalar is **zero**, so a
blended value simply *is* its default. `src/var.cyr` reads `fvar` and `avar`, normalizes an axis
setting onto [-1, 1], and turns the coordinates into one scalar per region of the variation store.
The `blend` operator then adds each delta weighted by its region's scalar — and with no axes set
RC_NSCAL is 0 and the deltas are dropped exactly as before, byte-identical to 0.4.9.

⭐ **CHECKED AGAINST fontTools AT EVERY LOCATION TESTED**, on a variable CFF2 it instanced too:

| `wght` | normalized | rekha | fontTools |
|---|---|---|---|
| 400 (default) | 0 | `(100,200) (400,200) (400,600)` | identical |
| 900 / 100 (both extremes) | ±1 | unchanged — the coordinate is ON a region edge | identical |
| 650 (a region's peak) | +0.5 | `(110,230) (410,230) (410,630)` | identical |
| 550 (interior) | +0.3 | `(106,218) (406,218) (406,618)` | identical |
| 550 through an `avar` map | +0.8 | `(104,212) (404,212) (404,612)` | identical |

### Added — `src/var.cyr`: the axes, and the scalars

- `rekha_var_axis_count` / `_tag` / `_min` / `_default` / `_max` / `_coord`, and
  `rekha_var_set_axis` / `rekha_var_reset`. Axis values are 16.16 **user** units, the scale `fvar`'s
  own Fixed fields use; `rekha_var_coord` reports the normalized result.
- ⭐ **The region scalar is OpenType's own rule, and three of its five branches mean "this axis does
  not constrain the region" rather than "the region is off"**: a peak of 0, a malformed
  start/peak/end triple, and a region spanning the default are each *ignored on that axis*, not
  treated as zero. Only being at or beyond an edge zeroes the whole region. Getting that inverted
  turns a font that should not move into one that moves everywhere.
- `avar` segment maps are applied after normalization, piecewise linear between positions. ⚠ avar
  **2.0** adds a variation store on top of the maps; rekha reads the maps, which 2.0 keeps, and does
  not apply that extra mapping.
- ⛔ `rekha_var_set_axis` is a **set-the-axes-then-draw** call: it normalizes, runs `avar` and
  rebuilds every region scalar. It is not cheap enough to call per glyph and is not meant to be.
- ⚠ ALLOCATION: the coordinate and scalar arrays are allocated on the first `set_axis` and reused.
  rekha's seam has no free, so a font whose axes are set keeps them.

### Changed — `blend` applies its deltas

The products are accumulated at 32.32 and shifted **once**, so a value blended over several regions
rounds like one sum rather than a chain of them. `REKHA_FONT_SIZE` **272 → 336** for the `fvar` /
`avar` cache, the normalized coordinates and the scalars. `rekha_cff2_ivd` replaces
`rekha_cff2_regions` as the primitive: instancing needs to know *which* regions a subtable blends
over, not just how many, so the region-index array is now bounds-checked as well.

### Added — `programs/cff2_test.cyr` groups F and G (144 → **258 checks**)

The builder gained an `fvar` (one `wght` axis, 100 / 400 / 900), an `avar` whose map kinks at
0.3 → 0.8, and **real region tents** in its variation store — region 0 peaking at +0.5 over (0, 1],
region 1 at -0.5 over [-1, 0). Every expected coordinate is worked out from those tents and the
charstrings' own deltas rather than read back off rekha: the default and both extremes (where a
coordinate sits on an edge and nothing moves), a region's peak, halfway up a tent, the negative
half, a glyph with no blend at all, and `rekha_var_reset` putting it all back.

⚠ **The builder's SFNT layout is now COMPUTED, not written down.** Adding `fvar` and `avar` grew the
directory past the offsets the old fixed layout used — which is exactly the defect 0.4.10 fixed in
`programs/cff_test.cyr`, where a hardcoded `head` offset ended up inside the directory and went
unnoticed for eight releases. The comment on those lines says so.

## [0.4.10] - 2026-09-20 — WOFF2 collections, and the fixture that hid the scaled readers

Two unrelated things, and the second one is why the first is not alone: the fixture fix was already
sitting unreleased under this number when the collection work landed.

### Added — WOFF2 collections (roadmap v0.4.x item 10)

A `ttcf`-flavoured WOFF2 has been refused since 0.4.6. It now rebuilds to a real `.ttc`:
`rekha_woff2_face_count` says how many faces it carries, `rekha_font_open_woff2_index` opens one,
and `rekha_woff2_decode` produces the whole collection — a TTC header, one offset table per face and
**one copy of each shared table** — which `rekha_font_open_index` (0.4.8) then walks.

⭐ **CHECKED AGAINST THE COLLECTIONS IT WAS BUILT FROM.** Two `.ttc` files fontTools authored — a
2-face one whose faces share **17 of 18** tables, and a 3-face one of unrelated fonts — each
compressed to WOFF2 with real Brotli and decoded back:

| | faces | glyphs | rebuilt | source `.ttc` |
|---|---:|---:|---:|---:|
| two faces from one font | 2 | 1,350 | 135,624 B | 135,624 B |
| three unrelated fonts | 3 | 948 | 247,168 B | 247,168 B |

Every face identical to its source face. ⭐ In the first, both faces resolve `glyf` to the **same
offset** in the rebuilt file, so the sharing that is the whole point of a collection survives.

⚠ **AND THERE IS NO INDEPENDENT DECODER TO CHECK AGAINST, which is worth saying plainly.** fontTools
has no WOFF2 collection support in either direction — its `woff2.py` contains no `ttcf`, no
`numFonts` and no CollectionHeader — so the encoder that produced those two files is rekha's own and
the WOFF2 layer itself is not independently witnessed. What anchors the result is the *outcome*: the
rebuilt `.ttc` must match a `.ttc` fontTools authored, face for face, through rekha's collection
reader, which 0.4.8 validated separately. An error in the decoder that the encoder does not mirror
exactly shows up; one mirrored in both would not.

#### Changed — the reassembly is now per FACE, and a plain font is a collection of one

⭐ **The single-font path was not left alone beside a collection path.** `rekha_w2_layout` and
`rekha_w2_write` now work from a list of faces, each owning a list of table-directory indices, and a
plain WOFF2 becomes a one-face collection whose list is `0..n-1`. One code path, so the collection
case cannot drift from the case 280 real files exercise. Everything the restructure touched still
passes: the 280-file differential is unchanged, and the suite's 127 pre-existing checks are green.

- The in-place sort of the table directory is gone — it would have invalidated the very indices a
  CollectionFontEntry names. Each face's own index list is sorted by tag instead.
- An entry carries a `done` flag and a cached checksum, so a table SHARED by several faces is
  transformed once, written once and summed once, and every directory naming it gets that number.
- ⛔ **Every entry must be named by some face.** An unreferenced one is data the output cannot reach,
  and for a transformed glyf it would never be measured — its length would silently stay the
  `origLength` the spec calls "only a reference point".

#### The decoder MUSTs, enforced

- ⚠ **Duplicate tags are CORRECT in a collection** and refused everywhere else: the table directory
  holds one entry per unique *table*, so two faces with different glyf tables contribute two `glyf`
  entries. One entry per *tag* is enforced **within each face** instead.
- ⛔ Spec 5.5: in a collection each `loca` must IMMEDIATELY follow its `glyf` in the table directory,
  which is what makes a pair unambiguous when several are present.
- ⛔ Spec 4.2, verbatim a decoder MUST: a face's CollectionFontEntry indices must name a `glyf` and
  `loca` that are *that* pair. A face naming one without the other, or naming another face's `loca`,
  is refused.
- ⚠ `checkSumAdjustment` is computed **per face**, over that face's offset table, directory and own
  tables — which for a plain font is the whole file, the OFF rule exactly. For a collection there is
  no "entire font", and a `head` shared between faces can hold only one value: the last face written
  wins. Said here rather than discovered.
- ⚠ The rebuilt TTC header is always **version 1.0**. A v2.0 header appends a digital-signature
  triple; spec 4.2 lets a decoder null those fields *or* emit a version 1 header, and 1.0 is the
  form with no fields left to get wrong.

#### Added — `programs/woff2_test.cyr` group E (127 → **183 checks**)

A three-face collection built from the embedded face, with and without the glyf/loca transform, and
carrying **two** glyf/loca pairs: faces 0 and 1 share one, face 2 has its own. Face 1 names only the
seven tables rekha reads, so a subset face must still decode to the same digest. The group asserts
the rebuilt file is a `ttcf`, that `rekha_ttc_count` sees three faces, that all three digest to the
embedded face, that faces 0 and 1 resolve `glyf` to one offset while face 2 does not, and that a
plain WOFF2 answers one face and refuses index 1.

### Fixed — the fixture that hid the scaled readers

**No library code changes in this half.** `programs/cff_test.cyr` built every one of its fonts with `head`
declared INSIDE the table directory, so rekha refused the table — correctly — and every CFF fixture
the suite has ever produced reported `unitsPerEm` **0**. Nothing noticed, because no upem-scaled
reader appeared anywhere in the suite: the defect and the coverage gap were the same fact, and each
is why the other survived. Found while writing `programs/cff2_test.cyr` (0.4.9), whose own builder
already lays its tables out past the directory and says why.

⚠ **0.4.9 filed this rather than fixing it, and its notes say so.** That paragraph is left exactly
as it shipped; this is the release that fixes it.

### Fixed — `programs/cff_test.cyr` built every font with `head` INSIDE the table directory

⛔ **THE FIXTURE WAS WRONG, NOT REKHA.** `build()` writes five directory entries — dir_end is
`12 + 5 * 16` = **92** — and declared `head` at **76**, where it overlaps the fifth entry, the
`CFF ` one. `rekha_find_table_len` refuses a table that begins below dir_end, so it did exactly
what it should: every font this suite has built since **0.4.2**, the release that added it, has had
an unreadable `head` and reported `rekha_units_per_em()` **0**.

⚠ **What that hid is the upem-scaled half of the API, on CFF faces entirely.** A zero upem does not
fail an open and does not crash a reader — `rekha_glyph_advance_px`, `rekha_glyph_advance_fx` and
`rekha_char_advance_px` all return 0, which means "unknown", and a consumer deriving a scale from it
divides by zero. 678 checks stayed green because `units_per_em`, `char_to_sdpath` and `char_advance`
appeared **nowhere** in the suite: the coverage gap and the defect were the same fact, and each is
why the other survived. `rekha_advance_width` WAS checked and passed throughout — it reads hmtx in
design units and never touches `head`, so metrics coverage looked complete.

⇒ Tables now start past the directory, the layout `programs/cff2_test.cyr` already uses — `head`
@92/54 · `maxp` @148/6 · `hhea` @156/36 · `hmtx` @192/(ng*4) · `CFF ` after that — with the rule
written on the lines that would otherwise be wrong again.

### Added — `programs/cff_test.cyr` group J, the guard on that (678 → **697 checks**)

`rekha_units_per_em` must be 1000 on a built font, and the readers that divide by it are now
exercised on a CFF face: `rekha_glyph_advance_px` / `_fx` and `rekha_char_advance_px` against
hand-computed half-up rounding, and `rekha_glyph_to_sdpath` at a scale **derived from upem** (500 px
on a 1000-unit em is exactly `SD_ONE / 2`) asserting 16.16 points. ⭐ **Neither half would do alone:**
a upem check passes on a `head` rekha reads but no reader consults, and a scaled reader that returns
0 does not name its cause. The group closes on the other direction — rebuild the old layout by hand
and require upem 0 and a 0 advance back, so the refusal that was right all along stays gated too.

## [0.4.9] - 2026-09-20 — CFF2, at the default instance

An OpenType face carrying a `CFF2` table instead of `CFF ` now draws. Roadmap v0.4.x item 9.
`src/cff2.cyr` parses the container; the charstrings go through cff.cyr's **same** Type 2
interpreter in a CFF2 mode, because the drawing operators, the subroutine machinery, the hint
operators and flex are all shared and a second interpreter would be a second thing to keep right.

⭐ **CHECKED AGAINST fontTools TWICE, and the second one is the real test.**

| | |
|---|---|
| a CFF font converted to CFF2 by fontTools | outlines IDENTICAL to the CFF it came from, cubics included |
| a hand-built **variable** CFF2, read from the SAME bytes by both | identical point for point |

The second font carries a two-subtable ItemVariationStore — one two regions wide, one one — a glyph
that blends against the Private DICT's default subtable, and a glyph that sets `vsindex 1` first.
fontTools and rekha agree on every coordinate.

⚠ **The default instance, and only that.** At the default location every region's scalar is zero, so
a blended value IS its default. Non-default axis coordinates need `fvar`, `avar` and the region
scalars, which rekha does not read; that is now roadmap item 11.

### Added — the container

- A 5-byte header (major must be 2, headerSize >= 5, then a u16 topDictLength), a Top DICT that is
  **raw bytes rather than an INDEX**, no Name or String INDEX, no charset, no encoding.
- **Every INDEX counts in u32**, including a count-0 one, which is 4 bytes and not 2. cff.cyr's
  readers took a count width (`rekha_cff_idx_next` / `_obj` / `_count_at`) so the bounds logic is
  written once and CFF's behaviour is untouched — `programs/cff_test.cyr`'s 678 checks pass
  unchanged across that refactor.
- An FDArray is **required** (a CFF2 font's Private DICTs live nowhere else); an FDSelect is
  optional, and `rekha_cff_fd` now answers 0 when there is none. ⛔ FDSelect **format 4** exists in
  CFF2 and rekha refuses it rather than misreading its wider fields as format 3's.
- The ItemVariationStore, read for exactly one thing: how many regions a subtable blends over.

### Added — `blend` and `vsindex`

⭐ **`blend` is three lines, and the reason is worth stating.** The stack holds n defaults, then
n x k deltas, then n. At the default location each result is its default — already sitting in place
below the deltas — so the operator is: drop the count, drop the deltas, leave the defaults.
⛔ `vsindex` is refused after a `blend` or a second time (both spec MUSTs), and refused outright if
it names a subtable the store does not have. ⚠ A `blend` in a font with **no** variation store keeps
its defaults rather than refusing: there is nothing to drop, and that is the right rendering.

### Fixed — two defects the fontTools differential found, neither of which a round trip would have

- ⛔ **`rekha_cff_dict_op` treated only bytes <= 21 as operators, and CFF2's `vstore` is 24.** The
  Top DICT scan hit byte 24, took it for a reserved operand prefix and **stopped** — so the variation
  store was never found, every `blend` ran with k = 0, and `vsindex` refused. The damage was
  positional and therefore quiet: `CharStrings` and `FDArray` were found because they happen to come
  first. A DICT read now takes an operator ceiling — 21 for CFF, where 22..27 really are reserved,
  and 27 for CFF2, where `vstore` (24), `vsindex` (22) and `blend` (23) live. CFF is bit-for-bit
  unaffected.
- ⛔ **The leading-width rule fired in CFF2, where there is no width.** A CFF charstring's first
  stack-clearing operator may carry one; a CFF2 one never does. MEASURED: a blended `rmoveto` whose
  two values had survived the blend correctly was then handed the *wrong pair*, because the width
  logic saw a third operand and dropped the first.

⚠ **Neither would have shown up in a round trip against our own encoder** — a test that built CFF2
the way rekha reads it would have agreed with both mistakes. They were found by handing fontTools
and rekha the same bytes.

### Added — `programs/cff2_test.cyr` (144 checks)

Every font is built in code: the container, one glyph per shape (including a cubic and a charstring
that ends with no `endchar`), then `blend` and `vsindex` against a real two-subtable store — with
deltas large enough that applying them would move the asserted points a long way. Group C is the
refusals: six that stop the table resolving (a CFF-1 major, a short header, no CharStrings, no
FDArray, FDSelect format 4) and six charstring-level ones (`endchar` in CFF2, `vsindex` out of
range, twice, after a `blend`, `blend` on an empty stack, `blend` asking for more than the stack
holds) — each beside a control glyph in the same font. Group D is a guard differential, a
truncation sweep over every cut, and a 900-iteration byte-mutation sweep over the CFF2 table.

⚠ **Noticed while writing it, and filed rather than fixed here:** `programs/cff_test.cyr`'s own
fixture declares `head` at offset 76 with five directory entries, so it lies inside the directory
(dir_end is 92) and rekha correctly reports it absent — every CFF fixture has `unitsPerEm` 0. No
check there notices, because cff_test reads no upem-scaled reader at all, which is the coverage that
hides it. `programs/cff2_test.cyr`'s builder lays its tables out past the directory and says why.

### Changed — the record, and the bundles

`REKHA_FONT_SIZE` **256 → 272**: `+256` says the outlines came from `CFF2`, `+264` is that table's
variation store. `src/cff2.cyr` joins `[lib]` and `[lib.woff]` after `src/cff.cyr`, whose helpers it
uses. ⚠ A font carrying BOTH `CFF ` and `CFF2` keeps the `CFF ` it had before 0.4.9.

## [0.4.8] - 2026-09-20 — TrueType Collections

A `.ttc` / `.otc` carries several faces in one file, each with its own SFNT offset table, all of
them **sharing table data** — which is the whole point of the format and the reason CJK families
ship this way. `rekha_ttc_count` says how many faces; `rekha_font_open_index` opens one.
`rekha_font_open` opens face 0 of a collection, so an existing consumer handed a `.ttc` now gets a
working font instead of nothing. Roadmap v0.4.x item 8, first half.

⭐ **CHECKED AGAINST COLLECTIONS fontTools AUTHORED**, and the second file is the one that matters:

| | faces | glyphs | result |
|---|---:|---:|---|
| three unrelated fonts in one `.ttc` | 3 | 948 | every face IDENTICAL to its source font |
| two faces built from ONE font | 2 | 1,350 | every face IDENTICAL to its source font |

In the second, face 1 shares **17 of its 18 tables** with face 0 — 135,624 bytes for what is 133,172
bytes as a single font — and its `glyf` resolves to offset **320** while its own directory begins at
**133,204**.

### Changed — the bounds rule a collection breaks, and what replaced it

⛔ **rekha's rule was "a table lies past its own directory"** (`off >= 12 + numTables * 16`). That is
true of every `.ttf` ever written and **false of almost every collection face**: a table shared with
an earlier face sits far below this face's directory, so the rule would have reported table after
table absent and opened a face with no glyphs at all — silently, since a missing table has never
failed an open.

⇒ Each face now carries the floor that IS true of it, at `+248` (`REKHA_FONT_SIZE` **248 → 256**):

- a plain SFNT keeps `12 + numTables * 16`, exactly the old rule, so nothing about opening a `.ttf`
  moves;
- a face inside a collection gets the end of the TTC header and its offset array, below which no
  table can legitimately begin.

⛔ **Lowering a floor loses something, so the check that the floor was also doing is now explicit:**
a table whose span runs through this face's own offset table and directory is refused. For a plain
SFNT that test is unreachable (the floor already covers it) and it changes no result; for a
collection face it is the only thing left saying so. Both directions are gated —
`programs/ttc_test.cyr` group B corrupts one directory entry to point into the TTC header and
another to run through the face's own directory, and requires the table absent and the open to
SUCCEED either way.

### Added — `programs/ttc_test.cyr` (53 checks)

No `.ttc` is committed and there is not one on the dev host to borrow, so the suite builds
collections from the embedded face: three faces over ONE copy of the table data, laid out
header · face 0's directory · the tables · face 1's directory · face 2's directory. So face 0 reads
like a plain `.ttf` and faces 1 and 2 do not — their tables lie below their own directories, the
real-world shape. Face 1 names only the seven tables rekha reads, and a subset face must still
decode to the same digest.

Group C is the refusals, each a one-defect copy: an index past the collection, a negative index,
`numFonts` of 0 or past `REKHA_TTC_MAXFONTS`, an offset array past the file, a face offset inside
the TTC header, a face offset table past the end, a member whose own sfntVersion is `ttcf`, and a
member directory that overruns the file. Group D is a guard differential over three faces plus a
truncation sweep.

⚠ **A plain `.ttf` answers 0 to `rekha_ttc_count` and opens perfectly.** 0 means "not a collection",
not "no font" — `rekha_font_open_index(buf, len, 0)` is the right call for either, and index 1 of a
non-collection is refused.

### Changed — the roadmap item split, because the two halves share nothing

Item 8 was filed as "TrueType Collections **and** CFF2". The collection half is here; **CFF2 is now
item 9** on its own. They have nothing in common beyond both being deferred: CFF2 is a different
container (no Name or String INDEX, a Top DICT that is not an INDEX, a required FDArray, a 32-bit
CharStrings INDEX) and a different charstring dialect (`blend`, `vsindex`, no `endchar`) over an
ItemVariationStore. A new **item 10** records what is left for WOFF2 collections, which
`dist/rekha-woff.cyr` still refuses: the CollectionDirectory between the table directory and the
compressed data.

## [0.4.7] - 2026-09-20 — CFF `seac`, the accented glyph built from two others

A four-argument `endchar` says: draw glyph `bchar` at the origin, then glyph `achar` displaced by
(adx, ady). Both are named by **Standard Encoding code**, so resolving one takes two tables rekha
did not read — the Standard Encoding (code → SID) and the font's own **charset** (SID → glyph id).
Through 0.4.6 such a glyph was EMPTY. Roadmap v0.4.x item 7.

⭐ **CHECKED AGAINST fontTools 4.65.0, ON A FONT fontTools ITSELF AUTHORED.** A CFF with
`Aacute = 100 200 65 66 endchar` over a 500x700 `A` and a 300x200 `B`, saved by fontTools and then
opened by rekha:

| | |
|---|---|
| fontTools, decomposed | `(0,0) (500,0) (500,700)` · `(100,200) (400,200) (400,400)` |
| rekha, 2 contours / 6 points | `(0,0) (500,0) (500,700) (100,200) (400,200) (400,400)` |

⛔ **That is what settles the one semantic question here.** Type 1's `seac` took a fifth argument,
`asb`, and sources differ on whether the Type 2 `endchar` form still positions through it. It does
not: the accent goes at (adx, ady) directly, and an independent implementation agrees point for
point.

⚠ **THE DEV-HOST CORPUS CANNOT CHECK THIS ONE, and that is worth saying rather than leaving
implied.** 0.4.2 validated CFF outlines against an independent reference on all 405 CFF faces of
this host. A re-survey for 0.4.7 scanned **406** CFF faces and found **0** using `seac`, and **0**
`seac` glyphs — confirming the roadmap's own note. So the evidence for this release is the fontTools
font above plus the built fonts in `programs/cff_test.cyr` group I, not a sweep. `seac` is a Type 1
relic, and a corpus of modern faces is silent about it by construction.

### Added — the Standard Encoding, as fourteen ranges and a generated gate

- `rekha_cff_stdenc(code)` → SID. ⭐ **Arithmetic, not a 256-entry table**: the encoding happens to
  be almost entirely contiguous runs — codes 32..126 are SIDs 1..95, and everything above 126 falls
  into thirteen more ranges.
- ⛔ **A wrong range picks the wrong accent silently**, so `programs/cff_stdenc_vectors.cyr` carries
  all 256 (code, SID) pairs, generated by `scripts/cff_stdenc.py` and gated in CI exactly as
  `programs/woff2_vectors.cyr` and `fonts/face_data.cyr` are. The script's `verify` mode re-derives
  the table from **fontTools** (`encodings.StandardEncoding` composed with `cffLib.cffStandardStrings`)
  and required a byte-equal match — 149 assigned codes — before the ranges were written. fontTools is
  not a dependency of this repo and CI does not run that mode.

### Added — the charset, cached at open

- `REKHA_FONT_SIZE` **240 → 248** for one new slot: the charset, resolved once at
  `rekha_font_open` like every other table. 0 is the ISOAdobe predefined charset (and the CFF
  default, where SID i IS glyph i), 1 and 2 the Expert charsets, -1 "present but unusable", anything
  else the absolute offset of a format 0 / 1 / 2 charset.
- ⚠ **It never fails the open.** A charset rekha cannot use costs only the `seac` path; every other
  reader is untouched.
- `rekha_cff_sid_to_gid` walks formats 0, 1 and 2, bounded by the CFF extent AND by the CharStrings
  count — a charset may describe more glyphs than the font has, and following it past `n` would hand
  back a glyph id the CharStrings INDEX cannot resolve.

### Added — the composition, outside the interpreter

The four-argument `endchar` **parks** its request in the decoder state instead of recursing;
`rekha_cff_run` composes the two components once the charstring has properly ended. The interpreter
has no business resolving a charset mid-charstring, and the two component charstrings then spend the
**same** operator budget and the **same** point ceiling as everything above them.

⛔ **EMPTY, not partial, for every one of:** an unassigned Standard Encoding code; an SID no charset
entry carries; the Expert / ExpertSubset charsets; a **CID-keyed** font (whose charset maps glyph ids
to CIDs, not to SIDs — the lookup would be nonsense rather than a miss); a component that is this
same glyph; and a component that is **itself** a `seac` (one level is what the operator means;
nesting it is how a font turns two glyph loads into a tree).

⚠ A leading width is handled: five arguments is width + `seac`, and the width is dropped so the four
below are the operator's own. `rekha_cff_width` returns early once a width has been consumed, so a
five-argument `endchar` AFTER another stack-clearing operator is not read as a `seac`.

### Fixed — a refusal check that had started passing for the wrong reason

⛔ `cff_test`'s `B0 seac` used codes `65 66`, and with `seac` implemented those now RESOLVE: that
font declares no charset, so the ISOAdobe default makes SID 34 glyph 34, which exists there. **The
check stayed green anyway** — glyph 34 is `B8`, itself a refusal — so a rule it claimed to test was
being carried by a coincidence. Both it and the matching case in group H now use code 128, which is
genuinely unassigned, and say so. Found by asking why the suite did not go red, not by it going red.

### Added — `programs/cff_test.cyr` group I (148 new checks, 530 → 678)

The font builder gained a charset (`o_charset`): formats 0, 1 and 2 with one entry per glyph, and a
format 1 written as a single multi-glyph range so `nLeft > 0` is exercised. Group I asserts the
composed outline **coordinate by coordinate** across all four charset shapes, the width form, and a
swap of the two codes (so the components are the glyphs named, not a coincidence of ordering); then
the nine refusals, an ISOAdobe font large enough for SID 34 to be a real glyph, and all 256 codes
against the generated vectors.

## [0.4.6] - 2026-09-20 — WOFF2

`rekha_font_open_woff2` opens a `.woff2`. WOFF 1.0 unwraps a container and hands back the same
bytes; WOFF2 concatenates every table into ONE Brotli stream and **transforms three of them**, so
this is not a container reader — it reconstructs a font. `src/woff2.cyr`, 1,262 lines, in
`[lib.woff]` beside WOFF 1.0. ⚠ **`dist/rekha.cyr` did not change by a line**: the base bundle is
2,353 lines before and after, and its sidecar is still the single leaf `string`. Roadmap v0.4.x
item 4, whose dependency landed in sankoch 2.8.0 one release ago.

⭐ **MEASURED AGAINST AN INDEPENDENT DECODER, on every WOFF2 on this host.** 280 unique files —
Liberation, KaTeX, Fira Sans / Mono, Source Serif 4, Source Code Pro, NanumBarunGothic and Xiaolai
CJK — decompressed with **fontTools 4.65.0** to reference SFNTs, then both sides opened through
rekha's own loader so the only variable is the reconstruction:

| | |
|---|---:|
| files whose glyphs, advances and cmap are IDENTICAL to fontTools' | **280 of 280** |
| glyphs compared | **111,732** |
| failures to open | **0** |
| rekha's rebuilt SFNTs, total | 32,483,072 B |
| fontTools' rebuilt SFNTs, total | 32,334,048 B (**+0.46%**) |

### Added — the container, the directory, and one Brotli stream

- **`rekha_font_open_woff2(buf, len)`**, and the granular trio under it —
  `rekha_woff2_block_size` / `_inflate` / `_sfnt_size` / `_decode`.
- ⚠ **`rekha_font_open_any` MOVED from `src/woff.cyr` to `src/woff2.cyr`** and now sniffs all three
  of `wOFF`, `wOF2` and a bare SFNT. Same name, same signature, same bundle — a consumer of
  `dist/rekha-woff.cyr` sees nothing. A program that includes only `src/woff.cyr` must now also
  include `src/woff2.cyr`; `programs/woff_test.cyr` does.
- The variable-length table directory: the 63 **known table tags**, `UIntBase128` and `255UInt16`.
  ⛔ UIntBase128 enforces all three of the spec's MUSTs — no leading `0x80`, no sequence past five
  bytes, nothing above 2^32-1 — while 255UInt16 deliberately enforces NO canonical form, because
  the spec requires a decoder to accept all three spellings of a value.
- ⛔ **Two things WOFF 1.0's API could do that this one cannot, said plainly.** `rekha_woff2_sfnt_size`
  cannot answer from the container alone — a transformed glyf's rebuilt size is a property of its
  point data, and the spec says the `origLength` beside it "should be treated only as a reference" —
  so it takes the inflated block. And an open costs **two** allocations where WOFF 1.0 needed one:
  the inflated table data has to exist somewhere before it can be reconstructed, and rekha's seam
  has no free, so that scratch stays charged. Open a WOFF2 once, outside a per-frame hook.

### Added — the glyf / loca reverse transform

Seven substreams walked in lockstep, one glyph at a time, with the offset each glyph lands at
becoming the loca table. Simple glyphs, composites (records copied verbatim), empty glyphs, the
bbox bitmap with both the explicit and the INFERRED path, instructions, and the optional
`overlapSimpleBitmap`.

- ⭐ **The 128-row "Triplet Encoding" table (spec 5.2) is ARITHMETIC, not a literal table** — six
  ranges, a base, a nibble split and two signs. ⛔ **A round-trip test cannot check that**, because
  `programs/woff2_test.cyr`'s own encoder would share any mistake in it. So
  `programs/woff2_vectors.cyr` is generated from the W3C table by `scripts/woff2_triplet.py` and
  gated in CI exactly as `fonts/face_data.cyr` is: **all 128 indices under two byte patterns, 256
  vectors, every one agreeing** — plus that the off-curve bit changes no coordinate and that one
  byte short of what an index needs is a refusal. The script's `verify` mode re-extracts the table
  from the W3C HTML and required a byte-equal match before any of this was written.
- ⛔ `>>` **is logical in Cyrius.** Every shift in the decoder is on a non-negative value for that
  reason and the signs are applied afterwards as `0 - v` — the same class of defect sadish 0.11.0
  caught in its own pattern sampler.
- ⚠ **A rebuilt glyf is not byte-identical to the original and cannot be.** The spec is explicit
  that several encodings of one outline are valid. rekha's is deterministic and plain: one flag byte
  per point, no REPEAT run-length. Measured over the corpus, that costs **0.46%** against fontTools.
- ⛔ A point delta or absolute coordinate outside Int16 is REFUSED, not truncated. The 16-bit
  triplet forms can express ±65535, which no conforming font uses, and a silently misplaced point
  is the worst failure a font parser has.

### Added — the hmtx reverse transform

Left side bearings rebuilt from each glyph's xMin, for the proportional run, the monospaced run or
both. ⛔ hmtx is reconstructed **last**, after glyf and loca are written, because it reads those
xMin values back out of them.

### Added — `programs/woff2_test.cyr` (127 checks) and its two encoders

- ⛔ **sankoch 2.8.0 decodes Brotli and does not encode it** (an encoder is its 2.8.1), so the suite
  emits RFC 7932 **stored** meta-blocks by hand — which is what the roadmap meant by testing
  "on transformed-but-uncompressed tables": the tables get the real transform, the Brotli layer
  around them is stored. Group S proves the emitter against sankoch's own decoder at three sizes
  spanning the 4-, 5- and 6-nibble MLEN forms before anything else trusts it.
- A **WOFF2 encoder** for the glyf transform, picking the NARROWEST of the six triplet forms per
  point so a round trip over a real face drives all six.
- Group B round-trips the face through both transforms three ways (glyf+loca, and hmtx, and the
  overlap bitmap forced present) and requires an identical font digest each time, with hmtx coming
  back byte for byte. ⚠ The face's own left side bearings are first aligned to xMin, because the
  hmtx transform is only *applicable* to a font where they already match — otherwise the
  elimination path would silently never run.
- Groups R and G: thirteen one-defect container copies, six one-defect copies of the table-data
  block, a guard differential and a truncation sweep over every cut.

### Fixed — a cursor the write pass left one varint short

⛔ The glyph stream holds a glyph's coordinates and THEN its `instructionLength`. The write pass
rewinds to re-walk the points and was landing back after the coordinates but before that varint, so
every following glyph decoded its triplets from the wrong byte. Found by
`rekha_w2_glyf_all`'s every-substream-exactly-consumed check, which exists for exactly this.

### Changed — the bundle, and one new CI gate

- `[lib.woff]` is now rekha plus `src/woff.cyr` **and** `src/woff2.cyr`; the bundle goes 2,554 →
  3,819 lines and its sidecar is unchanged (`string sankoch`). ⚠ Order matters: woff2 uses woff's
  `rekha_wr_u16` / `rekha_wr_u32` / `rekha_pad4`.
- `programs/woff_dist_test.cyr` gained six checks that the WOFF2 half really folded into the
  SHIPPED bundle. ⛔ `distlib --check` proves the bundle matches `src/`; it cannot prove the
  `[lib.woff]` module list names `woff2.cyr` at all — drop that line and every other suite still
  passes, because they include `src/` directly.
- ⛔ **Font collections (`ttcf`) are refused**, at the directory parse rather than part-way: a
  collection puts a CollectionDirectory between the table directory and the compressed data, so the
  data offset would otherwise point into it and every table would decode from the wrong bytes.
  Roadmap v0.4.x item 8.
- sankoch's floor for `dist/rekha-woff.cyr` rises to **2.8.0** (Brotli). `dist/rekha.cyr` still
  requires no sankoch at all.

## [0.4.5] - 2026-09-20 — the toolchain moves, and the gates that could not see it

A pin release: **`cyrius` 6.6.4 → 6.6.6**, **`[deps.sadish]` 0.9.0 → 0.11.2**, `lib/` re-resolved
against both. ⭐ **Not one line of rekha source changed for the bump.** All 24 programs (23 RUN
suites + smoke) build and run green under `CYRIUS_DCE=0` and `1` with no `warning`,
`undefined function` or `refusing to emit` in any build log; `lint --strict`, `vet` and
`distlib --check` are clean, and both bundles differ from 0.4.4 in exactly one line each — the
`# Version:` banner.

What the bump *did* do is move one consumer-visible number and expose **three CI gates that were
not gating**. Those are the release.

### Changed — `dist/rekha.deps`: two leaves become one, and the bundle did not move

- **`dist/rekha.deps` now names `string` alone**; `dist/rekha-woff.deps` is `string sankoch`.
- ⚠ **`alloc` left the sidecar because the TOOLCHAIN changed, not the bundle.** Through 6.6.4,
  `lib/string.cyr` called `alloc()` (`strdup`/`strndup`) and declared no include for it, so
  distlib's compile-verify pass had to re-add the leaf — which is what 0.4.4 published, correctly,
  and documented as "not padding". 6.6.6 makes that file **self-sufficient**
  (`include "lib/alloc.cyr"`; cyrius CHANGELOG [6.6.6] — without it, `include "lib/string.cyr"`
  alone compiled with `warning: undefined function 'alloc'` and any `strdup` call trapped). alloc
  now arrives **transitively** with `string`. It is still linked; only the name a consumer has to
  resolve went away.
- ⛔ **This ties the sidecar to the toolchain, and that is stated rather than discovered later.**
  A consumer **below 6.6.6** that vendors only `string` gets `warning: undefined function 'alloc'`
  and a `strdup`/`strndup` call traps (SIGILL). Consumers of `dist/rekha.cyr` 0.4.5 and up must be
  on 6.6.6 or later — the pin rekha itself builds under.
- `programs/dist_test.cyr` and `programs/woff_dist_test.cyr` dropped their `include "lib/alloc.cyr"`
  to match. Their headers already said to keep the list equal to the sidecar; ⚠ neither ENFORCES it
  (cyrius auto-prepends every resolved leaf inside the tree — 0.4.4 measured that), so this is
  documentation being kept honest, not a gate. Both still pass under DCE 0 and 1.

### Fixed — the format gate was reading an exit code that lies

- ⛔ **`cyrius fmt <file> --check` is a FALSE NEGATIVE on 6.6.6**, and CI's "Format check" step
  gated on exactly that exit code — so the gate could not catch the drift it exists to catch.
  **MEASURED** against sadish's `programs/paint_focal_test.cyr` @0.9.0, the file sadish filed this
  on: `--check` exits **0**, and formatting the same file in place rewrites it in **three** places
  (continuation lines at 12 spaces where 6.6.6 wants 10).
- ⇒ The step now formats in place on the clean checkout and lets `git diff --exit-code` report,
  which cannot silently agree — the diff *is* the formatter's output. `lib/` and `/build/` are
  gitignored, so only tracked source can dirty the tree at that point. The `--check` flag is left
  unused rather than trusted.
- ⚠ **rekha's own tree does not drift**, and the fix is not hiding a reformat: MEASURED by
  formatting a COPY of every file in `src/` and `programs/` and diffing against the original —
  **0 of 33 files move** under the 6.6.6 formatter, and `--check` agrees on all 33. The gate was
  broken; the tree was not.

### Fixed — the stale-`dist/` message sent you to a command that leaves the WOFF profile stale

- ⛔ **MEASURED: a bare `cyrius distlib` regenerates the BASE bundle only.** With `dist/` stale it
  rewrote `dist/rekha.cyr` + `dist/rekha.deps` and left `dist/rekha-woff.*` exactly as it found
  them, so following CI's own remediation text left `--check` red and the next reader hunting.
  cyrius's error says `--all`; CI's message now says it too.

### Changed — `[deps.sadish]` 0.9.0 → 0.11.2

- Three sadish releases ride along and **none of them reach rekha's code**: 0.10.0 (the
  `SdPolyline` inline-points ABI break, plus `sd_path_transform` / `sd_path_bounds`), 0.11.0
  (pattern paint, `SD_SPREAD_NONE`, `docs/api.md`) and 0.11.1 / 0.11.2 (an audit's correctness half,
  then its optimization half — 8.5x on a styled stroke, byte-identical output).
- ⚠ **0.10.0 IS an ABI break, and the check that it misses rekha is a real one, not an assumption.**
  It moved `SdPolyline`'s points inline, so `sd_polyline_points` strides 16 and an open-coded
  `load64(points + i * 8)` reads a **coordinate as an address** — an immediate SIGSEGV for any path
  off the origin. VERIFIED: `grep -rn polyline src programs` is **empty**. rekha emits paths through
  `sd_path_*` and never reads a flatten output, so the break has no surface here. A consumer that
  does walk polylines must port to `sd_polyline_point_x` / `_y` before taking this pin. Recorded in
  `cyrius.cyml` beside the floor note so the next bump does not re-derive it.
- The floor stays **>= 0.9.0** — `sd_path_point_x` / `_y` are what rekha's suites read — and the
  provenance check that does not rot is unchanged: `grep -c '^fn sd_path_point_x' lib/sadish.cyr`
  is 1 at 0.9.0 and up.

### Changed — both rekha filings against sankoch came back closed

The 6.6.6 stdlib snapshot ships **sankoch 2.8.0** (6.6.4 shipped 2.7.15), and it carries both things
rekha asked sankoch for. Nothing in rekha changes yet — this is the dependency picture being brought
up to date, and two stale ⚠ notes in `README.md` / `cyrius.cyml` being retired.

- ⭐ **The WOFF2 Brotli decoder SHIPPED.** `brotli_decompress` and `brotli_decompress_capped` are
  decode-only RFC 7932 entry points mirroring the zlib pair rekha already uses, plus
  `FORMAT_BROTLI = 9`. VERIFIED in the pinned leaf: `grep -ci brotli lib/sankoch.cyr` is **0** at
  2.7.15 and **54** at 2.8.0. sankoch's `[lib.woff]` profile is deliberately the `[lib.zlib]` module
  list **plus** Brotli, so one bundle covers WOFF 1.0 and WOFF2 — sankoch ADR
  `0001-brotli-decoder-placement.md`, filed by rekha; the proposal is archived. ⚠ **WOFF2 is still
  rekha's to write** (v0.4.x item 4); only the blocker is gone, and the roadmap entry now says so
  instead of pointing at a proposal that has moved.
- ⭐ **The lean `[lib.zlib]` profile links.** rekha's README carried this as an open filing: every
  alloc-bearing sankoch profile bundle was unlinkable from 2.7.10 through 2.7.15, because
  `runtime.cyr` called a `_sankoch_reset_tables` that only `lib.cyr` defined — *"refusing to emit
  binary with 1 reachable undefined function(s)"*. Fixed in 2.8.0 (per-profile reset dispatch,
  sankoch `docs/architecture/003-per-profile-reset-dispatch.md`); rekha's issue is archived.
  ⚠ **rekha's own suites never exercised it** — `programs/woff_test.cyr` takes the full
  `lib/sankoch.cyr` leaf from the toolchain pin, not a profile bundle — so this is a consumer's good
  news, not a gate that was red here.

### Changed — the toolchain pin, and the hashes that gate it

- `[package].cyrius` **6.6.4 → 6.6.6**. `scripts/ci-install-cyrius.sh` carries the new committed
  sha256s; the 6.6.4 entries are kept so a bisect or a revert still installs. Both hashes were
  verified before committing: `install.sh` from the `6.6.6` tag ref is byte-equal to
  `git show 6.6.6:scripts/install.sh` in a local clone
  (`a468278154c7a77ef17d74277a6ec3402b4213373b383de89ee4803d144cb75a`), and the tarball hash
  (`1866a671924b29b90e3e13333cf613cff55a107390ff5686699e1dc63e593e36`) equals the published
  `.sha256` sidecar and its line in `SHA256SUMS`, whose Ed25519 signature `cyrsign verify` accepted
  against `keys/cyrius-release.ed25519.pub`. The aarch64-linux tarball hash is committed too, from
  the same signed manifest.
- ⛔ **CVE-44**, fixed in 6.6.6's own installer: through 6.6.5 `install.sh` staged the tarball and
  its signature inputs at **fixed `/tmp` names**, so a local user could swap them between download
  and verify. This script's `CYRIUS_INSTALL_TARBALL` path never depended on that staging — it hands
  install.sh a file already verified against a committed hash inside a `mktemp -d` — but it is
  another reason not to pin below 6.6.6.
- The 6.6.6 pre-flight the sadish 0.9.1 bump published was re-run here and held item for item: zero
  `struct` declarations, no `async`/`operator` fns, no `ret2`/`rethi` pairs, no top-level `{ }`
  blocks (6.6.6 gave those function scoping), no locally defined `vec_*`.
- `lib/` goes **23 files → 25**: 6.6.6's snapshot adds `alloc_cx.cyr` and `args_agnos.cyr`, pulled in
  by the `alloc` and `args` leaves. ⚠ Nothing in rekha includes either directly; they are the
  resolver's transitive closure, and `cyrius.lock` records all 25 plus the sadish commit pin
  (`d9f41f3e02011c48dcb10f0835a81cc847c670aa`, tag 0.11.2).
- ⚠ The WOFF note in README moves with the snapshot: the 6.6.6 stdlib ships **sankoch 2.8.0**
  (6.6.4 shipped 2.7.15). The floor for `zlib_decompress_capped` is still 2.7.13.

## [0.4.4] - 2026-09-16 — nine published leaves become two

⭐ **Not one line of bundle CODE changed.** `dist/rekha.cyr` and `dist/rekha-woff.cyr` differ from
0.4.3 in exactly one line each — the `# Version:` banner `distlib` stamps. This release changes
what a consumer must *resolve*, not the code they get, which is why it ships on its own.

### Changed — `dist/rekha.deps`: nine stdlib leaves → `string`, `alloc`

- **The bundle's entire stdlib appetite is `strlen` + `memcpy`.** Through 0.4.3 the sidecar named
  `string fmt alloc vec str io syscalls assert bench`, so every consumer of `dist/rekha.cyr`
  vendored eight leaves it never called — for four releases. It now names **`string alloc`**.
  `dist/rekha-woff.deps` goes **five → three** (`string alloc sankoch`; `assert` and `vec` were
  never needed either).
- **`alloc` is not padding.** `lib/string.cyr` calls `alloc()` and declares no include for it, so
  `string` drags it in transitively. `distlib`'s compile-verify pass (`_distlib_verify_leaves`,
  which splices the bundle with `_skip_deps = 1`) derived that unaided — a symbol scan of `src/`
  alone would have wrongly published `string` and shipped a sidecar that does not link.
- **Why two files had to change, not one.** `cyrius distlib` builds the sidecar from the include
  scan of **`src/lib.cyr`** — the path is hardcoded at `cbt/commands.cyr:3903` — **unioned** with
  the `[deps].stdlib` array, so a leaf named in either place is published. Both are now trimmed to
  `string`.
- **New `programs/prelude.cyr`** holds the eight leaves rekha's own harness uses (`fmt_int_fd`,
  `arena_*`, `str_same`, `assert_*`, `bench_*`) and then includes `src/lib.cyr`; the 23 suites
  include the prelude. One hop outside the scan is the whole mechanism.

### Added — a CI pin, because `--check` cannot see the sidecar grow

- ⚠ **MEASURED: adding one `include "lib/fmt.cyr"` to `src/lib.cyr` takes the sidecar from
  `string alloc` to `string fmt alloc vec`** — three new leaves for every consumer, from a one-line
  convenience edit, with `cyrius distlib --check` staying **green** throughout. `--check` verifies
  the sidecar *matches* `src/`; it has no opinion on whether it has grown.
- A new CI step pins both expected leaf lists, so a re-tax is a red build and a deliberate edit.

### Fixed — three comments that claimed enforcement they do not have

Found by mutation-testing the new gates rather than by reading; the first two were written earlier
in this same release and were wrong.

- ⛔ **`dist_test` / `woff_dist_test` do NOT gate the sidecar, and no suite in this repo can.**
  Inside a resolved tree cyrius **auto-prepends** every leaf from every resolved sidecar into
  scope, so a program compiles whether or not it includes what it calls — MEASURED: deleting
  `include "lib/alloc.cyr"` from `dist_test` still builds clean, and a program with *no* includes
  at all calls `alloc`/`strlen`/`vec_new` and builds clean. Their trimmed include lists are honest
  documentation of a consumer's chain; sufficiency is proven only by `distlib --check`.
- ⛔ **There is no coupling to sadish's sidecar.** An earlier note here claimed rekha's harness
  leaves reach `lib/` only because sadish requires all nine, and would fail loudly if sadish
  trimmed. Both halves are false: an include resolves from vendored `lib/` first and the **pinned
  toolchain snapshot** otherwise. Proven twice — `lib/` has never contained `sync.cyr` or
  `sankoch.cyr`, yet `woff_test` includes both and passes; and resolving rekha against a sadish
  whose sidecar lists only `string alloc` cuts `lib/` to **8 files**, after which all 24 suites
  still build and run green. A file in neither place is a hard `cannot open include file`.
- README's `[deps.sadish]` line still read `tag = "0.5.5"` after 0.4.3 moved the floor to 0.9.0.

### Filed upstream

- `cyrius/docs/development/proposals/2026-09-16-declare-test-only-stdlib-leaves-instead-of-hiding-them-from-the-umbrella-scan.md`
  (+ roadmap P4). The fix works, but *which file an include sits in* decides what every downstream
  consumer vendors, and the deciding filename appears nowhere in the manifest. Asks for a
  declarative channel — and notes that trusting the compile-verify pass as the sole authority
  would have produced the right answer with no declaration discipline at all.

### Verified

- **48/48** — all 24 suites build and run green under `CYRIUS_DCE=0` **and** `1`, zero warnings and
  zero `undefined function` in every log; `lint --strict`, `fmt --check`, `vet`,
  `distlib --all --check` and the dist/ porcelain gate all clean.

## [0.4.3] - 2026-09-16 — sadish 0.9.0, and a path sized to its glyph

### Changed — `[deps.sadish]` 0.5.5 → 0.9.0 (commit-pinned 9a51a05)

- **sadish 0.9.0 stores an `SdPath`'s points INLINE** (16 B a slot) instead of 8 B pointers to
  separately allocated `SdPoint`s — the change rekha's own proposal asked for and measured. sadish
  filed the port against rekha (`docs/development/issues/archived/2026-09-16-sadish-0.9.0-inlines-path-points-five-programs-must-port.md`,
  now closed) and it reproduced exactly as written: **4 of 23 suites SIGSEGV, rc 139** (cff_test,
  glyf_edge_test, hostile_test, path_start_test), the other 19 green. All five sites — those four
  plus `bench_hotpath` — now read through **`sd_path_point_x` / `sd_path_point_y` / `sd_path_verb_at`**,
  and `src/` needed no change (it names no `SD_PATH_*` constant).
- **Two filings rekha made against sadish came back fixed** and are adopted here: `sd_path_flatten` no
  longer allocates mid-points past its output cap and flags a truncated polyline (sadish 0.7.1 /
  0.7.2), and a refused allocation inside path construction and strokes is a return code, not a fault
  (0.7.2).
- ⛔ **The floor is now sadish >= 0.9.0** and the manifest says why. ⚠ The reverse mistake is silent —
  rekha builds against sadish's `dist/`, so a stale `lib/` looks fine; the provenance check that does
  not rot is `grep -c '^fn sd_path_point_x' lib/sadish.cyr` (1 on 0.9.0, 0 below).

### Changed — every path opens at the size of its glyph

- ⭐ **`rekha_outline_to_sdpath` counts before it builds.** A new `rekha_contour_size` walks a
  contour's flags exactly as `rekha_emit_contour` does and totals the verbs and points the emit will
  push; the path is then opened with **`sd_path_new_cap(v, p)`** (sadish >= 0.7.2) instead of
  `sd_path_new`'s 4,144 B default. This is item 3 of rekha's own proposal
  (`sadish/docs/development/proposals/2026-09-15-path-capacity-for-known-size-paths.md`), the part
  sadish could not close from its side; the proposal is now closed.
- **MEASURED on rekha's tree**, LiberationSans:

| | 0.4.2 (sadish 0.5.5) | 0.4.3 (sadish 0.9.0, exact caps) |
|---|---:|---:|
| printable-ASCII paths (95 glyphs) | 433,648 B | **59,784 B** |
| `rekha_char_to_sdpath` 'A' | 4,776 B | **816 B** |
| one 3-point glyph, path + outline (alloc_test) | 4,304 B | **352 B** |
| 54-character label, arena per draw | 231,928 B | **55,320 B** |
| `rekha_outline_to_sdpath` (ASCII) | 921 ns | **818 ns** |
| `rekha_char_to_sdpath` (composite U+00C5) | 2,795 ns | 3,010 ns |

  The composite row is the one that went the wrong way (+8 %, three runs): a composite's path is
  counted as well as emitted, and its outline is the part the counting walk cannot skip. The bench's
  result checksum is unchanged (`-6023123829465929365`), so nothing rendered differently.
- **The estimate is exact, and a test says so.** `face_test` now asserts `sd_path_verb_cap ==
  sd_path_verb_count` and the same for points on **all 2,620 glyphs** of the embedded face: no path
  grows, and none carries slack (above sadish's 8-slot floor, which the sub-8 paths meet).

### Fixed — a refused allocation can no longer truncate a glyph

`rekha_emit_contour` ignored what `sd_path_moveto` / `_lineto` / `_quadto` / `_cubicto` / `_close`
returned. sadish >= 0.7.2 returns `SADISH_ERR_OOM` from those instead of faulting, so an ignored
status would have left a glyph MISSING THE VERBS the refusal ate — the silent-truncation failure mode
rekha itself filed against sadish's flatten. Every status is checked now and the first failure makes
`rekha_outline_to_sdpath` return 0 (OOM). MEASURED, a hook granting its first K blocks then refusing,
K = 0..63 over 'A': every call returns 0 or the whole 17-verb path — no fault, no truncation, gated by
`hostile_test`'s refusing-hook sweep, which now sweeps the DRAW as well as the load.
⚠ With paths sized exactly there is no growth left to refuse, so no test can kill these checks today:
they are what turns a future divergence between the counting walk and the emitter into a clean 0
instead of a silent truncation, and `face_test`'s capacity assertion is what would catch the
divergence itself.

## [0.4.2] - 2026-09-15 — CFF: OpenType `OTTO` faces draw

### Added — `src/cff.cyr`, the `CFF ` table and its Type 2 charstrings

- **`rekha_font_open` accepts the `OTTO` sfntVersion** and resolves the `CFF ` table once: the four
  INDEXes, the Top DICT (CharStrings, Private, CharstringType, and for a **CID-keyed** font ROS /
  FDArray / FDSelect), the Private DICT's local Subrs, and for CID fonts the per-FD Subrs reached
  through FDSelect (formats 0 and 3).
- **`rekha_load_glyph` interprets the glyph's Type 2 charstring** into the same `RekhaOutline` glyf
  produces — so `rekha_glyph_to_sdpath` / `rekha_char_to_sdpath` / the advances work on an OTTO face
  with **no consumer change**. Implemented: rmoveto / hmoveto / vmoveto (with the optional width),
  rlineto / hlineto / vlineto, rrcurveto / rcurveline / rlinecurve / vvcurveto / hhcurveto /
  vhcurveto / hvcurveto, flex / hflex / hflex1 / flex1, hstem / vstem / hstemhm / vstemhm / hintmask /
  cntrmask (read for their stem count), callsubr / callgsubr with the count-dependent bias, return and
  endchar.
- **A cubic control point carries on_curve flag 2** (glyf's 0 = quadratic control, 1 = on-curve);
  `rekha_emit_contour` turns control, control, on-curve into one `sd_path_cubicto`, and a pair of
  controls ending a contour curves back to its start. `RekhaOutline` is otherwise unchanged.
- **The decode contract**, pinned by both the suite and the reference: coordinates accumulate in 16.16
  and each point is rounded floor(v + ½) into design units (charstring units — all 405 faces surveyed
  carry FontMatrix = 1 / unitsPerEm); a contour holding only its moveto point is dropped; a glyph is
  EMPTY (never partial) for `seac` endchar arguments, the deprecated arithmetic / storage operators, an
  operator with too few arguments, drawing before any moveto, a charstring ending without endchar, and
  any bound below.
- **Bounds and work, whatever the font says:** every INDEX header, object span and DICT walk is checked
  against the CFF table's DECLARED extent; one decode is limited to 65,536 interpreted operators per
  pass, subroutine nesting 10, a 48-argument stack and `REKHA_COMPOSITE_MAXP` (4,096) points.
- **`RekhaFont` is 240 B** (was 176): the CFF cache holds the CharStrings / Global Subr / local Subrs
  INDEXes, FDArray / FDSelect, the table extent and the CharStrings count. Resolved once at open.
- ⚠ **A font rekha refused before now opens.** An `OTTO` file was rejected by `rekha_font_open` up to
  0.4.1; a consumer that treated 0 as "not a usable face" now gets a handle and outlines. An `OTTO`
  file with no `CFF ` table opens too and reads its glyf tables, the way any absent table behaves.
  A WOFF 1.0 container wrapping an OTTO face now works end to end.

### Verified

- **Against an independent reference, on every CFF face of the dev host.** A Python CFF parser and
  Type 2 interpreter written from the spec (Adobe TN 5176 / 5177), compared glyph by glyph — point
  coordinates, flags and contour ends — with `rekha_load_glyph` on **405 OTTO faces: 5,093,070 glyphs
  and 415,584,832 points, digest-identical, 405 / 405**. The same survey measured what those faces
  use: no CID-keyed, `seac`, flex or arithmetic operators among them, which is why the suite builds
  those cases itself.
- **`programs/cff_test.cyr`** (new, 530 checks): every operator shape decoded to hand-computed points
  and flags; each refusal asserted on a glyph that HAS drawn a contour, so emptiness means the rule
  fired; a CID-keyed font with both FDSelect formats and per-FD subroutines; the resolve refusals;
  cubic emission to exact sadish verbs and 16.16 points plus a fill; exact allocation; and an A/B
  guard differential over every cut of the CFF table plus 300 seeded mutations of its bytes.
- **Mutation testing:** 43 mutants over `cff.cyr` and the cubic emit path. The first pass killed 16 —
  the suite was passing several refusals for the wrong reason (glyphs that would be empty anyway) and
  had no case for the bias boundaries, the depth / operator / stack limits, a two-curve `vvcurveto`,
  the flex1 tie, or a trailing moveto-only contour (which sizes the allocation). With those added,
  19 of 20 re-run mutants are killed; the survivor is a bounds guard two later checks shadow.
  Three checks no test could observe were REMOVED as no-ops instead of papered over: the width pop on
  hint operators (floor(n/2) is the same either way) and on endchar (nothing can have been drawn yet),
  and the CFF loader's load-budget charges (a CFF glyph has no components, so its budget can never be
  reached).

### Performance — MEASURED, per glyph, whole-face decode under an arena hook (3 passes)

| | glyphs | points / glyph | ns / glyph |
|---|---:|---:|---:|
| glyf, LiberationSans (embedded) | 2,620 | 27 | **1,010** |
| CFF, FreeSans.otf | 6,272 | 49 | **6,005** |

A CFF glyph costs more than a glyf glyph of the same size: the charstring is interpreted TWICE (once to
count points and contours, once to fill) so each outline is still exactly one `sd_alloc`, and the
interpreter walks subroutines rather than a flat point array.

### Roadmap

- `seac` (accented glyphs an old CFF face builds from two others; EMPTY today), CFF2, and TrueType
  Collections (`.ttc`) are the next CFF-side items on README's ladder.

## [0.4.1] - 2026-09-15 — WOFF 1.0, opt-in

### Added — `src/woff.cyr` and the `[lib.woff]` bundle

- **`rekha_font_open_woff(buf, len)`** opens a W3C WOFF 1.0 file: it validates the container, rebuilds
  the SFNT it carries into ONE `sd_alloc(totalSfntSize)` (offset table with a recomputed
  searchRange / entrySelector / rangeShift, the WOFF's tag-sorted directory with each origChecksum, every
  table inflated where compLength < origLength and zero-padded to 4 bytes) and `rekha_font_open`s it.
  **`rekha_font_open_any(buf, len)`** sniffs `wOFF` and otherwise opens plain SFNT bytes.
  **`rekha_woff_sfnt_size(buf, len)`** validates header + directory without inflating (0 B) and
  returns the rebuilt size; **`rekha_woff_decode(buf, len, dst, cap)`** rebuilds into a caller buffer.
- ⛔ **Refused before anything is allocated or inflated:** a signature other than `wOFF`,
  reserved != 0, `length` past the bytes given, no tables, a directory that does not fit, tags not
  strictly ascending, table data outside [end of directory, length), compLength > origLength, an
  origLength past **1,032 x** its compLength (DEFLATE cannot expand further), padded compressed sizes
  summing past `length` (one stream named by many entries cannot be expanded many times), a
  totalSfntSize that is not exactly the rebuilt size, and metadata / private blocks outside `length`.
  Inflating must then produce **exactly** origLength under an output cap of origLength
  (`zlib_decompress_capped`, sankoch >= 2.7.13).
- ⭐ **Opt-in, so no consumer pays for it.** `src/woff.cyr` is in the new `[lib.woff]` profile
  (`dist/rekha-woff.cyr` = rekha's modules + woff), NOT in `[lib]`: `dist/rekha.cyr` and its
  `dist/rekha.deps` are unchanged and never require sankoch. A WOFF consumer takes `dist/rekha-woff.cyr`
  instead and includes `lib/sync.cyr` + `lib/sankoch.cyr` (the cyrius 6.6.4 stdlib ships sankoch
  2.7.15) before it. sankoch is not added to rekha's `[deps].stdlib` — that would union it into the base
  sidecar — and `cyrius.lock` is unchanged. The release publishes `rekha-woff-<tag>.cyr` beside
  `rekha-<tag>.cyr`.
- **Allocation, MEASURED:** under an arena hook, `rekha_font_open_woff` of the embedded face puts
  exactly the SFNT (410,824 B) + the `RekhaFont` (176 B) on the arena; sankoch's inflate does not use
  the sd_alloc seam and takes a flat 448 B of global heap per `rekha_woff_decode` (sankoch 2.7.15,
  19 tables). Open a WOFF once, outside a per-frame hook, like any font.

### Verified

- **29 real WOFF files from other encoders** on the dev host (QEMU docs: Lato ×4, Roboto Slab ×2,
  FontAwesome; KaTeX ×19; Qt docs' icomoon ×2): all accepted, every rebuilt table (tag, checksum,
  length, bytes) identical to an independent Python decoder using `zlib.decompress`, every one opens,
  and their cmaps map (Lato 2,164 codepoints each).
- **`programs/woff_test.cyr`** (new, 123 checks): LiberationSans wrapped into WOFF in the test with
  sankoch's own `zlib_compress` — compressed and stored — must rebuild with every table byte-identical,
  zero padding, the recomputed offset-table fields, and a font whose every glyph, BMP mapping and
  advance digests identically to the face opened directly; one one-defect copy per refusal rule
  (including each rule ALONE, with the padded sums and totalSfntSize kept valid); a corrupted glyf
  stream, streams inflating one table short and long; and an A/B guard differential over every cut of
  the header and directory and a stride through the data. No converted font is committed.
- **`programs/woff_dist_test.cyr`** (new): `dist/rekha-woff.cyr` compiled the consumer way, opening a
  WOFF and asserting the arena cost above to the byte.
- **Mutation testing** of `src/woff.cyr`: 30 mutants. The first pass left 10 alive: 5 real gaps
  (numTables 0 with a consistent totalSfntSize; out-of-range data and compLength > origLength each
  isolated from the padded-sum rule; the private block's offset; padding bytes), now killed; 2 dead
  checks (`length < 44`, shadowed by the directory fit; `origLength == 0` on the inflate path, where
  compLength <= origLength forces the stored path), removed; 2 bounds that change no RESULT but keep
  the header / directory reads inside `len` (`len < 44`, the directory fit), kept and commented; 1
  mutation that did not apply.

### Dependencies — filed where the work is

- **sankoch:** `docs/development/issues/2026-09-15-profile-bundles-call-sankoch-reset-tables-outside-their-closure.md`
  — every codec profile bundle (zlib, gzip, xz, bzip2, zstd, tar, zip, zipall) calls
  `_sankoch_reset_tables`, which only the full bundle defines, since 2.7.10: MEASURED, a program that
  calls `zlib_decompress_capped` through `dist/sankoch-zlib.cyr` is refused (`1 reachable undefined
  function`). This is why rekha's WOFF test uses the full stdlib `sankoch`. Noted at the head of
  sankoch's roadmap queue.

## [0.4.0] - 2026-09-15 — every Unicode cmap: formats 12 / 13 / 6 / 0, ranked selection, symbol faces

### Added — the cmap reads the whole Unicode range

- **Formats 12 (segmented coverage — U+0000..U+10FFFF), 13 (many-to-one), 6 (trimmed table) and 0
  (byte table)** beside format 4. Format 12 / 13 groups are binary-searched; an id past 0xFFFF has no
  glyph (glyph ids are u16) and maps to `.notdef`; a codepoint past U+10FFFF maps to `.notdef` even
  when a u32 group end reaches past it.
- **(3,0) SYMBOL faces map.** A symbol table is looked up at `cp` and, when that misses and
  `cp <= U+00FF`, at U+F000 + `cp` — symbol fonts keep their glyphs in the private-use F0xx block.
  (0.3.11 mapped nothing through a (3,0)-only cmap.)

### Changed — which subtable a font uses

- ⭐ **The best-RANKED valid subtable wins, not the last matching record.** Rank: (3,10) > (0,4) /
  (0,6) > a format 12 / 13 table under any other Unicode record > (3,1) > (0,3) > other (0,x) >
  (3,0); a later record wins a tie; (0,5) (Variation Sequences) and Macintosh (1,0) (Mac OS Roman, not
  Unicode) are never candidates. ⚠ Two consequences a consumer can observe: a (3,1) table now
  outranks a (0,3) table whatever the record order (0.3.11 took whichever came LAST), and a
  better-ranked record whose header or arrays do not fit the cmap extent is SKIPPED in favour of the
  next valid one (0.3.11 chose first and then found no usable subtable at all). Both follow what
  FreeType and HarfBuzz do. Every candidate is validated against the cmap table's DECLARED extent at
  `rekha_font_open`, as format 4 alone was in 0.3.11.
- **`RekhaFont` is 176 B** (was 160): the cmap cache holds the chosen table's entry count, format 6's
  firstCode, and its format + symbol flag. Paid once per `rekha_font_open`; every reader still
  allocates 0 B.
- ⚠ **~5 ns more per format-4 lookup.** MEASURED interleaved against 0.3.11, `bench_hotpath`,
  LiberationSans ASCII: `rekha_char_to_glyph` 29 -> 34 ns, `rekha_char_advance_px` 48 -> ~56 ns — the
  format dispatch. A format-4 fast path is in; inlining the lookup back into
  `rekha_char_to_glyph` did NOT recover it (measured, reverted). That is ~1 % of a 54-character label
  draw (~75 µs). Output is identical: the bench's result checksum over cp 32..255 is unchanged
  (`-6023123829465929365`).

### Verified

- **Real faces, against an independent reference.** A Python implementation of the selection rules
  and all five lookups, written from the spec, against `rekha_char_to_glyph` over EVERY codepoint
  U+0000..U+10FFFF, on 92 system `.ttf` faces (80 whose best map is format 12, 12 whose only map is
  format 4): **92 / 92 identical** (count of mapped codepoints and an FNV-1a digest of every
  (cp, gid) pair). On the 80 format-12 faces the BMP mapping is **identical to 0.3.11's** and every one
  of them gains codepoints past it — the Iosevka Nerd Fonts gain 9,442 (their plane-15 icons).
  LiberationSans still maps exactly 2,327 codepoints.
- **`programs/cmap_fmt_test.cyr`** (new, 90 checks): each format's mappings, range edges and a
  fits-exactly / one-byte-short pair on its arrays; every rank pair in BOTH record orders; symbol retry
  and its limits; supplementary codepoints through `rekha_char_to_sdpath` / the advance calls at 0 B;
  and a 600-group format-12 table whose lookup must equal a sequential reference on all 1,114,112
  codepoints, with and without the numGlyphs cap.
- **`hostile_test`** (540 checks): the A/B sentinel sweep now strides the supplementary planes, and
  formats 12 / 6 / 0 and a (3,0) table sit at EOF exactly long enough and one byte short — a fit
  check that reads one byte too far fails the differential itself (proven with three off-by-one
  mutants).
- **Mutation testing of the new cmap code:** 21 mutants. The first 16 left 5 alive — 3 real gaps
  (format 6's upper bound with a zero byte behind it, (0,5) / (1,0) only ever tested beside a better
  record, a u32 group end past U+10FFFF), now killed; 2 equivalent (`entryCount < 1` / `numGroups < 1`
  checks shadowed by the resolver's own `count > 0` gate), removed from the code.
- `cmap_ext_test` / `sfnt_edge_test` checks that pinned "last record wins", "a (3,0) table maps
  nothing" and "a cut header means no subtable" now pin the 0.4.0 behaviour, each with its reason in
  the comment.

### Dependencies — filed where the work is

- **sankoch:** `docs/development/proposals/2026-09-15-brotli-decoder-for-woff2.md` — a decode-only RFC
  7932 decoder as a `[lib.brotli]` profile for rekha's WOFF2 (roadmap Backlog note added).
  MEASURED on the embedded face: 410,820 B raw, 209,707 B WOFF1-style zlib, 169,278 B Brotli q11.
- **sadish:** two issues and one proposal, re-measured on sadish 0.6.0 — flatten keeps subdividing
  and allocating past `SD_FLATTEN_CAP` (50,200,616 B / 3,133,443 allocations for one flatten of
  4,096 curved quads, output silently truncated at 8,192 points); path construction stores through a
  refused `sd_alloc` (rc 139); and `sd_path_new_cap`, which would cut rekha's ASCII path arena
  433,648 -> 78,656 B. README's candidate list notes all three.
- README's roadmap is now an ordered v0.4.x ladder: WOFF 1.0, CFF outlines, WOFF2, the stdlib trim,
  adopting the sadish filings, then hinting.

## [0.3.11] - 2026-09-15 — hostile fonts: four overreads closed, fan-out bounded, the hot path cached

A full audit/hardening/optimization sweep. Eight independent audit lenses produced 88 raw findings
(59 after dedup, plus 3 from a completeness pass); every P0/P1 was reproduced with a running PoC
before it was fixed, and a second, fresh security review plus mutation testing ran against the
result. Public signatures are unchanged; the behaviour changes a consumer can observe are listed
under **Changed**.

### Security — out-of-bounds reads and unbounded work on untrusted font bytes

Every item below was reachable through `rekha_char_to_sdpath` (dhancha's per-glyph draw call) with a
crafted font that `rekha_font_open` accepts. Overreads on the bump allocator mostly land in mapped
memory, so they were PROVEN by a sentinel differential (the bytes past `len`, or an arena prefilled
A vs B — any output difference is a read outside the buffer) and then forced to fault at a guard page.

- ⛔ **Non-increasing `endPtsOfContours` → overread in `rekha_emit_contour`.** `rekha_load_simple`
  sized the point arrays from the LAST endPt only; an earlier one past it (`[65535, 2]` on a 3-point
  glyph) walked emit off xs / ys / on_curve. MEASURED: 59,417 verbs from 3 points; rc 139 at a
  guard page. Now: endPts must STRICTLY increase (checked again on the stored copy, after the
  allocation a hook could use to rewrite a shared buffer), and `rekha_outline_to_sdpath` stops at the
  first `end_pts` entry `< 0` or `>= n_points` whatever produced the outline.
- ⛔ **Composite merge past 4,096 points → `end_pts >= n_points`.** The merge clamped points at
  `REKHA_COMPOSITE_MAXP` but stored contour ends unclamped — from a fully VALID >4,096-point
  component. MEASURED: 16,381 verbs read from 4,096-entry buffers; rc 139. Now a merge over 4,096
  points or 128 contours is REJECTED (empty), never clamped.
- ⛔ **Composite fan-out: `sum N^L` bodies at ~70 KB each.** Nothing bounded total work across the
  depth-5 recursion. MEASURED: a 288-byte font whose glyph holds 4 self-references cost
  **96,733,552 B** in one `rekha_char_to_sdpath`; 6 self-references (~662 MB) faulted under a
  384 MB limit. ⚠ **Cycle detection alone does not fix it** — an ACYCLIC fan-out (glyph → 30× glyph
  → 30× glyph) amplifies the same way, which is why the fix is a budget. Now each
  `rekha_load_glyph` carries a stack context (0 B of heap): ≤ 64 glyph loads, ≤ 16,384 decoded points,
  depth ≤ 5, no gid repeated on its own component path; tripping any ABORTS the whole load (sticky —
  the result is EMPTY, never partial). MEASURED after: N = 1..8 self-references cost `8N + 96` B; the
  30×30 fan-out 11,184 B.
- ⛔ **`head` / `maxp` fields read past `len`.** `unitsPerEm` (+18), `indexToLocFormat` (+50) and
  `numGlyphs` (+4) were read after checking only that the table's declared span fit — a 0-length
  table at EOF read 16–48 B past the buffer (rc 139 at a guard page). Now `head` needs a declared
  length ≥ 54 B, `maxp` ≥ 6 B, `hhea` ≥ 36 B, or the table is treated as absent.
- ⛔ **Simple-glyph point count uncapped.** A ~530-byte glyph could declare 65,536 points via REPEAT
  flags: MEASURED 1,179,720 B per load. Now np > 4,096 is refused, and so is an np the remaining bytes
  could not encode as flags (2 bytes declare ≤ 256 points) — both before any allocation (48 B).
- ⚠ **Found by the second review, after the fixes above:** the endPts walk ran BEFORE the point cap
  and the budget, so a composite of 63 rejected 32,767-contour glyphs spent **9.6 ms** in one load.
  The O(1) gates and the budget charge now come first: MEASURED **10.5 µs**.

### Changed — hardening a consumer may observe

- **Tables obey an extent rule, checked once at open.** A table must start at/after the end of the
  directory and end inside `len` (a table overlapping the header/directory is absent). `cmap`
  records, the chosen format-4 subtable's header and all four segment arrays, and the glyphIdArray
  index are bounded by the `cmap` table's DECLARED length; `hmtx` reads by `hmtx`'s (a truncated
  `hmtx` now reads as advance 0 = unknown, never the next table's bytes); `loca` reads by `loca`'s and
  a glyph span by `glyf`'s (a last glyph overshooting `glyf` is refused, not clamped).
  `indexToLocFormat` other than 0 / 1 → no outline. Before, all of these were bounded by the FILE, so
  metrics and outlines could be decoded from a neighbouring table. Checked against 1,750 system
  `.ttf` files: 0 violate these rules.
- **`rekha_char_to_glyph` returns 0 for a mapped gid ≥ `maxp.numGlyphs`** (when maxp is present) — an
  id with no glyph behind it is `.notdef`, as FreeType maps it; `rekha_char_advance*` then report
  `.notdef`'s advance instead of the last hmetric's.
- **Every public reader returns 0 for a 0 font handle**; `rekha_font_open(0, n)` returns 0.
- **Composite decode is now spec-complete for positioning:** point matching (`ARGS_ARE_XY_VALUES`
  clear — unsigned point numbers; out-of-range → empty) was silently placed at (0, 0);
  `SCALED_COMPONENT_OFFSET` (0x800 without 0x1000) now scales the offset; the F2Dot14 transform
  ROUNDS, `sd_asr(v + 8192, 14)` (floor of v + ½), where 0.3.10 truncated toward zero. ⚠ Scaled or
  rotated components can move by up to 1 design unit: MEASURED old-vs-new over 71 system fonts
  (1,402,156 glyphs) — 69 identical, 53 composite glyphs in 2 fonts moved (contour/point/verb counts
  unchanged). LiberationSans is byte-identical (identity transforms only). A truncated LAST component
  record now yields an empty glyph (0.3.10 treated it as the end; FreeType rejects it).
- **`RekhaFont` is 160 B (was 40) and caches the table directory** — see Performance. ⚠ The buffer
  stays borrowed and the cache is a SNAPSHOT: mutating font bytes after `rekha_font_open` is
  unsupported (reads stay inside `len`; upem / numGlyphs / numberOfHMetrics / the cmap choice would
  describe the bytes as they were).
- **Allocation failure no longer faults inside rekha.** Every `sd_alloc` in the loaders is checked and
  0 propagates ("0 only on OOM"); `rekha_outline_to_sdpath(0, …)` returns an empty path. ⚠ sadish's
  `sd_path_new` / pushes still store through refused blocks, so a hook that can refuse must still
  fall back to the global allocator for a draw (MEASURED both ways; glyf.cyr head comment).
- **Removed (internal, unused downstream):** `rekha_px` / `rekha_py` (inlined), and the
  `RekhaPathVerb` enum — its QUADTO/CLOSE values disagreed with the sadish verb tags rekha actually
  emits. `rekha_load_glyph_d` takes a load context. `rekha_glyph_count` moved to sfnt.cyr (same
  signature).

### Added

- **`rekha_glyph_advance_px(font, gid, px)`** (what `rekha_char_advance_px` now wraps) so a consumer
  maps a codepoint ONCE and reuses the gid; **`rekha_glyph_advance_fx` / `rekha_char_advance_fx`**
  return the 16.16 advance. ⭐ Summing per-glyph-rounded pixel advances still drifts — MEASURED
  "ABABABABABAB" at 15 px: 78 px summed rounded vs 75 px from the 16.16 sum rounded once. The cmap.cyr
  comment that presented half-up rounding as the drift fix is corrected. All 0 B, 0 = unknown.
- **Ten new RUN suites (19 gating suites in all, each run under `CYRIUS_DCE=0` and `1`):**
  `hostile_test` (511 checks — a crafted corpus per audit class, an in-process A/B sentinel
  differential over every public entry point, and a 120-seed mutation loop over the embedded face;
  proven to fail against 12 deliberately broken copies of `src/`), `glyf_neg_test` (292 — one
  one-defect fixture per simple-glyph guard), `composite_flags_test` (262 — every component flag to
  hand-computed coordinates), `path_start_test` (247 — every contour-start branch, exact 16.16
  points), `extent_test` (325), `cmap_ext_test` (130 — incl. binary-search parity over all 65,536
  codepoints against a linear reference), `glyf_edge_test` / `sfnt_edge_test` (the gaps mutation
  testing found), `error_test`, and `dist_test`, which compiles the SHIPPED `dist/rekha.cyr` the
  consumer way (replacing the untested root `_distprobe.cyr`). `face_test` now loads and converts all
  2,620 glyphs of the embedded face under an arena hook and asserts exact totals (1,076 composites,
  5,288 contours, 71,785 points, 63,792 verbs, 2,327 mapped codepoints) at 0 B of global heap.
- **Mutation testing** of every new guard: 223 single-edit mutants over sfnt.cyr / cmap.cyr / glyf.cyr.
  The survivors that were real gaps (6 + 25) got the edge suites above, each verified to kill its
  mutant; the rest are equivalent mutants or guards no in-process test can observe (a 1-byte overread
  that changes no output). The reordered `rekha_load_simple` gates (Security, last item) were
  mutated again: the post-carve endPts re-checks survived until `glyf_edge_test` G14 rewrote the bytes
  from inside the allocation hook; the `nc > np` gate stays unkillable by an output check — removing
  it changes only the time a malformed glyph costs.
- **`programs/bench_hotpath.cyr`** — non-gating timings + arena bytes/op, with the result checksum
  (`-6023123829465929365` over cp 32..255, identical to 0.3.10's output).

### Performance — MEASURED, same machine, same session, median of 3 (bench_hotpath / audit bench)

The table directory used to be walked per call — `rekha_char_advance_px` walked it for head, cmap,
hhea and hmtx on every character, `rekha_char_to_sdpath` for cmap, maxp, loca, glyf and head. It is
now resolved once in `rekha_font_open`; cmap lookup takes segment 0 directly when it covers the
codepoint and binary-searches otherwise; each outline is ONE carved allocation; a composite is sized to
its children instead of fixed 4,096-point buffers; the span out-param moved to the stack; emit's
per-point helper calls are inlined.

| LiberationSans | 0.3.10 | 0.3.11 |
|---|---|---|
| `rekha_char_advance_px` | 787 ns | **48 ns** |
| `rekha_char_to_glyph` (ASCII) | 224 ns | **30 ns** |
| `rekha_glyf_span` | 785 ns | **36 ns** |
| `rekha_char_to_sdpath` (ASCII) | 2,473 ns | **1,398 ns** |
| `rekha_char_to_sdpath` (composite) | 5,473 ns | **3,231 ns** |
| 54-character label (advance + path per char) | 205,425 ns | **75,553 ns** |
| `rekha_font_open` (once per font) | 36 ns | ~1,500 ns |
| D2Coding (1,642 cmap segments), Hangul lookup | 7,686 ns | **85 ns** |

| bytes | 0.3.10 | 0.3.11 |
|---|---|---|
| 3-point simple outline (alloc_test) | 136 B | **112 B** |
| its `rekha_char_to_sdpath` | 4,328 B | **4,304 B** |
| one-component composite (alloc_test #51) | 70,856 B | **232 B** |
| `rekha_load_glyph` U+00C5 / U+00E9 | 71,632 / 71,464 B | **1,632 / 1,304 B** |
| Latin-1 U+00A0..00FF load pass | 4,237,264 B | **95,808 B** |
| `RekhaFont` (once) | 40 B | 160 B |

⚠ alloc_test check #51 used to assert the fixed-buffer waste EXISTED (`>= MAXP*17 + MAXC*8`); it is
now the exact composite cost, so a return to fixed buffers fails it by ~70 KB. The 0.3.10 table
above stays as it was measured. Output is unchanged on LiberationSans: every glyph's decoded points
and emitted 16.16 path match 0.3.10 and an independent spec-written Python reference (0 diff lines).

### CI, release, supply chain

- **Toolchain install pinned and verified** (`scripts/ci-install-cyrius.sh`, both workflows):
  `install.sh` is fetched from the `6.6.4` TAG (not `main`) and the release tarball is sha256-checked
  against hashes committed in the script (fails closed on a pin bump without a hash bump), under
  `set -euo pipefail`; the pin is parsed from `[package]` and must be `x.y.z`.
- **Permissions:** `contents: read` everywhere, `contents: write` only on the release job; every
  checkout `persist-credentials: false`; all actions pinned to full commit SHAs + `dependabot.yml`.
- **Build gate:** smoke and every `*_test.cyr` build AND run under `CYRIUS_DCE=0` and `1`; any
  `warning` / `undefined function` / `refusing to emit` line in a build log fails — 0.3.10's
  CHANGELOG described the green-build-that-faults and rekha's own CI never grepped for it.
- **Lock gate:** after `rm -rf lib && cyrius deps`, `cyrius.lock` must equal the committed file, and a
  live `path =` line in `cyrius.cyml` fails. **Dist gate:** `cyrius distlib --check` + no untracked
  `dist/` files; the release ships the COMMITTED bundle instead of regenerating it, and refuses a tag
  with no CHANGELOG section. **Lint gate** now fails on untracked deferrals and lint errors, not only
  `warn` lines.
- **Security scan** is an allowlist over every tracked `.cyr` / `.tcyr` (library code may only
  `syscall(1, 2, …)`; programs may also exit), and refuses process-spawn names, process/dlopen
  includes and inline `asm` (a working `asm` exit(7) passed the old scan).
- Job timeouts, `$RUNNER_TEMP` instead of `/tmp`, a dead cleanup step removed, prerelease comment
  corrected (every 0.x tag is a GitHub prerelease).

### Dependencies

- **`[deps.sadish]` drops `path = "../sadish"`.** It won over `tag` and skipped the commit pin, and
  its reason (0.5.5 not yet tagged) is gone — the tag is published (9760ead). `cyrius.lock` was
  regenerated from an EMPTY `lib/`: 110 → 23 entries plus the sadish `commit` pin; the 87 extra
  hashes were leftovers of a local full-snapshot `lib/` that no manifest asks for (and the source of
  the local "./lib/ shadows version-pinned" warning).

### Tooling

- `scripts/face2cyr.py` refuses short files, a directory past EOF, tables past EOF or over the
  directory, and a face with no format-4 Unicode cmap rekha can map (it used to accept one on which
  every codepoint is `.notdef`); writes atomically in UTF-8; escapes the file name in the generated
  string and comment. `fonts/face_data.cyr` regenerates byte-identically.

### Open items — where each one is tracked

- Glyphs over the load caps render EMPTY (a >4,096-point outline, a >128-contour composite, a
  composite needing >64 loads or >16,384 decoded points). No face checked exceeds them; LiberationSans
  peaks at 338 points (gid 2193).
- cmap formats 12 / 6 / 0 and `(3,0)` symbol fonts map nothing yet — first item of README's v0.4.0 line.
- Transform rounding is floor(v + ½) on the sum; FreeType rounds each product half away from zero,
  so exact negative halves can differ by 1 unit.
- **Filed in sadish (2026-09-15):** `sd_path_flatten` keeps subdividing and allocating after its
  8,192-point output is full and truncates silently — MEASURED on sadish 0.6.0: 12,386,304 B, 774,144
  allocations, ~47 ms for ONE `sd_canvas_fill_path` (64×64) of a glyph that fits every rekha cap
  (`sadish/docs/development/issues/2026-09-15-flatten-keeps-subdividing-and-allocating-after-the-output-cap-is-full.md`);
  `sd_path_new` / `sd_point_new` store through a refused `sd_alloc`
  (`…/issues/2026-09-15-path-construction-stores-through-a-refused-allocation.md`); and
  `sd_path_new_cap`, which would cut rekha's per-glyph path arena 5.5× on ASCII
  (`…/proposals/2026-09-15-path-capacity-for-known-size-paths.md`). rekha adopts each as it ships.
- `[deps].stdlib` still declares `io`, `vec`, `str`, `syscalls`, `assert`, `bench` that `src/` does not
  call. Trimming changes the `dist/rekha.deps` sidecar consumers resolve, so it goes out as its own
  release with the sidecar change called out — on README's v0.4.0 line.

## [0.3.10] - 2026-09-14 — rekha draws its memory from sadish's seam

### Changed — every allocation routes through `sd_alloc`; the draw stack has ONE knob

⭐⭐ **All 15 `alloc(` sites in `src/` — error.cyr 1, glyf.cyr 13, sfnt.cyr 1 — now call sadish's
`sd_alloc(n)`** (sadish 0.5.5's allocation seam: `sd_alloc_set(fp)` installs a hook and returns the
previous one, `sd_alloc_get()` reads it back, 0 = the global allocator). rekha adds no seam of its
own: it already hard-depends on sadish (`rekha_outline_to_sdpath` builds `SdPath`s), so the knob is
owned by the leaf, the way the fixed-point convention (16.16) already is. A consumer that scopes
`sd_alloc_set` around a text draw gets the **outlines, the paths and the coverage from the same
place**, and a per-frame arena reclaims all three at once.

**WHY.** `lib/alloc.cyr` is a bump allocator with **no `free()`**. dhancha's scalable text
(`dh_draw_text_ink`, `font != 0`) calls `rekha_char_to_sdpath` per glyph, per label, per frame, and
rekha drew its outline scratch — the 16-byte loca span, `end_pts`, `flags`, `on_curve`, `xs`, `ys`,
the 48-byte record, and for a composite (every accented letter in a real face) the 70,656 B of
merge buffers — from the global heap that no hook could reach. dhancha filed it (`2026-09-13-scalable-text-allocates-per-call-outside-the-frame-arena.md`);
crab's headline gate asserts a rendered frame costs the global heap **exactly 0 bytes** and cannot
adopt a proportional face until the whole draw stack can be pointed at its frame arena. sadish
0.5.5 is the rasterizer half of that fix; this is the outline half.

**MEASURED** (`alloc_used()` / `arena_used()` deltas, a 3-point triangle glyph, `'A'` via cmap,
sadish 0.5.5 vendored in both columns):

| call | 0.3.9, global heap | 0.3.9 under a sadish hook | 0.3.10 under the hook |
|---|---|---|---|
| `rekha_char_to_sdpath` | 4,328 B | **136 B leaked** on the global heap, 4,192 B on the arena | **0 B** global, 4,328 B on the arena |
| ...x 20 | 86,560 B | **2,720 B leaked** | **0 B** global, 86,560 B on the arena |
| `rekha_load_glyph` (simple) | 136 B | 136 B leaked, 0 on the arena | 0 B global, 136 B on the arena |
| `rekha_load_glyph` (composite of one) | 70,856 B | 70,856 B leaked | 0 B global, 70,856 B on the arena |
| `rekha_char_to_sdpath`, that composite | 75,048 B | **70,856 B leaked**, 4,192 B on the arena | 0 B global, 75,048 B on the arena |
| `rekha_font_open` | 40 B | 40 B leaked | 0 B global, 40 B on the arena |

The 4,328 B per glyph is 136 B of rekha (span 16 + end_pts 8 + flags 8 + on_curve 8 + xs 24 +
ys 24 + record 48) plus 4,192 B of sadish (`sd_path_new` 4,144 + 3 points x 16). Every byte
moved, none were added: the arena's high-water mark for twenty calls is exactly 20 x the global cost
0.3.9 paid, and after `arena_reset` twenty more calls land on the same mark.

⚠ **`rekha_font_open` lands in the hook too.** The 40-byte `RekhaFont` follows the seam like
everything else, which is why a consumer **opens fonts OUTSIDE a scoped hook** — a font opened under a
per-frame arena dies at that arena's reset. Reading a font costs nothing under any hook:
`rekha_char_to_glyph`, `rekha_advance_width`, `rekha_units_per_em`, `rekha_char_advance_px` allocate
0 B (asserted). ⛔ An outline or a path made under an arena hook must not be kept across that
arena's reset; that is the consumer's lifetime call, exactly as it is for sadish's own paths.
⛔ **The hook must not return 0.** `rekha_outline_empty` and `rekha_font_open` check their
allocation; the loaders store straight through theirs, as they always did with `alloc` — MEASURED
under a hook that returns 0: `rekha_font_open` returns 0 correctly, `rekha_char_to_sdpath` faults
(rc 139). A hook backed by an arena that can refuse falls back to the global allocator, as dhancha's
`dh_falloc` does, rather than returning 0. Said at the head of `src/glyf.cyr`.

⛔⛔ **FLOOR: sadish >= 0.5.5, HARD — AND BELOW IT THE BUILD MAY STILL GO GREEN.**
`sd_alloc` does not exist below 0.5.5, and MEASURED against a real 0.5.4 tree (a `git archive` of the
tag as the `path` dep): rekha's `path_test`, `glyf_test` and `smoke` **compile** — `warning: undefined
function 'sd_alloc'`, then `OK` — and the binary **dies at the first `rekha_font_open`**: `path_test`
and `glyf_test` exit 132 (SIGILL), the `CYRIUS_DCE=1` `path_test` exits 139 (SIGSEGV); only
`alloc_test` is refused (`error: refusing to emit binary with 2 reachable undefined function(s)`).
⚠ Which of the two a build gets is NOT "a direct call from the program vs one through the bundle"
(an earlier draft of this entry said so; it is wrong in both directions). cyrius 6.6.4 decides each
undefined NAME on its FIRST call site in code order: a first site inside a function DCE keeps live
refuses; a first site inside a dead function prints the warning, emits the binary, and every later
site of the same name — live or not — goes unexamined. MEASURED with a 4-line probe: a dead caller
of `missing_fn` listed before `main`'s own call → `OK (4456 bytes)`, rc 132; the same two fns with
`main` first → refused; a call three fns deep from `main` → refused. rekha's suites warn because the
first `sd_alloc(` in the fold is `rekha_err_new` (src/error.cyr), which no suite reaches — a copy of
`path_test` whose `main` calls `sd_alloc(16)` DIRECTLY still builds `OK (147320 bytes)` and exits 132.
A consumer whose first site is live is refused instead: crab, with no `sd_alloc*` call of its own,
against sadish 0.5.4 + dhancha 0.10.0 (`dh_draw_text_ink` is the first `sd_alloc_set(` site in its
fold, reachable from `main`) gets `refusing to emit binary with 2 reachable undefined function(s)`.
⇒ Either way the plain `warning: undefined function` line is printed; a consumer whose CI does not
grep build output for it can ship a green build that faults on its first glyph.
dhancha vendors the two bundles separately, so its `[deps.sadish]` tag must clear the same floor
when it takes this rekha — and its build gate should treat that warning as the error it is.
`[deps.sadish]` here moves `0.5.2` -> **`0.5.5`** and re-adds `path = "../sadish"` (the 0.5.5 tag
does not exist at the time of writing; ⛔ `path` WINS over `tag`, so a green build is not evidence
the tag resolves — re-verify with the `path` line disabled before moving the tag). `cyrius.lock`
loses the sadish `commit` line (a path dep pins no commit) and moves the `lib/sadish.cyr` hash;
nothing else in the lock changes.

**Proven by mutation** — `programs/alloc_test.cyr` (new, 67 numbered checks in groups A–D: the
no-hook baseline asserted > 0; twenty hooked calls cost the heap exactly 0 and the arena converges;
the outline record and all four buffers, the composite buffers and the font record lie inside the
arena's range; `sd_alloc_set(0)` restores and the next call is back on the heap at exactly the
group-A cost). Reverting one site at a time to `alloc(`:

| mutation | checks failed |
|---|---|
| glyf.cyr `rekha_load_simple` `xs` | **7** (#37, 38, 40, 41, 42, 46, 50) |
| glyf.cyr `rekha_load_glyph_d` `span` | **6** (#37, 38, 40, 41, 42, 50) |
| glyf.cyr `rekha_load_composite` `xs` | **3** (#50, 51, 53) |
| sfnt.cyr `rekha_font_open` `f` | **3** (#58, 59, 60) |

All **9** RUN suites pass (`sfnt meta glyf path cmap composite hmtx face alloc`); the eight
pre-existing ones are byte-for-byte unchanged in what they assert. `dist/rekha.cyr` 38,661 -> 40,750 B
(+2,089: the seam note in glyf.cyr and `sd_` on 15 call sites). The `CYRIUS_DCE=1` smoke binary
goes 16,208 -> 16,296 B, and **all +88 of it is the sadish 0.5.2 -> 0.5.5 bump** (0.3.9's sources
against the 0.5.5 bundle also build to 16,296; the non-DCE smoke is 143,272 B either way) — nothing
in rekha's change is reachable from the banner.

## [0.3.9] - 2026-09-14 — the literal defect is fixed upstream; the chunks stay

### Changed

- **Toolchain `6.6.3` → `6.6.4`**, moving with agnos 1.57.4 and kashi 1.0.8 (vendored `lib/` re-synced;
  `cyrius.lock` moves only for the six stdlib files 6.6.4 changed). All eight RUN suites pass.
- ✅ **The compiler defect 0.3.8 filed is FIXED in cyrius 6.6.4** — the lexer packed every string
  token as `(pool offset << 16) | length`, so a length ≥ 65,536 OR-ed into its own offset (the
  filing's "even length / alternate literal" narrative was the pool layout, not the mechanism);
  widened to `<< 32`. **Re-measured under 6.6.4:** the self-proving repro exits 0 and a SINGLE
  410,820-byte literal of this face compiles byte-exact (the same bisection that found it: 65,536,
  131,072 and 410,820 all OK). `scripts/face2cyr.py` and the generated header now record the defect
  as history rather than as a live constraint.
- ⚠ **The 4 KB chunks and `rekha_face_default_verify` stay.** A consumer that exposes bytes it has
  not hashed is trusting the compiler again; the boot-time verify that a chunked module makes cheap
  is what caught the last defect and is the only thing that would catch the next. `fonts/face_data.cyr`
  is byte-identical to 0.3.8 outside its header comment (regenerate-and-diff gate green).

## [0.3.8] - 2026-09-13 — the embedded default face: kernel support, half one

### Added — `fonts/face_data.cyr`, a freestanding data module carrying one TrueType face

⭐ **AGNOS had no proportional face a client could open, and the operator ruled rekha the
answer** (agnos issue `2026-09-13-no-proportional-face-on-the-target.md`, filed by crab). Stack-wide
there was no `.ttf` in any first-party repo; rekha parsed faces it never shipped. This is the
rekha half of the fix, shaped exactly like kashi's `src/font_data.cyr`: a **freestanding** module
(no stdlib, no heap, no syscalls — string literals, integer arithmetic, `load8`/`store8`) that a
freestanding kernel concatenates by path via `[deps.rekha] modules = ["fonts/face_data.cyr"]`.

- **The face is Liberation Sans Regular 2.1.5, embedded UNMODIFIED** (410,820 bytes, glyf outlines,
  format-4 BMP cmap — the two things `rekha_font_open` requires). `fonts/LiberationSans-Regular.ttf`
  is the source of truth and `fonts/LICENSE-LiberationFonts` (SIL OFL 1.1, Reserved Font Name
  *Liberation*) travels with it. ⚠ **Unmodified on purpose**: a subset is a Modified Version under
  the OFL and may not keep the Reserved Font Name, and no first-party subsetter exists; the full
  face costs a kernel ~410 KB of `.rodata` and a 2 MB page at boot, which agnos accepted.
- **API**: `rekha_face_default_len()` · `rekha_face_default_copy(dst, cap)` (→ length, or −1 when
  `cap` is short) · `rekha_face_default_verify(buf, len)` (FNV‑1a‑64 against the generator's hash of
  the source file → 1/0) · `rekha_face_default_name()`/`_name_len()` · per-chunk accessors.
- ⛔ **4096-byte chunks, and the reason is a compiler defect found while building this.** A cyrius
  6.6.3 string literal of EVEN length ≥ 65536 is emitted **shifted by one byte** (its first byte
  lost) on every alternate literal — `rc=0`, byte count intact, content wrong. Bisected over
  4096..131072 against an FNV‑1a of the file: odd lengths ≥ 65536 and every length < 65536 are
  byte-exact. Filed against cyrius; the generator stays far below the trap **and** the module carries
  the whole-face hash so a consumer verifies what it assembled rather than trusting the compiler.
  `programs/face_test.cyr` runs the same copy+verify path on the host, so the trap fails there before
  the bytes reach a target, and proves the verify is not vacuous (one flipped byte → 0).
- **`scripts/face2cyr.py`** (Python stdlib only — no fonttools) generates the module and refuses a
  CFF face or one missing `glyf`/`loca`/`cmap`/`hhea`/`hmtx`/`head`/`maxp`. CI regenerates into a
  temp file and requires a byte-identical match, so the data cannot drift from the `.ttf`.
- **Not in `[lib].modules`, not in `dist/rekha.cyr`, and outside `src/`**: 1.6 MB of generated
  literals must never ride into a consumer's bundle, and `cyrfmt` refuses files over 1028 KB.

### Changed

- **Toolchain `6.6.2` → `6.6.3`** (vendored `lib/` re-synced from the pin; `cyrius.lock` re-emitted in
  the sorted order 6.6.3 now writes — same entries, order only). All eight RUN suites pass, including
  the new `face_test`.

## [0.3.7] - 2026-09-11

### Changed

- **Toolchain `6.5.41` → `6.6.2`.** No source change; the value form needed none.
  Build, tests, and any bench/fuzz/distlib target the repo ships re-verified at the new pin.

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
