# Deferred for follow-up

Pending API groups that have `src/api/*.py` clients but no MCP tool
exposure yet (planned for a follow-up PR):

- Departments (CRUD)
- Project Roles (CRUD + delete)
- Sprint Stickers full CRUD + states (only `get_sprint_sticker_state` is exposed)

These were left out of this PR to keep its diff focused on transport,
multi-tenant routing, and per-tool API coverage. The HTTP clients in
`src/api/departments.py`, `src/api/project_roles.py`, `src/api/stickers.py`
are already present.
