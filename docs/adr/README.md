# Architecture decision records

The decisions behind rekha's shape — what was chosen, the situation that forced it, and the
consequences accepted. Every record carries the `path:line` or the measurement it rests on;
the source header stays the normative text where one exists.

## Conventions

- `NNNN-kebab-case-title.md`, four digits, never renumbered. One decision per record.
- Status: `Proposed` → `Accepted` → `Superseded by NNNN`. A superseding decision is a new record.
- The date is when the record was written; a decision older than the record says so.
- Start from [`template.md`](template.md).

## Index

- [0001 — rekha emits paths and allocates only through `sd_alloc`, which has no free](0001-the-sadish-seam-and-sd-alloc.md)
- [0002 — Refuse, don't guess; a refused glyph program draws unhinted, never partially hinted](0002-refuse-dont-guess.md)
- [0003 — The one-leaf sidecar, and the cyrius 6.6.6 floor it implies](0003-the-one-leaf-sidecar.md)
- [0004 — The opt-in WOFF bundle: both web containers, and sankoch, in `dist/rekha-woff.cyr` only](0004-the-opt-in-woff-bundle.md)
- [0005 — The hint machine rounds half away from zero; everything else half up](0005-the-rounding-split.md)
- [0006 — Why a call refused lives on the handle: a code and a static detail, no record, no global](0006-the-error-model-on-the-handle.md)
- [0007 — FreeType 2.14.3's classic interpreter is the hinting oracle, through `ctypes`](0007-freetype-as-the-hinting-oracle.md)
- [0008 — The embedded default face is a freestanding generated data module outside the bundle](0008-the-embedded-default-face.md)
- [0009 — The freeze: `public fn` in `src/`, a `private` bundle, a promise the compiler keeps](0009-the-freeze.md)
