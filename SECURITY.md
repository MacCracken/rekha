# Security policy

## Reporting a vulnerability

Report security issues to **security@agnosticos.org**. Do not open a public issue for one.
Say which release (`VERSION`), which entry point, and attach the font bytes that reach it if
you can — every finding so far reproduced with a crafted font under 300 bytes.

## What rekha is, and its threat model

rekha is a pure-Cyrius parser for TrueType / OpenType (and, in the WOFF bundle, WOFF 1.0 /
WOFF2) font bytes. **A font file is untrusted input.** A consumer hands rekha a buffer it
received from anywhere — a web font, a document, a USB stick — and every byte rekha reads is
checked against `len` before it is read. The invariants, each a check in code and a gate in
CI, not an aspiration:

- **No syscall in library code.** `src/`, the `dist/` bundles and `fonts/face_data.cyr` compute
  and return; every byte they write goes into a buffer the caller owns or an allocation the
  caller's `sd_alloc` hook granted. `.github/workflows/ci.yml` scans every tracked source with
  an *allowlist* (test programs may `write` and `exit`, nothing else; no spawn names, no
  process / dlopen includes, no inline `asm`).
- **Every read is bounded.** A table lies after its own directory and inside the file; a fixed
  field is read only when the table's *declared* length covers it; variable arrays stay inside
  their own table; every outline's `end_pts` strictly increase and stay below `n_points`
  (`src/sfnt.cyr`, "Font files are untrusted input"; CHANGELOG 0.3.11). A lying `loca`, a
  short `hmtx`, an offset past `len` answer nothing, with the reason on the handle.
- **Caps are refusals, and a composite's cap is a budget.** 4,096 points / 128 contours per
  outline, 64 glyph loads / 16,384 decoded points per `rekha_load_glyph`, nesting depth 5, no
  cycles; the hint machine takes at most 8,192 stack / storage slots, 4,096 functions, 256
  instruction defs, 16,384 control values, 4,096 zone points, and runs at most 1,000,000
  instructions per program at a `CALL` depth of 64; a WOFF may inflate at most 1,032:1, a
  WOFF2 exactly what its header declares (both through sankoch's `*_decompress_capped`). A
  tripped cap yields an empty glyph, never a partial one ([ADR 0002](docs/adr/0002-refuse-dont-guess.md)).
  Fan-out was the finding that motivated the budget: a 288-byte font that asked for 96 MB.
- **Allocation never faults.** Every allocation goes through the consumer's `sd_alloc` hook
  ([ADR 0001](docs/adr/0001-the-sadish-seam-and-sd-alloc.md)); a hook that refuses makes the
  call return 0 or an empty path — every `sd_alloc` and every `sd_path_*` status is checked.
- **Refuse, don't guess.** Malformed input produces a sentinel and a `RekhaErrCode`, never a
  plausible wrong glyph; a refused glyph program draws unhinted, never partially hinted.
- **The bundle is private.** Since 0.9.0 a consumer can reach only the documented surface; an
  internal reached by name is a compile error ([ADR 0009](docs/adr/0009-the-freeze.md)).

### Out of scope

- The consumer's `sd_alloc` hook and what it hands back; sadish's rasterizer; the kernel path
  that serves `fonts/face_data.cyr` (agnos verifies the FNV-1a before exposing it).
- sankoch's decoders themselves (their own `SECURITY.md`); rekha caps what they may write.
- Denial of service by *legitimate* size: a 4,096-point glyph or a 1,000,000-instruction
  program is what the caps permit, by design.
- Timing side channels: font parsing is not a secret-dependent computation.

## Evidence

- **0.3.11** (CHANGELOG): four out-of-bounds reads reachable from `rekha_char_to_sdpath` with a
  font `rekha_font_open` accepts — each proven by a sentinel differential, then forced to fault
  at a guard page — and the composite fan-out bound; 88 raw findings across eight audit lenses,
  a second fresh review, 223 single-edit mutants.
- **`programs/hostile_test.cyr`**, in CI on every push: one crafted font per audit class, a
  seeded 120-mutant sweep over the embedded face (undone byte by byte and re-verified), and an
  A/B sentinel differential across the allocation seam (a 4,096-byte redzone, 256 sentinel
  bytes around every font, two fill patterns, an FNV-1a digest per sweep — a one-byte overread
  changes the digest); since 0.8.2 every gid is also hinted (240,908 hinted loads over the
  mutants, a refused mutant answering 0 and an empty view, never a fault).
- **0.8.2's dev-host sweep**: the 25 unit fonts under a full single-byte and u16 mutation of
  every offset, ~85 M checks under a guard-page allocator with canaries; 75,000 random glyph
  programs through the composite loader; 400 face mutants; all 1,750 host TTFs — 0 faults,
  0 canary writes, 0 broken refusal invariants.

There is no `docs/audit/` directory: the audit record is the CHANGELOG, release by release,
with the measurement each claim rests on.

## Supported versions

| version | status |
|---|---|
| 0.9.x, and 1.x when it ships | security fixes, in a patch release with a CHANGELOG entry |
| 0.8.x and below | not supported — the API is frozen at 0.9.0; move to it |

A fix never changes a documented answer (`docs/api/README.md`, the stability promise); where
a fix must refuse an input a release accepted, the CHANGELOG says which.
