# rekha — Roadmap

> **Status:** stable — **1.1.1** (cyrius 6.7.18, sadish 0.12.1); the API frozen at 0.9.0 and
> promised for 1.x. Open filings: **1**, the WOFF2 encoder issue, unblocked and slotted in 1.1.2.
> **Next: 1.1.2, the P(-1) audit.** Every item of work has a release below. | **Last updated:**
> 2026-10-30
>
> This file is the **forward ladder**: **▶ Next**, then **▶ Scheduled**, every release pinned.
> Shipped history lives in [`CHANGELOG.md`](../../CHANGELOG.md), with the measurement each claim
> rests on; the capability summary is [`README.md`](../../README.md)'s *Scope*. Nothing shipped is
> re-listed here: a finished item leaves.
>
> Every item carries a `path:line` or a grep, because an item nobody can check is a wish. Line
> numbers are as of 1.1.1; the function or message named beside each one is the durable anchor.

## What 1.x means here

rekha's promise is **"what the glyph is"**: font bytes in, outlines and the numbers that place them
out, for `sadish` to fill. 1.0.0 shipped it complete, correct and frozen; 1.1.0 and 1.1.1 held the
surface byte-identical across the cyrius 6.7.9 and 6.7.18 pins (CHANGELOG). Through 1.x, from the
stability promise in [`docs/api/README.md`](../api/README.md):

- **a new function, constant or enum member** arrives only in a minor, **x.y.0**;
- **an answer measured wrong** against the font's own tables or against FreeType is a bug, fixed in a
  **patch**, with the measurement;
- **a divergence `docs/api/` states** (variable instances hinted off-reference, `hdmx` unread) moves
  only with a measurement on a real font;
- **a lenient hinting mode** can arrive only as a new, opt-in call (ADR 0002).

## How the ladder is kept

- **The order is committed; the numbers are not.** A toolchain or ecosystem release that has to land
  first takes the next patch number and shifts the rest, as 1.1.0 and 1.1.1 did.
- **New work does not go into a backlog.** It takes a slot: at the end of the unconditional lines
  (before the closeout), or ahead of something it outranks, with the reason written down. A 1.1.2
  finding that needs a new public call takes a slot in the line it fits.
- **A slot that adds a parser or a table reader ships with its own adversarial review** and rows in
  `programs/hostile_test.cyr`'s corpus and mutation loop. The full P(-1) recurs as **1.4.1**, the
  closeout over everything 1.2.0 – 1.4.0 added.
- **A slot marked *opens on request* waits for its entry condition.** When its turn comes without
  one, the next slot goes first and it keeps its number.

---

## ▶ Next — 1.1.2, the P(-1) audit (patch)

**Why now.** The last full audit was **0.3.11** (2026-09-15; CHANGELOG [0.3.11]: eight lenses, 88 raw
findings, every P0 / P1 reproduced by a running PoC before it was fixed, then a fresh review and
mutation testing). It covered **4 modules, 1,331 lines** — `error`, `sfnt`, `glyf`, `cmap`. `src/` is
now **13,175 lines**, and **16 modules arrived after it**: `hint.cyr` 4,680, `woff2.cyr` 1,605,
`cff.cyr` 1,436, `var.cyr` 478, `gvar.cyr` 456, `gpos.cyr` 366, `hvar.cyr` 320, `name.cyr` 290,
`vert.cyr` 249, `stat.cyr` 245, `kern.cyr` 226, `woff.cyr` 195, `cff2.cyr` 188, `os2.cyr` 149,
`post.cyr` 91, `freeze.cyr` 19 (`wc -l src/*.cyr`; `git show 0.3.11:cyrius.cyml`). Each shipped with
its suite, its refusals and, for hinting, FreeType's own outlines as the oracle — but no release since
has run a multi-lens adversarial review, and **the hostile suite's mutation loop mutates only the
embedded TrueType face** (the directory, `head` / `maxp` / `hhea`, `hmtx`, `loca`, `glyf`, `cmap`:
`programs/hostile_test.cyr`'s header). CFF, CFF2, the variation tables, GPOS / `kern`, and both web
containers — the two inputs most likely to arrive off a network — have never had a mutation sweep
(`grep -cin woff programs/hostile_test.cyr` → **0**).

A patch: it changes no surface. A fix that refuses an input a release accepted is named in the
CHANGELOG ([`SECURITY.md`](../../SECURITY.md)).

The P(-1), as sankoch and kashi run it (their `CLAUDE.md` § P(-1)), with 0.3.11's standard of proof:

0. **Read** CHANGELOG 0.3.11 → 1.1.1 and this file.
1. **Cleanliness** — CI's gates green at the pinned toolchain (they are at 1.1.1): `lint --strict`,
   formatting in place, `vet`, `distlib --check`, the API-surface gate and the private-bundle probes,
   zero-warning builds under both DCE modes, the aarch64 and AGNOS links.
2. **Baseline** — `programs/bench_hotpath.cyr` (medians of interleaved runs) and binary sizes, into
   the dossier.
3. **Internal deep review** — one read-only adversarial lens per surface; every finding reproduced by
   a probe before it is fixed (a sentinel differential or a guard page, as 0.3.11 proved its four
   overreads):
   - the hint interpreter (`src/hint.cyr`): stack, zone, storage and `cvt ` bounds; the 1,000,000
     instruction budget and call depth 64 (`:110-111`); twilight sizing; composites; the glyph-range
     rules;
   - CFF and CFF2 charstrings (`src/cff.cyr`, `src/cff2.cyr`): INDEX offsets, the argument stacks
     (48 / 513), subroutine recursion, `seac`, `blend`, FDSelect, the Private DICTs;
   - the containers (`src/woff.cyr`, `src/woff2.cyr`): the table directories, the size and ratio
     caps, the `glyf` / `loca` and `hmtx` transforms, the triplets, the `loca` rebuild, collections;
   - variations (`src/var.cyr`, `src/gvar.cyr`, `src/hvar.cyr`): `fvar` / `avar`, the
     ItemVariationStore and DeltaSetIndexMap readers, packed points and deltas, tuple counts, MVAR;
   - layout, metrics and names (`src/gpos.cyr`, `kern.cyr`, `vert.cyr`, `os2.cyr`, `name.cyr`,
     `post.cyr`, `stat.cyr`): coverage and class tables, offset chains, the UTF-16 and Mac Roman
     decoders;
   - the boundary: the `private` bundle against `docs/api/`, the sidecars, and 0.3.11's classes
     re-checked against today's `sfnt` / `glyf` / `cmap`.
4. **External research** — OpenType specification revisions, and FreeType's and google/woff2's
   security fixes since each module was written, checked class by class against rekha's code.
5. **The dossier** — `docs/audit/<date>-1.1.2-p-1.md`, rekha's first audit directory (0.3.11's record
   is its CHANGELOG entry): findings graded HIGH / MEDIUM / LOW / INFO, each with its resolution or a
   slot below; linked from `SECURITY.md`. **Done**:
   [`docs/audit/2026-10-30-1.1.2-p-1.md`](../audit/2026-10-30-1.1.2-p-1.md). Its pass over the
   review's unproven leads found a third HIGH (the WOFF2 `hmtx` transform's `loca` read), and its
   *Not covered* names what the next audit starts with.
6. **Tests from findings, and the tools the review needs** — each mutation-checked (the fix removed,
   the test seen to fail):
   - the mutation loop extended past the TrueType face: a CFF face, a CFF2 variable face, a `gvar` /
     HVAR face, a WOFF and a WOFF2, built in code as the suites build them; **done**:
     `programs/mutate_test.cyr`, seven seeds, the harness shared with hostile_test through
     `programs/hb_harness.cyr`. Its first run found the WOFF2 size cap (`REKHA_WOFF2_MAXSIZE`);
   - **a genuinely compressed WOFF2** through `programs/woff2_test.cyr`: sankoch 2.8.9's
     `brotli_compress` / `brotli_compress_level` are in the pinned stdlib's `lib/sankoch.cyr`
     ([the WOFF2 encoder issue](issues/2026-09-20-revisit-woff2-test-with-a-real-brotli-encoder-when-sankoch-2-8-1-lands.md),
     unblocked at 1.1.1). ⚠ sankoch's encoder through sankoch's decoder is a round trip, not an
     independent check; the issue names the reference-encoder fixture as the maintainer's call;
     **done**: groups A, B, R and G run a third time over `brotli_compress` streams (293 checks);
   - **`poison_alloc` through the `sd_alloc` seam** (cyrius 6.6.18, P6): `lib/poison.cyr`'s leading
     and trailing redzones and A/B differential, installed with sadish's `sd_alloc_set` around the
     mutation loop (an overwrite stops the harness with exit 86), beside the hand-built 4,096-byte
     redzone differential it complements; **done**: `pz_hook` in `programs/hb_harness.cyr`, a
     poisoned allocator over a growable arena reset after every mutant, one extra sweep per mutant
     in both loops (hostile_test 8.6 s → 13.2 s). Measured: an outline block or a rebuilt WOFF2
     one byte short — CFF, simple glyf, composite merge, WOFF2 — each stops the run with 86;
   - **the bounds-checked mode** (cyrius 6.7.8, `--bounds` / `[build] bounds`) counted against
     `src/`: it checks subscripts of typed arrays, `*T` and slices, and rekha's reads are
     overwhelmingly `load8` .. `load64` on computed addresses (1,448 sites) beside a few dozen
     fixed-size typed-array locals (`var m: i64[6]`, `src/cff.cyr:498`). Decide whether it earns a
     CI leg. **Decided: no leg.** MEASURED at 1.1.2: `--bounds` grows every binary by the same
     40 bytes (smoke 23,296 → 23,336, cff_test 232,808 → 232,848, hostile_test 739,424 → 739,464) —
     its runtime handler and not one check, because rekha reads through `load8` .. `load64` on
     computed addresses (1,350 sites) and reaches its 75 typed-array locals by address arithmetic,
     neither of which the mode sees. The suites pass under it unchanged. Revisit if `src/` ever
     indexes a typed array by subscript.
7. **Post-review benchmarks** — the fixes cost what the dossier says they cost.
8. **Documentation audit** — README, CONTRIBUTING, SECURITY, `docs/api/`, the ADRs, and the source
   comments that cite this file.
9. **Scaffold** — the same pass's cleanup:
   - **the nine internals with no call site** (execution coverage, 1.1.1): the seven table-directory
     accessors `rekha_w2_ent_tag` .. `rekha_w2_ent_ooff` (1.1.1: `src/woff2.cyr:182-188`),
     `rekha_hint_trig_atan` (1.1.1: `src/hint.cyr:3834`; `rekha_hint_vlen` keeps no angle, `:3850`)
     and `rekha_cff2_regions` (1.1.1: `src/cff2.cyr:74`) — each removed or given the caller it was
     written for.
     None is public; **done**: all nine removed — each one's fields or values are read inline where
     they are needed, and `rekha_hint_vlen` keeps no angle for the table to serve;
   - **the harness's eight leaves into a `[test] stdlib`** (cyrius 6.7.6): today they resolve partly
     from `lib/` (`syscalls`, `alloc`, `string`) and partly from the toolchain snapshot, recorded only
     in `programs/prelude.cyr`. CI's leaf pin proves nothing leaks into a sidecar either way.
     **Done**: `cyrius.cyml` `[test] stdlib` names the eight plus `sync` / `sankoch`. MEASURED at the
     6.7.18 pin: `lib/` 17 → 36 files, all in `cyrius.lock`; every program's binary byte-identical;
     `dist/*.deps` unchanged (cyrius keeps a `[test]` leaf out of builds and sidecars);

**Known going in** — found while writing this ladder, each checked:

- ⛔ **A CFF / CFF2 charstring refusal answers `REKHA_OK`.** `rekha_cff_load` returns
  `rekha_outline_empty()` on `RC_BAD` without recording a code (`src/cff.cyr:1577`, the sites at
  `:827`, `:926`-`:1107`), so `rekha_load_glyph` hands back a blank and a clean error slot — where
  `docs/api/outline.md` (`rekha_load_glyph`) and `src/glyf.cyr:656` promise *"REKHA_OK then means the
  blank was real"*. A documented answer measured wrong: a fix, here. **Fixed:** `rekha_cff_refused`
  names it — OOM `"point cap"` / `"operator budget"`, else BAD_GLYF `"charstring"`
  (`programs/cff_test.cyr`).
- **The sadish floor is stated two ways**: `docs/api/README.md:116` says 0.11.2; `README.md:309` and
  `cyrius.cyml:123` say 0.9.0. One is the fact. **Fixed:** 0.9.0 — `docs/api/README.md`'s 0.11.2
  was the pin at the freeze. MEASURED: `programs/dist_test.cyr` links and passes from sadish 0.7.1
  (0.7.0 has no `sd_path_new_cap`, which README dated 0.7.2); README and `cyrius.cyml` now say both.
- **Two stale citations of this file**: `src/var.cyr:12` says HVAR and MVAR *"are not read"*
  (`rekha_mvar_delta` is `src/hvar.cyr:392`, shipped 0.6.0); `scripts/metrics_var_diff.py:198` says
  rekha does not read `name` (shipped 0.6.2). **Fixed**, with three more headers the audit found
  stale (`src/os2.cyr`'s `post`, `src/hvar.cyr`'s map list, `src/var.cyr`'s DeltaSetIndexMap).

**Exit:** every HIGH and MEDIUM fixed here with a regression test; each LOW and INFO fixed or given a
slot below; the dossier committed and linked.

---

## ▶ Scheduled — the 1.x ladder

### 1.2.x — the formats still refused or skipped

#### 1.2.0 — variation selectors (minor)

- **`rekha_char_variant_to_glyph`** — `cmap` format 14, default and non-default UVS, as the supplement
  beside the primary map. Excluding format 14 as a PRIMARY map is correct and stays
  (`src/cmap.cyr:39`, `:117` — `enc == 5` ranks −1). Without the supplement, U+FE0E / U+FE0F
  presentation selectors and CJK ideographic variation sequences resolve as base + `.notdef`.

#### 1.2.1 — the reference differentials in CI (patch)

First in the line so that every format slot after it is measured by a standing oracle, not a dev-host
one-off.

- **The three self-building sweeps** already committed need fontTools and nothing else —
  `scripts/cff2_wide_diff.py` (550 points over 100 glyph instances), `scripts/cff_fontmatrix_diff.py`
  (12 matrices), `scripts/metrics_var_diff.py` (88 metric values over two axes): a scheduled workflow
  runs them.
- **The hinting oracle**: CI's Ubuntu ships FreeType 2.13.2, the vectors were recorded on 2.14.3, and
  `scripts/ftshim.py` refuses anything but 2.14.x — so `programs/hint_unit_vectors.cyr` and
  `programs/hint_glyph_vectors.cyr` are transcriptions regenerated by hand, and the whole-face sweep
  (`scripts/hint_glyph_diff.py sweep`, 26,200 loads, 0 differ) never runs in CI. A pinned 2.14.x build
  in the scheduled job turns both into regenerate-and-diff gates.
- **The corpus sweeps** — CFF (405 faces, 5,093,070 glyphs), WOFF2 (280 files, 111,732 glyphs),
  `cmap` (92 faces), the 165 + 50 hinted host faces — need fonts that are not committed (size,
  licensing). Decide on a licence-clean mini-corpus with committed digests, or record why not.

#### 1.2.2 — `cmap` formats 2, 8 and 10 (patch)

- Candidates ranked **below every current one** (`src/cmap.cyr`, the candidate validator), so no
  font's chosen subtable moves. A font carrying only one maps nothing today. Format 2 is legacy CJK
  multi-byte; 8 and 10 are near-extinct.

#### 1.2.3 — the last CFF refusals about missing data (patch)

- **The Expert and ExpertSubset charsets**: a `seac` on a font that uses one is refused because rekha
  does not carry the two tables (`src/cff.cyr:666`), not because the font is malformed.
- **CFF2 FDSelect format 4**, the 32-bit-gid form, refused today (`src/cff2.cyr:34`, *"an FDSelect in
  a format other than 0 or 3"*). No observed font needs it.

#### 1.2.4 — `kern` format 2 (patch)

- The two-dimensional class array (`src/kern.cyr:31-32`: *"Format 2's two-dimensional class array is
  rare and is not read"*). A font with
  one beside a format 0 kerns from the format 0 today; none of the 16 host `kern` fonts needed it.

1.2.2 – 1.2.4 each turn a refusal or a skip into the font's own answer — fixes, measured against the
font's tables (fontTools) and against FreeType, in patches.

### 1.3.x — what a composite and a variable font mean for metrics

#### 1.3.0 — the resolvers beside the O(1) readers (minor)

- **An advance resolver** that decodes the glyph when it must: `USE_MY_METRICS` (0x0200) on a
  composite, and `gvar`'s phantom-point advances on a face with no HVAR / VVAR (FreeType's rule).
  `rekha_advance_width` (`src/sfnt.cyr:671`) stays the frozen `hmtx` index measured at 47 ns (0.3.11);
  the hinted path already answers both (`src/hint.cyr:4151`; `rekha_gvar_apply_n`,
  `src/gvar.cyr:299`, notes `:25-35`).
- **A right-side-bearing accessor** that applies HVAR's rsb map, which rekha reads past today
  (`src/hvar.cyr:38`).
- **GPOS kerning that follows the axes**, as a NEW call: Device and VariationIndex deltas through
  GDEF's ItemVariationStore (`rekha_ivs_delta`, `src/hvar.cyr:91`, exists since 0.6.0; GDEF is the
  missing reader, `src/gpos.cyr:37-40`). The frozen `rekha_gpos_kern` documents them unapplied
  (`docs/api/kern.md`).

#### 1.3.1 — `avar` 2.0's variation store (patch)

- The DeltaSetIndexMap reader 0.6.0 built for HVAR, wired into `avar` 2.0's mapping
  (`src/var.cyr:23-29`; the segment maps already apply). An `avar` 2.0 font's normalised coordinates
  are wrong against its own tables until then — a fix, measured with fontTools as
  `scripts/metrics_var_diff.py` measures the rest.

### 1.4.x — the web containers, completed

#### 1.4.0 — the opens say why; metadata; one inflate per collection (minor)

- **`_why` twins for the container opens** — `rekha_font_open_woff` (`src/woff.cyr:185`),
  `rekha_font_open_woff2` / `_index` / `rekha_font_open_any` (`src/woff2.cyr:1589-1615`) — as 0.7.0
  gave `rekha_font_open` and `_index` theirs (`src/sfnt.cyr:295`, `:344`). They are the deepest
  pipeline in the library and answer a bare 0 (ADR 0004, ADR 0006).
- **Accessors for the metadata and private blocks**, which both readers validate for position only
  (`src/woff.cyr:35`, *"validated for position only and not copied"*; `src/woff2.cyr:48`) and the
  rebuilt SFNT never carries.
- **A cached decoded-collection handle**: `rekha_font_open_woff2_index` rebuilds the whole file per
  call (`src/woff2.cyr:1583`), so opening every face of an *n*-face collection inflates it *n* times,
  and `sd_alloc` has no free. The documented two-step (decode once, then `rekha_font_open_index`)
  stays.

#### 1.4.1 — the 1.2 – 1.4 closeout P(-1) (patch)

- 1.1.2's P(-1) over everything 1.2.0 – 1.4.0 added: `cmap` 2 / 8 / 10 / 14, the Expert charsets and
  FDSelect 4, `kern` format 2, the GDEF reader, the resolvers, `avar` 2.0, the container accessors and
  the collection cache — each new reader in the mutation loop, its dossier beside 1.1.2's.
- What 1.1.2's review did not finish (its dossier, *Not covered*): a second round for the
  containers, layout and names, the hint machine and research lenses, the *loop until dry* and
  *completeness critic* stages, and a `mutate_test` WOFF2 seed whose `hmtx` is transformed over a
  null-transformed glyf / loca — the shape behind 1.1.2's third HIGH.

### Opens on request — 1.5.x onward

Each line below waits for its entry condition and keeps its number while it waits.

#### 1.5.0 — hinting the way a consumer asks (minor) — *opens when a consumer needs a glyph rekha draws unhinted fitted the way FreeType fits it*

- **FreeType's default-mode fallbacks in the glyph range only** (`HC_RANGE` 4, `src/hint.cyr:223`):
  `RCVT` past the table reads 0 (ref2143/ttinterp.c:2861-2868), a short stack reads zeros, a bad point
  is skipped, and a refusing component keeps its partial hinting instead of unhinting the whole glyph.
  A NEW opt-in call on the hinting context; `rekha_hint_glyph`'s answer stays (ADR 0002). The measured
  case: 17,158 of 2,812,516 loads (0.61%) over 50 host faces, none ASCII; AdwaitaMono-Regular refuses
  2,624 of 8,818 glyphs at 9 of 25 ppems (its arrows at 9 ppem).
- **`GETINFO` answers a consumer can set** — rotated, stretched, ClearType, the version — fixed today
  (`rekha_hint_op_getinfo`, `src/hint.cyr:2080`), so a consumer applying its own transform cannot tell
  the font.
- **An `hdmx`-aware hinted advance**, as a new call beside `rekha_hint_advance_px` (`src/hint.cyr:4598`,
  `:4604`; ref2143/ttgload.c:2302-2313): on a synthetic face 4 of 4 advances differ at the listed
  ppem; 0 of 1,751 host `glyf` fonts carry the table.
- **Raisable load ceilings** — the five composite caps and the `gvar` work budget are internal
  constants (`src/glyf.cyr:133-137`, `REKHA_GVAR_MAXWORK` in `src/gvar.cyr`). A trip already
  reports `REKHA_ERR_OOM` named `"point cap"` / `"contour cap"` / `"glyph load cap"` / `"gvar budget"`
  (`docs/api/errors.md:19`, `docs/api/outline.md`); a consumer cannot raise them. **One host glyph
  trips one**: U+E783 in CodeNewRoman Nerd Font (a devicon, 4,220 points / 35 contours) is refused
  `"point cap"` in all 9 of its faces, where FreeType draws it — the only refusal of any code in
  every glyph of the host's 2,155 faces (1.1.2 sweep; through 1.1.1 it came back blank with
  `REKHA_OK`). Nothing else comes near: 1,129 hinted faces nest at most 5 deep and load at most 17
  glyphs; the `gvar` budget refuses 0 of 11,676 loads on the two `gvar` faces at their axis
  extremes; the most contours is 185.

#### 1.5.1 — variable instances hinted on reference (patch) — *opens with a hinted `gvar` face to measure (none on the host)*

- `cvar`; `gvar` deltas rounded once on 16.16 instead of per tuple from whole units (`src/gvar.cyr`);
  `prep` re-run only when the face has `cvar` (`rekha_hint_axes_changed`, `src/hint.cyr:901`;
  ref2143/ttgxvar.c:3993-3997); `GETINFO`'s variation bit and `GETVARIATION`'s gate as FreeType keeps
  them (`:2074`, `:2151`); the HVAR lsb delta on the hinted pp1 (`rekha_hint_hmetrics`, `:3627`;
  FreeType leaves `lsb_adjust` NULL, ref2143/ttdriver.c:559). `docs/api/hint.md` states the instance
  off-reference; it moves with the measurement, as a fix.

#### 1.6.0 — the default face as a profile (minor) — *opens with a consumer that would rather not vendor a generated `.cyr`*

- cyrius 6.6.19's `[embed]` (P2): `[embed] REKHA_FACE = "fonts/<face>.ttf"` and a `[lib.face]` profile
  producing `dist/rekha-face.cyr`, re-exporting the same ten names from an accessor module. ⛔ ADDED
  beside `fonts/face_data.cyr`, which stays — its path and ten accessors are frozen
  (`docs/api/open.md`, *The embedded default face*; agnos consumes it by path) — and so does
  `scripts/face2cyr.py`. ⚠ Measure first: a plain `[embed]` rides in every binary of this project
  (the 410,820 B face in each test binary) and shares cycc's 2 MiB string pool; cyrius refuses an
  `[embed]` name any stdlib leaf already declares (sankoch 2.8.3's notes).

#### 1.7.0 — colour, version 0 (minor) — *opens when a consumer asks (emoji in a UI toolkit)*

- **`COLR` v0 + `CPAL`**: a base glyph's layer list and palette entries, emitted as several `SdPath`s
  with an RGBA each — *N* of the outlines rekha already produces, through the existing seam.

#### 1.8.0 — readers shaped by a consumer (minor) — *each row opens when a consumer writes the loop itself*

- **GPOS script and language selection**: rekha takes the union of every `kern` feature's lookups
  (`src/gpos.cyr`'s header). Doing it properly puts a script and a language on the API — a design
  question before it is a walk.
- **`STAT` style-name synthesis**: which values apply, the `axisOrdering` sort, the elidable names
  (`src/stat.cyr`'s header) — the consumer's, like `rekha_use_typo_metrics`, until two consumers
  write the same loop.
- **`post` glyph names**: format 2.0's index and the 258-name Macintosh standard order
  (`src/post.cyr:23`) — for tooling (PDF export, a debugger naming the glyph that failed); nothing
  rekha draws needs one.
- **A vertical origin derived when a font states none**: with no `VORG` the convention derives one
  from the bounding box and the top side bearing; rekha answers 0 and says so
  (`rekha_vorg_present`, `src/vert.cyr:212`), because a derived origin is a plausible wrong height for
  every glyph in a run. Wants a bbox accessor beside it.

#### 1.9.0 — the two questions that need a decision first — *opens with the decision*

- **CFF hinting**: `src/cff.cyr` parses `hstem` / `vstem` / `hintmask` for stem COUNT — enough to know
  how many mask bytes follow — and discards the hints, so "hinting" is two jobs and only TrueType's has
  been done. An ADR first (whether rekha hints CFF at all, and against which reference), then the
  slot.
- **`COLR` v1**: gradients, composites and transforms need paint capability sadish does not have. When
  a consumer asks, it is filed as a proposal in sadish (`docs/development/proposals/`) and this slot
  waits on it under *Blocked on a sibling*.

---

## Standing divergences from FreeType 2.14.3 — recorded decisions

Stated at each site, in CHANGELOG 0.8.1 / 0.8.2, and in `docs/api/hint.md`. They are decisions, not
work: kept for 1.x unless a slot above names them. The source comments that say *"pinned in
docs/development/roadmap.md"* point here. `src/hint.cyr` unless another file is named.

| divergence | where | stands as |
|---|---|---|
| **Refuses** what FreeType's default mode reads as 0 or skips: a control value past the table, a point outside its zone, a storage index, a short stack — the glyph reloads scaled and unhinted, named through `rekha_hint_error` | `"RCVT index"` `:2013`; `"MIAP cvt"` / `"MIRP cvt"` `:2670`, `:2939`; `rekha_hint_pt_ok` `:1203`; `rekha_hint_op_mem` `:1987`; `"stack underflow"` `:616` | kept (ADR 0002, confirmed for 1.x at 1.0.0); opt-in alternative → **1.5.0** |
| A program refusal unhints the **whole** glyph, where FreeType keeps a partially hinted component | `:3596-3598`; the file header, `:26-27` | kept; → **1.5.0**'s opt-in mode |
| `SHZ` in a NESTED composite's program: FreeType walks `first_point` slots past its contours and writes past its points array; rekha **clamps** at the sub-zone's end | `rekha_hint_op_shz` `:2485`; `rekha_hint_first_point` `:1075`; unit rows `comp_nested_first_point`, `comp_nested_shz_low` | kept — FreeType's is an out-of-bounds write |
| FreeType's composite recursion cap of 100 is not modelled; the outline loader's caps apply and the zone is sized from `maxp` | `src/glyf.cyr:133-137`; `REKHA_HINT_MAXZONE` `:308`; `"glyph zone cap"` / `"contour cap"` `:943-944` | kept; on 1,129 hinted host faces they refuse nothing |
| The **scan-type bits** FreeType ORs into an instructed glyph's first tag byte are not kept | `rekha_hint_outline`'s header, `:4557` | kept; the oracle masks with 0x19 |
| **`hdmx` is not read** | `:4598`, `rekha_hint_advance_px` `:4604` | → **1.5.0** (a new call) |
| **Variable instances are hinted off-reference** (no `cvar`, per-tuple rounding, `prep` re-run on every axis change, the variation bit, the lsb delta on pp1) | `rekha_hint_glyph`'s header `:4398`; `rekha_hint_axes_changed` `:901`; `:2080`, `:2157`, `:3639` | → **1.5.1** |
| A `REPEAT` count past the last point is **clamped** — a leniency: FreeType refuses the glyph (ref2143/ttgload.c:451-452) | `src/glyf.cyr:250-254` | kept |
| Three `loca` rules FreeType sanitizes are **refused**: offsets running backwards, the last glyph's end past `glyf`, any other end or start past it | `rekha_glyf_span`, `src/sfnt.cyr:784`; refusals `:771-776` | kept; empty on every face measured |
| An `OS/2` shorter than 78 bytes is absent to rekha, so `hhea` decides the vertical phantoms | `rekha_hint_vmetrics` `:3683` | kept — the saner rule |
| **Glyph-only bytecode is not run**: no non-empty `fpgm` / `prep` / `cvt ` answers `NO_TABLE "hint tables"`, where FreeType's default load autohints (ref2143/ftobjs.c:1006-1016) | `rekha_hint_present` `:383` | kept — rekha has no autohinter |
| A composite's `n_ins` or bytes past its `loca` span refuse `TRUNCATED "composite instructions"`; the twilight bound has no +4 band and is the running minimum in one load; org is filled and the phantom tags are 0 when no program runs | `:4262`; `rekha_hint_twilight_bound` `:3471`; `HC_TWCAP` `:254` | kept; the last is observed by nothing |
| A point, contour or reference index ≥ 65536 is **refused**, where FreeType's `FT_UShort` cast wraps it | `rekha_hint_pt_ok`'s comment, `:1198` | kept; only stack arithmetic reaches it |
| A backward jump before a function's own start is **refused** | `"jump out of range"` `:3249` | kept |
| The twilight zone is zeroed with its tags and font-unit positions per `prep`; a face whose `prep` is absent gets the default graphics state where 2.14.3 saves a stale one | `rekha_hint_run_prep` `:3539` (comment `:3533`) | kept — the second is a FreeType defect |
| FreeType's `LOOPCALL` / backward-jump caps and call depth 32 are not modelled: one budget of 1,000,000 instructions and a depth of 64 | `:110-111`; `rekha_hint_exec` `:3161`; `rekha_hint_call` `:3398` | kept |
| `INSTCTRL`'s operand order is unobserved in the corpus (the one real site pushes `1 1`); bits 1 and 2 follow `tt_loader_init`'s order on the glyph path | `:87`, `:1905-1914`; `rekha_hint_load_instctrl` `:4335` | kept |
| `GETINFO`'s answers are fixed: version 35, no ClearType, not rotated, not stretched, grayscale — 0 inside `fpgm`, as FreeType has it | `rekha_hint_op_getinfo` `:2080` | → **1.5.0** |
| CI's FreeType is 2.13.2, the vectors' 2.14.3 | the headers of `programs/hint_unit_vectors.cyr` and `programs/hint_glyph_vectors.cyr` | → **1.2.1** |
| A `gvar` glyph offset array that runs **backwards** is refused — the table is not read — where FreeType raises the entry to the running maximum (ttgxvar.c:1901-1923) | `rekha_gvar_resolve`, `src/gvar.cyr:534` | kept — the `loca` rule above; no host face has one |
| An `avar` map is applied without the spec's −1 / 0 / +1 anchors, as FreeType applies it; a fromCoordinate that does not increase leaves the coordinate **unmapped**, where FreeType divides by the difference | `rekha_var_avar`, `src/var.cyr:171` | kept (1.1.2 audit) |
| A CFF `hintmask` that brings stems of its own after the mask is in force is **refused**: FreeType reads no mask bytes there and runs them as operators | `src/cff.cyr:1013` | kept (1.1.2 audit) |
| A CFF `endchar` with six or more operands after the width is **refused**, where FreeType takes a `seac` of the top four | `src/cff.cyr:1064` | kept (1.1.2 audit) |
| An outline past **4,096 points** is refused (OOM `"point cap"`); FreeType has no such cap. One host glyph trips it: CodeNewRoman Nerd Font's U+E783, 4,220 points, in 9 faces | `src/glyf.cyr:133` | → the raisable load ceilings item (1.x) |
| Every interpreter arithmetic result is **clamped** to TrueType's 32-bit range, where FreeType on LP64 keeps FT_Long values whole — a value past 2^31 that a later `DIV` brings back draws differently | `REKHA_HINT_CLAMP` `:118`; `rekha_hint_push` | kept — reached only by bytecode that leaves the 32-bit range (1.1.2 audit) |

---

## Blocked on a sibling

The rule: a missing sibling capability gets a filed proposal plus a line here — never "off the list".

| waiting on | filing | status |
|---|---|---|
| *(none open)* | | |

`COLR` v1 (1.9.0) files its sadish proposal the day a consumer asks for it.

⭐ **Closed, for the record:** the WOFF2 encoder filing was unblocked at 1.1.1 (sankoch 2.8.4 shipped
the encoder; the 6.7.18 stdlib carries 2.8.9) and is slotted in 1.1.2. Both earlier rekha filings
against sankoch shipped in 2.8.0 — the Brotli decoder and the profile bundles that could not link —
and all three against cyrius shipped: the test-only-leaf channel (6.6.18 option 2, ADR 0010), RUN
programs as a coverage corpus (6.6.17), and `fuzz --poison` following a custom allocator seam
(6.6.18; adopted in 1.1.2).

## Out of scope — committed

Non-goals. Taking one on would change what rekha is.

- **Text shaping and layout** — GSUB, GPOS beyond pair kerning, BiDi, complex-script reordering, line
  breaking. rekha hands back outlines and advances; a shaping library consumes them. ⚠ **No such repo
  exists in the AGNOS stack yet**, and no slot is reserved for one — the siblings are a rasterizer, a
  bitmap-font provider, two tokenizers, a language corpus and a TTS grapheme-to-phoneme engine. That
  is a stack gap worth its own proposal when a consumer needs it, not a rekha item.
- **Rasterization, anti-aliasing, subpixel** — `sadish`. rekha owns *what the glyph is*, sadish owns
  *how it becomes pixels*, and the seam is the whole design.
- **Bitmap glyph sources** — `kashi` (PSF1 / PSF2, VGA-ROM, BDF, PCF). This includes the strikes
  embedded in OpenType files (`EBDT` / `EBLC` / `EBSC`, `CBDT` / `CBLC`, `sbix`): they are PNG and
  bitmap data, not outlines, and rekha is the *outline* half of the pair.
- **The `SVG ` table** — needs an SVG renderer, which is neither rekha nor sadish.
- **`MATH`** — math typesetting is a document engine's capability, with no AGNOS consumer.
- **PostScript Type 1 (`.pfa` / `.pfb`) and bare CFF files** — Type 1 is a dead format; a bare CFF
  has no `cmap`, no `hmtx` and no `head`, so it cannot drive rekha's own API.
- **Subsetting and font writing** — rekha is a reader. It emits SFNT bytes only to rebuild a container
  it was handed (`rekha_woff_decode`, `rekha_woff2_decode`).
- **A glyph → Unicode reverse map** — the forward direction answers the question consumers actually
  ask; reverse mapping serves text extraction, which nothing here does.

## What moves the ladder

- **A consumer hits a pinned item in a real font and can show it** — its slot moves up, with the
  reason written here.
- **A CVE or an audit finding** against a format rekha parses — it takes the next patch number.
- **A toolchain or ecosystem release that has to land first** — the next patch number, the rest shift.
- **An entry condition is met** — a consumer for 1.5.0 – 1.8.0; a hinted `gvar` face for 1.5.1; the
  ADR for CFF hinting or a consumer for `COLR` v1 (1.9.0).
- **A hinted `hdmx` or `gvar` face turns up in the wild** — neither exists on the host, so 1.5.0's
  `hdmx` row and 1.5.1 were stated from the sources and a synthetic font, never measured on a real
  one.
- **A shaping library appears in the stack** and needs something from rekha that is not here.

## Where to look for…

- **Release history, with the measurements** → [`../../CHANGELOG.md`](../../CHANGELOG.md)
- **What rekha reads today** → [`../../README.md`](../../README.md), *Scope*
- **The API and its promise** → [`../api/README.md`](../api/README.md)
- **The threat model and supported versions** → [`../../SECURITY.md`](../../SECURITY.md)
- **Open filings** → [`issues/`](issues/)
- **The dependency floors and why** → [`../../README.md`](../../README.md), *Dependencies*
