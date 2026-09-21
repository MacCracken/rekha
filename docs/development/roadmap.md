# rekha — Roadmap

> **Last updated:** 2026-09-20, at **0.8.0**.
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

⭐ **0.5.x and 0.6.x are both closed.** 0.5.x was the conformance milestone that opened
this file; 0.6.x was "the tables rekha transports and never reads", and there are none left —
rekha resolves **twenty-one**, and **all 28 of MVAR's tags** land on the field the spec names.
⭐ **0.7.x is closed too**: the published error vocabulary has a producer, and the ambiguity turned
out to sit one level below where it was being looked for — in `rekha_glyf_span`, whose 0 meant both
"this glyph is a space" and "loca is lying". See CHANGELOG 0.5.0 through 0.7.0. What remains is
**hinting** and **the freeze**.

| milestone | what it closes |
|---|---|
| **0.8.x — hinting** | Outlines at small sizes. The last *rendering* gap. **0.8.0 shipped the machine**; two releases left. |
| **0.9.0 — the freeze** | An API that is declared, documented and promised, rather than merely exported. |
| **1.0.0** | Lock it in. |

Everything else is **pinned** (real, evidenced, unscheduled), **blocked on a sibling**, or an
explicit **non-goal**.

---

## 0.8.x — hinting

⭐ **0.8.0 shipped `src/hint.cyr`**: `cvt ` / `fpgm` / `prep` / `gasp`, the six `maxp` 1.0 limits,
the stack machine, the rounding engine, flow control, functions, the graphics state, and the FONT
PROGRAM running to completion — Liberation Sans's real 1,972 bytes, all 71 functions defined. What
it does not do is move a point: 101 of the 256 opcodes are refused **by name** through
`REKHA_ERR_UNSUPPORTED`.

### 0.8.1 — the zones, and `prep`

`grep -n 'REKHA_ERR_UNSUPPORTED' src/hint.cyr` → `rekha_hint_point_op`, the whole list.

The twilight zone (zone 0, `maxTwilightPoints` of them) and the point machinery every instruction
above needs: the projection and freedom vectors actually projecting, `GC` / `SCFS` / `MD`,
`MDAP` / `MIAP` / `MDRP` / `MIRP` with the control-value cut-in and the minimum distance,
`SHP` / `SHC` / `SHZ` / `SHPIX`, `IP`, `ALIGNRP` / `ALIGNPTS`, `ISECT`, `UTP`, `FLIPPT` and the
range forms, `SPVTL` / `SFVTL` / `SDPVTL`, and `DELTAP1/2/3`. Then `prep` runs, which is what makes
a size's control values the ones the font intended. ⚠ Liberation Sans's `prep` is 835 bytes and
CALLs into `fpgm` 65 times, so it exercises most of that list at once — a good gate and a poor
first test; the synthetic suite comes first.

### 0.8.2 — the glyph zone, and a hinted outline

Zone 1 with the four phantom points, the glyph program, composite hinting (`USE_MY_METRICS` and
the per-component instruction rules), `IUP`, and the public call that returns a hinted outline.
⚠ **The scaled-outline path does not exist yet either.** `rekha_load_glyph` answers in FONT UNITS
and `rekha_outline_to_sdpath` scales at emit; a hinted glyph is fitted in F26Dot6 at a ppem, so
this release also decides where that seam sits.

### Pinned by 0.8.0, and not blocking the milestone

- ⚠ **An out-of-range storage or control-value index is a refusal, where FreeType ignores it.**
  `src/hint.cyr`, the `rekha_hint_op_mem` header. rekha's refuse-don't-guess policy, visible
  through `rekha_hint_error`. The first thing to revisit if a real face trips it.
- ⚠ **`INSTCTRL`'s operand order is unobserved.** The only site in the host corpus pushes `1 1`.
  It follows FreeType and says so; a font that disagrees would be found by `prep` at 0.8.1.
- ⚠ **`GETINFO` answers are fixed, not settable.** Version 35, grayscale on, no ClearType, not
  rotated, not stretched. A consumer applying its own transform cannot tell the font about it.
- ⚠ **`MPS` assumes 72 dpi**, because rekha carries no dpi. A font branching on it rather than on
  `MPPEM` gets a consistent answer, not a device-correct one.

### ⚠ CFF hinting is a separate question the wording hides

`src/cff.cyr` parses `hstem` / `vstem` / `hintmask` for stem *count* — enough to know how many mask
bytes follow — and discards the hints themselves. So "hinting" is two jobs, and only the TrueType
one has ever been named or scheduled.

---

## 0.9.0 — the freeze

### Declare the public surface, then promise it

`cat src/*.cyr | grep -c '@public'` → **125**, against **362** `fn` in `src/`. `@internal` is a
*module* header tag, one per file, and one `@public` comment often covers a run of sibling
accessors — so neither number is a count of marked functions, which is itself the problem. The
boundary is undeclared: `rekha_font_open`, `rekha_units_per_em`, `rekha_glyph_count`,
`rekha_descender`, `rekha_line_gap` and `rekha_find_table` are public in practice — the README's
own Quick Start and every consumer use them — and carry no marker.
⚠ The figure here read "34 against 172" through 0.7.0 and was two milestones stale; eight releases
of accessor-heavy modules and the interpreter moved it. Re-measure it at the freeze rather than
quoting this line.

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
| **A vertical origin is not derived when a font states none** | `src/vert.cyr`, the header note | With no `VORG`, the convention is to derive one from the bounding box and the top side bearing. rekha answers 0 and says so through `rekha_vorg_present`, because a derived origin is a plausible wrong height for every glyph in a run. Wants a bbox accessor and a consumer that needs it. |
| **GPOS kerning does not follow the axes** | `src/gpos.cyr`, the header note | A GPOS ValueRecord can carry a Device table or a VariationIndex into GDEF's ItemVariationStore. The store reader exists (`rekha_ivs_delta`, 0.6.0); GDEF is what is missing, so a variable font's GPOS kerning is read at its default. |
| **GPOS script and language selection** | `src/gpos.cyr`, the header note | rekha takes the union of every `kern` feature's lookups. Doing it properly needs a script and a language on the API, which is a bigger question than the walk. |
| **The WOFF / WOFF2 opens do not say why** | `src/woff.cyr`, `src/woff2.cyr` | 0.7.0 gave `rekha_font_open` and `_index` their `_why` twins; the container opens still answer a bare 0, and they are the deepest pipeline in the library and the least diagnosable. |
| **The CFF interpreter's own refusals are silent** | `src/cff.cyr`, the `RC_BAD` sites | An OTTO glyph a charstring rule refused reports the same nothing a TrueType one used to. The handle slot is there; those sites are not wired. |
| **`kern` format 2** | `src/kern.cyr`, the skip list | The two-dimensional class array. Rare, and a font carrying one alongside a format 0 still kerns from the format 0; none of the 16 host `kern` fonts has one rekha needed. |
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
- ⭐ **The hinting evidence is the exception to the whole bullet above**: `scripts/hint_vectors.py`
  reads `fonts/LiberationSans-Regular.ttf`, which is COMMITTED, and the suite drives the same bytes
  through the embedded face module — so the font program, the 71 function numbers, the `gasp`
  ranges and the six per-size control-value digests all re-run in CI with no corpus at all. ⚠ What
  is NOT in CI is the script itself: it needs fontTools, and the constants are transcribed into
  `programs/hint_test.cyr` the way `programs/face_test.cyr`'s are.
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
