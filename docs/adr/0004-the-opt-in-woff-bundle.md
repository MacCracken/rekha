# 0004 — The opt-in WOFF bundle: `dist/rekha-woff.cyr` carries both web containers; `dist/rekha.cyr` never needs sankoch

**Status**: Accepted
**Date**: 2026-09-21 (decided 0.4.2 / 0.4.6; recorded at 0.9.0)

## Context

WOFF 1.0 needs zlib (`zlib_decompress_capped`, sankoch ≥ 2.7.13) and WOFF2 needs Brotli
(`brotli_decompress_capped`, sankoch ≥ 2.8.0). A consumer drawing text from a face on disk
needs neither, and sankoch in `[deps] stdlib` would be a leaf every consumer vendors (ADR 0003).

## Decision

`src/woff.cyr` and `src/woff2.cyr` live only in the `[lib.woff]` profile →
`dist/rekha-woff.cyr` with its own sidecar (`string` + `sankoch`). A consumer that wants either
container takes that bundle **instead of** `dist/rekha.cyr` and brings `sync` + `sankoch`
itself. One bundle for both containers, deliberately: sankoch's own ADR 0001 shaped its
`[lib.woff]` profile the same way, so a consumer links one sankoch and gets both.
`rekha_font_open_any` (the four-byte dispatcher) lives in that bundle.

## Consequences

- **Positive** — the base bundle stays a pure SFNT parser with one leaf.
- **Negative** — two bundles to keep in sync (`cyrius distlib --all`, gated) and a second
  sidecar to pin; `programs/woff_dist_test.cyr` exists only to prove the profile actually folds
  `woff2.cyr` in, which `distlib --check` cannot see.
- **Neutral** — the WOFF openers have no `_why` twins yet (roadmap, pinned).

## Alternatives considered

- **WOFF in the base bundle**: sankoch for everyone. Rejected.
- **Two profiles, one per container**: a consumer with both vendors sankoch twice over. Rejected,
  following sankoch's own shape.
