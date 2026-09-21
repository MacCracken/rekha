# rekha

Version: 0.8.2

**rekha** (रेखा — Sanskrit/Hindi: *line / outline / contour / stroke*) is
a pure-Cyrius vector/outline font subsystem for AGNOS. It parses
TrueType/OpenType (SFNT) font containers and decodes glyph outlines,
emitting them as **paths** (line / quadratic-Bézier verbs) into the
`sadish` 2D vector core, which rasterizes them.

rekha does **not** bundle its own Bézier rasterizer — it produces the
glyph-outline path; `sadish` fills it. The two form a clean seam: rekha
owns *what the glyph is* (SFNT tables → outlines), sadish owns *how it
becomes pixels* (fill → coverage). rekha is pure CPU Cyrius: no GPU, no C
shim, no external binaries.

## Scope

rekha turns **font bytes into glyph outlines** and hands them to `sadish` as paths. Everything in
this section is shipped and RUN-tested. This is the capability list; the per-release narrative —
and the measurement every claim rests on — is [`CHANGELOG.md`](CHANGELOG.md). What is *not* here
yet is [`docs/development/roadmap.md`](docs/development/roadmap.md).

### Containers

`rekha_font_open_any` sniffs all of them and returns a font.

| container | entry point | since | checked against |
|---|---|---|---|
| bare SFNT — `\0\1\0\0`, `true`, `OTTO` | `rekha_font_open` | 0.2.0 | — |
| TrueType Collections (`.ttc` / `.otc`) | `rekha_ttc_count` · `rekha_font_open_index` | 0.4.8 | 2- and 3-face collections fontTools authored; 2,298 glyphs identical |
| WOFF 1.0 | `rekha_font_open_woff` | 0.4.1 | all 29 `.woff` on the dev host, byte-identical to a Python/zlib decoder |
| WOFF2 | `rekha_font_open_woff2` | 0.4.6 | **280 files / 111,732 glyphs**, identical to fontTools 4.65.0 |
| WOFF2 collections | `rekha_woff2_face_count` · `rekha_font_open_woff2_index` | 0.4.10 | round trip to the `.ttc` each was built from |

⚠ The two web containers are **opt-in**: they live in `dist/rekha-woff.cyr` (`[lib.woff]`) and bring
sankoch with them. `dist/rekha.cyr` never requires it.
⚠ A rebuilt WOFF2 `glyf` is **not** byte-identical to the original and cannot be — the spec permits
several encodings of one outline. rekha's is deterministic and plain: one flag byte per point, no
REPEAT run-length. And there is **no independent WOFF2-collection decoder** to check against;
fontTools has no collection support in its WOFF2 reader or writer at all, so what anchors 0.4.10 is
the outcome — the rebuilt `.ttc` matching one fontTools authored, face for face.

### Outlines

Every format lands in the same `RekhaOutline`, so a consumer draws them the same way. Cubic control
points are flagged, so an `OTTO` face draws through `sd_path_cubicto` with no consumer change.

| outline source | since | checked against |
|---|---|---|
| `glyf` — simple and composite, the full flag set | 0.2.0 / 0.3.0 | — |
| `CFF ` Type 2 charstrings, name-keyed **and** CID-keyed | 0.4.2 | **all 405 CFF faces of the dev host — 5,093,070 glyphs, 415,584,832 points, identical** |
| `seac` — the accented glyph built from two others | 0.4.7 | a font fontTools authored, point for point ⚠ **0 of 406** host faces use `seac`, so there is no corpus sweep behind this one |
| `CFF2` | 0.4.9 | fontTools twice: a CFF→CFF2 conversion, and a variable CFF2 read from the same bytes |
| `FontMatrix` — charstring units to design units, for both | 0.5.1 | **12 of 12 matrices** agree with the ones fontTools parses from the same bytes |

### Variations

`rekha_var_set_axis` puts an axis at a user value; every later `rekha_load_glyph` draws the font
there. `fvar` + `avar` normalize the setting, and one scalar per region of the variation store
weights the deltas.

| | since | checked against |
|---|---|---|
| CFF2 `blend` / `vsindex` | 0.4.11 | fontTools at every location tested — axis defaults, both extremes, a region peak, halfway up one, the negative half, and a kinked `avar` map |
| `gvar` — packed points, packed deltas, per-contour IUP, composite offsets | 0.4.12 | **1,027 points across 29 glyph instances**, all identical to fontTools |
| wide stores — up to the 513-operand `blend` CFF2 specifies | 0.5.0 | **550 points across 100 glyph instances** over five region counts, all identical to fontTools |
| `HVAR` / `MVAR` — advances, and every OS/2 metric with a tag | 0.6.0, corrected in 0.6.1 | **160 of 160 metric values** over two axes and eight locations, all identical to fontTools |

`fvar` axes are enumerable, labelled and selectable: `rekha_var_axis_count` / `_tag` / `_min` /
`_default` / `_max` / `_name_id`, and since 0.6.3 the **named instances** a font ships —
`rekha_var_instance_count` / `_name_id` / `_coord` and **`rekha_var_set_instance`**, the one call
that turns "Bold Condensed" from a menu entry into a drawn font. `STAT` says how a family orders
and names those styles; rekha reads it and leaves the naming policy to the consumer. `avar` segment
maps apply, **version 1 and 2** (0.5.0).
⛔ The axis API is deliberately coarse: `rekha_var_set_axis` normalizes, runs `avar` and rebuilds
every region scalar, so it is a set-the-axes-then-draw call and not a per-glyph one.
⚠ **Advances and the intended metrics vary too**: `rekha_advance_width` reads HVAR (0.6.0), and
every `OS/2` field MVAR has a tag for takes its delta (0.6.1). With no axis set that costs one load
and a compare.
⛔ `hhea`'s ascender, descender and lineGap do **not** vary — MVAR has no tag for them, only for
its caret fields. 0.6.0 had this wrong; see CHANGELOG 0.6.1.
⛔ `avar` 2.0's variation store is not applied — only its segment maps. It needs the
`DeltaSetIndexMap` reader 0.6.0 added for HVAR, wired to `avar`, which is roadmap work.
⚠ A TrueType variable font with `gvar` and no HVAR varies its advances through `gvar`'s four
**phantom points**, which rekha decodes and discards — honouring them means a glyph decode behind
an advance query measured at 47 ns, so it is pinned rather than shipped.

### Characters, metrics, and the sadish seam

- **cmap** formats 4, 12, 13, 6 and 0; the best-ranked valid subtable wins and a broken record is
  skipped rather than fatal; (3,0) symbol faces retry U+00xx at U+F0xx (0.4.0). MEASURED on 92
  system faces against an independent reference: every codepoint U+0000..U+10FFFF identical.
- **Horizontal metrics** — `hhea` / `hmtx`: `rekha_advance_width`, `rekha_char_advance` / `_px` /
  `_fx` (rounded half-up), the line-box fields (0.3.6).
- **What the font is called** — `name` (0.6.2): family, subfamily, PostScript name, licence and
  the rest, decoded from UTF-16BE or Macintosh Roman to **UTF-8 in a buffer the caller owns** — a
  name query allocates nothing. The record is **ranked**, not last-one-seen, the way cmap's
  subtables are. `rekha_var_axis_name_id` finally labels the axes `rekha_var_axis_count` has been
  able to count since 0.4.11.
- **Kerning** — `rekha_kern_pair` / `_px` and `rekha_char_kern`, from wherever the font keeps it.
  **GPOS** pair positioning (0.6.6): both `PairPos` formats, both Coverage and ClassDef formats,
  and the extension wrapper — MEASURED against fontTools on **60 fonts, 264,964 pairs, all
  identical**. The legacy **`kern`** table (0.6.5), over both incompatible forms that share the
  tag — **163,183 pairs identical** across all 16 `kern` fonts of the dev host, and 8,000 probes
  for absent pairs all correctly 0. ⛔ GPOS wins when a font has both, because such a font says the
  same thing twice and adding them would double every pair; `rekha_kern_source` says which
  answered.
- **Vertical metrics** — `vhea` / `vmtx` / `VORG` / `VVAR` (0.6.7): the vertical line box and
  caret, per-glyph advance heights and top side bearings, and the vertical origin a CJK face sets
  its glyphs from. ⛔ rekha does **not** derive an origin when the font states none:
  `rekha_vorg_present` is the question to ask. ⚠ Horizontal remains the default and the tested
  path; this is metrics, not a vertical layout engine.
- **The metrics a font INTENDS** — `OS/2` (0.6.1): the sTypo trio, the usWin pair, `sxHeight`,
  `sCapHeight`, weight and width class, `fsType`, `fsSelection`, the strikeout rule and the
  sub/superscript boxes; plus `post` (0.6.4) for the **underline** pair, the italic angle and fixed
  pitch, and `hhea`'s caret. ⭐ Every field MVAR has a tag for varies — as of 0.6.4 that is every
  tag — **all 28 of them** as of 0.6.7 — and **312 of 312** values are identical to fontTools'
  instancer.
  ⛔ A face carries **three** vertical pairs and `fsSelection` bit 7 says which it means;
  `rekha_use_typo_metrics` reports the bit and rekha picks none of them, because choosing is layout
  policy. ⚠ `rekha_os2_version` returns -1 when there is no table — every metric answers 0, which a
  font is allowed to mean.
- **The seam** — `rekha_outline_to_sdpath` / `rekha_char_to_sdpath` emit y-flipped, scaled paths
  opened at exactly the glyph's verb and point count (0.4.3: the printable-ASCII set
  **433,648 B → 59,784 B**). Every byte rekha allocates goes through `sd_alloc` (0.3.10), so 20
  `rekha_char_to_sdpath` calls under an arena hook cost the global heap **exactly 0 bytes**.

### Hinting — a hinted outline, measured against FreeType

A TrueType face carries its own bytecode: `fpgm` is its function library, `prep` the program run
once per size, `cvt ` the control values both read, and each glyph may carry a program too. 0.8.0
was **the interpreter**, 0.8.1 the two zones and `prep`; **0.8.2 is the hinted glyph** — the
loader, the four phantom points, `IUP`, composites assembled FreeType's way, and the call that
answers a hinted outline. **0.8.x is closed.**

What a consumer calls, in order:

1. `rekha_should_gridfit(font, ppem)` — whether to hint at this size at all, from `gasp`. ⛔ That
   question is the consumer's: `rekha_hint_glyph` hints whenever asked, exactly as FreeType's
   loader never consults `gasp`. A face with no `gasp` answers 1, the long-standing convention.
2. `rekha_hint_ctx(font, ppem)` — the interpreter for that size: built on first use, `fpgm` run
   once, `prep` run on every size change. ⛔ **Call it once, OUTSIDE any scoped per-frame `sd_alloc`
   hook**, like `rekha_font_open` itself: the context is a lazy allocation cached on the handle.
   On a variable face load one glyph outside the hook too (the gvar scratch is allocated by the
   first varied load). After that a hinted glyph costs **0 bytes** — `programs/hint_test.cyr`
   group O pins it. ⚠ After an axis change **call it again**, at the same ppem if you like: the
   axis setters mark the cached context stale and that call re-runs `prep` for the new instance.
3. `rekha_hint_glyph(ctx, gid)` — the glyph into the glyph zone, scaled, phantoms appended, its
   program run under FreeType's glyph-range rules, every x translated so the left phantom is the
   origin. 1 when the zone holds what the bytecode intends; 0 when rekha refused, in one of three
   ways `rekha_hint_error` distinguishes: a standing `fpgm` / `prep` refusal (zone empty — draw the
   run unhinted), a PROGRAM refusal (the glyph reloaded scaled and UNHINTED, so the outline, path
   and advance still answer), or a structural one (a bad gid, record or cap — zone empty,
   `rekha_hint_gid` −1).
4. `rekha_hint_to_sdpath(ctx, ox, oy)` — the hinted outline as a positioned sadish path
   (F26Dot6 × 1024 IS 16.16, y flipped), or `rekha_hint_outline(ctx)` for the `RekhaOutline` view,
   valid until the next `rekha_hint_glyph`, `rekha_hint_run_prep` or size change. ⛔ Pass `ox` /
   `oy` on WHOLE PIXELS or the fit the program made is lost.
5. `rekha_hint_advance_px(ctx)` — the advance the glyph was fitted to, in whole pixels, **per
   glyph of a hinted run**, not `rekha_glyph_advance_px`: a program is free to move the right
   phantom, and Liberation Sans's 'H' at 16 ppem is **12 px** unhinted and **11 px** hinted.

| | since | checked against |
|---|---|---|
| `cvt ` / `fpgm` / `prep` / `gasp`, and the six `maxp` 1.0 limits | 0.8.0 | the embedded face, against `scripts/hint_vectors.py` |
| the machine: stack, storage, control values, arithmetic, all eight rounding modes, flow control, `FDEF` / `CALL` / `LOOPCALL` / `IDEF`, the graphics state | 0.8.0 | one instruction at a time, in `programs/hint_test.cyr` — **109,221 checks** over sixteen groups as of 0.8.2 |
| running the **real font program** | 0.8.0 | Liberation Sans's own 1,972 bytes: **all 71 functions defined, by number, stack empty** |
| the twilight and glyph zones, and every point instruction | 0.8.1, `IUP` in 0.8.2 | **FreeType 2.14.3 itself**: 167 glyph programs on 39 synthetic fonts, `programs/hint_unit_vectors.cyr`, every one also loaded clean under `FT_LOAD_PEDANTIC`, every row run three times — through the fill, through the real loader, and the consumer's way, glyphs 1, 2 and 3 in order on one context; rekha agrees **point for point, tag for tag, and on the advance** |
| running the **real control-value program**, once per size | 0.8.1 | Liberation Sans's 835-byte `prep` at 8 / 12 / 16 / 24 / 48 / 100 ppem: 65 `CALL`s, 858–1,037 instructions, 53 / 57 / 59 / 54 / 37 / 22 of 324 control values rewritten; digests and the ten inherited graphics-state fields pinned from a second interpreter written from the FreeType sources, itself read back out of `libfreetype` — **2,442 values, 0 mismatches** |
| **the hinted outline** — the loader, the phantoms, the glyph program, `IUP`, composites (per-component hinting, 2x2 transforms, scaled and rounded offsets, point matching, `USE_MY_METRICS`, the composite program at scale 1.0), `INSTCTRL` bits 1 and 2 | 0.8.2 | **FreeType's own hinted outlines of Liberation Sans** — `programs/hint_glyph_vectors.cyr`, **233 rows / 31 glyphs / 5,372 points**, point for point, tag for tag, end for end and on the advance; the whole face through `scripts/hint_glyph_diff.py`, **2,620 glyphs × 10 ppems = 26,200 loads, 0 differ, 0 refused**; a corpus of **165 host faces at 12 ppem, 2,593,954 loads, 0 differ**, and **50 more at 9 / 11 / 13 / 20 ppem, 2,812,516 loads, 0 differ**, every refusal one FreeType's own pedantic mode fails too |

⚠ **rekha refuses where FreeType's default mode reads a missing control value as 0 or skips a bad
point**, and that refusal is now measured: **17,158 of 2,812,516 loads (0.61%)** in the four-ppem
corpus, none of them ASCII, and AdwaitaMono-Regular refuses 2,624 of 8,818 glyphs at 9 of 25 ppems
— each drawn scaled and unhinted, never a plausible wrong glyph, with the instruction named through
`rekha_hint_error`. Kept as a decision; the alternative (FreeType's default-mode fallbacks in the
glyph range) is named in the roadmap for a consumer to ask for. `rekha_hint_ctx` is the one public
call that still answers the handle on a standing `fpgm` / `prep` refusal: the refusal is a
property of the size, re-raised on every call and mirrored onto `rekha_font_error`.
⚠ This layer rounds **half away from zero**, not half up like the rest of rekha, because its
reference is FreeType's interpreter rather than fontTools. They differ only on a negative value
landing exactly on .5 — which at 12 ppem is **five** of Liberation Sans's control values (0.8.0
counted four). The phantom points, a composite's offsets and the advance round by FreeType's
floor form instead, as its loader does.
⚠ Variable instances are hinted **off-reference** — no `cvar`, and `prep` is re-run on every axis
change where FreeType re-runs it only when the face has a `cvar` — and the default location is
bit-exact. `hdmx` is not read. CFF's own hints are parsed for stem count and discarded: two jobs,
and only the TrueType one was ever named.
⭐ **The hinting oracle is FreeType, reached through `ctypes`** — `scripts/ftshim.py` binds the
installed `libfreetype`, pinned to the classic interpreter and `FT_LOAD_NO_AUTOHINT`, the size set
ONCE per (face, ppem) the way a consumer drives it, with no freetype-py and no fontTools;
`scripts/hint_unit_vectors.py` records the unit programs from it, `scripts/hint_glyph_vectors.py`
the real glyphs of the embedded face, `scripts/hint_prep_xcheck.py` reads `prep`'s leftovers back
out of it, and `scripts/hint_glyph_diff.py` sweeps any hinted face on the host glyph by glyph and
says which point of which glyph disagrees. ⚠ Like every other differential sweep these run on the
dev host and not in CI: CI's FreeType is 2.13.2, whose move arithmetic differs, so both generated
modules are transcriptions, regenerated by hand on a 2.14.x host.

### Safety

0.3.11 closed four out-of-bounds reads reachable from `rekha_char_to_sdpath` and bounded composite
fan-out that could demand gigabytes. The invariant now enforced: every table lies after its own
directory and inside the file, a fixed field is read only when its table's DECLARED length covers
it, variable arrays stay inside their own table, and every outline's `end_pts` strictly increase and
stay `< n_points`. Load caps — 4,096 points / 128 contours per outline, 64 glyph loads and 16,384
decoded points per `rekha_load_glyph`, nesting depth 5, no component cycles — yield an EMPTY glyph,
never a partial one. `programs/hostile_test.cyr` is the standing corpus: a crafted font per audit
class, a seeded mutation sweep, and an A/B sentinel differential across the allocation seam.

⚠ The font buffer is **borrowed** and its metadata snapshotted at open — do not mutate it
afterwards, and open fonts OUTSIDE a scoped per-frame `sd_alloc` hook.
⚠ **One handle, one thread** (0.7.0). Readers write to the handle — GPOS resolves its kern lookups
lazily, `rekha_var_set_axis` writes the coordinates, and a refusal records its reason — so share
the borrowed font BYTES and open a handle per thread. That costs `REKHA_FONT_SIZE`, not the file.

### Why a call refused

A sentinel says something went wrong; it does not say what. Since 0.7.0 `rekha_font_error(font)`
and `rekha_font_error_detail(font)` answer for the last call, and `rekha_font_open_why` answers
where there is no handle yet to ask.

⛔ **The values did not change** — an empty outline for a refused glyph, a 0 advance, an empty path
— because every caller since 0.2.0 was written against them. What is new is telling them from the
legitimate answers that look identical: a space is also an empty outline, a combining mark's
advance is also 0, and `.notdef` is also glyph id 0. ⚠ Ask immediately after a call returned its
sentinel: every call that can set a code clears it first, but a reader that cannot refuse does not.

## Roadmap

The full list, with the evidence behind every item, is
[`docs/development/roadmap.md`](docs/development/roadmap.md). What stands between 0.4.12 and a
**1.0.0** — rekha's promise *complete, correct and frozen*:

| milestone | what it closes |
|---|---|
| ~~**0.5.x — conformance and the target**~~ | **Closed.** The CFF2 argument stack is the format's 513, not CFF's 48; `aarch64` and AGNOS are built in CI and the wrong syscall number that hid there is gone; `avar` 2.0's segment maps apply; `FontMatrix` is read and applied instead of assumed; the `tests/tcyr` tier three CI steps globbed and that never existed is gone. |
| ~~**0.6.x — the font's own answers**~~ | **Closed.** The tables rekha transports and never reads: it resolved twelve, and now twenty-one. `HVAR` / `MVAR` (0.6.0), `OS/2` (0.6.1), `name` (0.6.2), `STAT` with `fvar`'s named instances (0.6.3), `post` (0.6.4), `kern` (0.6.5), **GPOS** pair positioning (0.6.6) and the **vertical metrics** (0.6.7) — which closed MVAR too: all 28 of its tags land. |
| ~~**0.7.x — failures that say what failed**~~ | **Closed.** `RekhaErr` had been published and produced by nothing since 0.1.0. Every refusal now says which, out of the handle, with no byte allocated — and the ambiguity turned out to sit one level below where it was being looked for. |
| ~~**0.8.x — hinting**~~ | **Closed.** 0.8.0 shipped the machine, 0.8.1 the zones and `prep`, 0.8.2 the glyph loader, the phantom points, `IUP`, composites and the **hinted-outline call** — measured against FreeType 2.14.3 itself: 233 (glyph, ppem) rows of its hinted Liberation Sans point for point, the whole face and 165 + 50 host faces through `scripts/hint_glyph_diff.py` with 0 differences. ⚠ CFF's own hints are parsed for stem count and discarded — two jobs, and only the TrueType one was ever named. |
| **0.9.0 — the freeze** | **Next.** 137 `@public` markers against 465 `fn` in `src/` (re-measured at 0.8.2), so the API boundary is undeclared. Mark it, document it in `docs/api/`, write the 1.x stability promise, add `SECURITY.md`. |

⛔ **Out of scope, committed:** text shaping and layout (GSUB, GPOS beyond pair kerning, BiDi,
complex scripts) — a shaping library's job, and rekha is its glyph-data provider; rasterization and
anti-aliasing (`sadish`); bitmap glyph sources, including the strikes embedded in OpenType files
(`kashi`); subsetting and font writing, because rekha is a reader.

## Place in the stack

rekha is a **system library** in the Sanskrit/Hindi naming lane. It is the
*outline* half of a sibling font pair with `kashi` (काशि):

- **kashi** — **bitmap** glyph sources: PSF1/PSF2, VGA-ROM 8x16 / CGA 8x8,
  hand-drawn. Fixed-resolution; a freestanding kernel can embed it.
- **rekha** — **outline / Bézier** glyph sources: TrueType/OpenType.
  Scalable, resolution-independent; for high-DPI and arbitrary point sizes.

```
  font bytes ─▶ rekha (SFNT tables → glyph outlines → sadish paths)
                  │
                  ▼
                sadish (fill → coverage) ─▶ pixels
```

## The embedded default face

rekha ships one face as **data**, so a target with no font on disk still has
something to open: `fonts/face_data.cyr` is a freestanding module (no stdlib)
generated from `fonts/LiberationSans-Regular.ttf` (SIL OFL 1.1, unmodified;
licence in `fonts/LICENSE-LiberationFonts`). A kernel consumes it by path —

```toml
[deps.rekha]
path    = "../rekha"
modules = ["fonts/face_data.cyr"]
```

— copies it into one contiguous buffer with `rekha_face_default_copy(dst, cap)`
and **must** check `rekha_face_default_verify(buf, len)` before exposing it
(the 0.3.8 changelog records the compiler defect that check caught — fixed
in cyrius 6.6.4 — and 0.3.9 why the check stays). Regenerate with `python3 scripts/face2cyr.py fonts/<face>.ttf
fonts/face_data.cyr`; `programs/face_test.cyr` is the RUN proof.

## Consumers

**agnos** (1.57.2) is the first live consumer — of the *data* half: the
kernel folds `fonts/face_data.cyr` into its build and serves the face
read-only at `/fonts/default.ttf` (see *The embedded default face* above).
Downstream repos pull the *parser* half, `dist/rekha.cyr`, via a
`[deps.rekha]` git-tag entry; its intended consumers are the AGNOS
text/typography path — the `dhancha` UI toolkit, `crab`, a terminal,
document / UI text — anywhere scalable glyphs are needed.

## Dependencies

- **sadish** — the 2D vector-fill core rekha emits glyph paths into (the
  rasterize target), AND the allocation seam rekha draws from (`sd_alloc`).
  ⛔ Floor **0.9.0**: `SdPath`'s inline points and `sd_path_new_cap` are 0.7.2 / 0.9.0, and
  `sd_alloc` does not exist below 0.5.5 — the build may
  still compile (`warning: undefined function 'sd_alloc'`, printed either way)
  and fault at the first `rekha_font_open`, or be refused outright, depending
  on where the first call site sits (CHANGELOG 0.3.10). Wired via
  `[deps.sadish]` (`tag = "0.11.2"`, commit-pinned in `cyrius.lock`; for
  cross-repo dev add `path = "../sadish"` in an UNCOMMITTED copy — `path`
  wins over `tag`, skips the pin, and CI refuses a committed `path` line).
  A consumer vendoring `dist/rekha.cyr` next to its own `dist/sadish.cyr`
  must clear the same floor.
  ⚠ **sadish 0.10.0 is an ABI break that does not reach rekha.** It moved `SdPolyline`'s points
  inline, so `sd_polyline_points` strides 16 and an open-coded `load64(points + i * 8)` now reads a
  coordinate as an address. VERIFIED at the 0.4.5 pin bump: rekha names no polyline symbol anywhere
  in `src/` or `programs/` — it emits paths and never reads a flatten output. A consumer that *does*
  walk polylines must port to `sd_polyline_point_x` / `_y` before taking this pin.
- **Cyrius stdlib** — what a CONSUMER of `dist/rekha.cyr` must vendor is **`string`**, and that is
  the whole list (0.4.5; `dist/rekha.deps`). It is there because `src/` calls `strlen` + `memcpy`.
  The WOFF bundle adds `sankoch` (`dist/rekha-woff.deps`).
  ⚠ **`alloc` left that list in 0.4.5 and the bundle did not change — the toolchain did.** Through
  6.6.4 `lib/string.cyr` called `alloc()` (`strdup`/`strndup`) and declared no include for it, so
  distlib's compile-verify had to re-add the leaf; 6.6.6 makes that file self-sufficient, so `alloc`
  now arrives transitively with `string`. It is still linked; only the name a consumer has to
  resolve went away. ⛔ That ties the sidecar to the toolchain: a consumer **below 6.6.6** vendoring
  only `string` gets `warning: undefined function 'alloc'` and traps (SIGILL) at a `strdup` call, so
  consumers of `dist/rekha.cyr` 0.4.5 and up must be on 6.6.6 or later — rekha's own pin.
  ⚠ rekha's own test harness uses seven more (`fmt`, `vec`, `str`, `io`, `syscalls`, `assert`,
  `bench`) — those are declared in `programs/prelude.cyr` and are deliberately NOT published,
  because every leaf in the sidecar is one each consumer has to vendor. Resolved by
  `cyrius deps` into `lib/`.
- **sankoch** — only for the web containers, and only through `dist/rekha-woff.cyr`:
  `zlib_decompress_capped` for WOFF 1.0 (sankoch >= 2.7.13) and `brotli_decompress_capped` for
  WOFF2 (**>= 2.8.0**, which is the floor for that bundle as of 0.4.6; the cyrius 6.6.6 stdlib ships
  exactly 2.8.0). A consumer includes `lib/sync.cyr` and
  `lib/sankoch.cyr` before the bundle.
  ⭐ **Both rekha filings against sankoch are closed in 2.8.0**, which is what the 0.4.5 toolchain
  snapshot brings. The lean `[lib.zlib]` profile **links now** — every alloc-bearing profile bundle
  was unlinkable from 2.7.10 through 2.7.15 (`runtime.cyr` called a `_sankoch_reset_tables` that only
  `lib.cyr` defined, so a program using one was refused with *"refusing to emit binary with 1
  reachable undefined function(s)"*); rekha's issue is archived, and the rule that replaced it is
  sankoch's `docs/architecture/003-per-profile-reset-dispatch.md`. The WOFF2 Brotli decoder rekha
  requested **shipped** in the same release, which is what 0.4.6 was built on. ⚠ rekha does not exercise
  either: `programs/woff_test.cyr` takes the full `lib/sankoch.cyr` leaf from the toolchain pin, not a
  profile bundle, so the profile fix is a consumer's good news rather than a gate here.
  `dist/rekha.cyr` needs no sankoch.

The toolchain pin is `cyrius = "6.6.6"`.

## Quick Start

```bash
cyrius deps                                          # resolve stdlib + sadish into lib/
cyrius build programs/smoke.cyr build/rekha-smoke    # link-check
./build/rekha-smoke                                  # prints the banner

# RUN tests (each self-checks and exits non-zero on failure; CI runs them all
# under CYRIUS_DCE=0 and 1 and fails on any build-log warning)
for t in programs/*_test.cyr; do
  n=$(basename "$t" .cyr)
  cyrius build "$t" "build/$n" && "./build/$n" || break
done

# hot-path timings (visibility only; not a gate)
cyrius build programs/bench_hotpath.cyr build/bench_hotpath && ./build/bench_hotpath
```

## License

GPL-3.0-only.
