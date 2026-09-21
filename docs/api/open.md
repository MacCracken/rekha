# Opening a face

> **Frozen as of 0.9.0.** Signatures and documented answers hold through 1.x; the `src/` header a call sits under is the normative text. Sentinel first, `rekha_font_error` second ([README](README.md) rule 2).

A font is bytes the caller owns. `rekha_font_open(buf, len)` reads the SFNT directory at
offset 0 (or face 0 of a `'ttcf'` collection) and returns a `RekhaFont` handle — one
`sd_alloc(REKHA_FONT_SIZE)`, and the only allocation an open makes. The bytes are **borrowed**:
they must outlive the handle and must not change under it. A missing or malformed table never
fails the open; the reader that needs it answers 0 and says why.

`rekha_font_open_any` looks at the first four bytes and dispatches to the SFNT, WOFF 1.0 or
WOFF2 opener; it is in `dist/rekha-woff.cyr` only — the base bundle never requires sankoch
([ADR 0004](../adr/0004-the-opt-in-woff-bundle.md)). The WOFF openers allocate the rebuilt
SFNT on the seam; the two-step forms (`rekha_woff_sfnt_size` + `rekha_woff_decode`,
`rekha_woff2_block_size` + `rekha_woff2_inflate` + `rekha_woff2_sfnt_size` +
`rekha_woff2_decode`) let a consumer size and own that buffer — the escape hatch for a
collection, which the one-step opener re-inflates per face.

The embedded default face (`fonts/face_data.cyr`) is a freestanding generated data module a
kernel takes **by path**, never through a bundle ([ADR 0008](../adr/0008-the-embedded-default-face.md));
its ten accessors are frozen with the rest.

## Constants

### The size of a handle

Frozen by **name**: the value grew 816 → 832 at 0.8.1 and may grow again in a minor release. Size an arena by the name, never by the number.
| name | value | meaning |
|---|---|---|
| `REKHA_FONT_SIZE` | 832 |  |

## Functions

### `rekha_font_open(buf, len)`

```cyrius
fn rekha_font_open(buf, len): i64
```

Returns a RekhaFont handle, or 0 when buf is 0, len < 12, sfntVersion is not 0x00010000 / 'true' / 'OTTO', the table directory overruns len, or the allocation fails; no RekhaErrCode is surfaced (rekha_font_open_why is the twin that says why). A missing or malformed table NEVER fails the open: it is cached as absent and the reader that needs it returns 0. Allocates exactly one sd_alloc(REKHA_FONT_SIZE) = 832 B; the buffer is BORROWED and the cache is a snapshot, so mutating the bytes after open is unsupported; on a 'ttcf' collection it opens face 0 (tested at programs/ttc_test.cyr:192, undocumented in its own comment).

<!-- src/sfnt.cyr:246 -->

### `rekha_ttc_count(buf, len)`

```cyrius
fn rekha_ttc_count(buf, len): i64
```

Answers the number of faces in a 'ttcf' collection, or 0 when buf is 0, len < 12, the file is not a collection, the count is 0 or past REKHA_TTC_MAXFONTS (1024), or the offset array does not fit (12 + nf * 4 > len). Reads the 12-byte header and allocates 0 B. ⚠ 0 means 'not a collection', not 'no font': a plain .ttf answers 0 and opens fine through rekha_font_open_index(buf, len, 0).

<!-- src/sfnt.cyr:256 -->

### `rekha_font_open_index_why(buf, len, index, err_out)`

```cyrius
fn rekha_font_open_index_why(buf, len, index, err_out): i64
```

Opens face `index` of (buf, len) and writes a RekhaErrCode into the caller's i64 slot err_out (or 0 to ignore): REKHA_OK on success; REKHA_ERR_OTHER for buf 0, index < 0, index past the collection, or index != 0 on a non-collection; REKHA_ERR_TRUNCATED for len < 12, a face offset table or its directory past len; REKHA_ERR_BAD_SFNT for a collection whose count is 0 / offset array does not fit, or a face offset inside the TTC header; REKHA_ERR_UNSUPPORTED (not BAD_SFNT) for a version that is none of 0x00010000 / 'true' / 'OTTO' (a wOFF, a Type 1); REKHA_ERR_OOM when sd_alloc fails. Allocates one sd_alloc(REKHA_FONT_SIZE). ⛔ The open family cannot use rekha_font_error because there is no handle yet, which is why it takes a slot and stays reentrant.

<!-- src/sfnt.cyr:294 -->

### `rekha_font_open_index(buf, len, index)`

```cyrius
fn rekha_font_open_index(buf, len, index): i64
```

Opens face `index` of (buf, len): a 'ttcf' collection carries several faces sharing table data, anything else is one face and only index 0 opens it. Returns a handle or 0 for the reasons rekha_font_open lists plus an index past the collection, a collection whose header or offset array does not fit, and a face offset inside the TTC header; no code surfaced (use rekha_font_open_index_why). ⛔ A member face's tables are addressed from the START OF THE FILE and two faces routinely share a table, so each face carries its own floor (+248) below which no table may start. Allocates one sd_alloc(REKHA_FONT_SIZE).

<!-- src/sfnt.cyr:278 -->

### `rekha_font_open_why(buf, len, err_out)`

```cyrius
fn rekha_font_open_why(buf, len, err_out): i64
```

rekha_font_open with a reason: opens face 0 and writes REKHA_OK or the RekhaErrCode rekha_font_open_index_why lists (OTHER / TRUNCATED / BAD_SFNT / UNSUPPORTED / OOM) into err_out (i64 slot, or 0 to ignore). Returns the handle or 0; allocates one sd_alloc(REKHA_FONT_SIZE).

<!-- src/sfnt.cyr:343 -->

### `rekha_find_table_len(f, tag, len_out)`

```cyrius
fn rekha_find_table_len(f, tag, len_out): i64
```

Answers the byte offset within the font data of the FIRST directory entry carrying `tag` (4 ASCII bytes packed big-endian into an i64, e.g. 'glyf' = 0x676C7966) and stores its declared length in the 8-byte cell len_out. Returns 0 with *len_out = 0 when the handle is 0, the tag is absent, or the entry breaks the extent rule: the table must start at or after this face's floor (+248: the end of the directory for a plain SFNT, the end of the TTC header and offset array for a collection member), end within the file (offset + length <= len), and not overlap the face's own offset table and directory. ⚠ The declared length may be 0. Does not touch rekha_font_error; 0 B of heap.

<!-- src/sfnt.cyr:415 -->

### `rekha_find_table(f, tag)`

```cyrius
fn rekha_find_table(f, tag): i64
```

Offset-only rekha_find_table_len: the table's byte offset within the font data, or 0 when the handle is 0, the tag is absent, or its entry breaks the extent rule. One directory walk, 0 B of heap, and no rekha_font_error code.

<!-- src/sfnt.cyr:448 -->

### `rekha_units_per_em(font)`

```cyrius
fn rekha_units_per_em(font): i64
```

Answers head.unitsPerEm (u16 at head+18), the design-unit em square a consumer scales by pixel_size / unitsPerEm. Returns 0 when the handle is 0 or head is absent / shorter than 54 B. Cannot refuse and therefore does NOT clear or set rekha_font_error; 0 B of heap.

<!-- src/sfnt.cyr:535 -->

### `rekha_glyph_count(font)`

```cyrius
fn rekha_glyph_count(font): i64
```

Answers maxp.numGlyphs (u16 at maxp+4), the count of glyph ids. Returns 0 when the handle is 0 or maxp is absent / shorter than 6 B. Cannot refuse and does NOT clear or set rekha_font_error; 0 B of heap.

<!-- src/sfnt.cyr:551 -->

### `rekha_woff_sfnt_size(buf, len)`

```cyrius
fn rekha_woff_sfnt_size(buf, len): i64
```

Returns the byte size of the SFNT the WOFF 1.0 container at (buf, len) rebuilds to (its validated totalSfntSize, which must be EXACTLY 12 + 16 x numTables + the 4-byte-padded origLengths), or 0 when (buf, len) is not a valid WOFF 1.0 under the module's ⛔ rules (bad signature/reserved/length, non-strictly-ascending tags, table data outside [end of directory, length), compLength > origLength, padded compLengths summing past length, origLength > REKHA_WOFF_MAX_RATIO (1032) x compLength, or a metadata/private block outside length). Reads only the header and directory, inflates nothing, allocates 0 B; it does not touch rekha_font_error (there is no handle) and sets no RekhaErrCode.

<!-- src/woff.cyr:69 -->

### `rekha_woff_decode(buf, len, dst, cap)`

```cyrius
fn rekha_woff_decode(buf, len, dst, cap): i64
```

Rebuilds the SFNT carried by the WOFF 1.0 container at (buf, len) into `dst` (`cap` bytes) and returns the SFNT's byte length, or 0 when the container is invalid (rekha_woff_sfnt_size returns 0), `cap` is smaller than the SFNT, or a table does not inflate to EXACTLY its origLength (⛔ capped at origLength: a stream that would write more fails closed in sankoch with ERR_OUTPUT_LIMIT, one that writes less fails here). On 0 the contents of `dst` are unspecified. Allocates 0 B on rekha's sd_alloc seam; sankoch's inflate takes MEASURED 448 B of global heap per call; table checksums are carried, not verified; metadata and private blocks are not copied. Sets no RekhaErrCode.

<!-- src/woff.cyr:126 -->

### `rekha_font_open_woff(buf, len)`

```cyrius
fn rekha_font_open_woff(buf, len): i64
```

Opens a WOFF 1.0 font: validates, rebuilds its SFNT into ONE sd_alloc(totalSfntSize) that the returned RekhaFont borrows, then rekha_font_open's it; returns the font handle or 0 for an invalid container, a failed inflate, an allocation failure (sd_alloc returned 0), or an SFNT rekha_font_open refuses (e.g. an 'OTTO' flavor). Allocation is exactly two sd_allocs (the SFNT buffer and the RekhaFont; MEASURED 410,824 + 176 B for the embedded face) plus sankoch's MEASURED 448 B of global heap per inflate. ⚠ The rebuilt buffer lives as long as the allocator it came from, so open a WOFF once, outside a scoped per-frame hook, as with rekha_font_open; ⛔ the module is opt-in (dist/rekha-woff.cyr, [lib.woff]) and the consumer brings sankoch (>= 2.7.13 for zlib_decompress_capped). No RekhaErrCode is reported on 0 (there is no handle) and unlike rekha_font_open there is no `_why` variant.

<!-- src/woff.cyr:183 -->

### `rekha_woff2_face_count(buf, len)`

```cyrius
fn rekha_woff2_face_count(buf, len): i64
```

Answers how many faces the WOFF2 at (buf, len) carries: 1 for an ordinary font, the collection's face count for a 'ttcf'-flavoured one; 0 when (buf, len) is not a WOFF2 rekha accepts (any refusal in the module-header list). It allocates the parse context (REKHA_W2_CTX = 80 bytes plus the entry, face and index arrays via sd_alloc) and never frees it; no RekhaErrCode is produced — the container opens answer a bare 0 (roadmap: 'The WOFF / WOFF2 opens do not say why').

<!-- src/woff2.cyr:1494 -->

### `rekha_woff2_block_size(buf, len)`

```cyrius
fn rekha_woff2_block_size(buf, len): i64
```

Answers the exact byte length of the inflated table-data block: the sum of every directory entry's compressed-stream length; 0 when (buf, len) is not a WOFF2 rekha accepts. ⚠ Spec 5 makes this an EQUALITY with what Brotli produces, so it is both the buffer to allocate and the length rekha_woff2_inflate must return. Allocates the parse context via sd_alloc (never freed); sets no RekhaErrCode.

<!-- src/woff2.cyr:1504 -->

### `rekha_woff2_inflate(buf, len, td, cap)`

```cyrius
fn rekha_woff2_inflate(buf, len, td, cap): i64
```

Inflates the WOFF2's compressed font data into td (cap bytes) and returns the byte length, which is rekha_woff2_block_size exactly, or 0 (invalid container, cap < block size, td == 0, totalCompressedSize < 1 or running past length, or a Brotli output that is not exactly the block size). ⛔ The equality is the gate: a stream that expands to more fails closed inside sankoch (ERR_OUTPUT_LIMIT) and one that expands to less fails here. Requires sankoch >= 2.8.0 (brotli_decompress_capped) and is therefore only in dist/rekha-woff.cyr; allocates the parse context via sd_alloc; sets no RekhaErrCode.

<!-- src/woff2.cyr:1514 -->

### `rekha_woff2_sfnt_size(buf, len, td, tdlen)`

```cyrius
fn rekha_woff2_sfnt_size(buf, len, td, tdlen): i64
```

Answers the byte length of the SFNT (or TTC, for a collection) the WOFF2 rebuilds to, given its already-inflated block at (td, tdlen); 0 for any refusal, including tdlen != rekha_woff2_block_size and any transform refusal found by the measuring pass. ⚠ Unlike rekha_woff_sfnt_size this CANNOT be answered from the container alone — the measuring pass walks the transformed glyf point data. Allocates the parse context plus a REKHA_W2_GST (160-byte) state block via sd_alloc; sets no RekhaErrCode.

<!-- src/woff2.cyr:1535 -->

### `rekha_woff2_decode(buf, len, td, tdlen, dst, cap)`

```cyrius
fn rekha_woff2_decode(buf, len, td, tdlen, dst, cap): i64
```

Rebuilds the SFNT (or TTC) of the WOFF2 at (buf, len), whose inflated table data is at (td, tdlen), into dst (cap bytes) and returns its byte length, or 0 when the container is invalid, tdlen != block size, dst == 0, cap is short, or a transform refuses; on 0 the contents of dst are unspecified. ⭐ A 'ttcf' WOFF2 rebuilds to a real .ttc — TTC header (always version 1.0), one offset table per face and ONE copy of each shared table — which rekha_font_open_index then opens face by face. Checksums and head.checkSumAdjustment are recomputed; a rebuilt glyf is NOT byte-identical to the original (one flag byte per point, no REPEAT). Allocates the parse context plus REKHA_W2_GST via sd_alloc; sets no RekhaErrCode.

<!-- src/woff2.cyr:1549 -->

### `rekha_font_open_woff2_index(buf, len, index)`

```cyrius
fn rekha_font_open_woff2_index(buf, len, index): i64
```

Opens face index of a WOFF2 (inflate, rebuild, then rekha_font_open_index) and returns the RekhaFont handle, or 0 for index < 0, an invalid container, a failed inflate or transform, an allocation failure, an index past the collection, or an SFNT rekha_font_open refuses. ⚠ THIS REBUILDS THE WHOLE FILE PER CALL: a caller that wants more than one face should inflate and rekha_woff2_decode ONCE and walk the result with rekha_ttc_count / rekha_font_open_index. ⚠ TWO sd_alloc allocations outlive the call plus the RekhaFont (the inflated block and the rebuilt file; rekha's seam has no free) — open a WOFF2 once, outside a per-frame hook. Sets no RekhaErrCode of its own.

<!-- src/woff2.cyr:1571 -->

### `rekha_font_open_woff2(buf, len)`

```cyrius
fn rekha_font_open_woff2(buf, len): i64
```

Opens a WOFF2 font's face 0 (the only face an ordinary WOFF2 has) via rekha_font_open_woff2_index(buf, len, 0), returning the RekhaFont handle or 0 under the same refusals and with the same two never-freed sd_alloc allocations plus the RekhaFont. Available only through dist/rekha-woff.cyr ([lib.woff]); sets no RekhaErrCode.

<!-- src/woff2.cyr:1587 -->

### `rekha_font_open_any(buf, len)`

```cyrius
fn rekha_font_open_any(buf, len): i64
```

Opens font bytes of ANY container rekha reads: a 'wOFF' signature goes through rekha_font_open_woff, 'wOF2' through rekha_font_open_woff2, anything else (including buffers under 4 bytes) straight through rekha_font_open; returns 0 as whichever would return (buf == 0 is 0 outright). A collection — plain .ttc or 'ttcf' WOFF2 — gives face 0, the same as rekha_font_open does. ⚠ It lives in woff2.cyr (moved from woff.cyr in 0.4.6) and so is only in dist/rekha-woff.cyr, not dist/rekha.cyr; allocation follows the branch taken.

<!-- src/woff2.cyr:1597 -->

## The embedded default face

### `rekha_face_default_len()`

```cyrius
fn rekha_face_default_len(): i64
```

The byte length of the embedded face — 410,820 for the LiberationSans-Regular.ttf the module is generated from. Allocates nothing; freestanding.

<!-- fonts/face_data.cyr:34 -->

### `rekha_face_default_copy(dst, cap)`

```cyrius
fn rekha_face_default_copy(dst, cap): i64
```

Assembles the face's chunks into the caller's contiguous buffer `dst` of `cap` bytes. Returns the face length, or **−1** when `cap` is short (nothing is written then). ⛔ Call `rekha_face_default_verify` on the result before exposing it: the digest is what found a compiler defect in string-literal emission once (cyrius 6.6.3, fixed 6.6.4) and is the only thing that would find the next one.

<!-- fonts/face_data.cyr:50 -->

### `rekha_face_default_verify(buf, len)`

```cyrius
fn rekha_face_default_verify(buf, len): i64
```

FNV-1a-64 over `buf[0..len)` against the generator's hash of the source file: **1** when the bytes are the face, byte-exact; **0** means do not expose them.

<!-- fonts/face_data.cyr:68 -->

### `rekha_face_default_fnv1a()`

```cyrius
fn rekha_face_default_fnv1a(): i64
```

The expected digest itself (0xbb32949696578ce6 for the shipped face), for a consumer that hashes on its own schedule.

<!-- fonts/face_data.cyr:37 -->

### `rekha_face_default_name()`

```cyrius
fn rekha_face_default_name(): i64
```

The source filename as a string literal (`"LiberationSans-Regular.ttf"`), NOT NUL-terminated — take `rekha_face_default_name_len` bytes.

<!-- fonts/face_data.cyr:38 -->

### `rekha_face_default_name_len()`

```cyrius
fn rekha_face_default_name_len(): i64
```

The byte length of that name (26 for the shipped face).

<!-- fonts/face_data.cyr:39 -->

### `rekha_face_default_chunk_size()`

```cyrius
fn rekha_face_default_chunk_size(): i64
```

The storage model: the face is `chunk_count` string literals of this many bytes each (4,096), the last one shorter. A consumer that cannot afford one contiguous copy may read chunk by chunk.

<!-- fonts/face_data.cyr:35 -->

### `rekha_face_default_chunk_count()`

```cyrius
fn rekha_face_default_chunk_count(): i64
```

How many chunks there are (101 for the shipped face).

<!-- fonts/face_data.cyr:36 -->

### `rekha_face_default_chunk_len(i)`

```cyrius
fn rekha_face_default_chunk_len(i): i64
```

The byte length of chunk `i`: the chunk size for every chunk but the last, the remainder for the last, 0 for an index out of range.

<!-- fonts/face_data.cyr:42 -->

### `rekha_face_default_chunk(i)`

```cyrius
fn rekha_face_default_chunk(i): i64
```

A pointer to chunk `i`'s bytes — a string literal in `.rodata`, not NUL-safe; use the length. 0 for an index out of range.

<!-- fonts/face_data.cyr:78 -->
