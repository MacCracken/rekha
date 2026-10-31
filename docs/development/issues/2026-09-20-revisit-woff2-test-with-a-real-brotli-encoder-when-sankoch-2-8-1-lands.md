# Revisit the WOFF2 suite with a REAL Brotli encoder once sankoch's encoder lands (now 2.8.4)

**Status:** ✅ **RESOLVED at 1.1.2** (steps 1–3 below; step 4 not re-run — see the 1.1.2 note).
Was: 🟢 OPEN and UNBLOCKED — nothing is waited on; the steps below can be taken.
Reviewed 2026-10-30 at rekha 1.1.1: the cyrius 6.7.18 pin carries sankoch 2.8.9, encoder included.
Reviewed 2026-10-29 at 1.1.0: sankoch 2.8.4 had shipped the encoder, and rekha's 6.7.9 pin predated
the first stdlib that folds it (6.7.11). Reviewed 2026-10-13 at 1.0.0: the trigger this file was
filed against fired by NUMBER and not by CONTENT.
**Filed:** 2026-09-20, by rekha, at the close of **0.4.6 (WOFF2)**. The filename keeps the original
`2-8-1` slug so links stay stable; the trigger is **2.8.4**.
**Blocked on:** nothing since 1.1.1. It was sankoch's Brotli encoder, **renumbered 2.8.4** (✅
shipped 2026-10-13), AND a cyrius pin whose stdlib snapshot folds it (✅ cyrius 6.7.18, pinned at
1.1.1) —
rekha's suites take `lib/sankoch.cyr` from the toolchain pin, never from a git dep. sankoch's
roadmap: *"Nothing preempts 2.8.4"*, with fuzz round-trips (encode → both
decoders) in its own test plan; ADR `0001-brotli-decoder-placement.md` reserves the encode side as
*"its own decision about profiles"*. Nothing is asked of sankoch here — this is rekha's own
follow-up, recorded so the gap does not quietly become permanent.
**Affects:** `programs/woff2_test.cyr` only. `src/woff2.cyr` needs no change and is not suspected.
**Severity:** a **coverage gap in CI**, not a defect, and not a 1.0.0 blocker — it is test-only
and every step of the plan below is additive. Every claim 0.4.6 makes is true; one class of input
is reached today only by a measurement that CI cannot run.

## Resolved 2026-10-30 (rekha 1.1.2, cyrius 6.7.18)

- **Step 1, taken.** `programs/woff2_test.cyr` has the third variant: `g_w2_compress = 1` sends the
  table-data block through sankoch's `brotli_compress` in `w2_assemble`, and groups A, B, R and G
  (`t_null`, `t_xform`, `t_refuse`, `t_guard`) run again over genuinely compressed streams — 191
  checks became 293, both DCE modes. Group C pins that the variant really compresses (the null
  container is smaller than its stored twin) and that it decodes to the embedded face's digest.
- **Step 2, kept.** `brotli_store` and group S stay: a stored stream is a legal encoding rekha must
  go on accepting, and it is the gate the rest of the stored passes stand on.
- **Step 3, the floor.** Nothing in `src/` compresses; only the test needs the encoder, so the
  published `[lib.woff]` sankoch floor is unchanged. The 1.1.2 CHANGELOG says so.
- **Also (1.1.2):** `programs/mutate_test.cyr` takes a Brotli-compressed WOFF2 (`woff2z`) and a
  stored, transformed one (`woff2x`) through 1,000 mutants each; its first run found the declared
  size cap rekha now enforces (`REKHA_WOFF2_MAXSIZE`, 64 MB, FreeType's).
- **Step 4, NOT re-run.** fontTools is not on the dev host this release ran on, so the 280-file
  differential against fontTools 4.65.0 is still dated 0.4.6. ⚠ The independence caveat stands: an
  encoder and decoder from one author can share a mistake; the reference-encoder fixture remains
  the maintainer's call.

## Reviewed 2026-10-30 (rekha 1.1.1, cyrius 6.7.18) — unblocked here

- **The pinned stdlib encodes.** `~/.cyrius/versions/6.7.18/lib/sankoch.cyr` is `# Version: 2.8.9`
  and defines `brotli_compress_bound`, `brotli_compress` and `brotli_compress_level`
  (`grep -c '^fn brotli_compress'` is 3). rekha's suites already take this file from the toolchain
  pin (`programs/woff2_test.cyr` includes `lib/sankoch.cyr`), so step 1 below needs no manifest or
  dependency change.
- rekha's suites pass against 2.8.9 unchanged: `woff2_test` 186 checks, `woff_test` 124, both DCE
  modes, output byte-identical to 1.1.0's on 6.7.9.
- **Not taken at 1.1.1**, a release that changed only the pin. ⚠ One thing the plan below has to
  keep in view: sankoch's encoder round-tripped through sankoch's decoder is not an independent
  check of that decoder — it covers the compressed paths the stored stream never reaches, but a
  mistake both halves share would pass. The reference-encoder alternative below is the
  independent one.

## Reviewed 2026-10-29 (rekha 1.1.0, cyrius 6.7.9) — unblocked upstream, not yet here

- **sankoch 2.8.4 shipped the Brotli encoder** (2026-10-13, `src/brotli_enc.cyr`, sankoch ADR
  `0002-brotli-encoder-placement-and-quality.md`), listed in its `[lib]` — the full bundle rekha's
  suites take as the stdlib's `lib/sankoch.cyr`.
- **The cyrius 6.7.9 stdlib rekha now pins carries `# Version: 2.8.3`**, with no `brotli_compress`
  (`grep -c '^fn brotli_compress' ~/.cyrius/versions/6.7.9/lib/sankoch.cyr` is 0). 6.7.10 also
  carries 2.8.3; **6.7.11 is the first that folds the encoder** (sankoch 2.8.7: `brotli_compress`,
  `brotli_compress_level`, `brotli_compress_bound`), and 6.7.18 carries 2.8.9.
- rekha's suites pass against 2.8.3 unchanged: `woff2_test` 186 checks, `woff_test` 124, both DCE
  modes, output byte-identical to 1.0.0's on 6.6.20.
- **So the steps below wait on rekha's next pin move, to cyrius >= 6.7.11**, which will carry its
  own migration notes (cyrius `docs/development/ecosystem-migration.md`, 6.7.10 onward). Nothing is
  asked of sankoch any more. The alternative below (a committed reference-encoder WOFF2) stays the
  maintainer's call.

## Reviewed 2026-10-13 (rekha 1.0.0, cyrius 6.6.20) — why this stayed open

- **sankoch 2.8.1 shipped (2026-10-06) as a TOOLCHAIN release with no source change** — the cyrius
  6.6.18 regeneration wave (sankoch CHANGELOG [2.8.1]: *"every codec compiles and behaves exactly
  as at 2.8.0 … The 2.8.x feature ladder (Brotli encoder next) moves up one patch"*). 2.8.2 was a
  rename beside cyrius 6.7.5's `loop`, 2.8.3 the 6.7.5 pin; its roadmap now reads *"Brotli encoder
  (2.8.4)"*. sankoch's tree at 2.8.3 defines no `brotli_compress` (`grep -rn brotli_compress
  ../sankoch/src` is empty).
- **The cyrius 6.6.20 stdlib rekha now pins carries `# Version: 2.8.1`** — the decoder only
  (`brotli_decompress` / `brotli_decompress_capped`, `~/.cyrius/versions/6.6.20/lib/sankoch.cyr`).
  rekha's suites pass against it unchanged: `woff2_test` 186 checks, `woff_test` 124, both DCE modes.
- **So none of the four steps below can be taken yet.** When 2.8.4 tags, rekha also needs a cyrius
  pin that folds it: 2.8.3 reached the stdlib through cyrius 6.7.6's refold, so expect a 6.7.x pin
  move first — with its own migration notes (cyrius `ecosystem-migration` for 6.7.x).
- **The alternative, named and not taken here**: commit a genuinely compressed WOFF2 built ONCE by
  the reference `brotli` (via fontTools, on a dev host) from `fonts/LiberationSans-Regular.ttf`, and
  diff every glyph it decodes to against the committed `.ttf` through rekha itself. It closes the
  gap without waiting, with an encoder independent of the decoder under test — which a sankoch
  round-trip is not. Against it: it reverses "no converted font is committed to this repo", adds a
  binary fixture regenerated by hand (like the hinting vectors), and the face's OFL Reserved Font
  Name ("Liberation") makes a converted copy a licensing question to answer first (OFL-FAQ 2.2
  allows a WOFF of an unmodified font; whether a WOFF2 with the glyf transform qualifies is not
  settled here). The maintainer's call; this file records it so either route is a decision.

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

## What to do when 2.8.4 ships (and a cyrius pin folds it)

1. Add the encoder's entry point (sankoch names it; `brotli_compress` is the guess) beside `brotli_store` in `programs/woff2_test.cyr` and take a **third
   container variant** through every existing group, so groups A, B, R and G all run once over a
   genuinely compressed stream.
2. ⛔ **Keep the stored emitter.** A stored meta-block is a legal RFC 7932 encoding that a
   conforming WOFF2 producer may emit, so rekha must go on accepting one; deleting `brotli_store`
   would drop a real input class rather than upgrade it. Group S stays as its gate.
3. Check the pin: `[lib.woff]`'s sankoch floor is **2.8.0** today (`README.md`, `cyrius.cyml`). Only
   the TEST would need 2.8.4 — `src/woff2.cyr` decodes and never compresses — so the published floor
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
