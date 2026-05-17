"""
YouGile MCP Server

Main entry point for the YouGile Model Context Protocol server.
Registers all tools, resources, and prompts for YouGile API access.

Tool descriptions follow the canonical pattern:
  Purpose. USE WHEN: ... DO NOT USE: ... RETURNS: ... RELATED: ...
Parameter hints use Annotated[T, Field(description=...)] so the JSON
schema delivered to the LLM contains formats, defaults, and cross-refs.
Each tool also declares ToolAnnotations explicitly — defaults in the MCP
spec are pessimistic, so we set readOnly/destructive/idempotent/openWorld
on every tool.
"""

import asyncio
from typing import Annotated, Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import settings
from .core import auth
from .core.client import YouGileClient
from .core.registry import registry
from .core.session_state import get_active, set_active, resolve_workspace
from .core.models import MessageReact, TaskColor
from .utils.verbosity import Verbosity
from .api import auth as auth_api
from .yougile_mcp.tools.auth_tools import (
    create_api_key_tool,
    delete_api_key_tool,
    get_companies_tool,
    list_api_keys_tool,
)
from .yougile_mcp.tools.user_tools import (
    get_me_tool,
    get_user_tool,
    invite_user_tool,
    list_users_tool,
    remove_user_tool,
    update_user_tool,
)
from .yougile_mcp.tools.project_tools import (
    create_project_tool,
    get_project_tool,
    list_projects_tool,
    update_project_tool,
)
from .yougile_mcp.tools.board_tools import (
    create_board_tool,
    get_board_tool,
    list_boards_tool,
    update_board_tool,
)
from .yougile_mcp.tools.column_tools import (
    create_column_tool,
    get_column_tool,
    list_columns_tool,
    update_column_tool,
)
from .yougile_mcp.tools.chat_tools import (
    add_task_comment_tool,
    create_group_chat_tool,
    get_chat_message_tool,
    get_chat_messages_tool,
    get_group_chat_tool,
    get_task_comments_tool,
    list_group_chats_tool,
    send_chat_message_tool,
    update_chat_message_tool,
)
from .yougile_mcp.tools.task_tools import (
    create_task_tool,
    get_task_tool,
    get_tasks_by_date_tool,
    list_task_summaries_tool,
    list_tasks_tool,
)
from .yougile_mcp.tools.task_tools_extended import (
    get_task_chat_subscribers_tool,
    update_task_chat_subscribers_tool,
    update_task_tool,
)
from .yougile_mcp.tools.sticker_tools import (
    decode_task_stickers_tool,
    get_sprint_sticker_state_tool,
    get_string_sticker_state_tool,
    get_string_sticker_tool,
    list_string_stickers_tool,
)
from .yougile_mcp.tools.webhook_tools import (
    create_webhook_tool,
    list_webhooks_tool,
    update_webhook_tool,
)
from .yougile_mcp.tools.file_tools import upload_file_tool
from .yougile_mcp.tools.crm_tools import (
    create_crm_contact_tool,
    find_crm_contact_by_external_id_tool,
)
from .yougile_mcp.resources.api_docs import (
    get_api_endpoints,
    get_api_overview,
    get_html_guide,
)
from .yougile_mcp.tools.meta_tools import describe_response_impl, setup_yougile_skill_impl
from .yougile_mcp.resources.skill_template import get_skill_template_content
from .yougile_mcp.prompts.workflow_prompts import (
    create_task_workflow_prompt,
    daily_standup_prompt,
    deadline_crunch_management_prompt,
    onboarding_new_team_member_prompt,
    project_health_check_prompt,
    retrospective_analysis_prompt,
    setup_new_project_prompt,
    sprint_planning_prompt,
    task_escalation_prompt,
    user_productivity_report_prompt,
    weekly_team_report_prompt,
)


# ---------------------------------------------------------------------------
# Annotation presets
# ---------------------------------------------------------------------------
#
# MCP spec defaults assume the worst (non-readonly, destructive, non-idempotent,
# open-world). We override every tool with one of the presets below so the
# client can make informed UX decisions (auto-approve reads, prompt on writes).

# Pure reads against the YouGile API.
#
# openWorldHint=False everywhere: every tool talks to one specific closed API
# (YouGile v2). Per the MCP spec, openWorldHint=True signals the tool reaches
# an unbounded outer world (web search, generic HTTP), which is misleading
# here and would prompt clients to apply broader-scope confirmations.
ANN_READ = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

# Mutating but additive (create, send, invite, upload).
ANN_CREATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)

# Mutating, repeating with the same args is safe (re-applies same state).
ANN_UPDATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)

# Mutating, removes data (soft-delete, revoke, remove user).
ANN_DELETE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(name=settings.server_name)


def _resolve_ws(workspace: Optional[str], ctx: Context) -> str:
    """Обёртка resolve_workspace для тулов — прокидывает registry."""
    return resolve_workspace(workspace, ctx, registry)


# Reusable Annotated types ---------------------------------------------------

WorkspaceParam = Annotated[
    str,
    Field(
        description=(
            "Workspace slug from list_workspaces (maps to one YouGile company "
            "API key). Use 'default' for the legacy YOUGILE_API_KEY."
        ),
        examples=["default", "main", "team"],
    ),
]

UUIDParam = Annotated[
    str,
    Field(
        description="YouGile UUID (8-4-4-4-12 hex format).",
        examples=["086866d2-a230-4a4a-8225-e3a9d847b6d0"],
    ),
]

VerbosityParam = Annotated[
    Verbosity,
    Field(
        description=(
            "Response detail level. 'compact' (default) strips noisy fields "
            "(timestamps, internal IDs, empty defaults) and inserts a "
            "_meta.omitted_fields hint when anything was dropped. 'full' "
            "returns the raw YouGile API payload — use for debugging audit "
            "history, exact timestamps, or extension data. 'custom' returns "
            "only {id} per item; use include[] to add specific fields."
        ),
        examples=["compact", "full", "custom"],
    ),
]

IncludeParam = Annotated[
    Optional[List[str]],
    Field(
        description=(
            "List of opt-in field keys to include in the response. "
            "Works with any verbosity level. Special keys: 'description', "
            "'checklists', 'stickers', 'stopwatch', 'timer', 'time_tracking', "
            "'deal', 'extension_data', 'deadline_history', 'timestamps', 'all'. "
            "Unknown keys go to _meta.unknown_includes without error."
        ),
        examples=[["description"], ["checklists", "stickers"], ["all"]],
    ),
]


# ---------------------------------------------------------------------------
# Authorization & workspaces
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def get_companies(
    login: Annotated[str, Field(description="YouGile account email.")],
    password: Annotated[str, Field(description="YouGile account password (plain text — handled in-memory only).")],
    ctx: Context,
) -> list:
    """List YouGile companies the given account can access.

    USE WHEN: bootstrapping a new workspace and you need the company UUID
    before calling create_api_key.
    DO NOT USE: in normal operation — the server already holds API keys for
    pre-configured workspaces (see list_workspaces).
    RETURNS: list of {id, name} objects, one per company.
    """
    return await get_companies_tool(login, password, ctx)


@mcp.tool(annotations=ANN_CREATE)
async def create_api_key(
    login: Annotated[str, Field(description="YouGile account email.")],
    password: Annotated[str, Field(description="YouGile account password.")],
    company_id: Annotated[str, Field(description="Company UUID from get_companies.")],
    ctx: Context,
) -> dict:
    """Provision a new API key for a company.

    USE WHEN: setting up a new workspace from scratch.
    DO NOT USE: as part of regular workflow — keys persist on YouGile side
    until explicitly revoked (max 30 per account).
    RETURNS: {key: "..."} — store securely in the server env.
    RELATED: list_api_keys, delete_api_key.
    """
    return await create_api_key_tool(login, password, company_id, ctx)


@mcp.tool(annotations=ANN_READ)
async def list_api_keys(
    login: Annotated[str, Field(description="YouGile account email.")],
    password: Annotated[str, Field(description="YouGile account password.")],
    company_id: Annotated[
        Optional[str],
        Field(description="Optional company UUID filter."),
    ] = None,
    ctx: Context = None,
) -> list:
    """List API keys associated with the account (max 30 per account).

    USE WHEN: auditing existing keys before creating a new one.
    RETURNS: list of {key, companyId, ...} entries.
    """
    return await list_api_keys_tool(login, password, company_id, ctx)


@mcp.tool(annotations=ANN_DELETE)
async def delete_api_key(
    api_key: Annotated[str, Field(description="Full API key string to revoke.")],
    ctx: Context,
) -> dict:
    """Revoke an API key.

    USE WHEN: rotating credentials or cleaning up old keys.
    DESTRUCTIVE: any session using this key will fail with 401 afterwards.
    RETURNS: {success: bool}.
    """
    return await delete_api_key_tool(api_key, ctx)


@mcp.tool(annotations=ANN_READ)
async def list_workspaces(ctx: Context = None) -> list[dict]:
    """List workspaces this server is configured for.

    USE WHEN: starting any flow that needs a workspace slug, when you are
    unsure which slug the user means, or to verify a slug is configured.
    RETURNS: list of {slug, label, has_company_id} — `label` falls back to
    the slug if YOUGILE_LABEL_<SLUG> is unset; `has_company_id` is True
    when YOUGILE_COMPANY_<SLUG> is configured (needed for auth re-init).
    Never returns API keys.
    RELATED: every other tool accepts the returned slug as `workspace`.
    """
    from .core import registry as _registry

    if ctx:
        await ctx.info(f"Listing {len(_registry.slugs())} configured workspace(s)")
    return [w.to_dict() for w in _registry.list_workspaces()]


@mcp.tool(annotations=ANN_READ)
async def get_user_context(ctx: Context = None) -> str:
    """Return server-side user context (default project/board hints, if configured).

    USE WHEN: at the start of a session to discover any default
    project/board the user has pre-registered, so you can skip list_* calls.
    RETURNS: free-form string (the YOUGILE_USER_CONTEXT env value) or a
    fallback message if nothing is configured.
    """
    try:
        if ctx:
            await ctx.info("Retrieving user context settings")

        if settings.user_context:
            return settings.user_context
        return (
            "No user context configured. Discover projects/boards/columns via "
            "list_projects, list_boards, list_columns."
        )
    except Exception as exc:
        if ctx:
            await ctx.error(f"Error retrieving user context: {exc}")
        return "Error retrieving user context settings."


# ---------------------------------------------------------------------------
# Meta / introspection
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def describe_response(
    entity: Annotated[
        Optional[str],
        Field(
            description=(
                "Entity name (case-insensitive). One of: task, project, board, "
                "column, user, message, group_chat, sticker, webhook. "
                "Omit to get overview of all entities."
            ),
            examples=["task", "project", "webhook"],
        ),
    ] = None,
    verbosity: Annotated[
        Literal["compact", "full"],
        Field(
            description=(
                "'compact' shows only fields present in compact responses; "
                "'full' shows all fields including opt-in ones."
            ),
        ),
    ] = "compact",
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Return the response schema for a YouGile entity type.

    USE WHEN: You need to know which fields are available, which verbosity level
    includes them, or which include[] key to use for opt-in fields.
    Call BEFORE constructing an unusual field request — saves round-trips.

    DO NOT USE: For standard CRUD operations where fields are well-known.

    RETURNS: Without entity — overview of all 9 entities with field counts.
    With entity — field-level schema with types, verbosity levels, include keys, quirks.

    RELATED: All list_* and get_* tools accept verbosity and include[] parameters.
    """
    return await describe_response_impl(entity=entity, verbosity=verbosity)


@mcp.tool(annotations=ANN_READ)
async def setup_yougile_skill(
    memory_dir: Annotated[
        Optional[str],
        Field(
            description=(
                "Override path for briefing.md. "
                "Default: ~/.agents/skills/yougile-personal/briefing.md. "
                "Set YOUGILE_USER_MEMORY_DIR env var to make the override permanent."
            ),
            examples=["~/.agents/skills/yougile-personal", "/custom/path"],
        ),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Guide interactive setup of the yougile-personal SKILL.

    USE WHEN: User asks to 'configure skill', 'setup yougile', or briefing.md is missing.

    DO NOT USE: If briefing.md already exists and user hasn't asked to reconfigure.

    RETURNS: List of questions to ask the user + target path for briefing.md.
    After collecting answers — call list_projects to resolve UUIDs, then write briefing.md.

    RELATED: Resource yougile://skill-template — shows the SKILL.md template structure.
    """
    return await setup_yougile_skill_impl(memory_dir=memory_dir)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_users(
    email: Annotated[
        Optional[str],
        Field(description="Exact email match (server-side filter)."),
    ] = None,
    project_id: Annotated[
        Optional[str],
        Field(description="Restrict to members of this project UUID (server-side filter)."),
    ] = None,
    limit: Annotated[int, Field(description="Page size, default 50, max 1000.")] = 50,
    offset: Annotated[int, Field(description="Page offset.")] = 0,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List users in the workspace company, optionally filtered.

    USE WHEN: mapping a name/email to a user_id before assignment, or for
    roster snapshots.
    RETURNS (compact, default): {id, email, realName} per user. Use
    verbosity="full" to additionally include isAdmin, status (online/offline)
    and lastActivity timestamp.
    NOTE: YouGile /users does not support `includeDeleted`; soft-deleted
    users are never returned here. Does NOT include department membership
    or custom fields — call get_user for the full profile.
    """
    return await list_users_tool(
        email=email,
        project_id=project_id,
        limit=limit,
        offset=offset,
        verbosity=verbosity,
        include=include,
        workspace=workspace,
        ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def invite_user(
    email: Annotated[str, Field(description="Invitee email address.")],
    is_admin: Annotated[
        bool,
        Field(
            description=(
                "True to grant company-admin rights on invite. Default False."
            ),
        ),
    ] = False,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Invite a user to the workspace company by email.

    USE WHEN: onboarding a new team member.
    API CONTRACT: YouGile's CreateUserDto accepts ONLY `email` (required) and
    `isAdmin` (optional). Identity fields (first/last name, departments) are
    NOT settable via API v2 — the invitee provides those after accepting the
    invite, or an admin edits them in the YouGile web UI.
    SIDE EFFECT: YouGile sends an email invitation; consumes a license seat.
    RETURNS: {id} of the created user record.
    """
    return await invite_user_tool(email=email, is_admin=is_admin, workspace=workspace, ctx=ctx)


@mcp.tool(annotations=ANN_READ)
async def get_user(
    user_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get profile of one user.

    USE WHEN: looking up a single user by ID.
    RETURNS (compact, default): {id, email, realName}. Use verbosity="full"
    to additionally include isAdmin, status, lastActivity (raw UserDto).
    """
    return await get_user_tool(
        user_id=user_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_UPDATE)
async def update_user(
    user_id: UUIDParam,
    is_admin: Annotated[
        bool,
        Field(
            description=(
                "Target admin flag. Pass True to promote to company admin, "
                "False to demote."
            ),
        ),
    ],
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Update a user's admin status.

    API CONTRACT: YouGile's UpdateUserDto exposes ONLY `isAdmin`. Other
    identity fields (name, departments, email) are NOT settable via API v2 —
    edit those in the YouGile web UI.
    USE WHEN: promoting/demoting between company admin and regular user.
    """
    return await update_user_tool(user_id=user_id, is_admin=is_admin, workspace=workspace, ctx=ctx)


@mcp.tool(annotations=ANN_DELETE)
async def remove_user(
    user_id: UUIDParam,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Remove a user from the workspace company.

    DESTRUCTIVE: removes access; existing task assignments persist with a
    dangling user_id reference. Frees a license seat.
    USE WHEN: offboarding. Always confirm with the human first.
    """
    return await remove_user_tool(user_id=user_id, workspace=workspace, ctx=ctx)


@mcp.tool(annotations=ANN_READ)
async def get_me(
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Return the user account that owns this workspace's API key.

    USE WHEN: you need the calling user's UUID (e.g. to filter
    list_tasks(assigned_to=me) without asking the user).
    RETURNS (compact, default): {id, email, realName}. Use verbosity="full"
    for isAdmin/status/lastActivity.
    """
    return await get_me_tool(verbosity=verbosity, include=include, workspace=workspace, ctx=ctx)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_projects(
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List all projects in the workspace.

    USE WHEN: you do not yet know the project_id. The result is small (most
    companies have <50 projects) — safe to call on demand.
    RETURNS (compact, default): {id, title} per project. Use verbosity="full"
    to additionally include timestamp and the {user_id: role} users map
    (~2.5x larger). Full mode is required when you need to check who can
    access a project before assigning a task.
    """
    return await list_projects_tool(verbosity=verbosity, include=include, workspace=workspace, ctx=ctx)


@mcp.tool(annotations=ANN_CREATE)
async def create_project(
    title: Annotated[str, Field(description="Project title.")],
    users: Annotated[
        Optional[Dict[str, str]],
        Field(
            description=(
                "Initial user roles: {user_id: role}. Built-in roles: 'admin', "
                "'worker', 'observer'. Custom role slugs also accepted."
            ),
        ),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Create a new project.

    API CONTRACT: YouGile's CreateProjectDto only accepts `title` and
    `users`. There is no workflow association at create time — workflow
    concepts live on boards, not projects.
    RETURNS: {id} only — call get_project(project_id) for full details.
    RELATED: create_board to add boards after creation.
    """
    return await create_project_tool(
        title=title, users=users, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_project(
    project_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one project's details.

    RETURNS (compact, default): {id, title}. Use verbosity="full" to also
    include timestamp and the users-role map (needed for permission checks).
    """
    return await get_project_tool(
        project_id=project_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_UPDATE)
async def update_project(
    project_id: UUIDParam,
    title: Annotated[Optional[str], Field(description="New title.")] = None,
    users: Annotated[
        Optional[Dict[str, str]],
        Field(
            description=(
                "Replacement {user_id: role} map. REPLACES existing — read "
                "get_project first if you only want to add a user."
            ),
        ),
    ] = None,
    deleted: Annotated[
        Optional[bool],
        Field(description="True = soft-delete the project; False = restore."),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Update project title, users, or soft-delete state.

    API CONTRACT: YouGile's UpdateProjectDto exposes only `title`, `users`,
    and `deleted`. There is no workflow field.
    NOTE: `users` is a full replacement; preserve existing members by
    merging with get_project output.
    """
    return await update_project_tool(
        project_id=project_id, title=title, users=users, deleted=deleted,
        workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_boards(
    project_id: Annotated[
        Optional[str],
        Field(description="Optional project UUID to scope the list."),
    ] = None,
    title: Annotated[
        Optional[str],
        Field(description="Partial title filter."),
    ] = None,
    limit: Annotated[int, Field(description="Page size, default 50.")] = 50,
    offset: Annotated[int, Field(description="Page offset, default 0.")] = 0,
    include_deleted: Annotated[bool, Field(description="Include soft-deleted boards.")] = False,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List boards, optionally filtered by project or title.

    RETURNS (compact, default): {id, title, projectId, stickers} per board
    (default deleted=false flag stripped). Use verbosity="full" for raw API.
    """
    return await list_boards_tool(
        project_id=project_id, title=title, limit=limit, offset=offset,
        include_deleted=include_deleted, verbosity=verbosity, include=include,
        workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def create_board(
    title: Annotated[str, Field(description="Board title.")],
    project_id: Annotated[str, Field(description="Parent project UUID.")],
    stickers: Annotated[
        Optional[Dict[str, Any]],
        Field(
            description=(
                "Sticker visibility on the board (StickersDto). Keys: timer, "
                "deadline, stopwatch, timeTracking, assignee, repeat (all bool). "
                "Plus 'custom': {custom_sticker_uuid: bool}. "
                "Example: {'deadline': true, 'timeTracking': true, "
                "'custom': {'<uuid>': true}}."
            ),
        ),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Create a board inside a project.

    API CONTRACT: YouGile's CreateBoardDto only accepts `title`, `projectId`,
    and `stickers`. Workflow assignment is not part of board creation.
    RETURNS: {id} only — call get_board afterwards for full details.
    RELATED: create_column to add columns; create_task to populate them.
    """
    return await create_board_tool(
        title=title, project_id=project_id,
        stickers=stickers, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_board(
    board_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one board's configuration.

    RETURNS (compact, default): {id, title, projectId, stickers} (default
    deleted flag stripped). Use verbosity="full" for raw API.
    """
    return await get_board_tool(
        board_id=board_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_UPDATE)
async def update_board(
    board_id: UUIDParam,
    title: Annotated[Optional[str], Field(description="New title.")] = None,
    project_id: Annotated[
        Optional[str],
        Field(description="Move the board to a different project (UUID)."),
    ] = None,
    stickers: Annotated[
        Optional[Dict[str, Any]],
        Field(description="StickersDto — see create_board for shape."),
    ] = None,
    deleted: Annotated[
        Optional[bool],
        Field(description="True = soft-delete; False = restore previously-deleted board."),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Update a board's title, parent project, sticker visibility, or soft-delete state.

    API CONTRACT: YouGile's UpdateBoardDto exposes only `title`, `projectId`,
    `stickers`, and `deleted`. There is no workflow field.
    NOTE: only the fields you pass are touched.
    """
    return await update_board_tool(
        board_id=board_id, title=title, project_id=project_id,
        stickers=stickers, deleted=deleted, workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_columns(
    board_id: Annotated[
        Optional[str],
        Field(description="Board UUID filter; omit to list all columns in the workspace."),
    ] = None,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List columns, optionally scoped to a board.

    USE WHEN: you have a board_id but need the column_id (e.g. before
    create_task or update_task(column_id=...)).
    NOTE: ColumnDto is already minimal; compact and full are nearly
    identical here. The verbosity arg is exposed only for consistency
    with other list_* / get_* tools.
    """
    return await list_columns_tool(
        board_id=board_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def create_column(
    title: Annotated[str, Field(description="Column title.")],
    board_id: Annotated[str, Field(description="Parent board UUID.")],
    color: Annotated[
        Optional[int],
        Field(
            description=(
                "YouGile palette index, 1-16. Sample mapping: 1=gray, 2=red, "
                "3=orange, 4=yellow, 5=green, 6=teal, 7=blue, 8=purple."
            ),
            ge=1,
            le=16,
        ),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Create a column inside a board.

    RETURNS: {id} only.
    """
    return await create_column_tool(
        title=title, board_id=board_id, color=color, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_column(
    column_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one column's details.

    NOTE: ColumnDto is already minimal; verbosity rarely changes the
    output. Kept for consistency.
    """
    return await get_column_tool(
        column_id=column_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_UPDATE)
async def update_column(
    column_id: UUIDParam,
    title: Annotated[Optional[str], Field(description="New title.")] = None,
    color: Annotated[
        Optional[int],
        Field(description="New palette index, 1-16.", ge=1, le=16),
    ] = None,
    board_id: Annotated[
        Optional[str],
        Field(description="Move the column to a different board (UUID)."),
    ] = None,
    deleted: Annotated[
        Optional[bool],
        Field(description="True = soft-delete; False = restore."),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Update a column's title, color, parent board, or soft-delete state."""
    return await update_column_tool(
        column_id=column_id, title=title, color=color,
        board_id=board_id, deleted=deleted,
        workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_task_summaries(
    limit: Annotated[int, Field(description="Page size, default 50, max 1000.")] = 50,
    offset: Annotated[int, Field(description="Page offset.")] = 0,
    sticker_id: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side filter — only return tasks carrying this sticker. "
                "Discover IDs via list_string_stickers."
            ),
        ),
    ] = None,
    sticker_state_id: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side filter — only return tasks whose sticker value "
                "matches this state ID. Typically combined with sticker_id."
            ),
        ),
    ] = None,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List minimal task summaries (id + title) with pagination.

    USE WHEN: you need a roster and full task payloads would waste tokens.
    RETURNS (compact, default): paging envelope; each task strips timestamps,
    createdBy, idTaskCommon/idTaskProject, type and empty default fields.
    Use verbosity="full" to see audit history, exact timestamps, or creator.
    RELATED: list_tasks for the full task body.
    """
    return await list_task_summaries_tool(
        limit=limit, offset=offset,
        sticker_id=sticker_id, sticker_state_id=sticker_state_id,
        verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def list_tasks(
    column_id: Annotated[
        Optional[str],
        Field(description="Column UUID filter (server-side)."),
    ] = None,
    assigned_to: Annotated[
        Optional[str],
        Field(description="User UUID filter (server-side). Use get_me to find your own ID."),
    ] = None,
    title: Annotated[
        Optional[str],
        Field(description="Partial title filter (server-side)."),
    ] = None,
    limit: Annotated[int, Field(description="Page size, default 50, max 1000.")] = 50,
    offset: Annotated[int, Field(description="Page offset.")] = 0,
    include_deleted: Annotated[
        bool,
        Field(description="True to include soft-deleted tasks."),
    ] = False,
    sticker_id: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side filter — only return tasks carrying this sticker. "
                "Discover IDs via list_string_stickers."
            ),
        ),
    ] = None,
    sticker_state_id: Annotated[
        Optional[str],
        Field(
            description=(
                "Server-side filter — only return tasks whose sticker value "
                "matches this state ID (e.g. 'Priority=High'). Typically "
                "combined with sticker_id."
            ),
        ),
    ] = None,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List full task records with optional filters.

    USE WHEN: you need task bodies (description, stickers, deadlines).
    RETURNS (compact, default): each task contains id, title, columnId, plus
    completion/archive flags and content fields (description, checklists,
    deadline, assigned) only when set. Strips timestamps, createdBy,
    idTaskCommon/idTaskProject, type, deadline.history. Saves ~37% tokens.
    Use verbosity="full" when you need audit history, exact creation
    timestamps, who created tasks, or extension data.
    NOTE: the API does NOT support filtering by deadline range or
    creation date — those must be applied client-side after fetching.
    For date filtering, prefer get_tasks_by_date.
    """
    return await list_tasks_tool(
        column_id=column_id, assigned_to=assigned_to, title=title,
        limit=limit, offset=offset, include_deleted=include_deleted,
        sticker_id=sticker_id, sticker_state_id=sticker_state_id,
        verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def create_task(
    title: Annotated[str, Field(description="Task title.")],
    column_id: Annotated[
        Optional[str],
        Field(
            description=(
                "Column UUID. OPTIONAL: omitting it creates a 'floating' task "
                "(no board location) — useful as a standalone sub-task. Get "
                "column UUIDs via list_columns(board_id=...)."
            ),
        ),
    ] = None,
    description: Annotated[
        Optional[str],
        Field(
            description=(
                "HTML body. Use <br> for line breaks (NOT \\n). See resource "
                "yougile://guides/html for the full formatter."
            ),
        ),
    ] = None,
    assigned_users: Annotated[
        Optional[List[str]],
        Field(description="List of assignee user UUIDs. Look up via list_users."),
    ] = None,
    deadline: Annotated[
        Optional[Dict[str, Any]],
        Field(
            description=(
                "Deadline sticker {deadline: <ms_timestamp>, withTime: bool, "
                "blockedPoints: [], links: [], startDate?: <ms>}. "
                "blockedPoints and links are required even when empty — prefer "
                "set_task_deadline which auto-fills them."
            ),
        ),
    ] = None,
    time_tracking: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Time tracking sticker {plan: hours, work: hours}."),
    ] = None,
    stickers: Annotated[
        Optional[Dict[str, str]],
        Field(
            description=(
                "Custom stickers {sticker_id: state_id}. Resolve IDs via "
                "list_string_stickers + get_string_sticker. Special values: "
                "'-' detaches the sticker, 'empty' clears the value."
            ),
        ),
    ] = None,
    subtasks: Annotated[
        Optional[List[str]],
        Field(
            description=(
                "List of child task UUIDs (not nested dicts). Create children "
                "with separate create_task calls first, then reference their IDs."
            ),
        ),
    ] = None,
    checklists: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(
            description=(
                "Checklist groups: [{title: str, items: [{title: str, "
                "isCompleted: bool}, ...]}, ...]. Each item must include "
                "isCompleted (defaults to False)."
            ),
        ),
    ] = None,
    completed: Annotated[Optional[bool], Field(description="Mark as completed on create.")] = None,
    archived: Annotated[Optional[bool], Field(description="Create in archived state.")] = None,
    color: Annotated[
        Optional[TaskColor],
        Field(description="Card colour on the board."),
    ] = None,
    stopwatch: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Stopwatch sticker {running: bool, seconds: int}."),
    ] = None,
    timer: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Timer sticker {running: bool, seconds: int}."),
    ] = None,
    deal: Annotated[
        Optional[Dict[str, Any]],
        Field(description="CRM deal payload (DealDataDto). Marks the task as a CRM deal."),
    ] = None,
    id_task_common: Annotated[
        Optional[str],
        Field(description="Human-readable cross-company task ID (e.g. 'ID-484')."),
    ] = None,
    id_task_project: Annotated[
        Optional[str],
        Field(description="Human-readable per-project task ID (e.g. 'DEV-484')."),
    ] = None,
    extension_data: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Free-form data used by YouGile extensions."),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Create a task.

    USE WHEN: adding a new work item, sub-task, or CRM deal.
    BEFORE: call list_columns(board_id) for column_id, list_users for
    assignees, list_string_stickers + get_string_sticker for sticker IDs.
    RETURNS: {id} only — call get_task for the full payload.
    """
    return await create_task_tool(
        title=title,
        column_id=column_id,
        description=description,
        assigned_users=assigned_users,
        deadline=deadline,
        time_tracking=time_tracking,
        stickers=stickers,
        subtasks=subtasks,
        checklists=checklists,
        completed=completed,
        archived=archived,
        color=color,
        stopwatch=stopwatch,
        timer=timer,
        deal=deal,
        id_task_common=id_task_common,
        id_task_project=id_task_project,
        extension_data=extension_data,
        workspace=workspace,
        ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_task(
    task_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one task's payload (title, description, assigned, stickers, etc.).

    RETURNS (compact, default): drops timestamps (creation/archived/completed),
    createdBy, idTaskCommon/idTaskProject (duplicates of id), type,
    deadline.history, and empty default fields. _meta.omitted_fields lists
    what was actually dropped for this specific task.
    Use verbosity="full" to access audit history, the original creator,
    or extension data (raw TaskDto).
    """
    return await get_task_tool(
        task_id=task_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_tasks_by_date(
    assigned_to: Annotated[
        Optional[str],
        Field(description="User UUID — server-side filter (fast)."),
    ] = None,
    created_by: Annotated[
        Optional[str],
        Field(
            description=(
                "User UUID — client-side filter applied after fetch. Slow on "
                "companies with > a few thousand tasks."
            ),
        ),
    ] = None,
    target_date: Annotated[
        Optional[str],
        Field(description="YYYY-MM-DD date. Defaults to today.", examples=["2026-05-17"]),
    ] = None,
    completed_only: Annotated[bool, Field(description="Restrict to completed tasks.")] = False,
    limit: Annotated[int, Field(description="Max tasks fetched before client-side filtering.")] = 5000,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List tasks filtered by date and optional assignee / creator.

    USE WHEN: building standup, productivity, or retrospective reports.
    RETURNS (compact, default): same per-task pruning as list_tasks.
    Use verbosity="full" when you need raw payloads (e.g. to inspect
    creation timestamps separately from the filter date).
    EXAMPLES:
      get_tasks_by_date(assigned_to="<uid>") — today's tasks for a user.
      get_tasks_by_date(target_date="2026-01-15", completed_only=True).
      get_tasks_by_date(created_by="<uid>") — slow client-side filter.
    """
    return await get_tasks_by_date_tool(
        assigned_to=assigned_to, created_by=created_by, target_date=target_date,
        completed_only=completed_only, limit=limit, verbosity=verbosity, include=include,
        workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_UPDATE)
async def update_task(
    task_id: UUIDParam,
    title: Annotated[Optional[str], Field(description="New title.")] = None,
    description: Annotated[
        Optional[str],
        Field(description="HTML body (<br> for newlines). See yougile://guides/html."),
    ] = None,
    column_id: Annotated[
        Optional[str],
        Field(description="Move task to this column UUID. Pass '-' to detach from any column."),
    ] = None,
    assigned_users: Annotated[
        Optional[List[str]],
        Field(
            description=(
                "Replacement list of assignee UUIDs (REPLACES existing — read "
                "get_task and merge if you want to add)."
            ),
        ),
    ] = None,
    deadline: Annotated[
        Optional[Dict[str, Any]],
        Field(
            description=(
                "Deadline sticker — see create_task. Prefer set_task_deadline. "
                "Pass {'deleted': True} to remove the deadline."
            ),
        ),
    ] = None,
    time_tracking: Annotated[
        Optional[Dict[str, Any]],
        Field(description="{plan: hours, work: hours}. Pass {'deleted': True} to remove."),
    ] = None,
    stickers: Annotated[
        Optional[Dict[str, str]],
        Field(
            description=(
                "{sticker_id: state_id}. Use '-' to detach a sticker, 'empty' "
                "to clear its value."
            ),
        ),
    ] = None,
    subtasks: Annotated[
        Optional[List[str]],
        Field(description="Replacement list of child task UUIDs (REPLACES existing)."),
    ] = None,
    checklists: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(description="Replacement checklist groups — same shape as create_task."),
    ] = None,
    completed: Annotated[Optional[bool], Field(description="Mark as completed / reopen.")] = None,
    archived: Annotated[Optional[bool], Field(description="Archive / unarchive.")] = None,
    deleted: Annotated[
        Optional[bool],
        Field(
            description=(
                "True = soft-delete (hides from list_tasks unless "
                "include_deleted=true). False = restore."
            ),
        ),
    ] = None,
    color: Annotated[Optional[TaskColor], Field(description="Card colour.")] = None,
    stopwatch: Annotated[Optional[Dict[str, Any]], Field(description="Stopwatch sticker.")] = None,
    timer: Annotated[Optional[Dict[str, Any]], Field(description="Timer sticker.")] = None,
    deal: Annotated[Optional[Dict[str, Any]], Field(description="CRM deal payload.")] = None,
    id_task_common: Annotated[Optional[str], Field(description="Cross-company human ID.")] = None,
    id_task_project: Annotated[Optional[str], Field(description="Per-project human ID.")] = None,
    extension_data: Annotated[Optional[Dict[str, Any]], Field(description="Extension data.")] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Update a task. Only passed fields are touched.

    USE WHEN: any single-field edit, status move, or soft-delete.
    DESTRUCTIVE: list fields (assigned_users, subtasks, stickers,
    checklists) are REPLACED, not merged. Read get_task and rebuild the
    list if you want to add an item.
    RELATED: delete_task is a shortcut for update_task(deleted=True);
    set_task_deadline is a safer helper for deadlines.
    """
    return await update_task_tool(
        task_id=task_id,
        title=title,
        description=description,
        column_id=column_id,
        assigned_users=assigned_users,
        deadline=deadline,
        time_tracking=time_tracking,
        stickers=stickers,
        subtasks=subtasks,
        checklists=checklists,
        completed=completed,
        archived=archived,
        deleted=deleted,
        color=color,
        stopwatch=stopwatch,
        timer=timer,
        deal=deal,
        id_task_common=id_task_common,
        id_task_project=id_task_project,
        extension_data=extension_data,
        workspace=workspace,
        ctx=ctx,
    )


@mcp.tool(annotations=ANN_DELETE)
async def delete_task(
    task_id: UUIDParam,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Soft-delete a task (equivalent to update_task(deleted=True)).

    USE WHEN: removing a task. Exists as an explicit alias so the intent is
    visible in tool-call traces.
    REVERSIBLE: update_task(task_id, deleted=False) restores. Deleted tasks
    are hidden from list_tasks unless include_deleted=true is passed.
    """
    return await update_task_tool(task_id=task_id, deleted=True, workspace=workspace, ctx=ctx)


@mcp.tool(annotations=ANN_UPDATE)
async def set_task_deadline(
    task_id: UUIDParam,
    deadline_timestamp: Annotated[
        int,
        Field(
            description=(
                "Deadline as Unix timestamp in MILLISECONDS (13 digits). "
                "Seconds (10 digits) are auto-promoted."
            ),
            examples=[1653029146646],
        ),
    ],
    start_date_timestamp: Annotated[
        Optional[int],
        Field(description="Optional start date as Unix ms. Seconds auto-promoted."),
    ] = None,
    with_time: Annotated[bool, Field(description="Show time alongside date in the UI.")] = True,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Set or replace a task deadline sticker (safe wrapper).

    USE WHEN: setting a deadline. Prefer this over update_task(deadline=...)
    because it auto-fills the required blockedPoints=[] and links=[]
    fields that the YouGile API rejects when missing.
    RELATED: remove_task_sticker(sticker_type='deadline') to clear.
    """
    if deadline_timestamp < 10000000000:  # seconds → ms
        deadline_timestamp *= 1000
        if ctx:
            await ctx.info(f"Auto-converted deadline timestamp to ms: {deadline_timestamp}")

    deadline_data = {
        "deadline": deadline_timestamp,
        "withTime": with_time,
        "blockedPoints": [],
        "links": [],
    }

    if start_date_timestamp:
        if start_date_timestamp < 10000000000:
            start_date_timestamp *= 1000
            if ctx:
                await ctx.info(f"Auto-converted start date to ms: {start_date_timestamp}")
        deadline_data["startDate"] = start_date_timestamp

    return await update_task_tool(
        task_id=task_id, deadline=deadline_data, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_DELETE)
async def remove_task_sticker(
    task_id: UUIDParam,
    sticker_type: Annotated[
        str,
        Field(
            description=(
                "What to remove: 'deadline' / 'timeTracking' for system "
                "stickers, or a custom-sticker UUID for company stickers."
            ),
            examples=["deadline", "timeTracking", "086866d2-a230-4a4a-8225-e3a9d847b6d0"],
        ),
    ],
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Detach a sticker from a task.

    USE WHEN: clearing a deadline, time-tracking, or custom-sticker value.
    DESTRUCTIVE: removes the field from the task. To set a new value
    instead, use update_task(stickers=...) or set_task_deadline.
    """
    if sticker_type == "deadline":
        return await update_task_tool(
            task_id=task_id, deadline={"deleted": True}, workspace=workspace, ctx=ctx,
        )
    if sticker_type == "timeTracking":
        return await update_task_tool(
            task_id=task_id, time_tracking={"deleted": True}, workspace=workspace, ctx=ctx,
        )
    # Custom sticker — '-' detaches.
    return await update_task_tool(
        task_id=task_id, stickers={sticker_type: "-"}, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_task_chat_subscribers(
    task_id: UUIDParam,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List user UUIDs subscribed to a task's chat (receive notifications)."""
    return await get_task_chat_subscribers_tool(task_id=task_id, workspace=workspace, ctx=ctx)


@mcp.tool(annotations=ANN_UPDATE)
async def update_task_chat_subscribers(
    task_id: UUIDParam,
    subscribers: Annotated[
        List[str],
        Field(description="REPLACEMENT list of user UUIDs (full replacement, not append)."),
    ],
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Replace a task's chat subscriber list.

    NOTE: this is a full replacement. To add a user, read
    get_task_chat_subscribers first and append.
    """
    return await update_task_chat_subscribers_tool(
        task_id=task_id, subscribers=subscribers, workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Stickers
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_string_stickers(
    limit: Annotated[int, Field(description="Page size, default 50.")] = 50,
    offset: Annotated[int, Field(description="Page offset.")] = 0,
    include_deleted: Annotated[bool, Field(description="Include soft-deleted stickers.")] = False,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List custom string stickers defined in the company.

    USE WHEN: you need to discover sticker_ids (e.g. 'Priority', 'Sprint')
    before setting a sticker on a task.
    RETURNS (compact, default): list of {id, name, icon, states} per sticker
    with default deleted flag stripped. Use verbosity="full" for raw API.
    """
    return await list_string_stickers_tool(
        limit=limit, offset=offset, include_deleted=include_deleted,
        verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_string_sticker(
    sticker_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one string sticker including all its states.

    USE WHEN: you have a sticker_id (from list_string_stickers) and need
    state_ids — for example to set a 'Priority: High' value on a task.
    Compact (default) strips the default deleted flag.
    """
    return await get_string_sticker_tool(
        sticker_id=sticker_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_string_sticker_state(
    sticker_id: UUIDParam,
    state_id: UUIDParam,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one state of a string sticker (name, colour, icon)."""
    return await get_string_sticker_state_tool(
        sticker_id=sticker_id, state_id=state_id, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_sprint_sticker_state(
    sticker_id: UUIDParam,
    state_id: UUIDParam,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one state of a sprint sticker (sprint interval)."""
    return await get_sprint_sticker_state_tool(
        sticker_id=sticker_id, state_id=state_id, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def decode_task_stickers(
    stickers_dict: Annotated[
        Dict[str, str],
        Field(description="{sticker_id: state_id} as found on a task.stickers field."),
    ],
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Resolve a {sticker_id: state_id} map to human-readable labels.

    WARNING — N+1 API calls: this issues 2 requests per sticker (one for
    the sticker, one for the state). YouGile rate-limits at 50 req/min
    per company; for tasks with >5 stickers prefer caching the output of
    list_string_stickers and resolving labels client-side.
    """
    return await decode_task_stickers_tool(
        stickers_dict=stickers_dict, workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Chats & comments
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_group_chats(
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List standalone group chats (not bound to tasks).

    Compact (default) drops the bulky userRoleMap/roleConfigMap blocks —
    use verbosity="full" if you need permission/role configuration.
    """
    return await list_group_chats_tool(
        verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def create_group_chat(
    title: Annotated[str, Field(description="Chat title.")],
    users: Annotated[
        Optional[Dict[str, Any]],
        Field(description="{user_id: {'notified': bool}} — required by API."),
    ] = None,
    user_role_map: Annotated[
        Optional[Dict[str, str]],
        Field(description="{user_id: role_slug} — required by API (e.g. 'owner', 'admin')."),
    ] = None,
    role_config_map: Annotated[
        Optional[Dict[str, Any]],
        Field(
            description=(
                "{role_slug: {editProperties, editAdmins, editUsers, sendMessages, "
                "removeMessages, ...}} — required by API."
            ),
        ),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Create a group chat.

    NOTE: YouGile requires title + users + user_role_map + role_config_map
    together. Passing only title is likely to return 400.
    RETURNS: {id} of the chat.
    """
    return await create_group_chat_tool(
        title=title, users=users, user_role_map=user_role_map,
        role_config_map=role_config_map, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_group_chat(
    chat_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one group chat's details.

    Compact (default) drops userRoleMap/roleConfigMap. Use verbosity="full"
    for permission/role configuration.
    """
    return await get_group_chat_tool(
        chat_id=chat_id, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_chat_messages(
    chat_id: Annotated[
        str,
        Field(
            description=(
                "Chat UUID. For task comments, pass the task_id — every task "
                "has a chat with chat_id == task_id."
            ),
        ),
    ],
    limit: Annotated[int, Field(description="Page size, default 50.")] = 50,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List messages in a chat or task comment thread.

    USE WHEN: reading task comments or a group chat history.
    Compact (default) drops textHtml (duplicates `text` with markup),
    editTimestamp, empty reactions, and default deleted flag. Use
    verbosity="full" if you need the HTML body or edit timestamps.
    RELATED: get_task_comments is an alias for tasks.
    """
    return await get_chat_messages_tool(
        chat_id=chat_id, limit=limit, verbosity=verbosity, include=include,
        workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def send_chat_message(
    chat_id: Annotated[
        str,
        Field(description="Chat UUID (= task_id for task comments)."),
    ],
    text: Annotated[
        str,
        Field(description="Plain text body. Wrapped in <p>...</p> if text_html is not supplied."),
    ],
    text_html: Annotated[
        Optional[str],
        Field(
            description=(
                "HTML body. Use <br> for newlines (see yougile://guides/html). "
                "Server does NOT escape — sanitize untrusted input."
            ),
        ),
    ] = None,
    label: Annotated[
        Optional[str],
        Field(description="Short label / quick-link text. Defaults to 'Comment'."),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Post a message to a chat or task comment thread.

    USE WHEN: commenting on a task or messaging a group chat.
    RELATED: add_task_comment is an alias for tasks.
    """
    return await send_chat_message_tool(
        chat_id=chat_id, text=text, text_html=text_html, label=label,
        workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_chat_message(
    chat_id: UUIDParam,
    message_id: UUIDParam,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Get one chat message by ID.

    Compact (default) drops textHtml/editTimestamp/empty reactions.
    Use verbosity="full" for raw API payload.
    """
    return await get_chat_message_tool(
        chat_id=chat_id, message_id=message_id, verbosity=verbosity, include=include,
        workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_UPDATE)
async def update_chat_message(
    chat_id: UUIDParam,
    message_id: UUIDParam,
    label: Annotated[Optional[str], Field(description="New label / quick-link text.")] = None,
    react: Annotated[
        Optional[MessageReact],
        Field(description="Admin reaction emoji (enum of 👍 👎 👏 🙂 😀 😕 🎉 ❤ 🚀 ✔)."),
    ] = None,
    delete: Annotated[bool, Field(description="True = soft-delete the message.")] = False,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Update message metadata: label, admin reaction, or soft-delete.

    NOTE: the YouGile API does NOT support editing message text — only
    metadata. UpdateChatMessageDto exposes only deleted/label/react.
    """
    return await update_chat_message_tool(
        chat_id=chat_id, message_id=message_id, label=label, react=react,
        delete=delete, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def get_task_comments(
    task_id: UUIDParam,
    limit: Annotated[int, Field(description="Page size, default 50.")] = 50,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List comments on a task (alias for get_chat_messages(chat_id=task_id))."""
    return await get_task_comments_tool(
        task_id=task_id, limit=limit, verbosity=verbosity, include=include,
        workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def add_task_comment(
    task_id: UUIDParam,
    comment: Annotated[
        str,
        Field(
            description=(
                "HTML body. Use <br> for newlines (see yougile://guides/html). "
                "Plain text renders as a single line."
            ),
        ),
    ],
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Post a comment on a task (alias for send_chat_message(chat_id=task_id))."""
    return await add_task_comment_tool(
        task_id=task_id, comment=comment, workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_READ)
async def list_webhooks(
    limit: Annotated[int, Field(description="Page size (client-side, default 50).")] = 50,
    offset: Annotated[int, Field(description="Page offset (client-side).")] = 0,
    include_deleted: Annotated[bool, Field(description="Include soft-deleted webhooks.")] = False,
    verbosity: VerbosityParam = "compact",
    include: IncludeParam = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> list:
    """List webhook subscriptions for the workspace.

    NOTE: YouGile does not paginate /webhooks server-side; the full list is
    fetched and paginated client-side.
    Compact (default) drops lastSuccess/failuresSinceLastSuccess; use
    verbosity="full" when debugging delivery failures.
    """
    return await list_webhooks_tool(
        limit=limit, offset=offset, include_deleted=include_deleted,
        verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_CREATE)
async def create_webhook(
    url: Annotated[str, Field(description="HTTPS endpoint receiving the event POST.")],
    event: Annotated[
        str,
        Field(
            description="Event pattern — exact ('task-created') or wildcard ('task-*', '.*').",
            examples=["task-created", "task-updated", "chat-message"],
        ),
    ],
    filters: Annotated[
        Optional[List[Dict[str, Any]]],
        Field(
            description=(
                "List of {name, value} filters narrowing the scope (e.g. "
                "[{'name': 'location', 'value': ['<board_uuid>']}]). REQUIRED "
                "by API even if empty. Passing an empty list (or omitting it) "
                "is now REJECTED unless you also pass allow_unfiltered=True — "
                "this guard prevents accidental firehose subscriptions."
            ),
        ),
    ] = None,
    allow_unfiltered: Annotated[
        bool,
        Field(
            description=(
                "Explicit opt-in for a company-wide firehose webhook (no "
                "filters). Default False. Set True only when you really want "
                "to receive every event in the company."
            ),
        ),
    ] = False,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Create a webhook subscription.

    BEST PRACTICE: always pass `filters` — an unfiltered webhook fires on
    every event in the company and will rate-limit quickly.

    If you really do want a firehose, set `allow_unfiltered=True` explicitly.
    """
    return await create_webhook_tool(
        url=url, event=event, filters=filters or [],
        allow_unfiltered=allow_unfiltered, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_UPDATE)
async def update_webhook(
    webhook_id: UUIDParam,
    url: Annotated[Optional[str], Field(description="New target URL.")] = None,
    event: Annotated[Optional[str], Field(description="New event pattern.")] = None,
    filters: Annotated[Optional[List[Dict[str, Any]]], Field(description="Replacement filter list.")] = None,
    disabled: Annotated[Optional[bool], Field(description="True = pause deliveries without deleting.")] = None,
    deleted: Annotated[bool, Field(description="True = soft-delete the subscription.")] = False,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Update or soft-delete a webhook subscription."""
    return await update_webhook_tool(
        webhook_id=webhook_id, url=url, event=event, filters=filters,
        deleted=deleted, disabled=disabled, workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_CREATE)
async def upload_file(
    path: Annotated[
        str,
        Field(description="Absolute path to the file on the server filesystem."),
    ],
    filename: Annotated[
        Optional[str],
        Field(description="Optional override for the reported filename."),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Upload a file from the server's filesystem to YouGile storage.

    USE WHEN: attaching a file referenced by URL in a task description or
    comment. Embed the returned URL via <a href="..."> in the HTML body.
    RETURNS: {result, url, fullUrl}.
    """
    return await upload_file_tool(
        path=path, filename=filename, workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ANN_CREATE)
async def create_crm_contact(
    project_id: Annotated[str, Field(description="CRM project UUID.")],
    title: Annotated[str, Field(description="Contact display name.")],
    position: Annotated[Optional[str], Field(description="Job title / role.")] = None,
    phone: Annotated[Optional[str], Field(description="Primary phone.")] = None,
    email: Annotated[Optional[str], Field(description="Email address.")] = None,
    additional_phone: Annotated[Optional[str], Field(description="Secondary phone.")] = None,
    address: Annotated[Optional[str], Field(description="Postal / street address.")] = None,
    fields_extra: Annotated[
        Optional[Dict[str, Any]],
        Field(description="Additional custom fields merged last (overrides on key conflict)."),
    ] = None,
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Create a CRM contact person inside a CRM project.

    USE WHEN: registering a new contact before creating a deal task.
    """
    return await create_crm_contact_tool(
        project_id=project_id, title=title, position=position, phone=phone,
        email=email, additional_phone=additional_phone, address=address,
        fields_extra=fields_extra, workspace=workspace, ctx=ctx,
    )


@mcp.tool(annotations=ANN_READ)
async def find_crm_contact_by_external_id(
    provider: Annotated[
        str,
        Field(description="External provider slug (e.g. 'wazzup').", examples=["wazzup"]),
    ],
    chat_id: Annotated[
        str,
        Field(description="Provider-side chat / contact identifier."),
    ],
    workspace: WorkspaceParam = "default",
    ctx: Context = None,
) -> dict:
    """Look up a CRM contact by an external messenger ID.

    USE WHEN: routing an incoming Wazzup/Telegram message to an existing
    deal, before deciding whether to create_crm_contact.
    RETURNS: contact dict, or None if no match (YouGile 404 → None).
    """
    return await find_crm_contact_by_external_id_tool(
        provider=provider, chat_id=chat_id, workspace=workspace, ctx=ctx,
    )


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("yougile://api/overview")
def api_overview() -> str:
    """High-level YouGile API v2 overview and entity hierarchy."""
    return get_api_overview()


@mcp.resource("yougile://api/endpoints")
def api_endpoints() -> str:
    """Complete list of YouGile API v2 endpoints, annotated with MCP coverage."""
    return get_api_endpoints()


@mcp.resource("yougile://guides/html")
def html_guide() -> str:
    """HTML formatting reference for task descriptions and chat messages."""
    return get_html_guide()


@mcp.resource("yougile://skill-template")
async def skill_template_resource() -> str:
    """Canonical link to the SKILL.md template for personal workflow configuration.

    Use this resource to inspect the skill template BEFORE running setup_yougile_skill.
    The template lives at templates/yougile-personal-skill/SKILL.md in the MCP source.
    Read it to understand the briefing.md structure you're about to create.
    """
    return get_skill_template_content()


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(title="Setup New Project")
def setup_project(project_name: str, project_type: str = "kanban") -> str:
    """Guide for creating and configuring a new project in YouGile."""
    return setup_new_project_prompt(project_name, project_type)


@mcp.prompt(title="Create Task")
def create_task_prompt(task_title: str, priority: str = "medium") -> str:
    """Template for creating a well-structured task."""
    return create_task_workflow_prompt(task_title, priority)


@mcp.prompt(title="Sprint Planning")
def plan_sprint(sprint_name: str, duration_weeks: int = 2) -> str:
    """Sprint planning workflow with stop-gate before commitment."""
    return sprint_planning_prompt(sprint_name, duration_weeks)


@mcp.prompt(title="Daily Standup Report")
def daily_standup() -> str:
    """Generate a daily standup report (self or team)."""
    return daily_standup_prompt()


@mcp.prompt(title="Project Health Check")
def project_health_check(project_id: str) -> str:
    """Read-only audit of a project's task flow and bottlenecks."""
    return project_health_check_prompt(project_id)


@mcp.prompt(title="User Productivity Report")
def user_productivity_report(user_id: str, target_date: str = None) -> str:
    """Per-user productivity report for a given date."""
    return user_productivity_report_prompt(user_id, target_date)


@mcp.prompt(title="Weekly Team Report")
def weekly_team_report(team_user_ids: str, start_date: str) -> str:
    """Weekly read-only team performance report."""
    return weekly_team_report_prompt(team_user_ids, start_date)


@mcp.prompt(title="Task Escalation")
def task_escalation(task_id: str) -> str:
    """Escalate a blocked task with stop-gate before mutation."""
    return task_escalation_prompt(task_id)


@mcp.prompt(title="Onboard Team Member")
def onboard_team_member(new_member_name: str, role: str) -> str:
    """Onboarding workflow for a new team member."""
    return onboarding_new_team_member_prompt(new_member_name, role)


@mcp.prompt(title="Deadline Crunch Management")
def deadline_crunch_management(deadline_date: str) -> str:
    """Triage work as a critical deadline approaches."""
    return deadline_crunch_management_prompt(deadline_date)


@mcp.prompt(title="Sprint Retrospective")
def sprint_retrospective(sprint_end_date: str, team_user_ids: str) -> str:
    """Sprint retrospective analysis (read-only)."""
    return retrospective_analysis_prompt(sprint_end_date, team_user_ids)


# ---------------------------------------------------------------------------
# Legacy single-tenant init (kept for backwards compatibility)
# ---------------------------------------------------------------------------


def _mirror_legacy_into_registry(api_key: str, company_id: str) -> None:
    """Inject the legacy single-tenant credentials into the AuthRegistry
    under the `default` slug so multi-tenant tools (which all route through
    `registry.get(workspace)`) can serve calls with workspace="default"
    even when the user is on the legacy email/password bootstrap path.

    This is intentionally a direct mutation of the registry — there is no
    public `add` method because workspaces normally come from env at startup,
    but the legacy flow obtains its key at runtime.
    """
    from .core.registry import registry as _registry, LEGACY_SLUG
    from .core.auth import AuthManager as _AuthManager
    if not _registry.has(LEGACY_SLUG):
        mgr = _AuthManager(api_key=api_key)
        mgr.set_credentials(api_key, company_id)
        _registry._managers[LEGACY_SLUG] = mgr
    else:
        # Refresh credentials on the existing entry so a rotated key wins.
        _registry.get(LEGACY_SLUG).set_credentials(api_key, company_id)


async def initialize_auth():
    """Initialize authentication from environment variables (single-tenant fallback)."""
    if not all([settings.yougile_email, settings.yougile_password, settings.yougile_company_id]):
        return False

    try:
        api_key_to_test = settings.yougile_api_key
        if not api_key_to_test:
            api_key_to_test = load_api_key_from_credentials()

        if api_key_to_test:
            try:
                auth.auth_manager.set_credentials(api_key_to_test, settings.yougile_company_id)
                async with YouGileClient(auth.auth_manager) as client:
                    await client.get("/users")
                _mirror_legacy_into_registry(api_key_to_test, settings.yougile_company_id)
                return True
            except Exception:
                pass

        temp_auth = auth.auth_manager.__class__()
        async with YouGileClient(temp_auth) as client:
            api_key = await auth_api.create_api_key(
                client,
                settings.yougile_email,
                settings.yougile_password,
                settings.yougile_company_id,
            )
            auth.auth_manager.set_credentials(api_key, settings.yougile_company_id)
            await save_api_key_to_credentials(api_key)

        _mirror_legacy_into_registry(api_key, settings.yougile_company_id)
        return True

    except Exception:
        return False


async def save_api_key_to_credentials(api_key: str):
    """Save API key to credentials file for future reuse."""
    import json
    import os
    import tempfile
    import time
    from pathlib import Path

    temp_dir = Path(tempfile.gettempdir())
    credentials_file = temp_dir / "yougile_credentials.json"

    try:
        credentials = {}
        if credentials_file.exists():
            with open(credentials_file, "r") as f:
                credentials = json.load(f)

        credentials[settings.yougile_company_id] = {
            "api_key": api_key,
            "created_at": str(int(time.time())),
        }

        with open(credentials_file, "w") as f:
            json.dump(credentials, f, indent=2)

        try:
            os.chmod(credentials_file, 0o600)
        except (OSError, AttributeError):
            pass

    except Exception:
        pass


def load_api_key_from_credentials() -> str:
    """Load API key from credentials file."""
    import json
    import tempfile
    from pathlib import Path

    temp_dir = Path(tempfile.gettempdir())
    credentials_file = temp_dir / "yougile_credentials.json"

    if not credentials_file.exists():
        return None

    try:
        with open(credentials_file, "r") as f:
            credentials = json.load(f)
        company_data = credentials.get(settings.yougile_company_id, {})
        return company_data.get("api_key")
    except Exception:
        return None


def run_legacy_init() -> None:
    """Run single-tenant auto-auth if YOUGILE_EMAIL/PASSWORD/COMPANY_ID are set."""
    if settings.yougile_email and settings.yougile_password and settings.yougile_company_id:
        asyncio.run(initialize_auth())


def main() -> None:
    """Backwards-compatible entry point — stdio transport.

    Prefer running via `python run_server.py [--http]`.
    """
    run_legacy_init()
    mcp.run()


if __name__ == "__main__":
    main()
