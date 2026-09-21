# Contributing to rekha

rekha is the AGNOS scalable-typography library: pure Cyrius, TrueType / OpenType in, sadish
paths out. Its API is **frozen** since 0.9.0 ([`docs/api/`](docs/api/README.md)); read the
promise before touching anything a consumer can call.

## Toolchain

- cyrius **6.6.6**, pinned in `cyrius.cyml` (`[package] cyrius`) — the version the sidecar and
  the visibility keywords depend on ([ADR 0003](docs/adr/0003-the-one-leaf-sidecar.md),
  [ADR 0009](docs/adr/0009-the-freeze.md)). `cyrius --version` first.
- sadish at the tag `[deps.sadish]` pins (0.11.2); `cyrius deps` vendors it into `lib/`.
- python3 for the scripts under `scripts/` (no third-party modules); the hinting oracles need
  the host's `libfreetype` **2.14.x** — CI's is 2.13.2, so those never run in CI.

## Build and test

```bash
cyrius deps                                            # once; vendors lib/
cyrius build programs/smoke.cyr build/rekha-smoke      # the include chain compiles
cyrius build programs/hint_test.cyr build/hint_test && ./build/hint_test   # any suite, the same way
```

Every `programs/*_test.cyr` self-checks and exits non-zero on failure; CI builds and runs all of
them under `CYRIUS_DCE=0` and `1` and fails on any build-log warning. ⚠ **`cyrius build`
rewrites `cyrius.lock`** (it re-resolves and rehashes `lib/`): run `git checkout cyrius.lock`
after building, and regenerate the lock only through `rm -rf lib && cyrius deps`.

## The gates, in CI order

`.github/workflows/ci.yml` is the list; the local mirror is the same commands in a shell loop.

1. `cyrius.lock` equals a clean resolve.
2. `cyrius lint <file> --strict` on every `src/` and `programs/` file: no `warn`, no untracked
   `deferral`. The deferral words (`TODO`, `FIXME`, `XXX`, "for now", "not yet", "later",
   "out of scope", …) fail unless the line carries a tracking pointer (`docs/…`, `CHANGELOG`,
   the roadmap, a `vX.Y`).
3. Formatting: `cyrius fmt <file>` **in place**, then `git diff --exit-code`. ⛔ `cyrius fmt
   --check` is a false negative on 6.6.6; do not gate on its exit code.
4. `cyrius vet programs/smoke.cyr`.
5. `cyrius distlib --check` — `dist/` matches `src/`; regenerate with `cyrius distlib --all`
   (a bare `distlib` leaves the WOFF profile stale) and commit `dist/`.
6. **The freeze**: `python3 scripts/api_surface.py --check`, then a probe that includes each
   bundle and names three internals must fail to build with `is private to its file`.
7. The published sidecars are pinned: `dist/rekha.deps` is `string`, `dist/rekha-woff.deps` is
   `string` + `sankoch`. Growing either is a release decision with a CHANGELOG line.
8. The generated modules match a fresh regeneration: `fonts/face_data.cyr`
   (`scripts/face2cyr.py`), the vector modules under `programs/`.
9. Build and run every suite, both DCE modes; ELF checks; cross-target link checks
   (`--aarch64`, `--agnos`); the syscall allowlist scan; the docs job (`VERSION`, the
   CHANGELOG heading, README's `Version:` line, the required files).

## Rules

- **Every claim carries evidence.** A number in a doc or a comment has a `path:line`, a grep,
  or the measurement that produced it; a differential says what it was run against and how
  many loads differed. "Should work" is not a sentence rekha writes.
- **Refuse, don't guess** ([ADR 0002](docs/adr/0002-refuse-dont-guess.md)). A new reader that
  meets a malformed input answers its family's sentinel and records a code; it never clamps
  into a plausible answer.
- **Allocate through the seam only** — `sd_alloc`, never the stdlib — and check every status
  ([ADR 0001](docs/adr/0001-the-sadish-seam-and-sd-alloc.md)). Readers allocate 0 B.
- **No syscall in library code**, no stdlib include outside `src/lib.cyr`
  ([ADR 0003](docs/adr/0003-the-one-leaf-sidecar.md)).
- **Never paste FreeType's text.** Cite `ref2143/<file>:<line>` in a comment; write the rule in
  your own words. The reference sources are fetched per session, never committed.
- **Cyrius as rekha writes it**: `0 - x`, never `-x`; `>>` is logical, use `sd_asr` on anything
  signed; `/` truncates toward zero; six flat precedence tiers — parenthesise; a bare `!` is
  dropped by the lexer; a function falling off its end returns garbage; 120-byte lines.
- **One change per commit**, tests run after every change, the lock restored.

## Changing the public surface

The surface is what `public fn` / `public var` declare in `src/` under a `# @public` comment,
listed in [`docs/api/surface.txt`](docs/api/surface.txt).

- **Adding** a function or constant: `public fn` + a `# @public —` doc comment stating the
  answer, the units, the sentinel and the code, and what it allocates; an entry on the right
  `docs/api/` page (a `### \`name(...)\`` heading; a constant as a heading or a table row);
  `python3 scripts/api_surface.py --update`; `cyrius distlib --all`; a CHANGELOG line. Additions
  are minor releases.
- **Removing, renaming, or changing a documented answer**: a major version. Not in 1.x.
- **Internals** (everything without `public`) change freely; the tests reach them through the
  `src/` chain, consumers cannot.
- A fix to an answer that was measured wrong is a patch release, with the measurement.

## Releasing

`VERSION`, the CHANGELOG entry (`## [X.Y.Z] - date — title`, with the measurements), README's
`Version:` line and its tables, the roadmap (a finished item leaves it), `cyrius distlib --all`,
the lock regenerated, the local mirror green, then a commit whose subject is the CHANGELOG
title. The commit is the user's; the tag follows it.

## License

GPL-3.0-only. The embedded face is SIL OFL 1.1 and its licence file travels with the bytes.
