# Changelog

All notable changes to rekha are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - unreleased

### Added
- Repo scaffolded: pure-Cyrius vector/outline font subsystem (SFNT table
  parser + glyph-outline loader emitting paths for the `sadish` 2D
  vector core) — a buildable compiling skeleton with `RekhaErr` codes,
  the `RekhaFont`/`RekhaOutline` struct layouts, big-endian SFNT byte
  readers, and the `rekha_outline_to_path` sadish seam as stubs behind
  `# TODO(v0.2)` markers. Links clean via `programs/smoke.cyr`.
