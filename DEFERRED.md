# Deferred for follow-up

Pending API groups planned for a follow-up PR — kept out of this PR
to keep its diff focused on transport, multi-tenant routing, per-tool
API coverage, prompts refactor and verbosity.

Total deferred: **17 endpoints across 5 groups**.

## 1. Departments (4 endpoints)
- `GET /api-v2/departments` (list)
- `POST /api-v2/departments` (create)
- `GET /api-v2/departments/{id}`
- `PUT /api-v2/departments/{id}`

HTTP client exists: `src/api/departments.py`. MCP tool wrapper missing.

## 2. Project Roles (5 endpoints)
- `GET /api-v2/projects/{projectId}/roles`
- `POST /api-v2/projects/{projectId}/roles`
- `GET /api-v2/projects/{projectId}/roles/{roleId}`
- `PUT /api-v2/projects/{projectId}/roles/{roleId}`
- `DELETE /api-v2/projects/{projectId}/roles/{roleId}`

HTTP client exists: `src/api/project_roles.py`.

## 3. Sticker States CRUD (6 endpoints)

String sticker states: `POST/GET/PUT /api-v2/string-stickers/{stickerId}/states[/{stateId}]`.
Sprint sticker states: `POST/GET/PUT /api-v2/sprint-stickers/{stickerId}/states[/{stateId}]`.

Only `get_sprint_sticker_state` is currently exposed.

**Note:** `SprintStickerStateDto.begin/end` use **seconds**, not milliseconds —
unlike the rest of the API. The follow-up implementation must normalize.

## 4. Company endpoints (2 endpoints)
- `GET /api-v2/company`
- `PUT /api-v2/company`

HTTP client exists: `src/api/company.py`. `tools/company_tools.py` was
deleted in Phase 5 (was an empty file); needs to be re-created with
actual content.

**Note:** `CompanyListDtoBase.name` vs `CompanyDto.title` —
the same field is named differently across two DTOs.
