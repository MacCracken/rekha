# 0001 — rekha emits paths and allocates only through `sd_alloc`, which has no free

**Status**: Accepted
**Date**: 2026-09-21 (decided 0.1.0 for the paths, 0.3.10 for the allocator; recorded at 0.9.0)

## Context

rekha's job is "what the glyph is": font bytes in, outlines and the numbers that place them out.
The AGNOS draw stack already had a rasterizer, sadish, with one fixed-point convention (16.16)
and, from sadish 0.5.5, one allocation knob: `sd_alloc`, a hook a consumer sets — a per-frame
arena in dhancha's case. Before 0.3.10 rekha's outline scratch came from the stdlib bump
allocator, which has no `free`, and dhancha measured 136 B leaked per `rekha_char_to_sdpath`
per glyph per frame under its frame arena (its filing, 2026-09-13; `src/glyf.cyr:44-48`).

## Decision

rekha never rasterizes and never allocates on its own: every path it produces is a sadish
`SdPath` positioned in 16.16 (`src/glyf.cyr:39-43`), and every byte it allocates goes through
`sd_alloc` — the handle, the outline record and its arrays, the variation arrays, the hint
context, the GPOS lookups, the WOFF scratch (`grep -c sd_alloc src/*.cyr`). There is no
`rekha_close`: the seam has no free, so rekha has nothing to free with.

## Consequences

- **Positive** — one allocation policy for the whole draw stack, owned by the leaf; a consumer
  that scopes an arena per frame reclaims everything a frame drew. Readers allocate 0 B.
- **Negative** — lifetimes are the consumer's: a handle, a warm hint context and the first
  varied glyph load must happen *outside* a per-frame hook, or the pointer dangles when the
  arena resets (`src/glyf.cyr:52-58`; the five hinting rules in `docs/api/hint.md`). The hint
  context is one allocation cached on the handle and re-scaled in place, never reallocated,
  or a size walk would leak one interpreter per size (`src/hint.cyr:133-144`).
- **Neutral** — a hook may refuse, and every `sd_alloc` and `sd_path_*` status is checked so a
  refused allocation returns 0 or an empty path, never a fault or a partial glyph
  (`src/glyf.cyr:59-65`; CHANGELOG 0.3.11). `cyrius fuzz --poison` cannot instrument the seam;
  `programs/hostile_test.cyr`'s sentinel differential is the substitute.

## Alternatives considered

- **Own the allocation** (stdlib `alloc`): what 0.3.9 did, and what leaked per frame. Rejected.
- **Add a `free` to the seam**: sadish's hook is deliberately allocate-only (an arena); a free
  would be a second policy. Rejected in favour of stating lifetimes.
- **A private rasterizer**: duplicates sadish and forks the fixed-point convention. Rejected.
