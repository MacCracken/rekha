# 0003 — The one-leaf sidecar: stdlib includes live only in `src/lib.cyr`, and the bundle needs `string`

**Status**: Accepted
**Date**: 2026-09-21 (decided 0.4.4 / 0.4.5; recorded at 0.9.0)

## Context

`cyrius distlib` writes `dist/rekha.deps` from the include scan of `src/lib.cyr` unioned with
`[deps] stdlib`, and every leaf named there is one each consumer must vendor, used or not.
Through 0.4.3 that was nine leaves for a bundle whose whole stdlib appetite is `strlen` and
`memcpy` (`cyrius.cyml`, the `[deps]` comment).

## Decision

Stdlib includes live only in `src/lib.cyr`; the domain modules are flat, which is what lets
distlib's strip-include concatenation compile. `[deps] stdlib = ["string"]` and nothing else;
the harness's eight leaves (fmt, alloc, vec, str, io, syscalls, assert, bench) are declared in
`programs/prelude.cyr`, one hop outside the scan; sankoch is deliberately not declared
(ADR 0004). CI pins the published sidecar, and changing it is a deliberate act with a CHANGELOG
line (`.github/workflows/ci.yml`, "Pin the published leaf requirements").

## Consequences

- **Positive** — `dist/rekha.deps` is `string`; `dist/rekha-woff.deps` is `string` + `sankoch`.
- **Negative** — it ties the sidecar to the toolchain: `alloc` left the list at 0.4.5 only
  because cyrius 6.6.6 made `lib/string.cyr` self-sufficient, so a consumer below 6.6.6 that
  vendors only `string` traps at the first `strdup`. **The floor is cyrius 6.6.6**, and the
  0.9.0 freeze (ADR 0009) needs the same floor for its `private` / `public` keywords.
- **Neutral** — `rekha_err_print_name` was removed rather than fixed because a dispatched write
  would have added the `syscalls` leaf; library code makes no syscall at all, and CI's
  allowlist scan enforces it (`SECURITY.md`).

## Alternatives considered

- **Declare what the tests need**: taxes every consumer with eight leaves of nothing. Rejected.
- **A test-only-leaf channel in cyrius**: does not exist; filed as blocked-on-a-sibling.
