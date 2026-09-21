# Names and style attributes

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

`rekha_name_utf8(font, name_id, dst, cap)` decodes the best-ranked `name` record for an id
into the caller's buffer as UTF-8 — Windows English first, then any Windows, Unicode, then
Macintosh Roman — and answers the byte count it needs, writing nothing when `cap` is short.
Nothing is NUL-terminated. `STAT` is read field by field and joined by no one: which values
apply, the `axisOrdering` sort and the elidable names are the consumer's to assemble.

## Constants

### The name ids worth naming

Every other id is readable by number.
| name | value | meaning |
|---|---|---|
| `REKHA_NAME_COPYRIGHT` | 0 |  |
| `REKHA_NAME_FAMILY` | 1 |  |
| `REKHA_NAME_SUBFAMILY` | 2 |  |
| `REKHA_NAME_UNIQUE` | 3 |  |
| `REKHA_NAME_FULL` | 4 |  |
| `REKHA_NAME_VERSION` | 5 |  |
| `REKHA_NAME_POSTSCRIPT` | 6 |  |
| `REKHA_NAME_TRADEMARK` | 7 |  |
| `REKHA_NAME_MANUFACTURER` | 8 |  |
| `REKHA_NAME_DESIGNER` | 9 |  |
| `REKHA_NAME_DESCRIPTION` | 10 |  |
| `REKHA_NAME_VENDOR_URL` | 11 |  |
| `REKHA_NAME_LICENSE` | 13 |  |
| `REKHA_NAME_TYPO_FAMILY` | 16 |  |
| `REKHA_NAME_TYPO_SUBFAM` | 17 |  |
| `REKHA_NAME_SAMPLE` | 19 |  |

### The bits of `rekha_stat_value_flags`


| name | value | meaning |
|---|---|---|
| `REKHA_STAT_OLDER_SIBLING` | 1 |  |
| `REKHA_STAT_ELIDABLE` | 2 |  |

## Functions

### `rekha_name_count(font)`

```cyrius
fn rekha_name_count(font): i64
```

Number of name records in the resolved `name` table; 0 when `font` is 0 or the table was left absent at open (format > 1, header or record array outside the table, stringOffset outside the table or inside the records). Allocates nothing and never sets a RekhaErrCode — rekha_font_error is untouched.

<!-- src/name.cyr:155 -->

### `rekha_name_platform_at(font, i)`

```cyrius
fn rekha_name_platform_at(font, i): i64
```

Record `i`'s platformID as the raw u16 (0 Unicode, 1 Macintosh, 3 Windows); -1 when `font` is 0 or `i` is outside 0..rekha_name_count-1. Allocates nothing, never sets a RekhaErrCode.

<!-- src/name.cyr:176 -->

### `rekha_name_encoding_at(font, i)`

```cyrius
fn rekha_name_encoding_at(font, i): i64
```

Record `i`'s encodingID as the raw u16; -1 when `font` is 0 or `i` is out of range. Only Windows encodings 0, 1 and 10 and Macintosh encoding 0 are ones rekha_name_at_utf8 will decode. Allocates nothing, never sets a RekhaErrCode.

<!-- src/name.cyr:177 -->

### `rekha_name_language_at(font, i)`

```cyrius
fn rekha_name_language_at(font, i): i64
```

Record `i`'s languageID as the raw u16; -1 when `font` is 0 or `i` is out of range. Language 0 on Macintosh is English; 1033 on Windows is English (United States). Format 1 language tags are not resolved — the numeric id is all rekha exposes. Allocates nothing, never sets a RekhaErrCode.

<!-- src/name.cyr:178 -->

### `rekha_name_id_at(font, i)`

```cyrius
fn rekha_name_id_at(font, i): i64
```

Record `i`'s nameID as the raw u16 (compare against REKHA_NAME_FAMILY = 1, REKHA_NAME_SUBFAMILY = 2, etc.; every other id is readable by number); -1 when `font` is 0 or `i` is out of range. Allocates nothing, never sets a RekhaErrCode.

<!-- src/name.cyr:179 -->

### `rekha_name_at_utf8(font, i, dst, cap)`

```cyrius
fn rekha_name_at_utf8(font, i, dst, cap): i64
```

Decodes record `i` (UTF-16BE for platform 0 and for platform 3 encodings 0/1/10; Macintosh Roman for platform 1 encoding 0) into UTF-8 in the caller's buffer and returns the byte count the name needs, or 0 when `i` is out of range, the string lies outside the table, its length is 0, a UTF-16 length is odd, a surrogate is unpaired or low-first, or the platform/encoding pair is not decodable. Pass `dst` 0 to size it; when `cap < need` NOTHING is written and `need` is still returned, so the two-call idiom is safe. ⚠ NOT NUL-terminated — the return value is the length; allocates nothing; never sets a RekhaErrCode.

<!-- src/name.cyr:257 -->

### `rekha_name_utf8(font, name_id, dst, cap)`

```cyrius
fn rekha_name_utf8(font, name_id, dst, cap): i64
```

Returns the best-ranked record carrying `name_id` as UTF-8 under rekha_name_at_utf8's buffer contract (dst 0 sizes; cap below need writes nothing and returns need; ⚠ not NUL-terminated). Ranking: Windows enc 1 lang 1033 = 6, Windows enc 10 lang 1033 = 5, Windows enc 0 lang 1033 = 4, other-language Windows enc 0/1/10 = 3, platform 0 = 2, Macintosh enc 0 lang 0 = 1, other-language Macintosh enc 0 = 0; any other platform/encoding is not a candidate; the FIRST record wins a tie. 0 when `font` is 0, no readable record carries the id, or the winning record's string is undecodable — there is NO fallback to the next-ranked record (name_test pins this). Allocates nothing; never sets a RekhaErrCode.

<!-- src/name.cyr:269 -->

### `rekha_stat_present(font)`

```cyrius
fn rekha_stat_present(font): i64
```

Returns 1 when the font carries a STAT table that survived the open-time resolve, else 0; a null font handle answers 0. A refused table (majorVersion other than 1, a header that does not fit, designAxisSize below 8, or an axis / offset array outside the table) is reported as simply absent; no RekhaErrCode is set, stat.cyr never touches rekha_font_error. No allocation.

<!-- src/stat.cyr:73 -->

### `rekha_stat_fallback_name_id(font)`

```cyrius
fn rekha_stat_fallback_name_id(font): i64
```

Returns the elidedFallbackNameID (a name id for rekha_name_utf8) to use when every axis value in a style string was elided, or 0 when there is no STAT or the table is minorVersion 0 (the field exists from minorVersion 1 up; a 1.0 table has none). No allocation, no error code.

<!-- src/stat.cyr:81 -->

### `rekha_stat_axis_count(font)`

```cyrius
fn rekha_stat_axis_count(font): i64
```

Returns designAxisCount (u16), or 0 when there is no readable STAT. ⚠ This is STAT's own axis list, which a static member of a variable family also carries; it need not match rekha_var_axis_count. No allocation, no error code.

<!-- src/stat.cyr:90 -->

### `rekha_stat_axis_tag(font, i)`

```cyrius
fn rekha_stat_axis_tag(font, i): i64
```

Returns design axis i's 4-byte tag (u32, e.g. 0x77676874 'wght'), or 0 when there is no STAT or i is outside 0..rekha_stat_axis_count-1. No allocation, no error code.

<!-- src/stat.cyr:105 -->

### `rekha_stat_axis_name_id(font, i)`

```cyrius
fn rekha_stat_axis_name_id(font, i): i64
```

Returns design axis i's axisNameID (u16) for rekha_name_utf8, or 0 when there is no STAT or i is out of range. No allocation, no error code.

<!-- src/stat.cyr:112 -->

### `rekha_stat_axis_ordering(font, i)`

```cyrius
fn rekha_stat_axis_ordering(font, i): i64
```

Returns design axis i's axisOrdering (u16), its sort position within a style string, or 0 when there is no STAT or i is out of range. ⚠ 0 is also a legitimate ordering (the first axis usually has it), so bound i by rekha_stat_axis_count first rather than treating 0 as absence. No allocation, no error code.

<!-- src/stat.cyr:119 -->

### `rekha_stat_value_count(font)`

```cyrius
fn rekha_stat_value_count(font): i64
```

Returns axisValueCount (u16), the number of axis value tables, or 0 when there is no readable STAT. Entries in 0..count-1 may still be individually unreadable (rekha_stat_value_format answers 0 for those). No allocation, no error code.

<!-- src/stat.cyr:126 -->

### `rekha_stat_value_format(font, i)`

```cyrius
fn rekha_stat_value_format(font, i): i64
```

Returns axis value i's format, 1..4, or 0 when there is no readable entry there: no STAT, i outside 0..rekha_stat_value_count-1, an offset of 0 (the spec's 'no entry here'), a format past 4, or a body that does not fit inside the table. No allocation, no error code.

<!-- src/stat.cyr:166 -->

### `rekha_stat_value_flags(font, i)`

```cyrius
fn rekha_stat_value_flags(font, i): i64
```

Returns axis value i's flags (u16), or 0 when there is no readable entry. Test the bits REKHA_STAT_OLDER_SIBLING (1) and REKHA_STAT_ELIDABLE (2); ELIDABLE is the bit that matters for building a style string. A 0 result is also a legitimate 'no flags', so gate on rekha_stat_value_format. No allocation, no error code.

<!-- src/stat.cyr:173 -->

### `rekha_stat_value_name_id(font, i)`

```cyrius
fn rekha_stat_value_name_id(font, i): i64
```

Returns axis value i's valueNameID (u16) for rekha_name_utf8, or 0 when there is no readable entry. No allocation, no error code.

<!-- src/stat.cyr:180 -->

### `rekha_stat_value_pairs(font, i)`

```cyrius
fn rekha_stat_value_pairs(font, i): i64
```

Returns how many (axis, value) pairs entry i carries: 1 for formats 1, 2 and 3, and format 4's own axisCount. 0 when there is no readable entry. ⭐ This is the bound for rekha_stat_value_axis / _value_value's pair index k, so a consumer never branches on the format to reach the numbers. No allocation, no error code.

<!-- src/stat.cyr:188 -->

### `rekha_stat_value_axis(font, i, k)`

```cyrius
fn rekha_stat_value_axis(font, i, k): i64
```

Returns pair k of axis value i's axisIndex (u16) into STAT's own design-axis list, or -1 when there is no readable entry or k is outside 0..rekha_stat_value_pairs-1. ⚠ The axisIndex is NOT checked against designAxisCount: it is reported as written, so an out-of-range one is visible rather than quietly clamped; every BYTE read is inside the table. The only STAT accessor with a -1 sentinel. No allocation, no error code.

<!-- src/stat.cyr:202 -->

### `rekha_stat_value_value(font, i, k)`

```cyrius
fn rekha_stat_value_value(font, i, k): i64
```

Returns pair k of axis value i's value on that axis as a signed 16.16 Fixed in user (design) units, e.g. 700 << 16 for wght 700; for format 2 this is the NOMINAL value and its range is rekha_stat_value_min / _max. 0 when there is no readable entry or k is outside 0..rekha_stat_value_pairs-1 (0 is also a legitimate 0.0, so gate on the format and pair count). No allocation, no error code.

<!-- src/stat.cyr:213 -->

### `rekha_stat_value_min(font, i)`

```cyrius
fn rekha_stat_value_min(font, i): i64
```

Returns format 2's rangeMinValue as a signed 16.16 Fixed in user units; 0 for any other format (a format 1 or 3 entry names a point, not a span) or when there is no readable entry. No allocation, no error code.

<!-- src/stat.cyr:223 -->

### `rekha_stat_value_max(font, i)`

```cyrius
fn rekha_stat_value_max(font, i): i64
```

Returns format 2's rangeMaxValue as a signed 16.16 Fixed in user units; 0 for any other format or when there is no readable entry. No allocation, no error code.

<!-- src/stat.cyr:231 -->

### `rekha_stat_value_linked(font, i)`

```cyrius
fn rekha_stat_value_linked(font, i): i64
```

Returns format 3's linkedValue as a signed 16.16 Fixed in user units: the place on the same axis this style's bold-or-equivalent counterpart sits. 0 for any other format or when there is no readable entry. No allocation, no error code.

<!-- src/stat.cyr:240 -->
