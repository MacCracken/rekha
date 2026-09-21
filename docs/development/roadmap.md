# rekha — Roadmap

> **Last updated:** 2026-09-21, at **0.8.2**.
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

⭐ **0.5.x, 0.6.x, 0.7.x and 0.8.x are all closed.** 0.5.x was the conformance milestone that opened
this file; 0.6.x was "the tables rekha transports and never reads", and there are none left —
rekha resolves **twenty-one**, and **all 28 of MVAR's tags** land on the field the spec names;
0.7.x gave the published error vocabulary a producer, and the ambiguity turned out to sit one level
below where it was being looked for — in `rekha_glyf_span`, whose 0 meant both "this glyph is a
space" and "loca is lying"; 0.8.x is TrueType hinting, measured against FreeType itself. See
CHANGELOG 0.5.0 through 0.8.2. What remains is **the freeze**.

| milestone | what it closes |
|---|---|
| **0.8.x — hinting** | **Closed at 0.8.2.** The last *rendering* gap: a hinted outline, bit-exact with FreeType 2.14.3 on every face measured. The divergences are pinned below. |
| **0.9.0 — the freeze** | **Next.** An API that is declared, documented and promised, rather than merely exported. |
| **1.0.0** | Lock it in. |

Everything else is **pinned** (real, evidenced, unscheduled), **blocked on a sibling**, or an
explicit **non-goal**.

---

## 0.8.x — hinting, closed

⭐ **0.8.0 shipped `src/hint.cyr`**: `cvt ` / `fpgm` / `prep` / `gasp`, the six `maxp` 1.0 limits,
the stack machine, the rounding engine, flow control, functions, the graphics state, and the FONT
PROGRAM running to completion — Liberation Sans's real 1,972 bytes, all 71 functions defined.
⭐ **0.8.1 shipped the two zones, every point instruction but `IUP`, and `prep` running once per
size** (`rekha_hint_run_prep`, `src/hint.cyr:3517`), measured against **FreeType 2.14.3 itself**
through `scripts/ftshim.py` — the `ctypes` binding that replaced a second hand-written interpreter
as the reference.
⭐ **0.8.2 shipped the hinted glyph**: the loader into zone 1 (simple and composite, in place, no
per-glyph allocation), the four phantom points, `IUP`, the glyph program under FreeType's
glyph-range rules, composites assembled FreeType's way, and the calls that answer a hinted outline
— `rekha_hint_glyph` / `rekha_hint_outline` / `rekha_hint_to_sdpath` / `rekha_hint_advance_px`
(`src/hint.cyr:4358-4575`). Measured: FreeType's own hinted outlines of Liberation Sans, **233 rows
/ 31 glyphs / 5,372 points** point for point (`programs/hint_glyph_vectors.cyr`); **167 unit
programs on 39 synthetic fonts**, every row three times (`programs/hint_unit_vectors.cyr`); the
whole face at ten ppems, **26,200 loads, 0 differ**; **165 host faces at 12 ppem, 2,593,954 loads,
and 50 more at 9 / 11 / 13 / 20 ppem, 2,812,516 loads — 0 differ** (`scripts/hint_glyph_diff.py`). Every instruction of the machine runs; the interpreter produces no
`REKHA_ERR_UNSUPPORTED` (`grep -c UNSUPPORTED src/hint.cyr` → the header's one mention). What is
left of hinting is the pinned table below — each row a stated divergence with its site — and the
freeze.

### Pinned by 0.8.x, and not blocking the freeze

Each is a stated divergence from FreeType 2.14.3, said at its site and in CHANGELOG 0.8.1 / 0.8.2.
The first row's "revisit" trigger has fired and the decision is recorded there.

- ⚠ **rekha refuses what FreeType's default mode reads as 0 or silently skips** — a control value
  outside the table (`"RCVT index"`, `src/hint.cyr:1994-1996`; `"MIAP cvt"` / `"MIRP cvt"`,
  `:2651`, `:2920`), a point index outside a zone (`rekha_hint_pt_ok`, `:1184-1188`), a storage
  index (`rekha_hint_op_mem`, `:1968`), a short stack (`"stack underflow"`, `:601`) — and the refusal
  reloads the glyph scaled and unhinted, named through `rekha_hint_error`. ⭐ **MEASURED at 0.8.2,
  and the trigger has fired**: 17,158 of 2,812,516 loads (0.61%) over 50 host faces at 9 / 11 /
  13 / 20 ppem are glyphs FreeType's default mode hints and its pedantic mode fails — all `RCVT`
  past the table but five (`IP point` on LiberationMono's '♫', `stack underflow` on DejaVuSansM
  Bold's 'Д'); **AdwaitaMono-Regular refuses 2,624 of 8,818 glyphs at 9 of 25 ppems**, all
  non-ASCII; no ASCII glyph on any face. **Decision, kept for 0.8.2**: refuse-don't-guess stands,
  because the refused glyph is drawn unhinted and never wrong. **The alternative, named**: mirror
  FreeType's default-mode fallbacks in the GLYPH RANGE only (`HC_RANGE` 4) — `RCVT` past the table
  reads 0 (ref2143/ttinterp.c:2861-2868), a short stack reads zeros, a bad point is skipped — so a
  refused glyph hints as FreeType hints it. A consumer who wants AdwaitaMono's arrows fitted at
  9 ppem asks for it here.
- ⚠ **A program refusal unhints the WHOLE glyph** — every component's moves and the composite's —
  where FreeType outside its pedantic mode keeps the partially hinted component and carries on
  (`src/hint.cyr:3572-3578`, `rekha_hint_glyph`'s comment `:4370-4378`).
- ⚠ **`SHZ` in a NESTED composite's own program** walks `first_point` slots past its last contour
  as FreeType's `Ins_SHZ` does (it never subtracts `first_point`, ref2143/ttinterp.c:5139), and
  rekha CLAMPS at the sub-zone's end where FreeType writes past its points array — an out-of-bounds
  write that on the host corrupts `libfreetype`'s heap or the adjacent tag bytes
  (`rekha_hint_op_shz`, `src/hint.cyr:2444-2465`; `HC_FIRSTPT`, `rekha_hint_first_point`,
  `:1050-1058`). A SIMPLE component's program runs with `first_point` 0 whatever its base. The unit
  rows `comp_nested_first_point` (generated inside FreeType's undefined regime, and marked so) and
  `comp_nested_shz_low` (inside the allocation) pin the visible part.
- ⚠ **FreeType's composite recursion cap of 100 is not modelled**; rekha's caps are the outline
  loader's — 64 loads, 16,384 points, depth 5, a cycle (`src/glyf.cyr:118-121`) — plus the zone's
  own capacity from `maxp` (`REKHA_HINT_MAXZONE`, `src/hint.cyr:294-298`; `"glyph zone cap"` /
  `"contour cap"`, `:3917`, `:3985-3988`, `:4191`). A glyph past its own `maxp` maxima is refused
  structurally (empty zone) where FreeType, which sizes nothing from those fields, renders it. A
  scan of all 1,129 hinted host faces: deepest nesting exactly 5 (AgaveNerdFont gid 1441, loads
  and agrees), at most 9 direct components and 17 loads per glyph, no understated `maxp` — so the
  caps refuse nothing on this host.
- ⚠ **The scan-type bits** FreeType ORs into the first tag byte of every instructed glyph (4 |
  `scan_type << 5`) are not kept (`rekha_hint_outline`'s comment, `src/hint.cyr:4515-4519`); the
  oracle masks with 0x19.
- ⚠ **`hdmx` is not read, and `rekha_hint_advance_px` is where it would matter**
  (`src/hint.cyr:4558-4563`): on an `hdmx` face at a listed ppem FreeType reports the table's byte
  as a hinted slot's advance (ref2143/ttgload.c:2302-2313, :1974-1975); rekha answers the hinted
  phantom distance, equal only when the table is a faithful cache. Measured on a synthetic face
  (4 of 4 advances differ at the listed ppem); 0 of 1,751 host `glyf` fonts carry one.
- ⚠ **Variable instances are hinted off-reference** (`rekha_hint_glyph`'s comment,
  `src/hint.cyr:4389-4395`), the default location bit-exact: no `cvar`; `gvar` deltas rounded per
  tuple and scaled from whole units (`src/gvar.cyr`) where FreeType rounds once on 16.16; `prep`
  re-run on EVERY axis change (`rekha_hint_axes_changed`, `:877-891`; `rekha_hint_ctx`'s comment
  `:824-834`) where FreeType re-runs it only when the face has a `cvar`
  (ref2143/ttgxvar.c:3993-3997); `GETINFO`'s variation bit and `GETVARIATION`'s gate are an axis
  actually off its default (`rekha_hint_op_getinfo`, `:2061-2077`; `rekha_hint_op_getvariation`,
  `:2130-2147`) where FreeType's flag stays set once any variation call was made, even back at the
  defaults; and the HVAR lsb map applies to `rekha_left_side_bearing` (`src/sfnt.cyr:677-703`,
  `rekha_hvar_lsb_delta` `src/hvar.cyr:261-271`) and NOT to the hinted pp1
  (`rekha_hint_hmetrics`, `src/hint.cyr:3601-3614`; FreeType leaves `lsb_adjust` NULL,
  ref2143/ttdriver.c:559), so on such an instance the metric reader and the hinted outline's
  origin differ by the delta. No hinted `gvar` face exists on the host to measure any of it.
- ⚠ **A `REPEAT` flag count past the last point is CLAMPED** by the shared decoder
  (`src/glyf.cyr:235-241`) — a leniency the other way round: FreeType refuses the glyph as
  `Invalid_Outline` (ref2143/ttgload.c:451-452) where rekha draws and hints it. Predates 0.8.2.
- ⚠ **Three `loca` rules FreeType sanitizes and rekha refuses** (`rekha_glyf_span`,
  `src/sfnt.cyr:740-750`, `:789-790`, against `tt_face_get_location`, ref2143/ttpload.c:183-288):
  offsets that run backwards (FreeType reads to the end of `glyf`; rekha `"loca order"`), the LAST
  glyph's end past `glyf` (FreeType clips; rekha `"loca past glyf"`), any other glyph's end or
  start past `glyf` (FreeType loads an empty glyph with real phantoms; rekha the same refusal).
  With the `REPEAT` clamp these are the whole of the corpus's `refused` class on a face pedantic
  FreeType loads — empty on every face measured.
- ⚠ **An `OS/2` shorter than 78 bytes is absent** to rekha, so `hhea` decides the vertical
  phantoms (`rekha_hint_vmetrics`, `src/hint.cyr:3648-3652`), where FreeType reads its 78 field
  bytes from the stream regardless and takes the `OS/2` branch with whatever follows. rekha's gate
  is the saner rule and is kept.
- ⚠ **Glyph-only bytecode is not run** (`rekha_hint_present`, `src/hint.cyr:360-379`): a face with
  no `fpgm` / `prep` / `cvt ` of non-zero length answers `NO_TABLE "hint tables"` and draws
  unhinted. That is FreeType's DEFAULT load, which autohints a face with no `fpgm` and a `prep` of
  at most 7 bytes (ref2143/ftobjs.c:1006-1016), not its `NO_AUTOHINT` one; rekha has no
  autohinter to fall back to.
- ⚠ A composite's `n_ins` or bytes past the glyph's `loca` span refuse `TRUNCATED "composite
  instructions"` (`src/hint.cyr:4214-4219`) where FreeType reads on from the stream; the per-run
  twilight bound has no +4 band and is the running MINIMUM within one load
  (`rekha_hint_twilight_bound`, `:3447-3460`; `HC_TWCAP`, `:248-250`); org is filled and the
  phantom tags are 0 when no program runs (`:3969-3972`), which nothing observes.
- ⚠ **A point, contour or reference index ≥ 65536 is refused** where FreeType's `FT_UShort` cast
  wraps it onto point k in both modes (`rekha_hint_pt_ok`'s comment, `src/hint.cyr:1179-1183`).
  Only stack arithmetic reaches it.
- ⚠ **A backward jump before a function's own start is refused** (`"jump out of range"`,
  `src/hint.cyr:3222-3233`); FreeType executes the bytes before the body.
- ⚠ **The twilight zone is zeroed with its tags and font-unit positions** per `prep`, where
  FreeType zeroes org and cur only (`rekha_hint_run_prep`'s comment, `src/hint.cyr:3509-3512`).
- ⚠ **A font whose `prep` is absent or empty gets the default graphics state**; 2.14.3 saves a
  stale execution-context GS there (`src/hint.cyr:3511-3512`) — a FreeType defect, not copied.
- ⚠ **FreeType's `LOOPCALL` / backward-jump caps and its call depth of 32 are not modelled**: rekha
  has one instruction budget of 1,000,000 and a depth of 64 (`src/hint.cyr:108-111`,
  `rekha_hint_exec`, `rekha_hint_call`).
- ⚠ **`INSTCTRL`'s operand order is unobserved in the corpus**: the one real site pushes `1 1`
  (`src/hint.cyr:87-88`, `:1886-1898`). Bits 1 and 2 are implemented on the glyph path
  (`rekha_hint_load_instctrl`, `:4291-4300`) in `tt_loader_init`'s order.
- ⚠ **`GETINFO` answers are fixed, not settable.** Version 35, no ClearType, not rotated, not
  stretched, grayscale on — **0 inside `fpgm`**, as FreeType has it (`rekha_hint_op_getinfo`,
  `src/hint.cyr:2061`; unit font 8 is the measurement). A consumer applying its own transform
  cannot tell the font about it.
- ⚠ **CI's FreeType is 2.13.2, the host's 2.14.3**, and the two differ in the move arithmetic, cvt
  scaling, `ODD` / `EVEN`, the stack margin and `DELTAP`'s pops (the headers of
  `programs/hint_unit_vectors.cyr` and `programs/hint_glyph_vectors.cyr`; `fv_b1_regime` is a
  program they disagree on). Neither module is regenerated in CI, none of the six hinting scripts
  runs there, and `scripts/ftshim.py` refuses any FreeType but 2.14.x.

### ⚠ CFF hinting is a separate question the wording hides

`src/cff.cyr` parses `hstem` / `vstem` / `hintmask` for stem *count* — enough to know how many mask
bytes follow — and discards the hints themselves. So "hinting" is two jobs, and only the TrueType
one has ever been named or scheduled.

---

## 0.9.0 — the freeze

### Declare the public surface, then promise it

`cat src/*.cyr | grep -c '@public'` → **137**, against **465** `fn` in `src/` (0.8.2). `@internal`
is a *module* header tag, one per file, and one `@public` comment often covers a run of sibling
accessors — so neither number is a count of marked functions, which is itself the problem. The
boundary is undeclared: `rekha_font_open`, `rekha_units_per_em`, `rekha_glyph_count`,
`rekha_descender`, `rekha_line_gap` and `rekha_find_table` are public in practice — the README's
own Quick Start and every consumer use them — and carry no marker.
⚠ The figure here read "34 against 172" through 0.7.0 and was two milestones stale, "125
against 362" at 0.8.0 and "128 against 421" at 0.8.1; nine releases of accessor-heavy modules and
the interpreter moved it. Re-measure it at the freeze rather than quoting this line.

The sibling shows the shape: **kashi** froze its API at 0.9.0, locked it at 1.0.0, and carries
`docs/api/` with a written stability promise plus `docs/adr/` for the decisions behind it. rekha
has neither directory.

For 0.9.0: mark every function, write `docs/api/`, state the 1.x promise (no signature changes, no
removals, no semantic changes; additions are additive), and record as ADRs the decisions already
made and currently explained only in scattered comments — the opt-in WOFF bundle, the `sd_alloc`
seam, the refuse-don't-guess policy (and the hinting corollary above: a refused glyph program
draws unhinted, never partially hinted), the one-leaf sidecar, the half-away-from-zero rounding
of `src/hint.cyr` against the half-up of everything else.
⚠ **What to freeze includes the hinting family**, 33 `@public` comments in `src/hint.cyr` alone:
`rekha_hint_ctx` (the one non-zero answer that is not success — a standing `fpgm` / `prep`
refusal rides on the handle), `rekha_hint_glyph` and its three refusal classes,
`rekha_hint_outline`'s view (rewritten by every call, never kept), `rekha_hint_to_sdpath`,
`rekha_hint_advance_px` (whole pixels, the only advance published), `rekha_hint_gid`,
`rekha_hint_run_prep`, `rekha_hint_run` (RANGE 3, the test range, FDEF allowed and writes
persisting — say so in `docs/api/` or unmark it), the readers `rekha_hint_gs` / `_point` /
`_zone_points` / `_cvt_px` / `_storage` / `_error` / `_detail`, `rekha_should_gridfit`,
`rekha_left_side_bearing` and `rekha_hvar_lsb_delta`; and the seam that is NOT public,
`rekha_hint_load_simple` (`src/hint.cyr:4436-4449`), which every consumer of `dist/rekha.cyr` can
link anyway — the freeze decides whether an `_` prefix or a `docs/api/` line keeps it out. The
consumer rules a frozen `docs/api/` must carry are README's five steps: `gasp` is the consumer's,
the context warmed outside a per-frame hook (and one glyph on a variable face), whole-pixel
`ox` / `oy`, `rekha_hint_advance_px` per glyph, `rekha_hint_ctx` again after an axis change.

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
| **`USE_MY_METRICS` (0x0200) on the O(1) advance reader** | `src/hint.cyr:4112` honours it on the HINTED path (`rekha_hint_advance_px` answers the component's phantoms, FreeType's rule, pinned by é and Å in `programs/hint_glyph_vectors.cyr`); `rekha_advance_width` (`src/sfnt.cyr:651`) still indexes `hmtx` by the composite's own gid | Honouring it in the unhinted reader puts a glyph decode behind an advance query that 0.3.11 measured at 47 ns, so the honest fix is a separate resolver, not a change to the O(1) reader. A consumer on the hinted path already has the right answer. |
| **Expert / ExpertSubset charsets** | `src/cff.cyr`, the `seac` refusal list (0.4.7) | Refused rather than guessed. Carrying the two tables would close the last `seac` refusal that is about missing data rather than a malformed font. |
| **CFF2 FDSelect format 4** | `src/cff2.cyr`, formats 0 and 3 only | Format 4 is the 32-bit-gid form; no observed font needs it. |
| **cmap formats 2, 8, 10** | `src/cmap.cyr` candidate validator | Format 2 is legacy CJK multi-byte; 8 and 10 are near-extinct. Silently non-candidates today — a font carrying *only* one maps nothing. |
| **Load caps are compile-time and silent** | `src/glyf.cyr:118-122` | 4,096 points / 128 contours / depth 5 / 64 loads / 16,384 points. A trip yields an EMPTY glyph with no way for the consumer to raise the ceiling or learn it was hit — which is `RekhaErr` again. |
| **WOFF / WOFF2 metadata and private blocks discarded** | `src/woff.cyr:36`; `src/woff2.cyr:46` | Bounds-checked, then dropped. Consistent with rekha's scope, but a named W3C container feature no accessor reaches. |
| **WOFF2 collections re-inflate per face** | `src/woff2.cyr:1565` (the warning is at the call site) | Opening every face of an *n*-face collection rebuilds the file *n* times, and `sd_alloc` has no free. The two-step escape hatch is public and documented; a cached handle would remove the trap. |
| **`rekha_advance_width` and friends are horizontal-only by name** | `src/sfnt.cyr:422+` | Relevant only if the vertical-metrics item lands: the API shape would need a vertical twin. |
| **`gvar` phantom-point advances are decoded and discarded by the O(1) reader** | `src/gvar.cyr:23-31`; `rekha_gvar_apply_n` (`:275`) lands them for the hinted loader, on a face without HVAR / VVAR only, FreeType's rule | A TrueType variable font with `gvar` and no HVAR varies its advances through the four phantom points per glyph. The hinted path carries them since 0.8.2 (`rekha_hint_advance_px`); honouring them in `rekha_advance_width` puts a full glyph decode behind an advance query measured at 47 ns, so the honest shape is a separate resolver, not a change to the O(1) reader. No hinted `gvar` face on the host measures it. |
| **HVAR's rsb map is read past; its lsb map reaches one reader of two** | `src/hvar.cyr:37-39`, `rekha_hvar_lsb_delta` (`:261-271`); `rekha_left_side_bearing` (`src/sfnt.cyr:677-703`) applies it, the hinted pp1 (`rekha_hint_hmetrics`, `src/hint.cyr:3601-3614`) does not | 0.8.2 added the lsb accessor and its delta. FreeType's TrueType driver never adjusts the lsb (ref2143/ttdriver.c:559), so the hinted outline's origin follows FreeType and the metric reader follows `rekha_advance_width`'s frozen semantics — on a variation instance with an lsb map the two differ by the delta (the 0.8.x pin above). No right-side-bearing accessor exists for the rsb map. |
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
  ranges, the six per-size control-value digests, `prep`'s post-run digests, the 167
  FreeType-recorded unit programs on 39 fonts (every row three times) and, since 0.8.2, **FreeType's
  own hinted outlines of 31 glyphs of the face — 233 rows, 5,372 points** — all re-run in CI with
  no corpus at all: **109,221 checks** in `programs/hint_test.cyr`, and the hinted path inside
  `programs/hostile_test.cyr`'s sentinel sweep and mutation loop (240,908 hinted loads over 120
  mutants). ⚠ What is NOT in CI is the oracle side: `scripts/hint_vectors.py` needs fontTools, and
  the six hinting scripts (`scripts/ftshim.py`, `hint_unit_vectors.py`, `hint_glyph_vectors.py`,
  `hint_glyph_diff.py`, `hint_prep_xcheck.py`; `hint_prep_vectors.py` is the one written from the
  sources) reach the installed `libfreetype` through `ctypes` — **FreeType 2.14.3 on the dev
  host, where CI's Ubuntu ships 2.13.2**, whose interpreter differs in ways one recorded program
  shows. So `programs/hint_unit_vectors.cyr` and `programs/hint_glyph_vectors.cyr` are
  transcriptions like `programs/face_test.cyr`'s constants: regenerated by hand on a 2.14.x host
  and reviewed as a diff, never rebuilt by a gate. Nor does the whole-face sweep run there:
  `scripts/hint_glyph_diff.py sweep` (26,200 loads, 0 differ) and its `corpus` mode (165 host
  faces at 12 ppem, 50 more at 9 / 11 / 13 / 20, 0 differ) are dev-host one-offs recorded in
  CHANGELOG 0.8.2, and the host has no hinted `gvar` or `hdmx` face at all, so those two pins are
  unmeasured on any real font. Worth having: a CI runner with a 2.14.x FreeType, or a pinned build
  of one, and the sweep on a schedule.
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
- A consumer asks for FreeType's default-mode fallbacks in the glyph range — a control value past
  the `cvt ` read as 0, a short stack read as zeros, a bad point skipped — because a glyph rekha
  draws unhinted (AdwaitaMono's arrows at 9 ppem) has to be fitted the way FreeType fits it.
- A hinted `hdmx` face or a hinted `gvar` face turns up in the wild: neither exists on the host, so
  the two pins on them were stated from the sources and a synthetic font, never measured on a
  real one.
- A CVE or an audit finding lands against a format rekha parses.
- sankoch ships **2.8.1**, or cyrius answers either open proposal.
- `sadish` grows paint capability that makes `COLR` v1 tractable.
- A shaping library appears in the stack and needs something from rekha that is not here.

## Where to look for…

- **Release history, with the measurements** → [`../../CHANGELOG.md`](../../CHANGELOG.md)
- **What rekha reads today** → [`../../README.md`](../../README.md), *Scope*
- **Open filings** → [`issues/`](issues/)
- **The dependency floors and why** → [`../../README.md`](../../README.md), *Dependencies*
