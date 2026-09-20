# rekha

Version: 0.6.6

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
- **The metrics a font INTENDS** — `OS/2` (0.6.1): the sTypo trio, the usWin pair, `sxHeight`,
  `sCapHeight`, weight and width class, `fsType`, `fsSelection`, the strikeout rule and the
  sub/superscript boxes; plus `post` (0.6.4) for the **underline** pair, the italic angle and fixed
  pitch, and `hhea`'s caret. ⭐ Every field MVAR has a tag for varies — as of 0.6.4 that is every
  tag naming a table rekha reads, **264 of 264** values identical to fontTools' instancer.
  ⛔ A face carries **three** vertical pairs and `fsSelection` bit 7 says which it means;
  `rekha_use_typo_metrics` reports the bit and rekha picks none of them, because choosing is layout
  policy. ⚠ `rekha_os2_version` returns -1 when there is no table — every metric answers 0, which a
  font is allowed to mean.
- **The seam** — `rekha_outline_to_sdpath` / `rekha_char_to_sdpath` emit y-flipped, scaled paths
  opened at exactly the glyph's verb and point count (0.4.3: the printable-ASCII set
  **433,648 B → 59,784 B**). Every byte rekha allocates goes through `sd_alloc` (0.3.10), so 20
  `rekha_char_to_sdpath` calls under an arena hook cost the global heap **exactly 0 bytes**.

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

## Roadmap

The full list, with the evidence behind every item, is
[`docs/development/roadmap.md`](docs/development/roadmap.md). What stands between 0.4.12 and a
**1.0.0** — rekha's promise *complete, correct and frozen*:

| milestone | what it closes |
|---|---|
| ~~**0.5.x — conformance and the target**~~ | **Closed.** The CFF2 argument stack is the format's 513, not CFF's 48; `aarch64` and AGNOS are built in CI and the wrong syscall number that hid there is gone; `avar` 2.0's segment maps apply; `FontMatrix` is read and applied instead of assumed; the `tests/tcyr` tier three CI steps globbed and that never existed is gone. |
| **0.6.x — the font's own answers** | The tables rekha transports and never reads — it resolved twelve, and a consumer cannot compute any of the rest from outlines. **0.6.0 shipped `HVAR` / `MVAR`, 0.6.1 `OS/2`, 0.6.2 `name`, 0.6.3 `STAT` with `fvar`'s named instances 0.6.4 `post`, 0.6.5 `kern` and 0.6.6 **GPOS** pair positioning**, making twenty. Left is vertical metrics — which also closes the last four MVAR tags. |
| **0.7.x — failures that say what failed** | `RekhaErr` is published, documented, and produced by nothing: every refusal collapses to a 0 or an empty glyph, so a caller cannot tell "not a font" from "truncated" from "over a cap". |
| **0.8.x — hinting** | `fpgm` / `prep` / `cvt ` and the glyph bytecode interpreter, for small sizes. CFF's own hints are parsed for stem count and discarded — two jobs, and only the TrueType one was ever named. |
| **0.9.0 — the freeze** | 34 of 172 functions carry `@public`, so the API boundary is undeclared. Mark it, document it in `docs/api/`, write the 1.x stability promise, add `SECURITY.md`. |

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
