#!/usr/bin/env python3
"""face2cyr — emit a FREESTANDING Cyrius module carrying one TrueType face as data.

    python3 scripts/face2cyr.py fonts/LiberationSans-Regular.ttf fonts/face_data.cyr

The output uses NO stdlib, NO heap, NO syscalls — only string literals, integer arithmetic and
the load8/store8 intrinsics — so a freestanding kernel (agnos: `[deps] stdlib = []`) can
`include`/concatenate it exactly the way it consumes kashi's src/font_data.cyr.

⛔ WHY 4096-BYTE CHUNKS — HISTORY, AND WHY THEY STAY. Measured on cyrius 6.6.3 (2026-09-13): a
string literal of >= 65536 bytes came back read from its SECOND byte on alternate literals —
rc=0, byte COUNT intact, only the CONTENT wrong (bisected over 4096..131072 against an FNV-1a of
the source file; filed as cyrius issues/2026-09-13-agnos-large-string-literal-loses-first-byte).
✅ FIXED in cyrius 6.6.4 (2026-09-14): the lexer packed `(pool offset << 16) | length`, so a
length >= 65536 OR-ed into its own offset; widened to `<< 32`. Re-measured under 6.6.4: the
repro exits 0 and a SINGLE 410,820-byte literal of this face compiles byte-exact. The chunks
stay anyway — a consumer that reads bytes it has not hashed is trusting the compiler again,
and the boot-time verify a chunked module makes cheap is what caught the last one.
Python stdlib only — no fonttools. The face is embedded UNMODIFIED (no subsetting), which is
what keeps an OFL face's Reserved Font Name intact; see fonts/LICENSE-LiberationFonts.
"""
import hashlib
import os
import struct
import sys

CHUNK = 4096
FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3
MASK = (1 << 64) - 1


def fnv1a(data):
    h = FNV_OFFSET
    for b in data:
        h = ((h ^ b) * FNV_PRIME) & MASK
    return h


def u16(data, off):
    return struct.unpack_from('>H', data, off)[0]


def u32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def sfnt_summary(data):
    """(sfntVersion, numTables, tags, spans) — enough to refuse a CFF face up front.

    spans maps each tag to its FIRST directory record's (offset, length), the record
    rekha_find_table resolves. Raises ValueError on a file too short for the offset table,
    a directory that runs past EOF, or any table span outside the file (or overlapping the
    header + directory) — never a traceback, never a module generated from a truncated face.
    """
    n = len(data)
    if n < 12:
        raise ValueError('%d bytes is shorter than the 12-byte SFNT offset table' % n)
    ver, num = struct.unpack_from('>IH', data, 0)
    dir_end = 12 + 16 * num
    if dir_end > n:
        raise ValueError('table directory (%d records, ends at %d) runs past EOF (%d bytes)'
                         % (num, dir_end, n))
    tags = []
    spans = {}
    for i in range(num):
        rec = 12 + 16 * i
        tag = data[rec:rec + 4].decode('latin-1')
        off, length = u32(data, rec + 8), u32(data, rec + 12)
        if off < dir_end or off + length > n:
            raise ValueError('table %s spans %d..%d, outside %d..%d'
                             % (cyr_escape(data[rec:rec + 4]), off, off + length, dir_end, n))
        tags.append(tag)
        spans.setdefault(tag, (off, length))
    return ver, num, tags, spans


def has_unicode_fmt4(data, spans):
    """True when rekha's cmap selection finds a format-4 subtable rekha_char_to_glyph can read.

    Mirrors rekha_cmap_subtable (src/cmap.cyr): walk the encoding records in order, keep the
    LAST platform 0 (any encoding) or (3,1) record whose subtable reads format 4, all bounded by
    the cmap table's end; the winner must then hold its 14-byte header and all four segment
    arrays inside that bound, with segCountX2 >= 2.
    """
    cmap, clen = spans['cmap']
    end = cmap + clen
    if cmap + 4 > end:
        return False
    best = 0
    for i in range(u16(data, cmap + 2)):
        rec = cmap + 4 + i * 8
        if rec + 8 > end:
            break
        plat, enc = u16(data, rec), u16(data, rec + 2)
        sub = cmap + u32(data, rec + 4)
        if (plat == 0 or (plat == 3 and enc == 1)) and sub + 2 <= end and u16(data, sub) == 4:
            best = sub
    if best == 0 or best + 14 > end:
        return False
    segc2 = u16(data, best + 6)
    # endCode[] @ +14, reservedPad, startCode[], idDelta[], idRangeOffset[] — the last must end in cmap
    range_arr = best + 14 + segc2 + 2 + segc2 + segc2
    return segc2 >= 2 and range_arr + segc2 <= end


def cyr_escape(raw):
    """bytes -> text safe inside a Cyrius "..." literal AND a # comment line.

    Printable ASCII passes through unchanged (so an ordinary filename emits exactly as before);
    '"', '\\' and every other byte — a newline would end the comment and start a code line —
    become \\xNN.
    """
    return ''.join(chr(b) if 0x20 <= b <= 0x7e and b not in (0x22, 0x5c) else '\\x%02x' % b
                   for b in raw)


def main():
    if len(sys.argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    try:
        with open(src, 'rb') as f:
            data = f.read()
        ver, num, tags, spans = sfnt_summary(data)
    except (OSError, ValueError) as e:
        sys.stderr.write('refusing %s: %s\n' % (src, e))
        return 1
    n = len(data)
    if ver not in (0x00010000, 0x74727565):          # 0x00010000 / 'true' — glyf outlines only
        sys.stderr.write('refusing %s: sfntVersion 0x%08x is not a glyf face (rekha rejects CFF)\n' % (src, ver))
        return 1
    for need in ('glyf', 'loca', 'cmap', 'hhea', 'hmtx', 'head', 'maxp'):
        if need not in tags:
            sys.stderr.write('refusing %s: no %r table\n' % (src, need))
            return 1
    if not has_unicode_fmt4(data, spans):
        sys.stderr.write('refusing %s: no usable Unicode (platform 0, or 3/1) format-4 cmap subtable — '
                         'rekha_char_to_glyph would map every codepoint to .notdef\n' % src)
        return 1
    chunks = [data[i:i + CHUNK] for i in range(0, n, CHUNK)]
    h = fnv1a(data)
    sha = hashlib.sha256(data).hexdigest()
    name_b = os.fsencode(os.path.basename(src))     # name_len is a BYTE length
    name = cyr_escape(name_b)
    tag_list = ' '.join(cyr_escape(t.encode('latin-1')) for t in tags)
    # ⛔ Atomic, UTF-8, LF: the header carries U+2014/U+00B7, so a locale-encoded open(out, 'w')
    # truncated the target and THEN raised under a non-UTF-8 locale (a 0-byte face_data.cyr),
    # and text mode would write CRLF on Windows and break CI's byte compare.
    tmp = out + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            w = f.write
            w('# === rekha — freestanding default-face data (GENERATED, do not hand-edit) ===\n')
            w('#\n')
            w('# Generated by scripts/face2cyr.py from fonts/%s\n' % name)
            w('#   %d bytes · sha256 %s\n' % (n, sha))
            w('#   sfntVersion 0x%08x · %d tables: %s\n' % (ver, num, tag_list))
            w('#   FNV-1a-64 of the whole face: 0x%016x\n' % h)
            w('#\n')
            w('# THIS FILE IS FREESTANDING. It uses NO stdlib, NO heap, NO syscalls — only string\n')
            w('# literals, integer arithmetic and the load8/store8 intrinsics — so a freestanding\n')
            w('# kernel (agnos: `[deps] stdlib = []`, vendored klib/) can concatenate it exactly as it\n')
            w('# consumes kashi\'s src/font_data.cyr. Do NOT add includes here.\n')
            w('#\n')
            w('# The face is embedded UNMODIFIED and licensed under the SIL Open Font License 1.1 —\n')
            w('# Copyright (c) 2012 Red Hat, Inc., with Reserved Font Name Liberation; digitized data\n')
            w('# copyright (c) 2010 Google Corporation. The licence text ships next to the source face\n')
            w('# as fonts/LICENSE-LiberationFonts and MUST travel with any redistribution of these bytes.\n')
            w('# rekha itself is GPL-3.0-only; the OFL permits bundling with software under any licence.\n')
            w('#\n')
            w('# Storage model: %d string literals of %d bytes (the tail shorter), reachable by index\n' % (len(chunks), CHUNK))
            w('# through rekha_face_default_chunk(i). 4 KB chunks — history: cyrius 6.6.3 emitted a string\n')
            w('# literal of >= 65536 bytes read from its SECOND byte on alternate literals, silently (rc=0,\n')
            w('# count intact, content wrong); found by bisection here, filed, FIXED in cyrius 6.6.4 (the\n')
            w('# lexer packed a 16-bit length into the pool offset). The chunks stay: a consumer assembles\n')
            w('# them into ONE contiguous buffer with rekha_face_default_copy() and MUST check\n')
            w('# rekha_face_default_verify() before exposing the result — that verify is what found the last\n')
            w('# compiler defect and is the only thing that would find the next one.\n')
            w('#\n')
            w('# Consumption contract (agnos kernel):\n')
            w('#   var n = rekha_face_default_len();\n')
            w('#   rekha_face_default_copy(dst, cap)        -> n, or -1 when cap < n\n')
            w('#   rekha_face_default_verify(dst, n)        -> 1 when FNV-1a matches, else 0\n')
            w('#   rekha_face_default_name() / _name_len()  -> the source filename\n')
            w('\n')
            w('fn rekha_face_default_len() { return %d; }\n' % n)
            w('fn rekha_face_default_chunk_size() { return %d; }\n' % CHUNK)
            w('fn rekha_face_default_chunk_count() { return %d; }\n' % len(chunks))
            w('fn rekha_face_default_fnv1a() { return 0x%016x; }\n' % h)
            w('fn rekha_face_default_name() { return "%s"; }\n' % name)
            w('fn rekha_face_default_name_len() { return %d; }\n' % len(name_b))
            w('\n')
            w('# Byte length of chunk i (every chunk is full-size except the last).\n')
            w('fn rekha_face_default_chunk_len(i) {\n')
            w('    if (i < 0) { return 0; }\n')
            w('    if (i >= %d) { return 0; }\n' % len(chunks))
            w('    if (i == %d) { return %d; }\n' % (len(chunks) - 1, len(chunks[-1])))
            w('    return %d;\n' % CHUNK)
            w('}\n')
            w('\n')
            w('# Copy the whole face into dst (cap bytes). Returns the face length, or -1 if cap is too small.\n')
            w('fn rekha_face_default_copy(dst, cap) {\n')
            w('    var n = rekha_face_default_len();\n')
            w('    if (cap < n) { return 0 - 1; }\n')
            w('    var i = 0;\n')
            w('    var off = 0;\n')
            w('    while (i < rekha_face_default_chunk_count()) {\n')
            w('        var p = rekha_face_default_chunk(i);\n')
            w('        var l = rekha_face_default_chunk_len(i);\n')
            w('        var j = 0;\n')
            w('        while (j < l) { store8(dst + off + j, load8(p + j)); j = j + 1; }\n')
            w('        off = off + l;\n')
            w('        i = i + 1;\n')
            w('    }\n')
            w('    return off;\n')
            w('}\n')
            w('\n')
            w('# FNV-1a-64 over buf[0..len) compared to the generator\'s hash of the source file.\n')
            w('# 1 = the bytes are the face, byte-exact; 0 = do not expose them.\n')
            w('fn rekha_face_default_verify(buf, len) {\n')
            w('    if (len != rekha_face_default_len()) { return 0; }\n')
            w('    var h = 0x%016x;\n' % FNV_OFFSET)
            w('    var j = 0;\n')
            w('    while (j < len) { h = (h ^ load8(buf + j)) * 0x%x; j = j + 1; }\n' % FNV_PRIME)
            w('    if (h == rekha_face_default_fnv1a()) { return 1; }\n')
            w('    return 0;\n')
            w('}\n')
            w('\n')
            w('# Pointer to chunk i\'s bytes (a string literal in .rodata; NOT NUL-safe — use the length).\n')
            w('fn rekha_face_default_chunk(i) {\n')
            for i, c in enumerate(chunks):
                w('    if (i == %d) { return "%s"; }\n' % (i, ''.join('\\x%02x' % b for b in c)))
            w('    return 0;\n')
            w('}\n')
        os.replace(tmp, out)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print('%s: %d bytes, %d chunks, fnv1a 0x%016x, sha256 %s' % (out, n, len(chunks), h, sha))
    return 0


if __name__ == '__main__':
    sys.exit(main())
