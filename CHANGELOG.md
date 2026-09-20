# Changelog

All notable changes to rekha are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
  written once and CFF's behaviour is untouched — every one of `programs/cff_test.cyr`'s checks
  passes unchanged across that refactor.
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

⚠ **Its builder lays every table out past the directory, and says why** — which is how the defect
in `programs/cff_test.cyr`'s own fixture, fixed below, was found.

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
