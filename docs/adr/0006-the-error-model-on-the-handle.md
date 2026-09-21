# 0006 — Why a call refused lives on the handle: a code and a static detail, no record, no global

**Status**: Accepted
**Date**: 2026-09-21 (decided 0.7.0; recorded at 0.9.0)

## Context

`RekhaErr` was declared `@public` from 0.1.0 and produced by nothing for six releases: every
refusal collapsed to a sentinel, and `rekha_advance_width` answered 0 for "no hhea", "truncated
hmtx" and "this glyph is zero-width" alike. Worse, `rekha_err_new` called `sd_alloc(16)`, so
constructing an out-of-memory error allocated (`src/error.cyr` header).

## Decision

The record and its four functions are gone (removed before the freeze, so no promise was
broken). A `RekhaErrCode` and a static-cstring detail pointer live **on the font handle**, read
by `rekha_font_error` / `rekha_font_error_detail`, cleared at the top of every public call
that can set them. The open family has no handle to record into, so `rekha_font_open_why` /
`rekha_font_open_index_why` take a caller's i64 slot. The hint context mirrors the model with
`rekha_hint_error` / `_detail` / `_clear`, and a standing `fpgm` / `prep` refusal is mirrored
onto the font handle. Nine codes, `rekha_err_name` never null and never allocated.

## Consequences

- **Positive** — an error path that cannot fail the way the thing it reports failed; 0 B.
- **Negative** — **one handle, one thread** becomes a stated obligation: the slot is per handle,
  and Cyrius 6.6.6 has no TLS, so a global would have been unfixable (`src/sfnt.cyr`, the
  error-slot notes).
- **Neutral** — "this is not a success test": the return value says *whether* a call refused,
  the slot says *why*; read them in that order. Pinned: the CFF interpreter's own refusals and
  the WOFF opens are not wired to it yet (roadmap).

## Alternatives considered

- **A global last-error**: not thread-fixable without TLS. Rejected.
- **Keep `RekhaErr` as an output record**: allocates to report, and nothing produced it. Rejected.
