# rekha

Version: 0.4.7

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

- **v0.1.0 — scaffold.** Buildable compiling skeleton (error codes, struct
  layouts, SFNT byte readers, stub bodies). Superseded below.
- **v0.2.0 — real TrueType, end to end (shipped).** Font bytes → filled
  glyph, RUN-tested:
  - **SFNT container** — `rekha_font_open` (validated) + `rekha_find_table`
    (bounds-checked table directory).
  - **Metadata** — `rekha_units_per_em`, `rekha_loca_format`,
    `rekha_glyph_count`.
  - **loca → glyf** — `rekha_glyf_span` (glyph id → its glyf byte range).
  - **glyf decode** — `rekha_load_glyph` (contours, run-length flags,
    delta-encoded coords → `RekhaOutline`); reads bounded by the file (tightened
    to each table's own extent in 0.3.11).
  - **sadish seam** — `rekha_outline_to_sdpath` / `rekha_glyph_to_sdpath`
    convert TrueType quadratic contours (implied midpoints, off-curve
    starts) into a sadish `SdPath`, y-flipped + scaled to pixel space.
    **`sadish` is wired as a dependency; rekha is its first consumer.**
- **v0.3.0 — text (shipped).** Characters → glyphs, and composite glyphs:
  - **cmap format 4** — `rekha_char_to_glyph` (Unicode BMP codepoint → glyph
    id) + `rekha_char_to_sdpath` (one call: character → positioned sadish path).
  - **Composite glyphs** — `rekha_load_glyph` decodes numberOfContours < 0
    (recursive component load, F2Dot14 transform + offset, merged outline).
- **v0.3.6 — horizontal metrics (shipped).** `hhea`/`hmtx`: `rekha_advance_width`,
  `rekha_char_advance` / `rekha_char_advance_px` (rounded half-up), the `hhea`
  line-box fields; the `hmtx` left-side-bearing tail handled.
- **v0.3.10 — one allocation knob (shipped).** Every byte rekha allocates goes
  through sadish's seam (`sd_alloc`, sadish >= 0.5.5), so a consumer that scopes
  `sd_alloc_set` around a text draw gets the outlines, the paths and the coverage
  from the same arena: 20 `rekha_char_to_sdpath` calls under an arena hook cost
  the global heap **exactly 0 bytes** (MEASURED; 4,328 B each on the arena).
  ⚠ Open fonts OUTSIDE a scoped hook — `rekha_font_open` follows the seam too.
- **v0.3.11 — hardened against hostile fonts, and faster (shipped).** An
  audit found four out-of-bounds reads reachable from `rekha_char_to_sdpath`
  with crafted bytes, plus composite fan-out that could demand gigabytes;
  all are fixed and each has a regression suite. The invariant now enforced:
  every table lies after the directory and inside the file, a fixed field is
  read only when its table's DECLARED length covers it, variable arrays stay
  inside their own table, and every outline's `end_pts` strictly increase and
  stay `< n_points`. Load caps (not read from the font): 4,096 points / 128
  contours per outline, 64 glyph loads and 16,384 decoded points per
  `rekha_load_glyph`, nesting depth 5, no component cycles — tripping one
  yields an EMPTY glyph, never a partial one. Table offsets are cached at open
  (`RekhaFont` 40 → 160 B, once): a 54-character label draws **2.7× faster**
  (205 → 76 µs MEASURED) and an accented composite loads in 1.6 KB instead of
  71.6 KB. Composite point matching and scaled component offsets now decode;
  new `rekha_glyph_advance_px` / `_fx` and `rekha_char_advance_fx` (16.16).
  ⚠ The font buffer is borrowed and its metadata snapshotted at open — do not
  mutate it afterwards.
- **v0.4.0 — every Unicode cmap (shipped).** `rekha_char_to_glyph` reads formats 4, **12**
  (the whole Unicode range), **13**, **6** and **0**; the best-ranked valid subtable wins —
  (3,10) > (0,4)/(0,6) > a wide table under any other Unicode record > (3,1) > (0,3) > other (0,x)
  > (3,0) — and a broken record is skipped instead of blanking the map. (3,0) **symbol** faces map,
  with U+00xx retried at U+F0xx. MEASURED on 92 system faces against an independent reference: every
  codepoint U+0000..U+10FFFF identical; the 80 with a format-12 map keep 0.3.11's BMP mapping exactly
  and gain the planes past it (Iosevka Nerd Fonts: 9,442 icon codepoints).
- **v0.4.1 — WOFF 1.0 (shipped).** `rekha_font_open_woff` / `rekha_font_open_any` open a `.woff`
  (the W3C WOFF 1.0 container: per-table zlib) by rebuilding its SFNT into one `sd_alloc` and opening
  that; `rekha_woff_sfnt_size` validates without inflating, `rekha_woff_decode` rebuilds into a
  caller's buffer. Every declared size is checked before anything is allocated or inflated (tag
  order, table extents, DEFLATE's 1,032:1 ratio, the exact totalSfntSize, no stream shared between
  entries) and each table must inflate to exactly its origLength. **Opt-in:** it lives in
  `dist/rekha-woff.cyr` (`[lib.woff]`), which a WOFF consumer takes instead of `dist/rekha.cyr` and
  pairs with sankoch (the stdlib `sankoch` leaf + `sync`); the base bundle never requires sankoch.
  MEASURED: all 29 real `.woff` files on the dev host (Lato, Roboto Slab, KaTeX, FontAwesome, Qt
  icons) rebuild byte-identical to an independent Python/zlib decoder and open.
- **v0.4.2 — CFF outlines: OpenType `OTTO` faces (shipped).** `rekha_font_open` accepts the `OTTO`
  sfntVersion and resolves the `CFF ` table; `rekha_load_glyph` runs the glyph's **Type 2 charstring**
  (all the drawing, hint, subroutine and flex operators, name-keyed and **CID-keyed** fonts) into the
  same `RekhaOutline` glyf produces, with **cubic** control points flagged 2 — so
  `rekha_char_to_sdpath` draws an OTTO face through `sd_path_cubicto` with no consumer change. One
  decode is bounded: 65,536 operators, nesting 10, a 48-argument stack, 4,096 points. MEASURED against
  an independent reference on **all 405 CFF faces of the dev host — 5,093,070 glyphs, 415,584,832
  points, identical**. ⚠ Accented glyphs built with `seac`, CFF2 and TrueType Collections are on the
  list below; a WOFF wrapping an OTTO face now works end to end.
- **v0.4.3 — sadish 0.9.0, and a path sized to its glyph (shipped).** `[deps.sadish]` moves
  **0.5.5 → 0.9.0**, whose `SdPath` stores point coordinates INLINE (rekha filed the measurement that
  asked for it); five test programs move to `sd_path_point_x` / `_y` / `sd_path_verb_at`.
  `rekha_outline_to_sdpath` now counts a glyph's verbs and points first and opens the path at exactly
  that (`sd_path_new_cap`), so nothing grows: MEASURED, the printable-ASCII set **433,648 B → 59,784 B**
  of paths and a 54-character label **231,928 B → 55,320 B** of arena. A consumer hook that refuses now
  yields 0, never a glyph missing verbs — rekha checks every `sd_path_*` status.
- **v0.4.4 — nine leaves become two (shipped).** `dist/rekha.deps` told every consumer to vendor
  nine stdlib leaves for a bundle whose entire stdlib appetite is `strlen` + `memcpy`; it now says
  **`string`, `alloc`** and the WOFF sidecar says **`string`, `alloc`, `sankoch`** (was five).
  ⭐ **Not one line of bundle code changed** — both bundles differ from 0.4.3 only in the
  `# Version:` banner `distlib` stamps. This changes what a consumer has to resolve, not the code
  they get. `cyrius distlib` builds the sidecar from the
  include scan of `src/lib.cyr` unioned with `[deps].stdlib`, so both were trimmed and the harness's
  own leaves moved to a new `programs/prelude.cyr`, one hop outside the scan. `alloc` is not
  padding: `lib/string.cyr` calls `alloc()` and declares no include for it, which distlib's
  compile-verify pass found unaided. ⚠ MEASURED — re-adding one convenience `include "lib/fmt.cyr"`
  to `src/lib.cyr` takes the sidecar to **four** leaves with `distlib --check` staying green, so CI
  now pins the expected list. The positional nature of that fix is filed upstream
  (`cyrius/docs/development/proposals/2026-09-16-declare-test-only-stdlib-leaves-instead-of-hiding-them-from-the-umbrella-scan.md`).
- **v0.4.7 — CFF `seac` (shipped).** A four-argument `endchar` is an accented glyph built from two
  others: base at the origin, accent displaced by (adx, ady), both named by **Standard Encoding
  code** and resolved through the font's **charset** (formats 0 / 1 / 2 and the ISOAdobe default).
  It was an EMPTY glyph through 0.4.6.
  ⭐ **Checked against fontTools 4.65.0 on a font fontTools itself authored** — the composed outline
  is identical, point for point, which is what settles the one semantic question here: Type 1's
  `seac` had a fifth argument `asb`, Type 2's `endchar` form drops it and the accent goes at
  (adx, ady) directly.
  ⚠ **The dev-host corpus cannot check this one.** A re-survey found **0 of 406** CFF faces using
  `seac` — so unlike 0.4.2's outline differential, the evidence here is the fontTools font above and
  `programs/cff_test.cyr`'s group I (four charset shapes, the width form, and nine refusals), not a
  sweep. Said plainly because the absence is the interesting part: `seac` is a Type 1 relic.
  ⛔ Refused rather than guessed: an unassigned code, an SID no charset entry carries, the Expert /
  ExpertSubset predefined charsets (which rekha does not carry), a CID-keyed font (whose charset
  maps to CIDs, not SIDs), a component that is the glyph itself, and a component that is itself a
  `seac`. `REKHA_FONT_SIZE` grows 240 → 248 for the cached charset.
- **v0.4.6 — WOFF2 (shipped).** `rekha_font_open_woff2` opens a `.woff2` end to end: the container
  and its variable-length table directory, ONE Brotli stream through sankoch 2.8.0, the **glyf /
  loca** reverse transform (seven substreams, the triplet coordinate encoding, inferred and explicit
  bounding boxes, composites, the overlap bitmap) and the **hmtx** transform (left side bearings
  rebuilt from glyf's xMin), then a reassembled SFNT with every checksum and `checkSumAdjustment`
  RECOMPUTED, as the spec requires. `rekha_font_open_any` moved to `src/woff2.cyr` and now sniffs
  all three of `wOFF`, `wOF2` and a bare SFNT.
  ⭐ **MEASURED against an independent decoder on every WOFF2 on the dev host — 280 unique files
  (Liberation, KaTeX, Fira, Source Serif / Code, NanumBarunGothic, Xiaolai CJK), 111,732 glyphs:
  rekha's reconstruction and fontTools 4.65.0's are IDENTICAL for every glyph outline, advance and
  cmap mapping, with 0 failures to open.** rekha's rebuilt SFNTs total 0.46% more bytes than
  fontTools' (32,483,072 against 32,334,048).
  ⚠ A rebuilt glyf is **not** byte-identical to the original and cannot be — the spec says several
  encodings of one outline are valid. rekha's is deterministic and plain: one flag byte per point,
  no REPEAT run-length.
  ⚠ WOFF2 costs a consumer of `dist/rekha.cyr` **nothing**: it is in `[lib.woff]` only, beside
  WOFF 1.0, and the base bundle did not change a line. ⛔ Font COLLECTIONS (`ttcf`) are refused —
  item 8 below.
- **v0.4.5 — the toolchain moves, and two leaves become one (shipped).** `cyrius` **6.6.4 → 6.6.6**
  and `[deps.sadish]` **0.9.0 → 0.11.2**; `lib/` re-resolved against both. ⭐ **No rekha source
  changed** — all 24 RUN suites build and pass under `CYRIUS_DCE=0` and `1` with no build-log
  warning, and both bundles differ from 0.4.4 only in the `# Version:` banner. What the bump *did*
  do is move one consumer-visible number and expose two blind CI gates, all three fixed here:
  `dist/rekha.deps` now reads **`string`** alone (6.6.6's `lib/string.cyr` includes `lib/alloc.cyr`
  itself, so `alloc` arrives transitively instead of being re-added by distlib's compile-verify);
  the format gate stopped trusting `cyrius fmt --check`, which is a **measured false negative** on
  6.6.6; and the stale-`dist/` message now says `--all`, without which the `[lib.woff]` profile is
  left behind. ⚠ sadish **0.10.0 is an ABI break** — `SdPolyline` points went inline — and it does
  not touch rekha, VERIFIED: rekha consumes `sd_path_*` and never a flatten output.
- **v0.4.x line — next, in order:**
  1. ~~cmap formats 12 / 6 / 0 + symbol fonts~~ — shipped in 0.4.0, above.
  2. ~~WOFF 1.0~~ — shipped in 0.4.1, above.
  3. ~~OpenType/CFF (`OTTO`) outlines~~ — shipped in 0.4.2, above.
  4. ~~**WOFF2**~~ — shipped in 0.4.6, below. ⚠ One follow-up is filed, not forgotten:
     CI exercises WOFF2 over hand-emitted **stored** Brotli streams, because sankoch 2.8.0 decodes
     Brotli and does not encode it. Real compressed streams are covered only by the dev-host
     differential (280 files), which CI cannot run. When sankoch **2.8.1** ships its encoder, the
     suite gains a third, genuinely compressed container variant —
     `docs/development/issues/2026-09-20-revisit-woff2-test-with-a-real-brotli-encoder-when-sankoch-2-8-1-lands.md`.
  5. ~~`[deps].stdlib` trim~~ — shipped in 0.4.4, above.
  6. ~~Adopt the sadish filings as they ship~~ — done in 0.4.3: bounded flatten, checked path
     allocation and `sd_path_new_cap` all shipped in sadish 0.7.1–0.9.0 and are adopted here.
  7. ~~**CFF `seac`**~~ — shipped in 0.4.7, below.
  8. **TrueType Collections (`ttcf`)** and **CFF2** — a `.ttc` carries several faces in one file
     (CJK faces ship this way) and CFF2 is the variable-font charstring format.
- **after 0.4.x:** TrueType hinting (the `fpgm`/`prep`/glyph bytecode interpreter) for small
  sizes.

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
  requested **shipped** in the same release (item 4 of the v0.4.x line). ⚠ rekha does not exercise
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
