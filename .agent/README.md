# archolith-maintenance — Agent Docs

`archolith-maintenance` is a shared, domain-agnostic helper substrate for Archolith projects. It currently provides cross-process single-leader election via SQLite leases and canonical token-accounting primitives shared by `archolith-filter`, `archolith-context`, `archolith-bench`, and `archolith-mcp-audit`. Install via `pip install -e <path>` from a consumer venv.

## Files

| File | Purpose |
|------|---------|
| `architecture.md` | System design, data flow, tech stack, config/env reference |
| `data_models.md` | Entities, DTOs, enums, converters, repository reference |
| `CHANGELOG.md` | Running log of changes, most recent first |
| `workflows/code_conventions.md` | Language-specific style and formatting rules |

## Shared Helper Surfaces

- `SchedulerLeaseStore` — SQLite-backed single-leader lease store for background workers.
- `token_accounting` — canonical text token counting, tokenizer selection, and fallback heuristics. Consumer projects may add their own framing, floors, margins, or reporting DTOs, but should not reimplement fallback policy.

## Maintenance Rules

- Update `data_models.md` when any entity, DTO, or enum changes.
- Update `architecture.md` when adding services, integrations, or structural changes.
- Update the relevant workflow file when operational behavior changes.
- Add a `CHANGELOG.md` entry at the end of every session with meaningful changes.
  Format: `## YYYY-MM-DD — <short description>` with bullet points per file changed.
- Push to git regularly — at minimum at the end of each working session.
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.
- Only commit files worked on this session. Run `git diff --name-only` and `git status` before staging. Add files explicitly by path — never `git add .` or `git add -A`.
