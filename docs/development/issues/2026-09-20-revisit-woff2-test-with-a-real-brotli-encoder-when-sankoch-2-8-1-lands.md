# Revisit the WOFF2 suite with a REAL Brotli encoder once sankoch 2.8.1 lands

**Status:** 🟡 **OPEN — waiting on a dependency, not on a decision.**
**Filed:** 2026-09-20, by rekha, at the close of **0.4.6 (WOFF2)**.
**Blocked on:** sankoch **2.8.1**, the Brotli encoder. sankoch's roadmap has it next and says
*"Nothing preempts 2.8.1"*, with fuzz round-trips (encode → both decoders) in its own test plan; ADR
`0001-brotli-decoder-placement.md` already reserves the encode side as *"its own decision about
profiles"*. Nothing is asked of sankoch here — this is rekha's own follow-up, recorded so the gap
does not quietly become permanent.
**Affects:** `programs/woff2_test.cyr` only. `src/woff2.cyr` needs no change and is not suspected.
**Severity:** a **coverage gap in CI**, not a defect. Every claim 0.4.6 makes is true; one class of
input is reached today only by a measurement that CI cannot run.

## What 0.4.6 had to do, and why

A WOFF2's font data is one Brotli stream. sankoch **2.8.0 decodes Brotli and does not encode it**, so
the suite cannot compress anything, and no converted font is committed to this repo. So
`programs/woff2_test.cyr` emits RFC 7932 **stored** meta-blocks by hand — the uncompressed form —
and group S proves that emitter against sankoch's own decoder at three sizes spanning the 4-, 5- and
6-nibble MLEN forms before anything else trusts it. That is exactly what the roadmap item meant by
testing WOFF2 *"on transformed-but-uncompressed tables"*: the **tables** get the real glyf / loca and
hmtx transforms, and the **Brotli layer around them** is stored.

## What that leaves uncovered, precisely

The WOFF2 side is covered. What a stored stream never exercises is the part of sankoch that a real
`.woff2` depends on:

- compressed meta-block headers, prefix codes (simple and complex), the table builder;
- context maps and IMTF, block switching, the command loop, back-references and the window;
- the interaction between rekha's `brotli_decompress_capped` output cap and a stream whose
  decompressed size is only known from the table directory.

⚠ **It is not untested — it is tested somewhere CI cannot reach.** 0.4.6's headline measurement drove
all of it: 280 unique real `.woff2` files on the dev host, each one a genuinely compressed stream,
reconstructed identically to fontTools 4.65.0 across 111,732 glyphs. But those files are not
committed (size and licensing), fontTools is not a dependency of this repo, and the corpus is a
property of one machine. **CI sees only stored streams.**

## What to do when 2.8.1 ships

1. Add `brotli_compress` beside `brotli_store` in `programs/woff2_test.cyr` and take a **third
   container variant** through every existing group, so groups A, B, R and G all run once over a
   genuinely compressed stream.
2. ⛔ **Keep the stored emitter.** A stored meta-block is a legal RFC 7932 encoding that a
   conforming WOFF2 producer may emit, so rekha must go on accepting one; deleting `brotli_store`
   would drop a real input class rather than upgrade it. Group S stays as its gate.
3. Check the pin: `[lib.woff]`'s sankoch floor is **2.8.0** today (`README.md`, `cyrius.cyml`). Only
   the TEST would need 2.8.1 — `src/woff2.cyr` decodes and never compresses — so the published floor
   should stay where it is unless something in `src/` starts to need the encoder. Say so explicitly
   in that release's CHANGELOG, because "the tests need a newer sankoch than the bundle does" is the
   kind of thing a consumer reads backwards.
4. While there: re-run the dev-host differential and record the file and glyph counts again, so the
   two measurements (CI's synthetic containers and the host's real ones) are dated together.

## Pointers

- `programs/woff2_test.cyr` — `w2bw_init` / `w2bw_bits` / `w2bw_align`, `brotli_store`, group S
  (`t_store`), and `w2_assemble`, which is the single place a container's compressed block is
  produced and therefore the only place variant 3 has to reach.
- `src/woff2.cyr` — `rekha_woff2_inflate` is the only caller of sankoch, one call, output-capped to
  the exact size the directory declares.
