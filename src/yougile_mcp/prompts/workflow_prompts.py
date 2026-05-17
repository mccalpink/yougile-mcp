"""
MCP prompts for common YouGile workflows.

Prompts are user-facing templates (slash-commands in clients like Claude
Desktop). They describe conversation intent and tool sequences, but do NOT
hard-code user replies or placeholder IDs. The agent must discover real IDs
via list_* tools at runtime.
"""

from typing import List, Optional


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
