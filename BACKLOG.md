# Backlog

## Completed

- [x] **Config migration to TOML + Pydantic** — Replaced JSON config with TOML on disk and Pydantic models in memory. Per-collection overrides, watch/search config sections.
- [x] **FTS index fix** — Moved full-text search index creation from every query to store time.
- [x] **Path-prefix search filter** — `--path-prefix` option on `qmd search` to restrict results by file path. Configurable overfetch multiplier.
- [x] **Watch command** — `qmd watch` with watchdog filesystem events, optional polling fallback, configurable debounce and ignore patterns.

## Tech Debt

- [ ] **diskcache unsafe pickle deserialization (CVE-2025-69872)** — Transitive dep via `nano-graphrag` -> `dspy` -> `diskcache<=5.6.3`. No patched version available yet. Dismissed as tolerable risk since exploitation requires local write access to cache dir. Revisit when `diskcache` releases a fix. [Dependabot alert #1](https://github.com/jeffrichley/pyqmd/security/dependabot/1)
- [ ] **Default string duplication** — Default values (chunk_size=800, embed_model, etc.) are duplicated between `config.py` load() fallbacks and `Collection` model fields. Low risk but could diverge.
