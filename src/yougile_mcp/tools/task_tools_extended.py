"""
YouGile Tasks MCP tools - Extended operations.
Additional task operations (update, chat subscribers).
"""

from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import Context
from ...core import models
from ...core.models import TaskColor
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import tasks
from ...utils.validation import validate_uuid, validate_non_empty_string


async def update_task_tool(
    workspace: str,
    task_id: str,
    title: str = None,
    description: str = None,
    column_id: str = None,
    assigned_users: List[str] = None,
    deadline: Dict[str, Any] = None,
    time_tracking: Dict[str, Any] = None,
    stickers: Dict[str, str] = None,
    subtasks: List[str] = None,
    checklists: List[Dict[str, Any]] = None,
    completed: bool = None,
    archived: bool = None,
    deleted: bool = None,
    color: Optional[TaskColor] = None,
    stopwatch: Optional[Dict[str, Any]] = None,
    timer: Optional[Dict[str, Any]] = None,
    deal: Optional[Dict[str, Any]] = None,
    id_task_common: Optional[str] = None,
    id_task_project: Optional[str] = None,
    extension_data: Optional[Dict[str, Any]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Update task information. Description requires HTML format.

    Args:
        task_id: ID of the task to update
        title: New task title
        description: Task description in HTML format (use <br> for line breaks, <b>bold</b>, <i>italic</i>, etc)
        column_id: Move task to different column. Pass "-" to remove task from any column.
        assigned_users: List of user IDs to assign task to (REPLACE — not append)
        deadline: Deadline sticker data (dict with deadline, startDate, withTime, deleted fields)
        time_tracking: Time tracking sticker data (dict with plan, work, deleted fields)
        stickers: Custom stickers (dict of sticker_id -> state_id; "-" to detach, "empty" for empty)
        subtasks: List of subtask IDs (UUIDs of child tasks) — REPLACE
        checklists: List of checklist groups (dict with title and items)
        completed: Mark task as completed (True) or not completed (False)
        archived: Archive task (True) or unarchive (False)
        deleted: Soft-delete task (True) or restore (False)
        color: Task card color on the board. One of: task-primary, task-gray,
               task-red, task-pink, task-yellow, task-green, task-turquoise,
               task-blue, task-violet
        stopwatch: Stopwatch sticker data (dict with running, deleted fields)
        timer: Timer sticker data (dict with running, seconds, deleted fields)
        deal: CRM deal data (DealDataDto) — for tasks in CRM projects
        id_task_common: Cross-company human-readable task ID (API field: idTaskCommon)
        id_task_project: Per-project human-readable task ID (API field: idTaskProject)
        extension_data: Arbitrary data used by YouGile extensions (API field: extensionData)
    """
    try:
        if ctx:
            await ctx.info(f"Updating task: {task_id}")

        task_id = validate_uuid(task_id, "task_id")

        # Build update data with only provided fields
        task_data = {}

        if title is not None:
            title = validate_non_empty_string(title, "title")
            task_data["title"] = title

        if description is not None:
            # Description accepts HTML format - no validation needed for content
            task_data["description"] = description

        if column_id is not None:
            # API accepts "-" as a sentinel to detach the task from any column.
            if column_id != "-":
                column_id = validate_uuid(column_id, "column_id")
            task_data["columnId"] = column_id

        if assigned_users is not None:
            assigned_users = [validate_uuid(user_id, "user_id") for user_id in assigned_users]
            task_data["assigned"] = assigned_users

        if deadline is not None:
            task_data["deadline"] = deadline

        if time_tracking is not None:
            task_data["timeTracking"] = time_tracking

        if stickers is not None:
            task_data["stickers"] = stickers

        if subtasks is not None:
            subtasks = [validate_uuid(subtask_id, "subtask_id") for subtask_id in subtasks]
            task_data["subtasks"] = subtasks

        if checklists is not None:
            # Validate checklist structure
            for checklist in checklists:
                if not isinstance(checklist, dict) or "title" not in checklist or "items" not in checklist:
                    raise ValidationError("Each checklist must have 'title' and 'items' fields")
                validate_non_empty_string(checklist["title"], "checklist title")
                if not isinstance(checklist["items"], list):
                    raise ValidationError("Checklist 'items' must be a list")
                for item in checklist["items"]:
                    if not isinstance(item, dict) or "title" not in item:
                        raise ValidationError("Each checklist item must have a 'title' field")
                    validate_non_empty_string(item["title"], "checklist item title")
                    # Ensure isCompleted field exists and is boolean
                    if "isCompleted" not in item:
                        item["isCompleted"] = False
                    elif not isinstance(item["isCompleted"], bool):
                        raise ValidationError("Checklist item 'isCompleted' must be a boolean")
            task_data["checklists"] = checklists

        if completed is not None:
            task_data["completed"] = completed

        if archived is not None:
            task_data["archived"] = archived

        if deleted is not None:
            task_data["deleted"] = deleted

        if color is not None:
            # Defensive Literal check (FastMCP also enforces via JSON schema)
            valid_colors = (
                "task-primary", "task-gray", "task-red", "task-pink",
                "task-yellow", "task-green", "task-turquoise",
                "task-blue", "task-violet",
            )
            if color not in valid_colors:
                raise ValidationError(
                    f"color must be one of {valid_colors}, got: {color!r}",
                    field="color",
                )
            task_data["color"] = color

        if stopwatch is not None:
            task_data["stopwatch"] = stopwatch

        if timer is not None:
            task_data["timer"] = timer

        if deal is not None:
            task_data["deal"] = deal

        if id_task_common is not None:
            task_data["idTaskCommon"] = id_task_common

        if id_task_project is not None:
            task_data["idTaskProject"] = id_task_project

        if extension_data is not None:
            task_data["extensionData"] = extension_data

        if not task_data:
            raise ValidationError("At least one field must be provided for update")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await tasks.update_task(client, task_id, task_data)

        if ctx:
            await ctx.info(f"✅ Successfully updated task with ID: {result.get('id')}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while updating task: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_task_chat_subscribers_tool(workspace: str, task_id: str, ctx: Context) -> List[models.User]:
    """Get list of users subscribed to task chat."""
    try:
        await ctx.info(f"Fetching chat subscribers for task: {task_id}")

        task_id = validate_uuid(task_id, "task_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await tasks.get_task_chat_subscribers(client, task_id)
            
        subscribers = [models.User(**user) for user in result]
        
        await ctx.info(f"✅ Successfully retrieved {len(subscribers)} chat subscribers")
        return subscribers
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while fetching chat subscribers: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def update_task_chat_subscribers_tool(
    workspace: str,
    task_id: str,
    subscribers: List[str],
    ctx: Context
) -> Dict[str, Any]:
    """Update task chat subscribers list."""
    try:
        await ctx.info(f"Updating chat subscribers for task: {task_id}")

        task_id = validate_uuid(task_id, "task_id")
        subscribers = [validate_uuid(user_id, "user_id") for user_id in subscribers]

        async with YouGileClient(registry.get(workspace)) as client:
            result = await tasks.update_task_chat_subscribers(client, task_id, subscribers)
            
        await ctx.info(f"✅ Successfully updated {len(subscribers)} chat subscribers")
        return {
            "success": True, 
            "message": "Chat subscribers updated successfully",
            "task_id": task_id,
            "subscriber_count": len(subscribers)
        }
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while updating chat subscribers: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise