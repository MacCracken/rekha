# 0010 — The zero-leaf sidecar: a bundle's leaves are what the compile-verify proves

**Status**: Accepted (supersedes the sidecar half of [0003](0003-the-one-leaf-sidecar.md))
**Date**: 2026-10-13 (1.0.0, at the cyrius 6.6.20 pin)

## Context

Through cyrius 6.6.17, `cyrius distlib` seeded `dist/rekha.deps` from the include scan of
`src/lib.cyr` UNIONED with `[deps] stdlib`, and its compile-verify only ever added to that seed
(ADR 0003). rekha cut the list from nine leaves to one, `string`, and pinned it in CI. But the
base modules have called nothing in `lib/string.cyr` since 0.5.0 removed `rekha_err_print_name`
and its `strlen` (`git log -S'strlen(' -- src`): the one leaf was the union's doing, and every
consumer from 0.5.0 to 0.9.0 vendored it for nothing. rekha filed for the fix in cyrius
(proposal 2026-09-16, "declare test-only stdlib leaves"); it shipped in **6.6.18 as option 2** —
the compile-verify fixpoint, run on six targets, is the ONLY authority for a sidecar, and every
bundle opens with a compile-verified requires block (cyrius `ecosystem-migration-6.6.18.md`).

## Decision

rekha publishes what the fixpoint proves and pins that in CI. At 1.0.0: **`dist/rekha.cyr`
needs no stdlib leaf** — `distlib` writes no `dist/rekha.deps` at all — and
**`dist/rekha-woff.deps` is `string` + `sankoch`** (the WOFF modules call `memcpy`), which the
WOFF bundle also opens with as its requires block, ahead of `private`. `[deps] stdlib =
["string"]` stays, for rekha's own builds of the WOFF modules; it no longer reaches a consumer.
ADR 0003's other half stands: stdlib includes live only in `src/lib.cyr`, domain modules flat.

## Consequences

- **Positive** — a consumer of `dist/rekha.cyr` includes sadish and the bundle, nothing else.
  Measured at 1.0.0 on a cyrius **6.6.6** consumer (`cyrius deps` with a `[deps.rekha]` entry
  and no sidecar to read): both bundles build, the public probe links clean, and three internals
  are refused `is private to its file`.
- **Positive** — the WOFF bundle is raw-includable: `include "dist/rekha-woff.cyr"` brings its own
  `string` and `sankoch`.
- **Negative** — the sidecar now follows the toolchain's verify rather than a list rekha writes,
  so a cyrius change can move it. CI's leaf pin ("Pin the published leaf requirements") is what
  turns that into a deliberate act: base `[]`, WOFF `[string sankoch]`.
- **Neutral** — the consumer floor stays **cyrius 6.6.6**, now for the `private` / `public`
  keywords alone (ADR 0009); the `alloc`-through-`string` reason ADR 0003 gave no longer applies.
  `scripts/api_surface.py` accepts the requires block before `private` only when it is exactly
  the sidecar's leaves, in order.

## Alternatives considered

- **Keep shipping `string`** (a hand-written `dist/rekha.deps`): `distlib --check` would call it
  stale on every run, and it would go on taxing every consumer for a leaf nothing calls. Rejected.
- **Drop `string` from `[deps] stdlib`**: the WOFF modules' `memcpy` would then resolve only
  through auto-prepend in rekha's own tree. It changes nothing a consumer sees. Not taken.
