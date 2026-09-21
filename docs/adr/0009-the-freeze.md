# 0009 — The freeze: `public fn` in `src/`, a `private` bundle, and a promise the compiler keeps

**Status**: Accepted
**Date**: 2026-09-21 (0.9.0)

## Context

Through 0.8.2 the API boundary was undeclared: 137 `# @public` comments against 465 functions,
where one comment covered a run of accessors and `@internal` was a module-header tag, so
neither number counted anything; `rekha_font_open` itself carried no marker; every consumer of
`dist/rekha.cyr` could link every internal (roadmap, "0.9.0 — the freeze"). Cyrius 6.5.0 added
file-level visibility: a bare `private` line makes a file private-by-default, `public fn` /
`public var` re-expose items, and reaching a private item from another file is a compile error.
`cyrius distlib` concatenates the module list into one file, while the tests include the
`src/` chain where each module is its own file.

## Decision

Every promised function is `public fn` and every promised constant `public var` in `src/`
(a no-op there, because no `src/` file is private, so the tests keep every internal), under a
`# @public` doc comment; a new module `src/freeze.cyr` — one code line, `private` — is first
in both `[lib]` lists and is not included by `src/lib.cyr`. The bundles therefore begin with
`private`, and a consumer reaches exactly the public surface. `scripts/api_surface.py` pins the
conventions around the keyword (spelling, governance by a doc comment, no orphaned comments,
`freeze.cyr` first, the bundles' first code line, docs coverage, `docs/api/surface.txt`), and
CI compiles a probe against each bundle that must **fail** on three internal names. What is
public was decided by one rule: a call or constant a consumer of "what the glyph is" needs, or
that README or a consumer already used. `rekha_hint_run` (the test range), the stack readers
and `rekha_hint_load_simple` stayed internal; the interpreter's observability readers stayed
public. Constants are public only where a consumer compares against the *name* (bits, indices,
ids, sizes to allocate by); caps are stated as values.

## Consequences

- **Positive** — `grep -c '^public fn' src/*.cyr` is the count of public functions, exactly;
  the promise is enforced in the artefact a consumer takes, at compile time, with zero binary
  delta (measured byte-identical with and without `private`); a consumer may name its own
  `rekha_rd_u16` without a collision.
- **Negative** — consumers need cyrius ≥ 6.6.6 (the one-leaf sidecar already did, ADR 0003);
  a consumer that reached an internal through the bundle breaks at compile time — which is the
  point. `programs/woff_dist_test.cyr`, which is a consumer's include chain, lost fourteen
  internals and carries its own byte helpers now.
- **Neutral** — the `RekhaOutline` layout, the `REKHA_GS_*` slot order and the `REKHA_FONT_SIZE`
  name (not its value) are frozen with the surface; `docs/api/README.md` states the promise.

## Alternatives considered

- **Comment markers only** (`# @public` / `# @internal` per function, a script gate): declares
  nothing the compiler checks; the miscount that motivated the freeze came from comments.
- **A `_rekha_` prefix on internals** (kashi's way): ~290 renames across every file and test,
  enforcing nothing. Rejected.
- **`private` in each `src/` module**: file-level semantics would cut the modules off from
  each other and the tests from every seam. Rejected; the concatenation is what makes one
  `private` line the whole freeze.
