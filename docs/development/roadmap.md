# rekha — Roadmap

> **Last updated:** 2026-09-20, at **0.6.4**.
>
> This file tracks **forward-facing work only**. Nothing struck through lives here: a finished item
> leaves. What already shipped is in [`CHANGELOG.md`](../../CHANGELOG.md), release by release, with
> the measurement each claim rests on; the capability summary is [`README.md`](../../README.md)'s
> *Scope*.
>
> Every item below carries a `path:line` or a grep, because an item nobody can check is a wish.

## What 1.0.0 means here

rekha's promise is **"what the glyph is"**: font bytes in, outlines and the numbers that place them
out, for `sadish` to fill. 1.0.0 is that promise **complete, correct and frozen** — not a wider
surface, but no remaining place where a consumer has to reach around rekha to a byte rekha already
holds, and no published name that does nothing.

⭐ **0.5.x is closed** (CHANGELOG 0.5.0 and 0.5.1): the conformance milestone that opened this file
is done, and what remains is surface, not correctness. **0.6.0 shipped `HVAR` / `MVAR`**, **0.6.1
`OS/2`**, **0.6.2 `name`**, **0.6.3 `STAT`** with `fvar`'s named instances and **0.6.4 `post`**, so the
tables rekha resolves are now eighteen and **two** of this milestone's items are left. ⭐ Every tag
in MVAR that names a table rekha reads now lands on it; the four `vhea` ones are what remain.

| milestone | what it closes |
|---|---|
| **0.6.x — the font's own answers** | The tables rekha transports and never reads. A consumer cannot compute any of them from outlines, so today it must parse the SFNT itself — the one thing rekha exists to stop. |
| **0.7.x — failures that say what failed** | `RekhaErr` is published and has no producer. |
| **0.8.x — hinting** | Outlines at small sizes. The last *rendering* gap. |
| **0.9.0 — the freeze** | An API that is declared, documented and promised, rather than merely exported. |
| **1.0.0** | Lock it in. |

Everything else is **pinned** (real, evidenced, unscheduled), **blocked on a sibling**, or an
explicit **non-goal**.

---

## 0.6.x — the font's own answers

The tables rekha **transports and never reads**. The set it DOES resolve is fourteen: `head`,
`maxp`, `loca`, `glyf`, `hhea`, `hmtx`, `cmap`, `CFF `, `CFF2`, `fvar`, `avar`, `gvar`, `HVAR`,
`MVAR`, `OS/2`, `name`, `STAT` and `post`. Every other OpenType tag in the codebase lives only inside WOFF2's
known-tag strings at `src/woff2.cyr:100-102`: lookup bytes, not readers.

### `kern`, and GPOS pair positioning only

`grep -rn -E '\bkern\b|GPOS' src/` → only the WOFF2 tag strings. rekha owns advance widths and
therefore decides inter-glyph spacing, and every pair is placed at its raw advance. Nothing else in
the stack can supply it: no sibling repo is a shaper.

⛔ **The split is deliberate.** Flat `kern` format 0 (a sorted pair array) and GPOS lookup types 2 /
9 restricted to pair kerning are **metrics**, which rekha already owns. Everything else in GPOS —
marks, cursive attachment, contextual chains — is a positioning engine and belongs to the shaping
library named under *Out of scope*.

### Vertical metrics — `vhea`, `vmtx`, `VORG`

`grep -rn -E 'vhea|vmtx|VORG' src/` → only the WOFF2 tag strings. A CJK face laid out vertically
needs a per-glyph vertical advance, a vertical line box, and (for CFF faces) a vertical origin that
is not derivable. The block mirrors the existing `hhea` / `hmtx` one almost exactly, long-metrics
tail included.

⚠ **Scheduled last in this milestone, and movable past 1.0.** rekha names *horizontal* metrics as
its shipped scope (0.3.6) and has never claimed vertical; no AGNOS consumer lays out vertical text
today. It is here because it is metrics, not because anything is waiting.

---

## 0.7.x — failures that say what failed

### `RekhaErr` is published and nothing produces one

`src/error.cyr:1` — *"@public — stable API surface for rekha error handling"*: eight codes, a
16-byte record, four accessors, a RUN suite. `src/lib.cyr:45` states the fact plainly — *"error.cyr
depends on nothing in rekha, and nothing in rekha calls it."* `grep -rn 'rekha_err' src/ programs/`
outside `error.cyr` returns one comment and one test.

Every failure collapses to a sentinel instead. `rekha_font_open` returns 0 for *null buffer*,
*truncated*, *not an sfntVersion rekha takes*, *directory overruns the file* and *allocation
failed* alike (`src/sfnt.cyr:186-190`). `rekha_load_glyph` returns an EMPTY outline for a malformed
glyph, a tripped cap and a genuinely blank glyph alike. `rekha_advance_width` returns 0 for *no
hhea*, *truncated hmtx* and *unknown* alike — and `src/sfnt.cyr:462` documents that 0 as "UNKNOWN,
NOT ZERO-WIDTH", which is precisely the distinction the caller cannot make.

⛔ **This is rekha's own house rule turned on rekha.** `src/sfnt.cyr:401`: *"THESE TWO TAGS WERE
DECLARED AND NEVER READ … A declared tag with no reader is a promise, not a feature."* A declared
error vocabulary with no producer is the same defect one layer up. Shipping it is a convention
(out-param or a per-font last-error slot) plus wiring the refusal sites; the enum is already
designed for it.

---

## 0.8.x — hinting

### TrueType hinting — `fpgm` / `prep` / `cvt ` and the glyph bytecode interpreter

Already the standing "after 0.4.x" item. `grep -rn -E 'fpgm|prep' src/` → only the WOFF2 tag
strings. This is the last thing between rekha's outlines and a legible 9-pixel glyph.

⚠ **CFF hinting is a separate question the current wording hides.** `src/cff.cyr` parses `hstem` /
`vstem` / `hintmask` for stem *count* — enough to know how many mask bytes follow — and discards
the hints themselves. So "hinting" is two jobs, and only the TrueType one has ever been named.

---

## 0.9.0 — the freeze

### Declare the public surface, then promise it

`grep -c '@public' src/*.cyr` → **34**, against 172 `fn` in `src/`. `@internal` is a *module*
header tag, one per file. So the boundary is undeclared: `rekha_font_open`, `rekha_units_per_em`,
`rekha_glyph_count`, `rekha_descender`, `rekha_line_gap` and `rekha_find_table` are public in
practice — the README's own Quick Start and every consumer use them — and carry no marker, while
138 functions are neither marked nor hidden.

The sibling shows the shape: **kashi** froze its API at 0.9.0, locked it at 1.0.0, and carries
`docs/api/` with a written stability promise plus `docs/adr/` for the decisions behind it. rekha
has neither directory.

For 0.9.0: mark every function, write `docs/api/`, state the 1.x promise (no signature changes, no
removals, no semantic changes; additions are additive), and record as ADRs the decisions already
made and currently explained only in scattered comments — the opt-in WOFF bundle, the `sd_alloc`
seam, the refuse-don't-guess policy, the one-leaf sidecar.

### `SECURITY.md` and `CONTRIBUTING.md`

`.github/workflows/ci.yml:362` already names both and prints *"WARN (optional, not yet present)"* —
deferred, not declined. For a library whose whole job is parsing untrusted input, which shipped a
hardening release (0.3.11: four out-of-bounds reads) and maintains a standing hostile corpus, the
`SECURITY.md` — reporting channel and threat model — is the consequential one.

---

## Pinned — real, evidenced, unscheduled

Each is genuine deferred work with a pointer. None blocks 1.0.0 on its own; any of them could join
a milestone when a consumer asks.

| item | evidence | note |
|---|---|---|
| **cmap format 14 / UVS lookup** | `src/cmap.cyr:39`, `:88` (`enc == 5` → rank −1) | Excluding format 14 as a *primary* map is correct and permanent. What is missing is the supplement: no `rekha_char_variant_to_glyph`, so U+FE0E/FE0F presentation selectors and CJK IVS resolve as base + `.notdef`. |
| **`USE_MY_METRICS` (0x0200)** | `grep -rn USE_MY_METRICS` → nothing; `src/sfnt.cyr:481` indexes `hmtx` by the composite's own gid | Honouring it puts a glyph decode behind an advance query that 0.3.11 measured at 47 ns, so the honest fix is a separate resolver, not a change to the O(1) reader. |
| **Expert / ExpertSubset charsets** | `src/cff.cyr`, the `seac` refusal list (0.4.7) | Refused rather than guessed. Carrying the two tables would close the last `seac` refusal that is about missing data rather than a malformed font. |
| **CFF2 FDSelect format 4** | `src/cff2.cyr`, formats 0 and 3 only | Format 4 is the 32-bit-gid form; no observed font needs it. |
| **cmap formats 2, 8, 10** | `src/cmap.cyr` candidate validator | Format 2 is legacy CJK multi-byte; 8 and 10 are near-extinct. Silently non-candidates today — a font carrying *only* one maps nothing. |
| **Load caps are compile-time and silent** | `src/glyf.cyr:118-122` | 4,096 points / 128 contours / depth 5 / 64 loads / 16,384 points. A trip yields an EMPTY glyph with no way for the consumer to raise the ceiling or learn it was hit — which is `RekhaErr` again. |
| **WOFF / WOFF2 metadata and private blocks discarded** | `src/woff.cyr:36`; `src/woff2.cyr:46` | Bounds-checked, then dropped. Consistent with rekha's scope, but a named W3C container feature no accessor reaches. |
| **WOFF2 collections re-inflate per face** | `src/woff2.cyr:1565` (the warning is at the call site) | Opening every face of an *n*-face collection rebuilds the file *n* times, and `sd_alloc` has no free. The two-step escape hatch is public and documented; a cached handle would remove the trap. |
| **`rekha_advance_width` and friends are horizontal-only by name** | `src/sfnt.cyr:422+` | Relevant only if the vertical-metrics item lands: the API shape would need a vertical twin. |
| **`gvar` phantom-point advances are decoded and discarded** | `src/gvar.cyr:23` | A TrueType variable font with `gvar` and no HVAR varies its advances through the four phantom points per glyph. Honouring them puts a full glyph decode behind an advance query measured at 47 ns, so the honest shape is a separate resolver, not a change to the O(1) reader. |
| **HVAR's lsb and rsb maps are read past** | `src/hvar.cyr`, the header note | rekha publishes no side-bearing accessor for them to vary, and a glyph's real bearing already follows its outline. Wants the accessor first. |
| **`post` glyph names** | `src/post.cyr`, the header note | Format 2.0's per-glyph name index, and the 258-name Macintosh standard order it indexes into — a table the size of everything else in that file. Glyph names serve tooling (PDF export, a debugger naming the glyph that failed); nothing rekha draws depends on one. |
| **STAT style-name synthesis** | `src/stat.cyr`, the header note | rekha reads every field and joins none of them: which values apply, the `axisOrdering` sort, dropping the elidable names. Deliberately the consumer's, like `rekha_use_typo_metrics` — but if two consumers write the same loop it belongs here after all. |
| **`avar` 2.0's variation store** | `src/var.cyr`, the avar note | 0.6.0 built the `DeltaSetIndexMap` reader that `avar` 2.0's mapping needs; wiring the two together is what is left. Its segment maps already apply. |

---

## Coverage — what the gates cannot see

Not defects. Places where the evidence is real but unreproducible, written down so the gap does not
quietly become permanent.

- ⚠ **Every headline ⭐ differential is a dev-host one-off.** CFF (405 faces / 5,093,070 glyphs),
  WOFF2 (280 files / 111,732 glyphs), cmap (92 faces), CFF2 and `gvar` — none of it runs in CI.
  ⭐ Three sweeps are the exception and the model: `scripts/cff2_wide_diff.py` (550 points over 100
  glyph instances), `scripts/cff_fontmatrix_diff.py` (12 matrices) and `scripts/metrics_var_diff.py`
  (88 metric values over two axes) each build their own font, so they need fontTools and nothing
  else, and all three are committed. The remaining sweeps need corpora that are not. fontTools is not a dependency, the corpora are not committed (size and licensing), and the
  in-repo fixtures are narrower by construction. A regression after 0.4.12 in any of those decoders
  would be caught only by the synthetic suites. Worth having: a scheduled workflow that installs
  fontTools and re-runs the sweeps, or a licence-clean mini-corpus with committed digests.
- ⚠ **The hostile corpus never touches the container parsers.** `grep -cin woff
  programs/hostile_test.cyr` → **0**. The seeded mutation sweep and the A/B sentinel differential
  cover the bare-SFNT reader; `.woff` and `.woff2` — the two inputs most likely to arrive off a
  network — get per-rule refusals and a guard differential, but never a mutation sweep, and they
  reach a much deeper decode path (substream walks, triplet decoding, `loca` rebuild, checksum
  recomputation).
- ⚠ **No coverage number exists at all** — see *Blocked on a sibling*.
- ⚠ **WOFF2 CI sees only STORED Brotli blocks** — see *Blocked on a sibling*.

---

## Blocked on a sibling

The rule: a missing sibling capability gets a filed proposal plus a line here. Never "off the list".

| waiting on | filing | status |
|---|---|---|
| **sankoch 2.8.1** — the Brotli **encoder**, so CI can build a genuinely compressed WOFF2 instead of a hand-emitted stored one | [`issues/2026-09-20-revisit-woff2-test-with-a-real-brotli-encoder-when-sankoch-2-8-1-lands.md`](issues/2026-09-20-revisit-woff2-test-with-a-real-brotli-encoder-when-sankoch-2-8-1-lands.md) | 🟡 open — sankoch is at **2.8.0**; its roadmap has the encoder next |
| **cyrius** — a declarative channel for test-only stdlib leaves, so `dist/*.deps` stops depending on which file an `include` sits in | `cyrius/docs/development/proposals/2026-09-16-declare-test-only-stdlib-leaves-instead-of-hiding-them-from-the-umbrella-scan.md` | 🟡 open — did not ship in 6.6.6; the standing workaround is the hand-pinned expected-leaf list in CI |
| **cyrius** — `coverage` should accept RUN programs as a corpus; it reads `tests/**/*.tcyr` only and reports ~0% for a fully exercised API | `cyrius/docs/development/proposals/2026-09-20-coverage-should-accept-run-programs-as-a-corpus.md` | 🟡 open — **filed 2026-09-20**, in this cleanup; the gap had lived only in a CI comment |
| **cyrius** — `fuzz --poison` should follow a custom allocator seam; its redzones live in the freelist allocator and rekha draws from `sd_alloc`, so it cannot instrument rekha at all | `cyrius/docs/development/proposals/2026-09-20-fuzz-poison-should-follow-a-custom-allocator-seam.md` | 🟡 open — **filed 2026-09-20**, in this cleanup; `programs/hostile_test.cyr` is rekha's ~2,100-line substitute |

⭐ **Closed, for the record:** both earlier rekha filings against sankoch shipped in **2.8.0** — the
WOFF2 Brotli decoder, and the profile bundles that could not link. Both are archived upstream.

---

## Out of scope — committed

Non-goals. Taking one on would change what rekha is.

- **Text shaping and layout** — GSUB, GPOS beyond pair kerning, BiDi, complex-script reordering,
  line breaking. rekha hands back outlines and advances; a shaping library consumes them.
  ⚠ **No such repo exists in the AGNOS stack yet**, and no slot is reserved for one — the siblings
  are a rasterizer, a bitmap-font provider, two tokenizers, a language corpus and a TTS
  grapheme-to-phoneme engine. That is a stack gap worth its own proposal when a consumer needs it,
  not a rekha item.
- **Rasterization, anti-aliasing, subpixel** — `sadish`. rekha owns *what the glyph is*, sadish owns
  *how it becomes pixels*, and the seam is the whole design.
- **Bitmap glyph sources** — `kashi` (PSF1/PSF2, VGA-ROM, BDF, PCF). This includes the strikes
  embedded in OpenType files (`EBDT`/`EBLC`/`EBSC`, `CBDT`/`CBLC`, `sbix`): they are PNG and bitmap
  data, not outlines, and rekha is the *outline* half of the pair.
- **The `SVG ` table** — needs an SVG renderer, which is neither rekha nor sadish.
- **`MATH`** — math typesetting is a document engine's capability, with no AGNOS consumer.
- **PostScript Type 1 (`.pfa` / `.pfb`) and bare CFF files** — Type 1 is a dead format; a bare CFF
  has no `cmap`, no `hmtx` and no `head`, so it cannot drive rekha's own API.
- **Subsetting and font writing** — rekha is a reader. It emits SFNT bytes only to rebuild a
  container it was handed (`rekha_woff_decode`, `rekha_woff2_decode`).
- **A glyph → Unicode reverse map** — the forward direction answers the question consumers actually
  ask; reverse mapping serves text extraction, which nothing here does.

## Out of scope — unbooked

Additive, understood, and waiting on a consumer to ask.

- **`COLR` v0 + `CPAL`** — the one colour format that is genuinely rekha-shaped: a base glyph maps
  to a list of layer glyphs, each with a palette index. That is *N* of the outlines rekha already
  produces plus an RGBA each, and it fits the existing seam by emitting several `SdPath`s instead of
  one. The gap is real (no emoji in a UI toolkit) and the work is honest outline work.
- **`COLR` v1** — gradients, composites and transforms need paint capability sadish does not have
  today. A joint item with sadish, not a rekha one.
- **A cached decoded-collection handle** — the fix for the WOFF2 re-inflate pin above, if anyone
  opens more than one face in a hot path.

## What would legitimately reopen this file

- A consumer hits one of the pinned items in a real font and can show it.
- A CVE or an audit finding lands against a format rekha parses.
- sankoch ships **2.8.1**, or cyrius answers either open proposal.
- `sadish` grows paint capability that makes `COLR` v1 tractable.
- A shaping library appears in the stack and needs something from rekha that is not here.

## Where to look for…

- **Release history, with the measurements** → [`../../CHANGELOG.md`](../../CHANGELOG.md)
- **What rekha reads today** → [`../../README.md`](../../README.md), *Scope*
- **Open filings** → [`issues/`](issues/)
- **The dependency floors and why** → [`../../README.md`](../../README.md), *Dependencies*
