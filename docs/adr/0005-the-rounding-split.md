# 0005 — The hint machine rounds half away from zero; everything else rounds half up

**Status**: Accepted
**Date**: 2026-09-21 (decided 0.8.0; recorded at 0.9.0)

## Context

Every differential since 0.5.0 was measured against fontTools, whose `otRound` is half up:
`rekha_fx_mul` (`src/var.cyr`), the `_px` advances (`(adv × px + upem/2) / upem`), the composite
F2Dot14 transform. The hinting layer's reference is not fontTools but the interpreter a hinted
glyph was drawn against: FreeType's `FT_MulFix` / `FT_DivFix` take the absolute value, add a
half and re-sign (`src/hint.cyr:65-71`).

## Decision

`src/hint.cyr` rounds half away from zero (`rekha_hint_mulfix`); the rest of rekha keeps half
up. Inside the hinting layer the phantom points, a composite's offsets and the published
advance use FreeType's floor form `(v + 32) & −64` instead, as its loader does
(`src/hint.cyr:72-74`).

## Consequences

- **Positive** — bit-exact with FreeType 2.14.3 on every face measured (ADR 0007).
- **Negative** — two rounding rules in one library. They differ only on a negative value landing
  exactly on .5 — at 12 ppem, five of Liberation Sans's control values — and `docs/api/hint.md`
  says so.
- **Neutral** — per-glyph rounding halves the bias but does not stop drift in a run: sum the
  16.16 advances (`rekha_*_advance_fx`) and round once.

## Alternatives considered

- **Half up everywhere**: five wrong control values at 12 ppem, and every hinted glyph that reads
  them wrong. Rejected.
- **Half away from zero everywhere**: breaks every measured `_px` answer against fontTools for
  no consumer benefit. Rejected.
