# Hinting

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

The interpreter runs a TrueType face's own bytecode — `fpgm` once per face, `prep` once per
size, the glyph program per glyph — the way FreeType 2.14.3's classic interpreter does
([ADR 0007](../adr/0007-freetype-as-the-hinting-oracle.md)), and hands back the outline the
bytecode intended. This layer rounds **half away from zero** where the rest of rekha rounds
half up ([ADR 0005](../adr/0005-the-rounding-split.md)); it works in F26Dot6 (64 = one pixel),
and `rekha_hint_to_sdpath`'s scale of 1024 turns that into sadish's 16.16 exactly.

## The five rules

1. **`gasp` is the consumer's.** `rekha_should_gridfit(font, ppem)` says whether the font wants
   hinting at this size; `rekha_hint_glyph` hints whenever asked, as FreeType's loader does.
2. **Warm the context outside a per-frame hook.** `rekha_hint_ctx(font, ppem)` is a lazy
   allocation cached on the handle (`fpgm` run on the first build, `prep` on every size change);
   on a variable face load one glyph outside the hook too. After that a hinted glyph costs 0 B.
   After an axis change call it again: the setters mark it stale and it re-runs `prep`. It is
   the one call that still answers the handle on a **standing** `fpgm` / `prep` refusal — the
   refusal is a property of the size, re-raised on every call.
3. **`rekha_hint_glyph(ctx, gid)`** answers 1 when the zone holds what the bytecode intends and
   0 in three ways `rekha_hint_error` tells apart: a standing refusal (zone empty — draw the run
   unhinted), a **program** refusal (the glyph reloaded scaled and unhinted, so outline, path
   and advance still answer), or a structural one (bad gid, record or cap — zone empty,
   `rekha_hint_gid` −1). A refused program never draws a partially hinted glyph.
4. **Whole-pixel origins.** `rekha_hint_to_sdpath(ctx, ox, oy)` and `rekha_hint_outline(ctx)`
   (a view valid until the next `rekha_hint_glyph`, `rekha_hint_run_prep` or size change) place
   the glyph with its left phantom at the origin; pass `ox` / `oy` on whole pixels or the fit
   is lost.
5. **The advance is per glyph.** `rekha_hint_advance_px(ctx)` is what the program fitted the
   glyph to, in whole pixels — not `rekha_glyph_advance_px`.

## Frozen as measured, and what is not read

rekha refuses where FreeType's default mode reads a missing control value as 0 or skips a bad
point — 17,158 of 2,812,516 loads (0.61 %) across 50 host faces at four sizes, none of them
ASCII; every such glyph draws scaled and unhinted ([ADR 0002](../adr/0002-refuse-dont-guess.md)).
A variable instance is hinted off-reference — no `cvar`, and `prep` re-runs on every axis
change where FreeType re-runs it only for a face with `cvar`; the default location is
bit-exact. `hdmx` is not read. CFF's own hints are parsed for stem count and discarded.

## Constants

### The graphics-state fields of `rekha_hint_gs`

⛔ Frozen with their values — the index IS the slot order.
| name | value | meaning |
|---|---|---|
| `REKHA_GS_PVX` | 0 | projection vector, F2Dot14 |
| `REKHA_GS_PVY` | 1 |  |
| `REKHA_GS_FVX` | 2 | freedom vector |
| `REKHA_GS_FVY` | 3 |  |
| `REKHA_GS_DVX` | 4 | dual projection vector |
| `REKHA_GS_DVY` | 5 |  |
| `REKHA_GS_RP0` | 6 | the three reference points |
| `REKHA_GS_RP1` | 7 |  |
| `REKHA_GS_RP2` | 8 |  |
| `REKHA_GS_ZP0` | 9 | the three zone pointers: 0 twilight, 1 glyph |
| `REKHA_GS_ZP1` | 10 |  |
| `REKHA_GS_ZP2` | 11 |  |
| `REKHA_GS_LOOP` | 12 |  |
| `REKHA_GS_ROUND` | 13 | one of the REKHA_RND_* states |
| `REKHA_GS_PERIOD` | 14 | SROUND's decomposition, all three F26Dot6 |
| `REKHA_GS_PHASE` | 15 |  |
| `REKHA_GS_THRESHOLD` | 16 |  |
| `REKHA_GS_MINDIST` | 17 | F26Dot6 |
| `REKHA_GS_CVTCUTIN` | 18 | F26Dot6 |
| `REKHA_GS_SWCUTIN` | 19 | F26Dot6 |
| `REKHA_GS_SWVALUE` | 20 | F26Dot6, scaled from font units by SSW |
| `REKHA_GS_AUTOFLIP` | 21 |  |
| `REKHA_GS_DELTABASE` | 22 | unsigned 16-bit, as SDB stores it (FreeType's FT_UShort delta_base) |
| `REKHA_GS_DELTASHIFT` | 23 |  |
| `REKHA_GS_INSTCTRL` | 24 |  |
| `REKHA_GS_SCANCTRL` | 25 |  |
| `REKHA_GS_SCANTYPE` | 26 |  |
| `REKHA_GS_COUNT` | 27 |  |

### The rounding states (`REKHA_GS_ROUND`)


| name | value | meaning |
|---|---|---|
| `REKHA_RND_GRID` | 0 | RTG  — to the nearest pixel |
| `REKHA_RND_HALF` | 1 | RTHG — to the nearest half pixel |
| `REKHA_RND_DOUBLE` | 2 | RTDG — to the nearest half pixel, on a half-pixel grid |
| `REKHA_RND_DOWN` | 3 | RDTG |
| `REKHA_RND_UP` | 4 | RUTG |
| `REKHA_RND_OFF` | 5 | ROFF — no rounding at all |
| `REKHA_RND_SUPER` | 6 | SROUND |
| `REKHA_RND_SUPER45` | 7 | S45ROUND |

### The point fields of `rekha_hint_point`


| name | value | meaning |
|---|---|---|
| `REKHA_PT_ORUSX` | 0 | original position, FONT UNITS (twilight: 0) |
| `REKHA_PT_ORUSY` | 1 |  |
| `REKHA_PT_ORGX` | 2 | original position scaled to F26Dot6 |
| `REKHA_PT_ORGY` | 3 |  |
| `REKHA_PT_CURX` | 4 | where the point is now, F26Dot6 |
| `REKHA_PT_CURY` | 5 |  |
| `REKHA_PT_TAGS` | 6 | REKHA_TAG_ONCURVE | TOUCHX | TOUCHY |
| `REKHA_PT_COUNT` | 7 |  |

### The tag bits of a hinted point


| name | value | meaning |
|---|---|---|
| `REKHA_TAG_ONCURVE` | 1 |  |
| `REKHA_TAG_TOUCHX` | 2 |  |
| `REKHA_TAG_TOUCHY` | 4 |  |

### The behavior bits of `rekha_gasp_behavior`


| name | value | meaning |
|---|---|---|
| `REKHA_GASP_GRIDFIT` | 1 |  |
| `REKHA_GASP_DOGRAY` | 2 |  |
| `REKHA_GASP_SYMMETRIC_GRIDFIT` | 4 |  |
| `REKHA_GASP_SYMMETRIC_SMOOTH` | 8 |  |

## Functions

### `rekha_max_zone_points(font)`

```cyrius
fn rekha_max_zone_points(font): i64
```

The point capacity the interpreter's glyph zone is built at: the larger of maxp's maxPoints and maxCompositePoints (the zone itself adds the 4 phantom points). Answers 0 when font is 0, or maxp is absent, shorter than 32 bytes, or not version 0x00010000. Reads the cached slot at font+816; allocates nothing.

<!-- src/hint.cyr:364 -->

### `rekha_max_zone_contours(font)`

```cyrius
fn rekha_max_zone_contours(font): i64
```

The contour capacity of the glyph zone: the larger of maxp's maxContours and maxCompositeContours. 0 when font is 0 or maxp is not version 1.0. Reads font+824; allocates nothing.

<!-- src/hint.cyr:365 -->

### `rekha_hint_present(font)`

```cyrius
fn rekha_hint_present(font): i64
```

1 when the face has a version 1.0 maxp AND at least one of fpgm / prep / cvt with a non-zero length; 0 otherwise (font 0 included). ⛔ Glyph-only bytecode is NOT run: such a face answers 0 here and rekha_hint_ctx refuses with REKHA_ERR_NO_TABLE 'hint tables'. ⚠ 1 does not promise every glyph is hinted — fpgm or a size's prep may still refuse, reported by rekha_hint_error on the context. Allocates nothing.

<!-- src/hint.cyr:380 -->

### `rekha_max_storage(font)`

```cyrius
fn rekha_max_storage(font): i64
```

maxp 1.0 maxStorage (offset +18). 0 when font is 0 or maxp is version 0.5, absent or short — which is also a legal answer for a font that declares 0. Allocates nothing.

<!-- src/hint.cyr:391 -->

### `rekha_max_function_defs(font)`

```cyrius
fn rekha_max_function_defs(font): i64
```

maxp 1.0 maxFunctionDefs (+20). 0 when font is 0 or maxp is not version 1.0 (also legal for a font declaring 0). Note the interpreter floors the function table at 64 records regardless. Allocates nothing.

<!-- src/hint.cyr:392 -->

### `rekha_max_instruction_defs(font)`

```cyrius
fn rekha_max_instruction_defs(font): i64
```

maxp 1.0 maxInstructionDefs (+22). 0 when font is 0 or maxp is not version 1.0. Allocates nothing.

<!-- src/hint.cyr:393 -->

### `rekha_max_stack_elements(font)`

```cyrius
fn rekha_max_stack_elements(font): i64
```

maxp 1.0 maxStackElements (+24). 0 when font is 0 or maxp is not version 1.0. The context's stack gets max(maxStackElements / 2, 128) slots more than declared. Allocates nothing.

<!-- src/hint.cyr:394 -->

### `rekha_max_instruction_size(font)`

```cyrius
fn rekha_max_instruction_size(font): i64
```

maxp 1.0 maxSizeOfInstructions (+26). 0 when font is 0 or maxp is not version 1.0. Allocates nothing.

<!-- src/hint.cyr:395 -->

### `rekha_max_twilight_points(font)`

```cyrius
fn rekha_max_twilight_points(font): i64
```

maxp 1.0 maxTwilightPoints (+16). 0 when font is 0 or maxp is not version 1.0. The twilight zone holds exactly this many points, with no +4 band. Allocates nothing.

<!-- src/hint.cyr:396 -->

### `rekha_fpgm_length(font)`

```cyrius
fn rekha_fpgm_length(font): i64
```

Byte length of the fpgm table; 0 = absent or font 0. Allocates nothing.

<!-- src/hint.cyr:399 -->

### `rekha_prep_length(font)`

```cyrius
fn rekha_prep_length(font): i64
```

Byte length of the prep table; 0 = absent or font 0. Allocates nothing.

<!-- src/hint.cyr:400 -->

### `rekha_cvt_count(font)`

```cyrius
fn rekha_cvt_count(font): i64
```

Number of i16 entries in the cvt table (table length / 2); 0 when absent or font 0. Reads the FONT, not the interpreter's scaled copy. Allocates nothing.

<!-- src/hint.cyr:405 -->

### `rekha_cvt_value(font, i)`

```cyrius
fn rekha_cvt_value(font, i): i64
```

cvt entry i in FONT UNITS as a signed 16-bit value, unscaled and unhinted. 0 for font 0, i < 0 or i >= rekha_cvt_count(font) — 0 is also a legal value. ⚠ rekha_hint_cvt_px reads the interpreter's own copy, which prep is entitled to have rewritten; the two answer different questions at the same index. Allocates nothing.

<!-- src/hint.cyr:412 -->

### `rekha_gasp_present(font)`

```cyrius
fn rekha_gasp_present(font): i64
```

1 when a gasp table of at least 4 bytes was found at open; 0 otherwise (font 0 included). Allocates nothing.

<!-- src/hint.cyr:434 -->

### `rekha_gasp_behavior(font, ppem)`

```cyrius
fn rekha_gasp_behavior(font, ppem): i64
```

The gasp behavior flags for ppem — REKHA_GASP_GRIDFIT 1, REKHA_GASP_DOGRAY 2, REKHA_GASP_SYMMETRIC_GRIDFIT 4, REKHA_GASP_SYMMETRIC_SMOOTH 8, version 1 bits reported unchanged — from the first range whose rangeMaxPPEM >= ppem. -1 when there is no gasp or its range array runs past the table (NOT 0: 0 is a real answer meaning neither grid-fit nor smooth). ⚠ The 'no gasp means grid-fit everywhere' convention is left to rekha_should_gridfit. Allocates nothing.

<!-- src/hint.cyr:445 -->

### `rekha_should_gridfit(font, ppem)`

```cyrius
fn rekha_should_gridfit(font, ppem): i64
```

1 when this ppem should be grid-fit (gasp GRIDFIT bit set), 0 when not. ⚠ A face with no gasp answers 1, the long-standing convention, stated here. ⛔ (README) The question is the consumer's: rekha_hint_glyph hints whenever asked and never consults gasp. Allocates nothing.

<!-- src/hint.cyr:463 -->

### `rekha_hint_error(ctx)`

```cyrius
fn rekha_hint_error(ctx): i64
```

The RekhaErrCode of the last run's refusal on this context; REKHA_OK (0) when nothing refused or ctx is 0. ⛔ NOT a success test — it says WHICH refusal. After rekha_hint_ctx it carries the standing fpgm refusal first, else the size's prep refusal, on every call for that size. Allocates nothing.

<!-- src/hint.cyr:550 -->

### `rekha_hint_error_detail(ctx)`

```cyrius
fn rekha_hint_error_detail(ctx): i64
```

A short STATIC cstring naming the instruction or invariant that refused (e.g. 'stack overflow', 'DIV by zero', '<MNEMONIC> point'); never allocated and never owned by the caller. 0 when there is nothing to name or ctx is 0.

<!-- src/hint.cyr:557 -->

### `rekha_hint_error_clear(ctx)`

```cyrius
fn rekha_hint_error_clear(ctx): i64
```

Sets the context's error code to REKHA_OK and its detail to 0; answers 0 (also 0 for ctx 0). Every run clears first, so a code always describes the LAST run; a consumer rarely needs to call this. Allocates nothing.

<!-- src/hint.cyr:563 -->

### `rekha_hint_round(ctx, d)`

```cyrius
fn rekha_hint_round(ctx, d): i64
```

Puts d (an F26Dot6 distance, 64 = one pixel) through the context's current rounding state (REKHA_RND_GRID 0 .. REKHA_RND_SUPER45 7): d unchanged for ctx 0 or ROFF; the five fixed grids fold to a non-negative distance, round, restore the sign and never carry a distance across zero; SROUND/S45ROUND use the font's own period/phase/threshold. Allocates nothing.

<!-- src/hint.cyr:662 -->

### `rekha_hint_cvt_px(ctx, i)`

```cyrius
fn rekha_hint_cvt_px(ctx, i): i64
```

The scaled control value i in F26Dot6 as the interpreter CURRENTLY holds it — after this size's prep rewrote it (Liberation Sans rewrites 22 to 59 of its 324 entries depending on the size) and, right after a rekha_hint_glyph whose programs wrote through WCVTP or DELTAC, the GLYPH's private copy until the next load repoints it. 0 for ctx 0, i < 0 or i >= the cvt count. ⚠ Not rekha_cvt_value (font units); the fresh scale is rekha_hint_mulfix(rekha_cvt_value(font, i), scale). Allocates nothing.

<!-- src/hint.cyr:754 -->

### `rekha_hint_storage(ctx, i)`

```cyrius
fn rekha_hint_storage(ctx, i): i64
```

The storage-area value at i through the CURRENT pointer (a glyph program's WS writes a private copy that this answers until the next glyph load). 0 for ctx 0 or i outside 0..maxStorage-1, which is also a legal stored value. Cleared before every prep run, so it holds what this size's prep wrote. Allocates nothing.

<!-- src/hint.cyr:765 -->

### `rekha_hint_ppem(ctx)`

```cyrius
fn rekha_hint_ppem(ctx): i64
```

The ppem this context is scaled for; 0 for ctx 0, and 0 after an axis change until the next rekha_hint_ctx rebuilds the size. Allocates nothing.

<!-- src/hint.cyr:775 -->

### `rekha_hint_scale(ctx)`

```cyrius
fn rekha_hint_scale(ctx): i64
```

The 16.16 multiplier taking FONT UNITS to F26Dot6 for this size (ppem * 64 / unitsPerEm, FT_DivFix rounding); 0 for ctx 0 or a context not yet scaled. Allocates nothing.

<!-- src/hint.cyr:776 -->

### `rekha_hint_bytes(ctx)`

```cyrius
fn rekha_hint_bytes(ctx): i64
```

The exact byte count of the context's single sd_alloc (REKHA_HINT_HDR 832 plus the inline arrays, byte arrays rounded up to 8); 0 for ctx 0. Allocates nothing.

<!-- src/hint.cyr:777 -->

### `rekha_hint_func_defined(ctx, n)`

```cyrius
fn rekha_hint_func_defined(ctx, n): i64
```

1 when the font program defined function number n (looked up by NUMBER, not position — numbers may run to 0xFFFF with gaps); 0 otherwise or for ctx 0. Allocates nothing.

<!-- src/hint.cyr:801 -->

### `rekha_hint_func_count(ctx)`

```cyrius
fn rekha_hint_func_count(ctx): i64
```

How many DISTINCT function numbers the font program defined (HC_FDEFN); a redefinition takes no second record and the numbers need not be 0..count-1 (Liberation Sans's 71 functions run up to 91 with gaps). 0 for ctx 0. Allocates nothing.

<!-- src/hint.cyr:808 -->

### `rekha_hint_ctx(font, ppem)`

```cyrius
fn rekha_hint_ctx(font, ppem): i64
```

The interpreter for font at ppem: ONE sd_alloc on first use cached on the handle at font+808, fpgm run once, prep re-run on every size change and after every axis change (rekha_var_set_axis / _set_instance / _reset mark it stale). Answers 0 — with rekha_font_error(font) carrying REKHA_ERR_NO_TABLE 'hint tables' (no runnable bytecode), REKHA_ERR_OTHER 'ppem' (ppem <= 0), REKHA_ERR_NO_TABLE 'head' (unitsPerEm <= 0) or REKHA_ERR_OOM naming the tripped cap ('stack cap' 8192, 'storage cap' 8192, 'function cap' 4096, 'instruction cap' 256, 'cvt cap' 16384, 'twilight cap' / 'glyph zone cap' / 'contour cap' 4096, or 'hint context' when sd_alloc failed). ⛔ A NON-ZERO answer does not mean success: a standing fpgm or prep refusal is re-raised through rekha_hint_error(ctx) and mirrored onto rekha_font_error(font) on every call for that size; rekha_hint_glyph is what answers 0 for it. ⛔ Call it once, OUTSIDE any scoped per-frame sd_alloc hook, right after rekha_font_open; on a variable face load one glyph outside the hook too.

<!-- src/hint.cyr:847 -->

### `rekha_hint_run_prep(ctx)`

```cyrius
fn rekha_hint_run_prep(ctx): i64
```

Rebuilds the size's state — control values re-scaled FROM THE FONT at this ppem, storage area CLEARED, twilight zone zeroed (tags and positions), graphics state to defaults, stack emptied, glyph zone and outline view invalidated — then runs `prep`. 1 when `prep` ran (an absent or empty `prep` counts as ran); 0 for a null context, when `prep` refused (rekha_hint_error carries the code, REKHA_ERR_BAD_HINT naming the instruction, and the refusal is kept as the size's standing refusal), or when the font program's standing refusal is re-raised without running; it sets the context's error only, not rekha_font_error (rekha_hint_ctx does the mirroring). ⛔ Afterwards the graphics state is the defaults plus the ten fields `prep` may leave (minimum distance, the two cut-ins, the single width, delta base and shift, auto-flip, INSTCTRL, SCANCTRL, SCANTYPE) snapshotted into HC_GSSAVE; a REFUSED `prep` leaves pure defaults. Called for you by rekha_hint_ctx on every size change; calling it again is idempotent. Allocates nothing.

<!-- src/hint.cyr:3530 -->

### `rekha_hint_glyph(ctx, gid)`

```cyrius
fn rekha_hint_glyph(ctx, gid): i64
```

Loads glyph `gid` into the glyph zone at the context's size and hints it: outline in font units (gvar applied) scaled to F26Dot6, the four phantom points appended from the header bbox and hmtx (vmtx, else OS/2, else hhea) and rounded to the grid, the glyph program run under FreeType's glyph-range rules with IUP (a composite: each component on its own, then the composite's program at scale 1.0), then every x translated so the left phantom is the origin. 1 when zone 1 holds what the bytecode intends (a glyph with no program, an empty glyph, a program-less composite and a size whose `prep` disabled programs through INSTCTRL bit 1 all count); 0 for a null context or when rekha REFUSED in one of three ways rekha_hint_error distinguishes: a standing `fpgm` / `prep` refusal re-raised (zone 1 EMPTY); a PROGRAM refusal (REKHA_ERR_BAD_HINT naming the instruction, or a truncated program) after which zone 1 holds the glyph RELOADED UNHINTED so rekha_hint_outline / _to_sdpath / _advance_px still answer; anything else — bad gid, truncated or malformed glyph or component record (REKHA_ERR_TRUNCATED / REKHA_ERR_BAD_GLYF), a cyclic or over-cap composite or a glyph past the zone's maxp capacity (REKHA_ERR_OOM "glyph load cap" / "glyph zone cap" / "contour cap"), a point-matching index past the assembled points (REKHA_ERR_BAD_GLYF "composite point") — with zone 1 EMPTY, rekha_hint_gid -1, the outline 0 and the path call refusing. rekha_font_error(font) mirrors the code either way. Allocates nothing. ⛔ EVERY CALL INVALIDATES THE PREVIOUS GLYPH, success or not, as do rekha_hint_run_prep and a size change through rekha_hint_ctx. ⚠ `gasp` is not consulted (rekha_should_gridfit is the consumer's question); the advance of a hinted run is rekha_hint_advance_px's, not rekha_glyph_advance_px's; variation instances are hinted OFF-REFERENCE and after an axis change rekha_hint_ctx must be called again.

<!-- src/hint.cyr:4409 -->

### `rekha_hint_outline(ctx)`

```cyrius
fn rekha_hint_outline(ctx): i64
```

Answers the loaded glyph as a RekhaOutline VIEW into zone 1: n_points EXCLUDING the four phantoms, n_contours, end_pts absolute (phantoms never inside), xs / ys = the zone's cur in F26Dot6 with x translated so that the left phantom is the origin, on_curve one byte per point (the tag's bit 0 alone; the touch bits a program left are only on rekha_hint_point's REKHA_PT_TAGS). 0 for a null context or when no glyph is loaded (rekha_hint_gid is -1). The record lives in the context and is REWRITTEN BY EVERY rekha_hint_glyph, rekha_hint_run_prep and size change: read it before the next, never keep it. Allocates nothing; it goes through rekha_outline_to_sdpath with scale 1024 (F26Dot6 times 1024 IS 16.16), which is what rekha_hint_to_sdpath does.

<!-- src/hint.cyr:4532 -->

### `rekha_hint_gid(ctx)`

```cyrius
fn rekha_hint_gid(ctx): i64
```

Answers the gid zone 1 holds, or -1 when it holds no glyph; -1 for a null context too. Allocates nothing.

<!-- src/hint.cyr:4539 -->

### `rekha_hint_to_sdpath(ctx, ox, oy)`

```cyrius
fn rekha_hint_to_sdpath(ctx, ox, oy): i64
```

Answers the loaded glyph as a positioned sadish SdPath: sd_x = ox + cur_x * 1024, sd_y = oy - cur_y * 1024 (F26Dot6 to 16.16, y flipped). ⛔ Pass ox / oy on WHOLE PIXELS (n << 16) or the fit the program made is lost. A fresh path each call, exactly sized (allocated through sd_alloc); an empty glyph gives an empty path with its advance still on rekha_hint_advance_px. 0 for a null context, for no glyph loaded (REKHA_ERR_OTHER "no glyph" on the context AND the font, nothing allocated) and when an allocation is refused (REKHA_ERR_OOM "sdpath", on both) — never a truncated path.

<!-- src/hint.cyr:4550 -->

### `rekha_hint_advance_px(ctx)`

```cyrius
fn rekha_hint_advance_px(ctx): i64
```

Answers the advance the loaded glyph was fitted to, in WHOLE PIXELS: the right phantom minus the left, rounded with FT_PIX_ROUND `(v + 32) & -64` then divided by 64. THIS is what a hinted run adds to its pen for every glyph, not rekha_glyph_advance_px: a program may have moved the right phantom (Liberation Sans 'H' at 16 ppem is 12 px unhinted and 11 hinted), a USE_MY_METRICS composite carries its component's, an empty glyph and a program-less composite are whole only through this rounding. 0 for a null context or no glyph loaded. Allocates nothing. ⚠ `hdmx` IS NOT READ (a roadmap pin): on a face with an hdmx FreeType reports the table's byte instead.

<!-- src/hint.cyr:4577 -->

### `rekha_hint_gs(ctx, field)`

```cyrius
fn rekha_hint_gs(ctx, field): i64
```

Answers one graphics-state field by its REKHA_GS_* index (0..26; REKHA_GS_COUNT = 27): projection / freedom / dual vectors in F2Dot14, the three reference points, the three zone pointers (0 twilight, 1 glyph), loop, the round state (one of REKHA_RND_*), SROUND's period / phase / threshold, minimum distance, the two cut-ins and the single width in F26Dot6, auto-flip, delta base (unsigned 16-bit) and shift, INSTCTRL, SCANCTRL, SCANTYPE. 0 for a null context or an index outside the set, which is also a legal value for most fields. After rekha_hint_ctx it shows the defaults plus the ten fields `prep` left — what a glyph program starts from. Allocates nothing.

<!-- src/hint.cyr:4630 -->

### `rekha_hint_point(ctx, zone, i, field)`

```cyrius
fn rekha_hint_point(ctx, zone, i, field): i64
```

Answers one field of point `i` of zone `zone` (0 twilight, 1 glyph) by its REKHA_PT_* index: ORUSX / ORUSY in FONT UNITS (twilight: 0), ORGX / ORGY and CURX / CURY in F26Dot6, TAGS the byte (REKHA_TAG_ONCURVE | TOUCHX | TOUCHY). 0 for a null context, a zone other than 0 or 1, a point the zone does not have, or a field outside REKHA_PT_* (REKHA_PT_COUNT = 7); 0 is also a legal value for every field. The glyph zone holds nothing until rekha_hint_glyph (or rekha_hint_load_simple) loads a glyph, then its n real points followed by the four phantom points, cur x already translated so the left phantom is the origin after rekha_hint_glyph. Allocates nothing.

<!-- src/hint.cyr:4650 -->

### `rekha_hint_zone_points(ctx, zone)`

```cyrius
fn rekha_hint_zone_points(ctx, zone): i64
```

Answers how many points a zone holds. For the twilight zone (0) it is the per-run bound — 2 * (glyph points + control values), floored at 30 and capped at the font's maxTwilightPoints (rekha_hint_twilight_bound); for the glyph zone (1) it is 0 until a glyph is loaded, then n + 4 with the four phantom points included (an empty glyph holds exactly four). 0 for a null context or a zone other than 0 or 1. Allocates nothing.

<!-- src/hint.cyr:4667 -->

### `rekha_hint_zone_contours(ctx, zone)`

```cyrius
fn rekha_hint_zone_contours(ctx, zone): i64
```

Answers how many contours a zone holds: 0 for the twilight zone, and for the glyph zone 0 until a glyph is loaded, then the loaded glyph's contour count (the phantoms are never inside a contour). 0 for a null context or a zone other than 0 or 1. Allocates nothing.

<!-- src/hint.cyr:4675 -->
