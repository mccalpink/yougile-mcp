"""
MCP prompts for common YouGile workflows.

Prompts are user-facing templates (slash-commands in clients like Claude
Desktop). They describe conversation intent and tool sequences, but do NOT
hard-code user replies or placeholder IDs. The agent must discover real IDs
via list_* tools at runtime.
"""

from typing import List, Optional


def api_usage_guide_prompt() -> str:
    """Quick reference: how to use this MCP — workspaces, verbosity,
    include[], describe_response, skill, common pitfalls."""
    return """Quick reference for working with this YouGile MCP. Read once
at session start; details are also discoverable through `describe_response`
and the `yougile://api/overview` resource.

## 1. Pick a workspace (multi-tenant)

This server can hold API keys for several YouGile companies at once.
Each key is exposed as a `workspace` slug (env var `YOUGILE_KEY_<SLUG>`).
Legacy single-tenant configs (`YOUGILE_API_KEY`) map to slug `default`.

  1. `list_workspaces()` — see configured slugs + human labels.
     Returns `[{slug, label, has_company_id}]`. Never exposes the keys.
  2. `set_active_workspace(slug="main")` — make it the session default;
     subsequent tools omit `workspace=`.
  3. `get_active_workspace()` — verify the current slug + available list.
  4. Explicit `workspace="other"` in a tool call overrides the session
     active workspace (one-off cross-workspace queries).

Persist the chosen default in the personal skill — see §5.

## 2. Read tools: verbosity + include[]

All `list_*` / `get_*` tools accept `verbosity` and `include[]`. The MCP
server post-processes raw API responses to cut noise; the agent controls
how much detail it asks for per call.

| Verbosity | What you get | When |
|---|---|---|
| `custom`  | `id` only (or `id` + fields listed in `include`) | counts, aggregations |
| `compact` | curated core fields + ISO timestamps + `_hints` block on lists | DEFAULT — normal work |
| `full`    | pass-through of the raw API payload | debugging, audits |

`include[]` adds extra fields on top of the chosen verbosity. Opt-in
keys are entity-scoped (task: `description`, `checklists`, `stickers`,
`stopwatch`, `timer`, `time_tracking`, `deal`, `extension_data`,
`deadline_history`, `timestamps`; sticker: `sprint_states`,
`string_states`; group_chat: `chat_maps`). Direct field names are also
accepted: `include=["title"]` works even when `title` is already in
compact (no-op). Unknown / wrong-DTO keys surface as
`_meta.unknown_includes` rather than silent no-ops.

Examples:
```
# Default: compact — minimal payload, _hints block on list responses
list_tasks(column_id="<uuid>")

# Want descriptions for a list scan
list_tasks(column_id="<uuid>", include=["description"])

# Just count completed vs not — minimum tokens
list_tasks(column_id="<uuid>", verbosity="custom", include=["completed"])

# Debugging — raw API payload
get_task(task_id="<uuid>", verbosity="full")
```

The compact response always carries a `_meta` envelope with what was
dropped, what include keys were unknown, and any auto-heal notes. Use
`describe_response(entity="task")` to discover which fields live where
without making an API round-trip.

## 3. describe_response: the schema cheat-sheet

`describe_response(entity?, verbosity?)` is a meta tool that does NOT
hit the YouGile API. It returns the field-level schema for any of the
9 entities (task, project, board, column, user, message, group_chat,
sticker, webhook):
- which fields appear in `compact` vs `full` vs require `include[]`
- type hints (UUID / ms epoch / ISO / enum / HTML)
- known quirks (the auto-heal normalizers)

Call it before constructing an unusual field request — saves
trial-and-error round-trips.

## 4. Auto-heal quirks

Some YouGile DTOs are inconsistent with the OpenAPI spec or each
other. The MCP transparently normalises them so the agent sees one
canonical shape. When the normaliser does something, it adds a note to
`_meta.notes`:

- `SprintStickerState.begin/end` — stored in seconds, normalised to ms
  (both request and response paths are idempotent via a threshold).
- `WebhookFilters.name` — described as array in OpenAPI, accepted as
  string by the API; we coerce single-element arrays to a string with
  a note.
- `Company.name` vs `Company.title` — both unified to `title`.
- `Stopwatch` runtime field-name discovery — placeholder; integration
  test pending a stopwatch fixture.

## 5. Personal skill = your project shorthand

Without the skill, you re-discover the same UUIDs (workspaces,
projects, columns, stickers, users) at the start of every session.
With it, they sit in a local briefing file the agent reads first.

  1. `setup_yougile_skill()` returns a manifest:
     - `questions` for the user (workspaces, default workspace,
       project shorthands, routing rules, board columns,
       anti-patterns)
     - `default_target_dir` (recommended install path)
     - `files: [{uri, target, sha256}]` — each entry is a concrete
       MCP resource under `yougile://skill-template/<relpath>`
     - `instructions` for the install protocol
  2. The agent reads each `files[i].uri` via `resources/read`
     (content arrives verbatim), then writes it to disk with its
     own Write tool — under the user's normal permissions. The MCP
     server itself never writes to the client filesystem.
  3. Verify each file matches `sha256` after Write; if not, re-write.
  4. Ask the user the `questions`; fill in
     `templates/briefing.template.md`; save as `briefing.md` in the
     target dir.
  5. From the next session start, the agent reads `briefing.md` and
     `set_active_workspace(...)` for the recorded
     `default_workspace` before any tool calls.

The skill is the right place to persist project-specific routing
rules ("when the user says 'клиент ACME' → workspace
`client_acme`"), preferred verbosity defaults, frequently-used
column UUIDs, and anti-patterns. Update `briefing.md` whenever the
project surface changes; the agent will pick up the new context on
the next session.

## 6. Create-then-read pattern

`create_*` tools return only the new `id` — they do NOT return the
full object. If you need the full state immediately, follow with
`get_<entity>(id=...)`. The skip-the-get optimisation is the
default because most callers only need the id for the next step.

Example (project → board → columns → task):
```
proj = create_project(title="Website redesign",
                      users={"<user-uuid>": "admin"})
board = create_board(project_id=proj["id"], title="Backlog")
col_todo  = create_column(board_id=board["id"], title="To Do",        color=1)
col_doing = create_column(board_id=board["id"], title="In Progress",  color=5)
col_done  = create_column(board_id=board["id"], title="Done",         color=13)
task = create_task(column_id=col_todo["id"], title="Wire up auth")
```

`column_id` is optional in `create_task` (matches the API DTO) —
useful for floating subtasks that you attach later via
`update_task(parent_id, subtasks=[new_id, ...])`.

## 7. HTML formatting reminder

Task descriptions and chat messages must be HTML. Use `<br>` for
line breaks (NOT `\\n` — it won't display), `<b>` / `<i>` / `<u>`,
`<a href="...">`, `<ul><li>` / `<ol><li>`. Full reference: read
the resource `yougile://guides/html`.

## 8. Checklists

Tasks can have multiple checklists. Format:
```
checklists=[
  {"title": "Backend",  "items": [{"title": "API",  "isCompleted": False}]},
  {"title": "Frontend", "items": [{"title": "Form", "isCompleted": False}]},
]
```
`update_task` replaces the entire `checklists` array — read current
state first, mutate the list, write the full array back. Same rule
applies to `assigned`, `subtasks`, `stickers`.

## 9. Common pitfalls

- Timestamps are MILLISECONDS (13 digits), not seconds.
- `soft-delete vs hard-delete`: most delete operations are
  `update_<entity>(deleted=True)`. Lists hide deleted entities by
  default; pass `include_deleted=True` (where supported) to find them.
- Don't pass `workspace="default"` in every tool call once you have
  set an active workspace — leave the argument off; explicit only for
  cross-workspace overrides.
- `list_api_keys` returns `key_preview` only (security — never raw
  keys); use `create_api_key` / `delete_api_key` to manage keys.
"""


def setup_new_project_prompt(project_name: str, project_type: str = "kanban") -> str:
    """Guide for creating and configuring a new project."""
    return f"""Set up a new {project_type} project called "{project_name}" in YouGile.

Steps to follow:
1. Call list_workspaces to confirm which workspace to target. If multiple
   exist and the user has not specified one, ask before proceeding.
2. Create the project: create_project(workspace, title="{project_name}",
   users={{user_id: role, ...}}). Roles: "admin", "developer", "viewer".
3. Create one or more boards: create_board(workspace, project_id, title).
4. Add columns: create_column(workspace, board_id, title, color=1..16).
   Typical kanban layout: Backlog (gray), In Progress (yellow),
   Review (blue), Done (green).
5. Report the resulting project_id, board_id, and column_ids back to the user.

Do NOT create tasks yet — wait for the user's first feature request.
"""


def create_task_workflow_prompt(task_title: str, priority: str = "medium") -> str:
    """Template for creating a well-structured task."""
    return f"""Create a task titled "{task_title}" (priority: {priority}) in YouGile.

Information you need before calling create_task:
- workspace slug (call list_workspaces if unsure).
- column_id — call list_columns(board_id=...) to pick the right column,
  or omit column_id to create a "floating" task usable as a sub-task.
- assignee user_id(s) — call list_users to map names/emails to UUIDs.

When you call create_task:
- description must be HTML (see yougile://guides/html). Use <br> not \\n.
- For deadlines, prefer set_task_deadline(task_id, deadline_timestamp_ms)
  over passing a raw deadline dict — it auto-fills required fields.
- For custom stickers (priority, sprint, etc.), look up sticker_id and
  state_id via list_string_stickers + get_string_sticker first.

Return the created task_id and a one-line summary.
"""


def sprint_planning_prompt(sprint_name: str, duration_weeks: int = 2) -> str:
    """Sprint planning workflow: surface candidates, do not commit."""
    return f"""Plan sprint "{sprint_name}" ({duration_weeks} weeks) in YouGile.

YouGile models sprints as a sprint-sticker whose states are time intervals.

Steps:
1. Identify the sprint-sticker and the state corresponding to "{sprint_name}"
   (or the next empty one). The sticker is company-wide.
2. List candidate tasks: typically tasks in the Backlog column without a
   sprint assigned, sorted by priority. Use list_tasks with column_id.
3. For each candidate, surface title, assignee, time estimate, and any
   blockers. Do NOT assign the sprint sticker yet — present a shortlist
   to the user for confirmation first.
4. Once the user confirms, batch-call update_task to set
   stickers={{sprint_sticker_id: target_state_id}} on each chosen task.

Stop after step 3 and wait for user approval before any update_task.
"""


def daily_standup_prompt() -> str:
    """Generate daily standup report for the current user or a team."""
    return """Generate a daily standup report from YouGile.

Steps:
1. If the user has not specified a team, default to themselves: call get_me
   to find the current user_id. Otherwise list_users to resolve names to IDs.
2. For each user, gather:
   - Done yesterday: get_tasks_by_date(assigned_to=user_id,
     target_date=<yesterday>, completed_only=true).
   - In progress today: list_tasks(assigned_to=user_id) filtered by an
     "In Progress" column. If unknown, call list_columns and pick by name.
   - Blockers: tasks in a "Blocked" column (look it up via list_columns)
     OR tasks whose deadline is past and not completed.
3. Format as a concise markdown report grouped by user. Highlight overdue
   items and unassigned blockers.
"""


def project_health_check_prompt(project_id: str) -> str:
    """Project health analysis — read-only audit."""
    return f"""Audit health of project {project_id}.

Read-only operation — do NOT modify any tasks.

Gather:
1. list_boards(project_id="{project_id}") and list_columns per board to map
   the workflow structure.
2. For each board, list_tasks per column to surface distribution. Flag
   columns with > 20 tasks (likely bottleneck).
3. Find overdue tasks: list_tasks(include_deleted=false) then client-side
   filter by deadline.deadline < now and not completed.
4. Find stale tasks: those whose timestamp is older than 14 days and
   not completed.

Output a markdown report with sections: workflow map, bottlenecks,
overdue, stale, recommended next actions.
"""


def user_productivity_report_prompt(user_id: str, target_date: Optional[str] = None) -> str:
    """Per-user productivity report for a given date (default: today)."""
    date_clause = f"target_date=\"{target_date}\"" if target_date else "target_date omitted (today)"
    return f"""Report productivity for user {user_id} ({date_clause}).

Read-only.

Gather:
1. Completed: get_tasks_by_date(assigned_to="{user_id}", completed_only=true{(', target_date="' + target_date + '"') if target_date else ''}).
2. Created: get_tasks_by_date(created_by="{user_id}"{(', target_date="' + target_date + '"') if target_date else ''}).
3. Active workload: list_tasks(assigned_to="{user_id}") minus the completed set.
4. If tasks expose timeTracking, sum plan vs work hours.

Output a short markdown summary (counts, ratios, notable items).
Do not assign or update any tasks.
"""


def weekly_team_report_prompt(team_user_ids: str, start_date: str) -> str:
    """Weekly team performance report (read-only)."""
    return f"""Generate a weekly team report starting {start_date} for users {team_user_ids}.

team_user_ids: comma-separated UUIDs.

For each user, for each day in the 7-day window:
- Call get_tasks_by_date(assigned_to=<uid>, target_date=<day>, completed_only=true)
  to count completed work.
- Call get_tasks_by_date(created_by=<uid>, target_date=<day>) to count created.

Aggregate into a single markdown table (rows = users, columns = days,
plus a totals row). Highlight imbalances (one user > 2x team median or
one user < 0.5x team median).

Read-only.
"""


def task_escalation_prompt(task_id: str) -> str:
    """Escalate a blocked task: gather context, propose actions, wait for approval."""
    return f"""Escalate blocked task {task_id}.

Steps:
1. get_task(task_id="{task_id}") to read current state, assignees, deadline.
2. get_task_comments(task_id="{task_id}") to see recent discussion.
3. Summarise the blocker and propose an escalation plan:
   - Add a comment flagging the blocker (add_task_comment with HTML body).
   - Optionally move the task to a "Blocked" column (look up via list_columns).
   - Optionally add stakeholders to the chat (update_task_chat_subscribers).
4. Present the plan to the user and wait for approval before executing.

Do not execute any mutating calls before the user confirms.
"""


def onboarding_new_team_member_prompt(new_member_name: str, role: str) -> str:
    """Onboarding workflow for a new team member."""
    return f"""Onboard "{new_member_name}" as {role} in YouGile.

Steps:
1. Confirm the workspace (list_workspaces) and gather their email.
2. Invite: invite_user(workspace, email, first_name, last_name, role).
3. Identify projects they need: list_projects, ask the user which ones.
4. Grant access: update_project(workspace, project_id, users={{...}})
   for each project, merging the new user into the existing users map.
5. Optionally create onboarding tasks (create_task) and subscribe a
   mentor via update_task_chat_subscribers.

Propose the plan and wait for confirmation before mutating anything.
"""


def deadline_crunch_management_prompt(deadline_date: str) -> str:
    """Help triage work as a critical deadline approaches."""
    return f"""Triage work as the {deadline_date} deadline approaches.

Steps:
1. list_tasks with no completion filter, then client-side filter by
   deadline.deadline <= {deadline_date}.
2. Group by completion status and assignee.
3. Present a priority matrix: must-have vs nice-to-have, blocked vs
   on-track. Ask the user which items to deprioritise or reassign.
4. After user confirms, update_task for affected items (move column,
   change assignee, push deadline, etc.).

Do not mutate before confirmation. For >5 simultaneous changes, present
a preview and confirm explicitly.
"""


def retrospective_analysis_prompt(sprint_end_date: str, team_user_ids: str) -> str:
    """Sprint retrospective analysis — read-only insight gathering."""
    return f"""Retrospective for sprint ending {sprint_end_date}, team {team_user_ids}.

Read-only.

For the sprint window:
1. Identify the sprint state on the company sprint-sticker.
2. list_tasks filtered by stickers={{sprint_sticker_id: state_id}}
   (client-side filter — YouGile API does not filter by sticker value).
3. Split into: completed in sprint, carried over, added mid-sprint
   (timestamp > sprint_start).
4. For each user in {team_user_ids}, count tasks completed / added / blocked.

Output a markdown retro doc with sections: delivered, missed, themes,
suggested action items. Surface raw numbers; let the user interpret.
"""
