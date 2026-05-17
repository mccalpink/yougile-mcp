"""
YouGile MCP Server

Main entry point for the YouGile Model Context Protocol server.
Registers all tools, resources, and prompts for YouGile API access.
"""

import asyncio
from mcp.server.fastmcp import FastMCP, Context
from .config import settings
from .core import auth
from .core.client import YouGileClient
from .api import auth as auth_api
from .yougile_mcp.tools.auth_tools import (
    get_companies_tool, 
    create_api_key_tool,
    list_api_keys_tool,
    delete_api_key_tool,
)
from .yougile_mcp.tools.user_tools import (
    list_users_tool,
    invite_user_tool,
    get_user_tool,
    update_user_tool,
    remove_user_tool,
)
from .yougile_mcp.tools.project_tools import (
    list_projects_tool,
    create_project_tool,
    get_project_tool,
    update_project_tool,
)
from .yougile_mcp.tools.board_tools import (
    list_boards_tool,
    create_board_tool,
    get_board_tool,
    update_board_tool,
)
from .yougile_mcp.tools.column_tools import (
    list_columns_tool,
    create_column_tool,
    get_column_tool,
    update_column_tool,
)
from .yougile_mcp.tools.chat_tools import (
    list_group_chats_tool,
    create_group_chat_tool,
    get_group_chat_tool,
    get_chat_messages_tool,
    send_chat_message_tool,
    get_chat_message_tool,
    update_chat_message_tool,
    get_task_comments_tool,
    add_task_comment_tool,
)
from .yougile_mcp.tools.task_tools import (
    list_task_summaries_tool,
    list_tasks_tool,
    create_task_tool,
    get_task_tool,
    get_tasks_by_date_tool,
)
from .yougile_mcp.tools.task_tools_extended import (
    update_task_tool,
    get_task_chat_subscribers_tool,
    update_task_chat_subscribers_tool,
)
from .yougile_mcp.tools.sticker_tools import (
    list_string_stickers_tool,
    get_string_sticker_tool,
    get_string_sticker_state_tool,
    decode_task_stickers_tool,
)
from .yougile_mcp.resources.api_docs import (
    get_api_overview,
    get_project_info,
    get_task_info,
    get_api_endpoints,
)
from .yougile_mcp.prompts.workflow_prompts import (
    setup_new_project_prompt,
    create_task_workflow_prompt,
    sprint_planning_prompt,
    daily_standup_prompt,
    project_health_check_prompt,
    user_productivity_report_prompt,
    weekly_team_report_prompt,
    task_escalation_prompt,
    onboarding_new_team_member_prompt,
    deadline_crunch_management_prompt,
    html_formatting_guide_prompt,
    api_usage_guide_prompt,
    retrospective_analysis_prompt,
)

# Create MCP server instance
mcp = FastMCP(name=settings.server_name)

# Register MCP Tools
@mcp.tool()
async def get_companies(login: str, password: str, ctx: Context) -> list:
    """Get list of companies available to user for API access."""
    return await get_companies_tool(login, password, ctx)

@mcp.tool()
async def create_api_key(login: str, password: str, company_id: str, ctx: Context) -> dict:
    """Create API key for accessing YouGile API.""" 
    return await create_api_key_tool(login, password, company_id, ctx)

@mcp.tool()
async def list_api_keys(login: str, password: str, company_id: str = None, ctx: Context = None) -> list:
    """Get list of existing API keys. Useful for managing keys (max 30 per account)."""
    return await list_api_keys_tool(login, password, company_id, ctx)

@mcp.tool()
async def delete_api_key(api_key: str, ctx: Context) -> dict:
    """Delete an API key. Useful for cleaning up old keys."""
    return await delete_api_key_tool(api_key, ctx)

@mcp.tool()
async def list_workspaces(ctx: Context = None) -> list[dict]:
    """List YouGile workspaces (companies) this server is configured for.

    Each workspace = one YouGile company API key declared via
    YOUGILE_KEY_<SLUG> in the server environment. Pass the returned `slug`
    as the `workspace` parameter to any other tool to route the call to
    that company. Use 'default' (also exposed via legacy YOUGILE_API_KEY)
    as the fallback workspace.

    Returns metadata only — no API keys or other secrets are exposed.
    """
    from .core import registry as _registry
    if ctx:
        await ctx.info(f"Listing {len(_registry.slugs())} configured workspace(s)")
    return [w.to_dict() for w in _registry.list_workspaces()]


@mcp.tool()
async def get_user_context(ctx: Context = None) -> str:
    """Get user-configured context and default settings for YouGile operations."""
    try:
        if ctx:
            await ctx.info("Retrieving user context settings...")
        
        if settings.user_context:
            if ctx:
                await ctx.info("✅ User context found")
            return settings.user_context
        else:
            if ctx:
                await ctx.info("ℹ️ No user context configured")
            return "Пользовательские настройки не заданы. Используйте стандартный подход с получением списка проектов и досок."
            
    except Exception as e:
        if ctx:
            await ctx.error(f"Error retrieving user context: {str(e)}")
        return "Ошибка получения пользовательских настроек."


# User Management Tools
@mcp.tool()
async def list_users(workspace: str = "default", ctx: Context = None) -> list:
    """Get list of all users in the company.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_users_tool(workspace, ctx)

@mcp.tool()
async def invite_user(workspace: str = "default", email: str = None, first_name: str = None, last_name: str = None, role: str = "user", departments: list = None, ctx: Context = None) -> dict:
    """Invite a new user to the company.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await invite_user_tool(workspace, email, first_name, last_name, role, departments or [], ctx)

@mcp.tool()
async def get_user(workspace: str = "default", user_id: str = None, ctx: Context = None) -> dict:
    """Get detailed information about a specific user.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_user_tool(workspace, user_id, ctx)

@mcp.tool()
async def update_user(workspace: str = "default", user_id: str = None, first_name: str = None, last_name: str = None, role: str = None, departments: list = None, ctx: Context = None) -> dict:
    """Update user information.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_user_tool(workspace, user_id, first_name, last_name, role, departments, ctx)

@mcp.tool()
async def remove_user(workspace: str = "default", user_id: str = None, ctx: Context = None) -> dict:
    """Remove user from the company.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await remove_user_tool(workspace, user_id, ctx)

# Project Management Tools
@mcp.tool()
async def list_projects(workspace: str = "default", ctx: Context = None) -> list:
    """Get list of all projects in the company.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_projects_tool(workspace, ctx)

@mcp.tool()
async def create_project(workspace: str = "default", title: str = None, users: dict = None, workflow_id: str = None, ctx: Context = None) -> dict:
    """Create a new project.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await create_project_tool(workspace, title, users, workflow_id, ctx)

@mcp.tool()
async def get_project(workspace: str = "default", project_id: str = None, ctx: Context = None) -> dict:
    """Get detailed information about a specific project.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_project_tool(workspace, project_id, ctx)

@mcp.tool()
async def update_project(workspace: str = "default", project_id: str = None, title: str = None, users: dict = None, workflow_id: str = None, ctx: Context = None) -> dict:
    """Update project information.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_project_tool(workspace, project_id, title, users, workflow_id, ctx)

# Board Management Tools
@mcp.tool()
async def list_boards(workspace: str = "default", project_id: str = None, title: str = None, limit: int = 50, offset: int = 0, include_deleted: bool = False, ctx: Context = None) -> list:
    """Get list of boards with optional filtering.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_boards_tool(workspace, project_id, title, limit, offset, include_deleted, ctx)

@mcp.tool()
async def create_board(workspace: str = "default", title: str = None, project_id: str = None, workflow_id: str = None, ctx: Context = None) -> dict:
    """Create a new board in a project.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await create_board_tool(workspace, title, project_id, workflow_id, ctx)

@mcp.tool()
async def get_board(workspace: str = "default", board_id: str = None, ctx: Context = None) -> dict:
    """Get detailed information about a specific board.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_board_tool(workspace, board_id, ctx)

@mcp.tool()
async def update_board(workspace: str = "default", board_id: str = None, title: str = None, workflow_id: str = None, ctx: Context = None) -> dict:
    """Update board information.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_board_tool(workspace, board_id, title, workflow_id, ctx)

# Column Management Tools
@mcp.tool()
async def list_columns(workspace: str = "default", board_id: str = None, ctx: Context = None) -> list:
    """Get list of columns with optional filtering by board.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_columns_tool(workspace, board_id, ctx)

@mcp.tool()
async def create_column(workspace: str = "default", title: str = None, board_id: str = None, color: int = None, ctx: Context = None) -> dict:
    """Create a new column in a board. Color must be between 1-16.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await create_column_tool(workspace, title, board_id, color, ctx)

@mcp.tool()
async def get_column(workspace: str = "default", column_id: str = None, ctx: Context = None) -> dict:
    """Get detailed information about a specific column.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_column_tool(workspace, column_id, ctx)

@mcp.tool()
async def update_column(workspace: str = "default", column_id: str = None, title: str = None, color: int = None, ctx: Context = None) -> dict:
    """Update column information. Color must be between 1-16.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_column_tool(workspace, column_id, title, color, ctx)

# Task Management Tools
@mcp.tool()
async def list_task_summaries(workspace: str = "default", limit: int = 50, offset: int = 0, ctx: Context = None) -> list:
    """Get list of task summaries with pagination.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_task_summaries_tool(workspace, limit, offset, ctx)

@mcp.tool()
async def list_tasks(workspace: str = "default", column_id: str = None, assigned_to: str = None, title: str = None, limit: int = 50, offset: int = 0, include_deleted: bool = False, ctx: Context = None) -> list:
    """Get detailed list of tasks with optional filtering.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_tasks_tool(workspace, column_id, assigned_to, title, limit, offset, include_deleted, ctx)

@mcp.tool()
async def create_task(workspace: str = "default", title: str = None, column_id: str = None, description: str = None, assigned_users: list = None, deadline: dict = None, time_tracking: dict = None, stickers: dict = None, subtasks: list = None, checklists: list = None, completed: bool = None, archived: bool = None, ctx: Context = None) -> dict:
    """Create a new task.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.

    🚨 CRITICAL: description parameter MUST be in HTML format!
    - Use <br> for line breaks (NOT \\n)
    - Use <b>text</b> for bold, <i>text</i> for italic
    - Example: "Fix bug<br><br><b>Steps:</b><br>1. Check login<br>2. Fix error"
    - Plain text will display incorrectly in YouGile interface!

    📋 Checklists format:
    - Structure: [{"title": "Checklist Name", "items": [{"title": "Item 1", "isCompleted": false}]}]
    - Multiple checklists: [{"title": "Backend", "items": [...]}, {"title": "Frontend", "items": [...]}]
    - Each item MUST have "isCompleted" field (boolean)
    """
    return await create_task_tool(workspace, title, column_id, description, assigned_users, deadline, time_tracking, stickers, subtasks, checklists, completed, archived, ctx)

@mcp.tool()
async def get_task(workspace: str = "default", task_id: str = None, ctx: Context = None) -> dict:
    """Get detailed information about a specific task.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_task_tool(workspace, task_id, ctx)

@mcp.tool()
async def get_tasks_by_date(workspace: str = "default", assigned_to: str = None, created_by: str = None, target_date: str = None, completed_only: bool = False, limit: int = 5000, ctx: Context = None) -> list:
    """Get tasks filtered by date and completion status.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.

    Examples:
    - get_tasks_by_date(assigned_to="user-id") - all tasks assigned to user for today
    - get_tasks_by_date(created_by="user-id") - all tasks created by user for today
    - get_tasks_by_date(target_date="2024-01-15", completed_only=True) - completed tasks for specific date
    - get_tasks_by_date(assigned_to="user-id", completed_only=True) - completed tasks by user for today
    - get_tasks_by_date(created_by="user-id", target_date="2024-01-15") - tasks created by user on specific date
    """
    return await get_tasks_by_date_tool(workspace, assigned_to, created_by, target_date, completed_only, limit, ctx)

@mcp.tool()
async def update_task(workspace: str = "default", task_id: str = None, title: str = None, description: str = None, column_id: str = None, assigned_users: list = None, deadline: dict = None, time_tracking: dict = None, stickers: dict = None, subtasks: list = None, checklists: list = None, completed: bool = None, archived: bool = None, deleted: bool = None, ctx: Context = None) -> dict:
    """Update task information.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.

    🚨 CRITICAL: description parameter MUST be in HTML format!
    - Use <br> for line breaks (NOT \\n)
    - Use <b>text</b> for bold, <i>text</i> for italic
    - Example: "Updated requirements<br><br><b>Changes:</b><br>• Added validation<br>• Fixed bugs"
    - Plain text will display incorrectly in YouGile interface!

    📋 Checklists format:
    - Structure: [{"title": "Checklist Name", "items": [{"title": "Item 1", "isCompleted": false}]}]
    - Multiple checklists: [{"title": "Backend", "items": [...]}, {"title": "Frontend", "items": [...]}]
    - Each item MUST have "isCompleted" field (boolean)
    """
    return await update_task_tool(workspace, task_id, title, description, column_id, assigned_users, deadline, time_tracking, stickers, subtasks, checklists, completed, archived, deleted, ctx)

@mcp.tool()
async def delete_task(workspace: str = "default", task_id: str = None, ctx: Context = None) -> dict:
    """Delete a task (soft delete).

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_task_tool(workspace, task_id, deleted=True, ctx=ctx)

@mcp.tool()
async def set_task_deadline(workspace: str = "default", task_id: str = None, deadline_timestamp: int = None, start_date_timestamp: int = None, with_time: bool = True, ctx: Context = None) -> dict:
    """Set task deadline sticker.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.

    Args:
        task_id: ID of the task to set deadline for
        deadline_timestamp: Deadline timestamp in MILLISECONDS (13 digits, e.g. 1653029146646)
        start_date_timestamp: Optional start date timestamp in MILLISECONDS
        with_time: Whether to display time on the sticker, or only date
    """
    # Auto-convert seconds to milliseconds if needed
    if deadline_timestamp < 10000000000:  # Less than 10 digits = seconds
        deadline_timestamp *= 1000
        if ctx:
            await ctx.info(f"Auto-converted deadline timestamp to milliseconds: {deadline_timestamp}")

    deadline_data = {
        "deadline": deadline_timestamp,
        "withTime": with_time,
        "blockedPoints": [],  # Required field
        "links": []  # Required field
    }

    if start_date_timestamp:
        # Auto-convert start date if needed
        if start_date_timestamp < 10000000000:
            start_date_timestamp *= 1000
            if ctx:
                await ctx.info(f"Auto-converted start date timestamp to milliseconds: {start_date_timestamp}")
        deadline_data["startDate"] = start_date_timestamp

    return await update_task_tool(workspace, task_id, deadline=deadline_data, ctx=ctx)

@mcp.tool()
async def set_task_time_tracking(workspace: str = "default", task_id: str = None, planned_hours: int = None, actual_hours: int = None, ctx: Context = None) -> dict:
    """Set task time tracking sticker.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    time_tracking_data = {}
    if planned_hours is not None:
        time_tracking_data["plan"] = planned_hours
    if actual_hours is not None:
        time_tracking_data["work"] = actual_hours
    return await update_task_tool(workspace, task_id, time_tracking=time_tracking_data, ctx=ctx)

@mcp.tool()
async def set_task_custom_stickers(workspace: str = "default", task_id: str = None, sticker_values: dict = None, ctx: Context = None) -> dict:
    """Set custom stickers on task (sticker_id -> state_id mapping).

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_task_tool(workspace, task_id, stickers=sticker_values, ctx=ctx)

@mcp.tool()
async def remove_task_sticker(workspace: str = "default", task_id: str = None, sticker_type: str = None, ctx: Context = None) -> dict:
    """Remove sticker from task by setting it to deleted/removed state.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    if sticker_type == "deadline":
        return await update_task_tool(workspace, task_id, deadline={"deleted": True}, ctx=ctx)
    elif sticker_type == "timeTracking":
        return await update_task_tool(workspace, task_id, time_tracking={"deleted": True}, ctx=ctx)
    else:
        # For custom stickers, use "-" to detach
        sticker_data = {sticker_type: "-"}
        return await update_task_tool(workspace, task_id, stickers=sticker_data, ctx=ctx)

@mcp.tool()
async def get_task_chat_subscribers(workspace: str = "default", task_id: str = None, ctx: Context = None) -> list:
    """Get list of users subscribed to task chat.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_task_chat_subscribers_tool(workspace, task_id, ctx)

@mcp.tool()
async def update_task_chat_subscribers(workspace: str = "default", task_id: str = None, subscribers: list = None, ctx: Context = None) -> dict:
    """Update task chat subscribers list.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_task_chat_subscribers_tool(workspace, task_id, subscribers, ctx)

# String Stickers Management Tools
@mcp.tool()
async def list_string_stickers(workspace: str = "default", limit: int = 50, offset: int = 0, include_deleted: bool = False, ctx: Context = None) -> list:
    """Get list of custom string stickers available in the company.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_string_stickers_tool(workspace, limit, offset, include_deleted, ctx)

@mcp.tool()
async def get_string_sticker(workspace: str = "default", sticker_id: str = None, ctx: Context = None) -> dict:
    """Get detailed information about a specific string sticker including its states.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_string_sticker_tool(workspace, sticker_id, ctx)

@mcp.tool()
async def get_string_sticker_state(workspace: str = "default", sticker_id: str = None, state_id: str = None, ctx: Context = None) -> dict:
    """Get information about a specific state of a string sticker.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_string_sticker_state_tool(workspace, sticker_id, state_id, ctx)

@mcp.tool()
async def decode_task_stickers(workspace: str = "default", stickers_dict: dict = None, ctx: Context = None) -> dict:
    """Decode task stickers dictionary into readable sticker and state information.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.

    Takes a dictionary of sticker_id -> state_id (like from task.stickers) and returns
    readable names, colors, and icons for each sticker and its current state.
    """
    return await decode_task_stickers_tool(workspace, stickers_dict, ctx)

# Chat and Communication Tools
@mcp.tool()
async def list_group_chats(workspace: str = "default", ctx: Context = None) -> list:
    """Get list of all group chats.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await list_group_chats_tool(workspace, ctx)

@mcp.tool()
async def create_group_chat(workspace: str = "default", title: str = None, participants: list = None, ctx: Context = None) -> dict:
    """Create a new group chat.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await create_group_chat_tool(workspace, title, participants, ctx)

@mcp.tool()
async def get_group_chat(workspace: str = "default", chat_id: str = None, ctx: Context = None) -> dict:
    """Get detailed information about a specific group chat.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_group_chat_tool(workspace, chat_id, ctx)

@mcp.tool()
async def get_chat_messages(workspace: str = "default", chat_id: str = None, limit: int = 50, ctx: Context = None) -> list:
    """Get messages from a chat (task comments or group chat messages).

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_chat_messages_tool(workspace, chat_id, limit, ctx)

@mcp.tool()
async def send_chat_message(workspace: str = "default", chat_id: str = None, message: str = None, ctx: Context = None) -> dict:
    """Send a message to a chat (add comment to task or send group chat message).

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await send_chat_message_tool(workspace, chat_id, message, ctx)

@mcp.tool()
async def get_chat_message(workspace: str = "default", chat_id: str = None, message_id: str = None, ctx: Context = None) -> dict:
    """Get a specific message from a chat.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_chat_message_tool(workspace, chat_id, message_id, ctx)

@mcp.tool()
async def update_chat_message(workspace: str = "default", chat_id: str = None, message_id: str = None, message: str = None, ctx: Context = None) -> dict:
    """Update/edit a message in a chat.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await update_chat_message_tool(workspace, chat_id, message_id, message, ctx)

# Task Comment Tools (convenient aliases)
@mcp.tool()
async def get_task_comments(workspace: str = "default", task_id: str = None, limit: int = 50, ctx: Context = None) -> list:
    """Get comments for a specific task.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.
    """
    return await get_task_comments_tool(workspace, task_id, limit, ctx)

@mcp.tool()
async def add_task_comment(workspace: str = "default", task_id: str = None, comment: str = None, ctx: Context = None) -> dict:
    """Add a comment to a specific task.

    workspace: YouGile workspace slug (see list_workspaces). Defaults to 'default'.

    🚨 CRITICAL: comment parameter MUST be in HTML format!
    - Use <br> for line breaks (NOT \\n)
    - Use <b>text</b> for bold, <i>text</i> for italic
    - Example: "Status update<br><br><b>Progress:</b><br>• Completed testing<br>• Ready for review"
    - Plain text will display incorrectly in YouGile interface!
    """
    return await add_task_comment_tool(workspace, task_id, comment, ctx)

# Register MCP Resources
@mcp.resource("yougile://api/overview")
def api_overview() -> str:
    """YouGile API v2.0 comprehensive overview and getting started guide."""
    return get_api_overview()

@mcp.resource("yougile://api/endpoints")
def api_endpoints() -> str:
    """Complete list of all 65 YouGile API endpoints organized by category."""
    return get_api_endpoints()

@mcp.resource("yougile://projects/{project_id}")
def project_info(project_id: str) -> str:
    """Detailed information about a specific project including schema and examples."""
    return get_project_info(project_id)

@mcp.resource("yougile://tasks/{task_id}")
def task_info(task_id: str) -> str:
    """Detailed information about a specific task including schema and operations."""
    return get_task_info(task_id)


# Register MCP Prompts
@mcp.prompt(title="Setup New Project")
def setup_project(project_name: str, project_type: str = "kanban"):
    """Step-by-step guide for creating and configuring a new project in YouGile."""
    return setup_new_project_prompt(project_name, project_type)

@mcp.prompt(title="Create Task")
def create_task_prompt(task_title: str, priority: str = "medium") -> str:
    """Template for creating well-structured tasks with all necessary details."""
    return create_task_workflow_prompt(task_title, priority)

@mcp.prompt(title="Sprint Planning")
def plan_sprint(sprint_name: str, duration_weeks: int = 2):
    """Complete sprint planning workflow with backlog refinement and capacity planning."""
    return sprint_planning_prompt(sprint_name, duration_weeks)

@mcp.prompt(title="Daily Standup Report")
def daily_standup(team_user_ids: str = "team-user-ids-here"):
    """Generate daily standup report for team meetings."""
    user_list = team_user_ids.split(",") if team_user_ids != "team-user-ids-here" else None
    return daily_standup_prompt(user_list)

@mcp.prompt(title="Project Health Check")
def project_health_check(project_id: str):
    """Comprehensive project health analysis with task flow, team performance, and timeline metrics."""
    return project_health_check_prompt(project_id)

@mcp.prompt(title="User Productivity Report")
def user_productivity_report(user_id: str, target_date: str = None):
    """Individual user productivity analysis with task completion, creation, and collaboration metrics."""
    return user_productivity_report_prompt(user_id, target_date)

@mcp.prompt(title="Weekly Team Report")
def weekly_team_report(team_user_ids: str, start_date: str):
    """Weekly team performance report with productivity trends and collaboration metrics."""
    user_list = team_user_ids.split(",")
    return weekly_team_report_prompt(user_list, start_date)

@mcp.prompt(title="Task Escalation")
def task_escalation(task_id: str):
    """Task escalation workflow when something is blocked or needs urgent attention."""
    return task_escalation_prompt(task_id)

@mcp.prompt(title="Onboard Team Member")
def onboard_team_member(new_member_name: str, role: str):
    """Team member onboarding workflow with project access and task assignment."""
    return onboarding_new_team_member_prompt(new_member_name, role)

@mcp.prompt(title="Deadline Crunch Management")
def deadline_crunch_management(deadline_date: str):
    """Managing tasks when approaching critical deadlines with priority triage and resource allocation."""
    return deadline_crunch_management_prompt(deadline_date)

@mcp.prompt(title="Sprint Retrospective")
def sprint_retrospective(sprint_end_date: str, team_user_ids: str):
    """Sprint/project retrospective analysis with performance patterns and improvement insights."""
    user_list = team_user_ids.split(",")
    return retrospective_analysis_prompt(sprint_end_date, user_list)

@mcp.prompt(title="HTML Formatting Guide")
def html_formatting_guide():
    """Essential guide for HTML formatting in YouGile tasks and comments - CRITICAL for proper display."""
    return html_formatting_guide_prompt()

@mcp.prompt(title="API Usage Guide") 
def api_usage_guide():
    """Quick reference for using YouGile MCP tools with correct parameters and formats."""
    return api_usage_guide_prompt()


async def initialize_auth():
    """Initialize authentication automatically from environment variables."""
    if not all([settings.yougile_email, settings.yougile_password, settings.yougile_company_id]):
        return False
    
    try:
        # First try API key from environment (MCP config)
        api_key_to_test = settings.yougile_api_key
        
        # If no API key in environment, try loading from credentials file
        if not api_key_to_test:
            api_key_to_test = load_api_key_from_credentials()
        
        # Test existing API key if we have one
        if api_key_to_test:
            try:
                # Test existing key
                auth.auth_manager.set_credentials(api_key_to_test, settings.yougile_company_id)
                async with YouGileClient(auth.auth_manager) as client:
                    # Test key with a simple API call (get users)
                    await client.get("/users")
                
                return True
                
            except Exception:
                pass
        
        # Create new API key
        temp_auth = auth.auth_manager.__class__()
        async with YouGileClient(temp_auth) as client:
            api_key = await auth_api.create_api_key(
                client, 
                settings.yougile_email, 
                settings.yougile_password, 
                settings.yougile_company_id
            )
            
            # Save to global auth manager
            auth.auth_manager.set_credentials(api_key, settings.yougile_company_id)
            
            # Save API key to credentials file for future use
            await save_api_key_to_credentials(api_key)
            
        return True
        
    except Exception:
        return False

async def save_api_key_to_credentials(api_key: str):
    """Save API key to credentials file for future reuse."""
    import json
    import os
    import tempfile
    from pathlib import Path
    
    # Save to temp directory to avoid read-only filesystem issues
    temp_dir = Path(tempfile.gettempdir())
    credentials_file = temp_dir / "yougile_credentials.json"
    
    try:
        # Load existing credentials or create new
        credentials = {}
        if credentials_file.exists():
            with open(credentials_file, 'r') as f:
                credentials = json.load(f)
        
        # Update API key for current company  
        import time
        credentials[settings.yougile_company_id] = {
            "api_key": api_key,
            "created_at": str(int(time.time()))
        }
        
        # Save to credentials file
        with open(credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        # Set file permissions to be readable only by owner (Unix-like systems)
        try:
            os.chmod(credentials_file, 0o600)
        except (OSError, AttributeError):
            pass  # Windows or other systems that don't support chmod
        
    except Exception:
        pass


def load_api_key_from_credentials() -> str:
    """Load API key from credentials file."""
    import json
    import tempfile
    from pathlib import Path
    
    # Load from temp directory
    temp_dir = Path(tempfile.gettempdir())
    credentials_file = temp_dir / "yougile_credentials.json"
    
    if not credentials_file.exists():
        return None
    
    try:
        with open(credentials_file, 'r') as f:
            credentials = json.load(f)
        
        company_data = credentials.get(settings.yougile_company_id, {})
        api_key = company_data.get("api_key")
        return api_key
        
    except Exception:
        return None

def run_legacy_init() -> None:
    """Run single-tenant auto-auth if YOUGILE_EMAIL/PASSWORD/COMPANY_ID are set.

    Multi-tenant workspaces from YOUGILE_KEY_<SLUG> env vars are loaded eagerly
    at import time by core.registry; nothing to do for them here.
    """
    if settings.yougile_email and settings.yougile_password and settings.yougile_company_id:
        asyncio.run(initialize_auth())


def main() -> None:
    """Backwards-compatible entry point — stdio transport.

    Prefer running via `python run_server.py [--http]`, which handles the
    transport selection consistently.
    """
    run_legacy_init()
    mcp.run()


if __name__ == "__main__":
    main()