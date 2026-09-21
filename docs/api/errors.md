# Why a call refused

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

Every refusal is a sentinel *and* a reason. The reason is a `RekhaErrCode` on the handle,
readable through `rekha_font_error(font)` with a static detail string from
`rekha_font_error_detail(font)` (a table tag or a field name; never allocated, never owned by
the caller). Every public call that can refuse clears the slot on entry, so read the sentinel
first and the code second. The open family has no handle to record into, so
`rekha_font_open_why` / `rekha_font_open_index_why` take a caller's i64 slot. The hinting layer
has its own slot on the context — `rekha_hint_error` / `rekha_hint_error_detail` /
`rekha_hint_error_clear` ([`hint.md`](hint.md)) — mirrored onto the font handle.

## `RekhaErrCode`

| member | value | meaning |
|---|---|---|
| `REKHA_OK` | 0 | no error — including a legal zero from a metric reader |
| `REKHA_ERR_OOM` | 1 | an allocation was refused, or a cap of the machine or the zone was hit |
| `REKHA_ERR_BAD_SFNT` | 2 | a missing or corrupt SFNT header, table directory, or `cmap` glyph id |
| `REKHA_ERR_TRUNCATED` | 3 | the bytes end before a table, a record or a field completes |
| `REKHA_ERR_NO_TABLE` | 4 | a table the call needs is absent (`head`, `cmap`, `glyf`, `loca`, `hhea`, `hmtx`, …) |
| `REKHA_ERR_BAD_GLYF` | 5 | a malformed glyph record: contour or point counts, `loca` order, a lying span |
| `REKHA_ERR_UNSUPPORTED` | 6 | a valid font whose container or feature rekha does not read — the open family; never a hinting refusal since 0.8.2 |
| `REKHA_ERR_BAD_HINT` | 7 | bytecode that contradicts itself, or a machine invariant broken (stack, an undefined function, `IF` without `EIF`, a cap) |
| `REKHA_ERR_OTHER` | 99 | a bad argument: a negative gid, a codepoint no subtable maps, a context with no glyph |

## Functions

### `rekha_err_name(code)`

```cyrius
fn rekha_err_name(code): i64
```

Takes a RekhaErrCode value and returns a pointer to a fixed NUL-terminated cstring naming it ("ok", "out of memory", "bad SFNT header", "truncated input", "required table absent", "malformed glyf entry", "unsupported feature", "malformed hint program", "other error"). Never returns 0 and never allocates: every string is a literal in the bundle. An unknown code (e.g. 12345 or -1) answers "unknown error" rather than refusing; it does not touch any font handle, so rekha_font_error is unaffected.

<!-- src/error.cyr:62 -->

### `rekha_font_error(font)`

```cyrius
fn rekha_font_error(font): i64
```

Answers the RekhaErrCode for why `font`'s LAST public call refused, or REKHA_OK (0) when it did not; a 0 handle answers REKHA_OK. ⛔ Not a success test: test the call's sentinel first and ask second. Every public call that can set it clears it on entry, but a reader that cannot refuse (rekha_units_per_em, rekha_glyph_count) does not clear, so ask immediately after the sentinel. ⚠ One handle, one thread: readers write these two slots, so share the font BYTES and open a handle per thread.

<!-- src/sfnt.cyr:497 -->

### `rekha_font_error_detail(font)`

```cyrius
fn rekha_font_error_detail(font): i64
```

Answers a short static cstring naming WHERE the last refusal was (a table tag such as "hmtx", a field such as "glyph id", "loca order") or 0 when there is none or the handle is 0. ⛔ Never allocated and never owned by the caller: a literal in the bundle, valid for the life of the program.

<!-- src/sfnt.cyr:505 -->

### `rekha_font_error_clear(font)`

```cyrius
fn rekha_font_error_clear(font): i64
```

Resets `font`'s error slot to REKHA_OK and its detail to 0; returns 0 (also for a 0 handle). Rarely needed because every public call that can set the code clears it on entry.

<!-- src/sfnt.cyr:511 -->
