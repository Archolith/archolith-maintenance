# archolith-maintenance — Agent Docs

`archolith-maintenance` is a shared, domain-agnostic background-maintenance substrate providing cross-process single-leader election via SQLite leases. It is consumed by `archolith-context`'s curator worker to ensure only one leader schedules maintenance tasks per lease key; `cth.mcp.memory` will converge onto it at the `cth.memory → archolith.memory` rename. Install via `pip install -e <path>` from a consumer venv.

## Files

| File | Purpose |
|------|---------|
| `architecture.md` | System design, data flow, tech stack, config/env reference |
| `data_models.md` | Entities, DTOs, enums, converters, repository reference |
| `CHANGELOG.md` | Running log of changes, most recent first |
| `workflows/code_conventions.md` | Language-specific style and formatting rules |

## Maintenance Rules

- Update `data_models.md` when any entity, DTO, or enum changes.
- Update `architecture.md` when adding services, integrations, or structural changes.
- Update the relevant workflow file when operational behavior changes.
- Add a `CHANGELOG.md` entry at the end of every session with meaningful changes.
  Format: `## YYYY-MM-DD — <short description>` with bullet points per file changed.
- Push to git regularly — at minimum at the end of each working session.
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.
- Only commit files worked on this session. Run `git diff --name-only` and `git status` before staging. Add files explicitly by path — never `git add .` or `git add -A`.
