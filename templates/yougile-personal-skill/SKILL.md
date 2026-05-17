---
name: yougile-personal
description: Personal workflow context for YouGile MCP. Use whenever the user asks for any YouGile operation — creating/updating/closing tasks, listing projects/boards/columns, working with sprints or CRM deals, posting to task chats, or mentions specific workspaces/projects from the user's setup. Also triggers on Russian phrases "задача", "канбан", "доска", "колонка", "проект", "спринт", "дедлайн", "сделка", "клиент", on slash commands /yougile /задача /спринт, and on direct mentions of project names from the workspace map below. Do NOT trigger for generic project-management questions that aren't about YouGile (use it only when the user is actually going to operate on their YouGile data via the MCP).
---

# YouGile — Personal Workflow Skill

This skill tells you (the assistant) which YouGile workspaces are configured, where the user typically works, which project/board/column UUIDs to use without round-trip lookups, and which patterns this user prefers.

It backs the `yougile-mcp` server. Tools you'll use live under `yougile_*` (e.g. `yougile_list_projects`, `yougile_create_task`). Every tool takes a `workspace` parameter — the slug from the map below. Pass it explicitly even when using the default workspace; it future-proofs the call.

---

## Workspaces

<!-- FILL: list one row per `YOUGILE_KEY_<SLUG>` configured on the MCP server.
     Drop rows that don't apply. The "default" workspace is whichever you pass
     when the user doesn't specify one. -->

| slug | label | role | sprints | CRM | notes |
|---|---|---|---|---|---|
| `{{SLUG_1}}` | {{LABEL_1}} | {{ROLE_1}} | {{TRUE_OR_FALSE}} | {{TRUE_OR_FALSE}} | {{FREEFORM_NOTES_1}} |
| `{{SLUG_2}}` | {{LABEL_2}} | {{ROLE_2}} | {{TRUE_OR_FALSE}} | {{TRUE_OR_FALSE}} | {{FREEFORM_NOTES_2}} |

**Default workspace:** `{{DEFAULT_SLUG}}` — used when the user doesn't specify one and the request isn't obviously tied to another workspace.

---

## Project / board / column shortcuts

When the user names a project in plain language, map to UUIDs below — skip the `list_projects` → `list_boards` → `list_columns` chain. Re-fetch if a UUID stops working (workspace got restructured).

<!-- FILL: one block per project the user works on regularly. Drop blocks that
     don't apply. If a board has only one logical "inbox" column, list it as
     such. If the user has many columns, just record the 2-3 that matter for
     automation (inbox / in_progress / done / blocked). -->

### `{{SLUG_1}}` / {{PROJECT_HUMAN_NAME_1}}

- spoken aliases: {{ALIAS_1A}}, {{ALIAS_1B}}
- `project_id`: `{{UUID}}`
- main `board_id`: `{{UUID}}`
- columns:
  - `inbox`: `{{UUID}}` — where new tasks land
  - `in_progress`: `{{UUID}}`
  - `done`: `{{UUID}}`
  - `blocked`: `{{UUID}}` (optional)

### `{{SLUG_1}}` / {{PROJECT_HUMAN_NAME_2}}

- spoken aliases: {{ALIAS_2A}}
- `project_id`: `{{UUID}}`
- main `board_id`: `{{UUID}}`
- columns:
  - `inbox`: `{{UUID}}`
  - `done`: `{{UUID}}`

---

## Sticker shortcuts (custom fields)

YouGile stickers are custom fields shared across the company. Setting a value
on a task is a **double-lookup** problem: you need both `sticker_uuid` and the
`state_uuid` for the option you want. To avoid the N+1 hit (each lookup ≈ 2
API calls, rate limit 50/min), the user has pre-mapped commonly-used stickers.

<!-- FILL: one entry per sticker the user actually uses in automations. If the
     user doesn't use stickers, delete this whole section. -->

### Priority

- `sticker_id`: `{{UUID}}`
- workspaces: {{SLUG_LIST}}
- states:
  - `low`: `{{UUID}}`
  - `medium`: `{{UUID}}`
  - `high`: `{{UUID}}`
  - `urgent`: `{{UUID}}`

### Sprint (if `sprints_enabled` for the workspace)

- `sticker_id`: `{{UUID}}`
- current sprint: `{{STATE_UUID}}` (rotate manually or read via `yougile_get_sprint_sticker`)
- previous sprint: `{{STATE_UUID}}`

---

## Self user IDs

For "my tasks" / "assign to me" — use the user's UUID per workspace (one account can be a member of several companies, with a different UUID in each).

<!-- FILL: ID of the user themselves, per workspace. -->

| workspace | self user_id |
|---|---|
| `{{SLUG_1}}` | `{{UUID}}` |
| `{{SLUG_2}}` | `{{UUID}}` |

---

## Routing rules (natural-language → workspace)

How to pick `workspace` from what the user says.

<!-- FILL: rules the user dictates. Keep them concrete. -->

- **Default:** `{{DEFAULT_SLUG}}`. Use when no other rule matches.
- **"клиент {{CLIENT_NAME}}", "проект для {{CLIENT_NAME}}"** → `{{CLIENT_SLUG}}`.
- **"в команде", "команда", "team"** → `{{TEAM_SLUG}}`.
- **"лично", "себе", "личный"** → `{{PERSONAL_SLUG}}`.
- **Explicit slug in the message** ("в main", "в team") → use that slug.
- **Ambiguous** ("создай задачу X") → use default, but say which workspace you used in the response so the user can correct.

---

## Operational rules (always)

These are non-negotiable defaults for this user.

1. **Show before mutating, when stakes are high.** Before `yougile_update_task(..., deleted=True)`, `yougile_delete_task`, `yougile_remove_user`, or any mass operation (> 5 items), state what you're about to do and wait for an explicit OK. "Я найду 17 задач и заархивирую" is **not** an action — it's a preview.
2. **Replace-not-append for arrays.** `assigned`, `subtasks`, `stickers`, `checklists` are full-replacement fields. To add a value: `yougile_get_task` first → mutate the array → pass the full array to `yougile_update_task`. Never send a one-element array thinking it will be merged.
3. **HTML, not Markdown, not plain text.** YouGile renders task descriptions and chat messages as HTML. Use `<br>` instead of `\n`, `<b>`/`<i>` instead of `**`/`*`, `<a href="">` for links. Plain text with newlines becomes one wall of text in the UI.
4. **Milliseconds for timestamps.** `deadline.deadline`, `startDate`, sticker timestamps — all `ms` since epoch, never seconds. The `yougile_set_task_deadline` helper auto-corrects if you forget, but `yougile_update_task(deadline=...)` does not.
5. **Workspace must be passed explicitly.** Even if there is only one workspace, write `workspace="{{DEFAULT_SLUG}}"` in the call. It future-proofs against the user adding a second workspace later.
6. **Confirm destination on creation.** When creating a task, say "I'll put it in {{column}} on {{board}} in {{project}} ({{workspace}})." The user often realises mid-sentence they meant a different board.

---

## Operational rules (per workspace flags)

<!-- FILL: flip these to actually-relevant. -->

- `crm_enabled`: if **false** for a workspace, do not propose `yougile_create_crm_contact` / deal-style flows there. If the user explicitly asks for CRM ops in a non-CRM workspace, say it's not configured and stop.
- `sprints_enabled`: if **false**, don't fish for sprint-stickers when listing tasks.
- `mass_op_threshold`: prompts for confirmation kick in at > 5 items. Adjust if the user wants tighter/looser confirmation.

---

## Style — how this user wants you to behave

(Pre-filled defaults; edit to match.)

- Russian-language conversation. Technical identifiers (UUIDs, tool names, field names) stay in English.
- Short paragraphs, tables and lists. **Bold** for the key fact.
- Always explain "why", not just "how". One sentence is enough.
- When multiple ways exist, list them with trade-offs; don't pick silently.
- This user (ADHD + OCD profile) benefits from explicit structure and stated intent before each action. Don't batch surprises.

---

## Common request → tool chain (cheat-sheet)

| User says (RU) | Tool sequence |
|---|---|
| "Создай задачу X" | `yougile_create_task(workspace=default, title=X, column_id=cached.inbox, description=html)`. State workspace+project in reply. |
| "Создай задачу X в проекте Y" | Look up Y in the project shortcuts above. If unknown → `yougile_list_projects(workspace)` + fuzzy match, ask if ambiguous. |
| "Покажи мои задачи на сегодня" | `yougile_get_tasks_by_date(workspace, assigned_to=self_uuid, target_date=today)`. |
| "Отметь Z как сделано" | `yougile_update_task(workspace, task_id=Z, completed=true)`. Only also move column if user has a "Done"-style column convention. |
| "Дедлайн через N дней" | `yougile_set_task_deadline(workspace, task_id, deadline_timestamp=now_ms + N*86400000)`. |
| "Назначь на Иван" | `yougile_list_users(workspace)` → find by realName/email → **`yougile_get_task` first**, then `yougile_update_task(assigned=[ivan_uuid, *existing])`. |
| "Создай подзадачу" | `yougile_create_task(workspace, title, column_id=None)` → read parent's `subtasks` → `yougile_update_task(parent_id, subtasks=[new_uuid, *existing])`. |
| "Прокомментируй задачу X: ..." | `yougile_add_task_comment(workspace, task_id=X, comment="<p>...</p>")`. |
| "Поставь приоритет High" | Use the cached Priority sticker mapping above. `yougile_update_task(stickers={priority_id: high_id})`. |
| "Что я сделал вчера" | `yougile_get_tasks_by_date(assigned_to=self, target_date=yesterday, completed_only=true)`. |
| "Удали задачу X" | **Confirm first.** Then `yougile_update_task(task_id, deleted=true)`. Mention that this is soft-delete and reversible. |
| "Загрузи файл к задаче" | `yougile_upload_file(workspace, path="/abs/path")` → take `url` from result → embed in description or comment. |
| "Найди контакт ACME" | (CRM-only workspaces) `yougile_find_crm_contact_by_external_id(workspace, provider, chat_id)` or `yougile_list_tasks` filtered by client sticker. |

---

## Anti-patterns (don't do)

1. Don't pick a workspace silently when the request is ambiguous.
2. Don't use plain newlines in `description` or comments — always HTML.
3. Don't pass timestamps in seconds — always ms.
4. Don't send `assigned`/`subtasks`/`stickers`/`checklists` arrays without reading the current state — they replace, not append.
5. Don't try to edit chat message *text* via `yougile_update_chat_message` — the YouGile API only allows changing `label`/`react`/`delete`. State this when the user asks.
6. Don't create webhook subscriptions without `filters` — they become firehoses across the whole company.
7. Don't mass-archive or mass-delete without an explicit OK.
8. Don't decode a task's stickers field via `yougile_decode_task_stickers` for tasks with > 3 stickers without caching — it's an N+1 call (2 API requests per sticker × 50/min limit).
9. Don't propose CRM operations in a workspace where `crm_enabled` is false in the table above.
10. Don't quietly retry on `429` — the rate limit is 50 req/min per company, surface it.

---

## When this skill should refresh itself

If during a session you discover UUIDs above are stale (404/wrong shape), call `yougile_list_projects` / `yougile_list_boards` etc. to recover, then **tell the user** which entry to update — don't silently use a different UUID and forget. Refreshing the file is the user's job (or an explicit `yougile_refresh_workspace_index` later).
