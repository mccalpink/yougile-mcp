"""
MCP resources for YouGile API documentation and HTML formatting guide.

Resources are static reference documents fetched by URI on demand. They are
NOT auto-loaded into the LLM context — the agent must explicitly request them
when relevant (e.g. yougile://guides/html before writing a long task description).
"""


def get_api_overview() -> str:
    """YouGile REST API v2 — high-level overview and entity hierarchy."""
    return """# YouGile REST API v2 — Overview

YouGile is a Russian kanban + chat-first project management tool.
This MCP server is a multi-tenant wrapper: one API key = one company
(workspace). Use `list_workspaces` to see configured workspaces and pass
the slug as `workspace=...` to every tool.

## Authentication
- Bearer token per workspace (configured via YOUGILE_KEY_<SLUG> env vars).
- Rate limit: 50 req/min per company. Exceeded calls return 429.
- Base URL: https://yougile.com/api-v2/

## Entity hierarchy
- Company (= workspace; one API key per company)
  - Users (members; isAdmin: bool)
  - Departments (org structure; does NOT control project access)
  - Stickers (company-wide custom fields: string, sprint, text, number)
  - Projects
    - Project Roles (built-in: manager/employee/observer; plus custom)
    - Boards
      - Columns
        - Tasks
          - Subtasks (= regular tasks referenced via parent.subtasks: [uuid])
          - Stickers (values: {sticker_id: state_id})
          - Checklists
          - Chat messages (= comments; chat_id == task_id)
          - Deal (CRM only)
  - Group chats (independent of tasks)
  - Webhooks

## Multi-tenant routing
Every data tool accepts an optional `workspace` parameter. Resolution
priority on each call:
  1. explicit `workspace="<slug>"` — overrides everything
  2. session-active workspace — set via `set_active_workspace("<slug>")`,
     reset via `get_active_workspace()` or omit slug to re-default
  3. `default` — auto-mapped from legacy `YOUGILE_API_KEY`

Set the session-active workspace once at session start (most agent
workflows do this from `briefing.md` `default_workspace`); after that
omit `workspace=` from per-tool calls. Use explicit `workspace=` only
for one-off overrides (e.g. cross-company queries).

`list_workspaces` enumerates configured slugs and human-readable labels.

## Common pitfalls
- Timestamps are MILLISECONDS (13 digits), not seconds.
- Task description and chat messages must be HTML (`<br>`, not `\\n`).
  See yougile://guides/html for the full formatter.
- update_task replaces list fields entirely (assigned, subtasks, stickers,
  checklists). Read current state first, modify, then write back.
- soft-delete vs hard-delete: deleted=true hides from list_*; restore via
  update_*(deleted=false). Lists hide deleted by default — pass
  include_deleted=true when searching for a possibly-deleted item.
"""


def get_api_endpoints() -> str:
    """Complete list of YouGile API v2 endpoints (reference; not all are exposed via MCP)."""
    return """# YouGile API v2 — Endpoints Reference

Total: 65 endpoints across 17 categories. Items marked [MCP] are exposed
as MCP tools by this server; the rest are reachable only via raw HTTP.

## Authorization (4)
- POST /api-v2/auth/companies            [MCP: get_companies]
- POST /api-v2/auth/keys/get             [MCP: list_api_keys]
- POST /api-v2/auth/keys                 [MCP: create_api_key]
- DELETE /api-v2/auth/keys/{key}         [MCP: delete_api_key]

## Company (2)
- GET /api-v2/companies
- PUT /api-v2/companies

## Users (5)
- GET /api-v2/users                      [MCP: list_users]
- POST /api-v2/users                     [MCP: invite_user]
- GET /api-v2/users/{id}                 [MCP: get_user]
- PUT /api-v2/users/{id}                 [MCP: update_user]
- DELETE /api-v2/users/{id}              [MCP: remove_user]

Also: GET /api-v2/users/me               [MCP: get_me]

## Projects (4)
- GET /api-v2/projects                   [MCP: list_projects]
- POST /api-v2/projects                  [MCP: create_project]
- GET /api-v2/projects/{id}              [MCP: get_project]
- PUT /api-v2/projects/{id}              [MCP: update_project]

## Project Roles (5)
- GET /api-v2/projects/{projectId}/roles
- POST /api-v2/projects/{projectId}/roles
- GET /api-v2/projects/{projectId}/roles/{id}
- PUT /api-v2/projects/{projectId}/roles/{id}
- DELETE /api-v2/projects/{projectId}/roles/{id}

## Departments (4)
- GET /api-v2/departments
- POST /api-v2/departments
- GET /api-v2/departments/{id}
- PUT /api-v2/departments/{id}

## Boards (4)
- GET /api-v2/boards                     [MCP: list_boards]
- POST /api-v2/boards                    [MCP: create_board]
- GET /api-v2/boards/{id}                [MCP: get_board]
- PUT /api-v2/boards/{id}                [MCP: update_board]

## Columns (4)
- GET /api-v2/columns                    [MCP: list_columns]
- POST /api-v2/columns                   [MCP: create_column]
- GET /api-v2/columns/{id}               [MCP: get_column]
- PUT /api-v2/columns/{id}               [MCP: update_column]

## Tasks (7)
- GET /api-v2/task-list                  [MCP: list_task_summaries]
- GET /api-v2/tasks                      [MCP: list_tasks]
- POST /api-v2/tasks                     [MCP: create_task]
- GET /api-v2/tasks/{id}                 [MCP: get_task]
- PUT /api-v2/tasks/{id}                 [MCP: update_task, delete_task,
                                                set_task_deadline, remove_task_sticker]
- GET /api-v2/tasks/{id}/chat-subscribers   [MCP: get_task_chat_subscribers]
- PUT /api-v2/tasks/{id}/chat-subscribers   [MCP: update_task_chat_subscribers]

Also: helper get_tasks_by_date           [MCP] — date-filtered wrapper over /tasks.

## String Stickers (4)
- GET /api-v2/string-stickers            [MCP: list_string_stickers]
- POST /api-v2/string-stickers
- GET /api-v2/string-stickers/{id}       [MCP: get_string_sticker]
- PUT /api-v2/string-stickers/{id}

## String Sticker States (3)
- GET /api-v2/string-stickers/{stickerId}/states/{stateId}    [MCP: get_string_sticker_state]
- PUT /api-v2/string-stickers/{stickerId}/states/{stateId}
- POST /api-v2/string-stickers/{stickerId}/states

## Sprint Stickers (4)
- GET /api-v2/sprint-stickers
- POST /api-v2/sprint-stickers
- GET /api-v2/sprint-stickers/{id}
- PUT /api-v2/sprint-stickers/{id}

## Sprint Sticker States (3)
- GET /api-v2/sprint-stickers/{stickerId}/states/{stateId}    [MCP: get_sprint_sticker_state]
- PUT /api-v2/sprint-stickers/{stickerId}/states/{stateId}
- POST /api-v2/sprint-stickers/{stickerId}/states

## Group Chats (4)
- GET /api-v2/group-chats                [MCP: list_group_chats]
- POST /api-v2/group-chats               [MCP: create_group_chat]
- GET /api-v2/group-chats/{id}           [MCP: get_group_chat]
- PUT /api-v2/group-chats/{id}

## Chat Messages (4)
- GET /api-v2/chats/{chatId}/messages    [MCP: get_chat_messages, get_task_comments]
- POST /api-v2/chats/{chatId}/messages   [MCP: send_chat_message, add_task_comment]
- GET /api-v2/chats/{chatId}/messages/{id}    [MCP: get_chat_message]
- PUT /api-v2/chats/{chatId}/messages/{id}    [MCP: update_chat_message]

## Files (1)
- POST /api-v2/upload-file               [MCP: upload_file]

## Webhooks (3)
- GET /api-v2/webhooks                   [MCP: list_webhooks]
- POST /api-v2/webhooks                  [MCP: create_webhook]
- PUT /api-v2/webhooks/{id}              [MCP: update_webhook]

## MCP-only helpers (not 1:1 with REST)
- list_workspaces — enumerate tenants this server is configured for.
- get_user_context — return user-configured default project/board hints.
- decode_task_stickers — resolve {sticker_id: state_id} to human-readable labels.
- create_crm_contact, find_crm_contact_by_external_id — CRM contact helpers.
"""


def get_html_guide() -> str:
    """HTML formatting reference for task descriptions and chat messages."""
    return """# YouGile HTML formatting guide

YouGile stores task description and chat message bodies as HTML. Plain
text with `\\n` renders as a single line. Always wrap content in HTML.

## Minimum vocabulary
- `<br>` — line break (instead of `\\n`)
- `<p>...</p>` — paragraph (added automatically by send_chat_message if
  you pass plain `text` without `text_html`)
- `<b>...</b>` `<i>...</i>` `<u>...</u>` — bold / italic / underline
- `<a href="https://...">label</a>` — link
- `<ul><li>...</li></ul>` — bullet list
- `<ol><li>...</li></ol>` — numbered list

## Examples

Bug report:
```
<b>Bug:</b> login fails<br><br>
<b>Steps:</b><br>
1. Open /login<br>
2. Submit form<br>
3. See 500<br><br>
<b>Expected:</b> 200 + redirect to /dashboard
```

Feature spec with link:
```
<b>Feature:</b> dark mode<br>
<a href="https://figma.com/x">Design mockup</a><br>
Acceptance: toggle persists across sessions.
```

Multi-section comment:
```
<b>Progress:</b><br>
<ul>
  <li>API done</li>
  <li>UI in review</li>
</ul>
Blocked on QA env.
```

## Anti-patterns
- `\\n` for line breaks — invisible in UI.
- Markdown (`**bold**`, `# h1`) — not parsed.
- Raw user input without escaping — XSS risk; sanitize untrusted text.
"""
