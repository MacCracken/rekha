# 0002 — Refuse, don't guess: a refusal is an empty answer with a reason, never a plausible wrong one

**Status**: Accepted
**Date**: 2026-09-21 (the policy is 0.3.x; measured at 0.8.2; recorded at 0.9.0)

## Context

Font files are untrusted input, and a parser that guesses produces a *plausible* wrong glyph — a
descender at the wrong height, a half-varied outline, a stack shorter than the font asked for
computing a different glyph silently (`src/hint.cyr:98-100`, `src/vert.cyr:28-32`,
`src/gvar.cyr:33`). A wrong glyph is worse than a missing one because nothing downstream can
tell. FreeType's default mode reads a missing control value as 0 and skips a bad point; its
pedantic mode refuses.

## Decision

A malformed table, a lying offset, a cap exceeded or bytecode that contradicts itself yields
the family's sentinel (0, −1, an empty outline, an empty path) and a `RekhaErrCode` with a
detail string on the handle (ADR 0006). Caps are refusals, not clamps, and a composite's cap is
a *budget* (64 loads / 16,384 points per `rekha_load_glyph`), not a depth, because depth alone
lets an acyclic fan-out decode `sum N^L` bodies (`src/glyf.cyr:105-122`). **Hinting corollary:**
a refusal inside any program of a glyph load unhints the whole glyph — it is reloaded scaled
and unhinted, never left partially hinted (`src/hint.cyr:25-27`, `rekha_hint_glyph`).

## Consequences

- **Positive** — a consumer can trust every non-sentinel answer; the hostile corpus
  (`programs/hostile_test.cyr`) can test a single invariant.
- **Negative, measured** — rekha refuses where FreeType's default mode hints: 17,158 of
  2,812,516 loads (0.61 %) across 50 host faces at 9 / 11 / 13 / 20 ppem, none ASCII;
  AdwaitaMono-Regular refuses 2,624 of 8,818 glyphs at 9 of 25 ppems (its programs read a
  control value past the table). Each draws scaled and unhinted, with the instruction named
  through `rekha_hint_error` (CHANGELOG 0.8.2). The roadmap's "revisit if a real face trips it"
  trigger fired at 0.8.2 and the policy was kept; the alternative — FreeType's default-mode
  fallbacks in the glyph range only — is named in the roadmap for a consumer to ask for.
- **Neutral** — what is *skipped* rather than refused is the spec's own tolerance: an unknown
  GPOS lookup type, an MVAR tag with no reader, a broken `cmap` record ranked out.

## Alternatives considered

- **FreeType's default-mode fallbacks**: hints AdwaitaMono's arrows at 9 ppem, and draws a
  glyph the bytecode did not intend everywhere else the fallback fires. Kept as the named
  alternative, not taken.
- **Clamp instead of refuse** (a shorter stack, a smaller zone): computes a different glyph
  silently. Rejected.
