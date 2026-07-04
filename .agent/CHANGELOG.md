# Changelog — archolith-maintenance

## 2026-06-21 — Shared Token Accounting Helper

- Added `archolith_maintenance.token_accounting` as the canonical text-token counting primitive for Archolith projects.
- Exposed shared helpers for text counts, message-content counts, estimated-count detection, and fallback diagnostics.
- Added explicit token-counting modes: `auto`, `fallback`, and `tiktoken`.
- Documented that consumer projects own surface-specific framing/floors while maintenance owns tokenizer selection and fallback policy.

## YYYY-MM-DD — Initial project setup

- Created project skeleton
- Added `.agent/` documentation
- Added LLM instruction files
