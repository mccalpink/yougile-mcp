"""
YouGile Tasks MCP tools.
Task operations and lifecycle management (7 endpoints).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from mcp.server.fastmcp import Context
from ...core import models
from ...core.models import TaskColor
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import tasks
from ...utils.validation import validate_uuid, validate_non_empty_string, normalize_deadline


async def list_task_summaries_tool(
    limit: int = 50,
    offset: int = 0,
    sticker_id: Optional[str] = None,
    sticker_state_id: Optional[str] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """Get list of task summaries with pagination.

    Args:
        limit: Maximum number of tasks to return (default: 50)
        offset: Number of tasks to skip (default: 0)
        sticker_id: Server-side filter — only return tasks carrying this sticker.
        sticker_state_id: Server-side filter — only return tasks whose sticker
            value matches this state ID (typically combined with sticker_id).
    """
    try:
        if ctx:
            await ctx.info(f"Fetching task list from YouGile (limit: {limit}, offset: {offset})...")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await tasks.get_task_list(
                client,
                limit=limit,
                offset=offset,
                sticker_id=sticker_id,
                sticker_state_id=sticker_state_id,
            )

        if ctx:
            await ctx.info(f"✅ Successfully retrieved {len(result)} task summaries")
        return result
        
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while fetching task list: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def list_tasks_tool(
    column_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    title: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False,
    sticker_id: Optional[str] = None,
    sticker_state_id: Optional[str] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """Get detailed list of tasks with optional filtering.

    Args:
        column_id: Filter tasks by column ID
        assigned_to: Filter tasks by assigned user ID
        title: Filter tasks by title (partial match)
        limit: Maximum number of tasks to return (default: 50)
        offset: Number of tasks to skip (default: 0)
        include_deleted: Include deleted tasks (default: False)
        sticker_id: Server-side filter — only return tasks carrying this sticker.
        sticker_state_id: Server-side filter — only return tasks whose sticker
            value matches this state ID (typically combined with sticker_id).
    """
    try:
        if ctx:
            await ctx.info(f"Fetching detailed tasks from YouGile (limit: {limit}, offset: {offset})...")

        if column_id:
            column_id = validate_uuid(column_id, "column_id")
            if ctx:
                await ctx.info(f"Filtering by column: {column_id}")

        if assigned_to:
            assigned_to = validate_uuid(assigned_to, "assigned_to")
            if ctx:
                await ctx.info(f"Filtering by assignee: {assigned_to}")

        if title:
            if ctx:
                await ctx.info(f"Filtering by title: {title}")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await tasks.get_tasks(
                client,
                column_id=column_id,
                assigned_to=assigned_to,
                title=title,
                limit=limit,
                offset=offset,
                include_deleted=include_deleted,
                sticker_id=sticker_id,
                sticker_state_id=sticker_state_id,
            )

        if ctx:
            await ctx.info(f"✅ Successfully retrieved {len(result)} detailed tasks")
        return result
        
    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while fetching tasks: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def create_task_tool(
    title: str,
    column_id: Optional[str] = None,
    description: str = None,
    assigned_users: List[str] = None,
    deadline: Dict[str, Any] = None,
    time_tracking: Dict[str, Any] = None,
    stickers: Dict[str, str] = None,
    subtasks: List[str] = None,
    checklists: List[Dict[str, Any]] = None,
    completed: bool = None,
    archived: bool = None,
    color: Optional[TaskColor] = None,
    stopwatch: Optional[Dict[str, Any]] = None,
    timer: Optional[Dict[str, Any]] = None,
    deal: Optional[Dict[str, Any]] = None,
    id_task_common: Optional[str] = None,
    id_task_project: Optional[str] = None,
    extension_data: Optional[Dict[str, Any]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Create a new task. Returns the task ID. Description requires HTML format.

    Args:
        title: Task title (required)
        column_id: ID of the column to place task in (OPTIONAL — API allows tasks
                   without a column, e.g. for use as standalone subtasks)
        description: Task description in HTML format (use <br> for line breaks, <b>bold</b>, <i>italic</i>, etc)
        assigned_users: List of user IDs to assign task to
        deadline: Deadline sticker data (dict with deadline, startDate, withTime fields)
        time_tracking: Time tracking sticker data (dict with plan, work fields)
        stickers: Custom stickers (dict of sticker_id -> state_id)
        subtasks: List of subtask IDs (UUIDs of child tasks, not nested objects)
        checklists: List of checklist groups (dict with title and items: [{"title": "Item", "isCompleted": false}])
        completed: Create task as already completed (True) or active (False)
        archived: Create task as archived (True) or active (False)
        color: Task card color on the board. One of: task-primary, task-gray,
               task-red, task-pink, task-yellow, task-green, task-turquoise,
               task-blue, task-violet
        stopwatch: Stopwatch sticker data (dict with running, seconds fields)
        timer: Timer sticker data (dict with running, seconds fields)
        deal: CRM deal data (DealDataDto) — if provided, task becomes a CRM deal
        id_task_common: Cross-company human-readable task ID (API field: idTaskCommon)
        id_task_project: Per-project human-readable task ID (API field: idTaskProject)
        extension_data: Arbitrary data used by YouGile extensions (API field: extensionData)
    """
    try:
        if ctx:
            await ctx.info(f"Creating task: {title}")

        # Validate inputs
        title = validate_non_empty_string(title, "title")

        task_data = {
            "title": title,
        }

        if column_id is not None:
            column_id = validate_uuid(column_id, "column_id")
            task_data["columnId"] = column_id

        if description is not None:
            # Description accepts HTML format - no validation needed for content
            task_data["description"] = description

        if assigned_users is not None:
            assigned_users = [validate_uuid(user_id, "user_id") for user_id in assigned_users]
            task_data["assigned"] = assigned_users

        if deadline is not None:
            # Auto-fill required blockedPoints/links arrays so callers don't
            # have to remember the DTO contract. See normalize_deadline().
            task_data["deadline"] = normalize_deadline(deadline, for_update=False)

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

        async with YouGileClient(registry.get(workspace)) as client:
            result = await tasks.create_task(client, task_data)

        if ctx:
            await ctx.info(f"✅ Successfully created task with ID: {result.get('id')}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while creating task: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_task_tool(task_id: str, workspace: str = "default", ctx: Context = None) -> Dict[str, Any]:
    """Get detailed information about a specific task."""
    try:
        if ctx:
            await ctx.info(f"Fetching task details: {task_id}")

        task_id = validate_uuid(task_id, "task_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await tasks.get_task(client, task_id)
            
        if ctx:
            await ctx.info(f"✅ Successfully retrieved task: {result.get('title', task_id)}")
        return result
        
    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while fetching task: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_tasks_by_date_tool(
    assigned_to: Optional[str] = None,
    created_by: Optional[str] = None,
    target_date: Optional[str] = None,
    completed_only: bool = False,
    limit: int = 5000,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """Get tasks filtered by date and completion status.
    
    Args:
        assigned_to: Filter tasks by assigned user ID (API filter)
        created_by: Filter tasks by creator user ID (client-side filter)
        target_date: Date in YYYY-MM-DD format (default: today)
        completed_only: Only return completed tasks
        limit: Maximum number of tasks to fetch and filter (max 5000)
    """
    try:
        if ctx:
            await ctx.info(f"Fetching tasks with date filtering...")
        
        # Parse target date
        if target_date:
            try:
                filter_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("target_date must be in YYYY-MM-DD format", field="target_date")
        else:
            filter_date = date.today()
        
        if ctx:
            await ctx.info(f"Filtering tasks for date: {filter_date}")
        
        # Validate user IDs if provided
        if assigned_to:
            assigned_to = validate_uuid(assigned_to, "assigned_to")
        if created_by:
            created_by = validate_uuid(created_by, "created_by")
        
        # Get tasks from API with pagination to handle large datasets
        all_tasks = []
        offset = 0
        batch_size = 1000  # API max per request
        
        # If filtering by created_by, we need to get more tasks since API doesn't support this filter
        fetch_limit = limit if assigned_to else 5000  # Get more tasks if filtering by created_by
        
        async with YouGileClient(registry.get(workspace)) as client:
            while len(all_tasks) < fetch_limit:
                current_limit = min(batch_size, fetch_limit - len(all_tasks))
                
                batch = await tasks.get_tasks(
                    client,
                    assigned_to=assigned_to,
                    limit=current_limit,
                    offset=offset,
                    include_deleted=False
                )
                
                if not batch:  # No more tasks
                    break
                    
                all_tasks.extend(batch)
                
                if len(batch) < current_limit:  # Got fewer than requested - no more data
                    break
                    
                offset += len(batch)
        
        if ctx:
            await ctx.info(f"Retrieved {len(all_tasks)} tasks total, filtering by criteria...")
            if created_by:
                await ctx.debug(f"Looking for tasks created by: {created_by}")
            if target_date:
                await ctx.debug(f"Looking for tasks on date: {filter_date}")
        
        # Check if tasks are sorted by date (newest first or oldest first)
        if len(all_tasks) > 1:
            first_timestamp = all_tasks[0].get('timestamp', 0)
            last_timestamp = all_tasks[-1].get('timestamp', 0)
            
            if isinstance(first_timestamp, str):
                first_timestamp = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00')).timestamp()
            if isinstance(last_timestamp, str):
                last_timestamp = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00')).timestamp()
                
            if first_timestamp > last_timestamp:
                sort_order = "newest first"
            elif first_timestamp < last_timestamp:
                sort_order = "oldest first"
            else:
                sort_order = "mixed/same"
                
            if ctx:
                await ctx.debug(f"Tasks appear to be sorted: {sort_order}")
        
        filtered_tasks = []
        
        for task in all_tasks:
            # Filter by completion status if requested
            if completed_only and not task.get('completed', False):
                continue
                
            # Filter by creator if requested
            if created_by and task.get('createdBy') != created_by:
                if ctx:
                    await ctx.debug(f"Task {task.get('id', 'unknown')} created by {task.get('createdBy', 'unknown')}, not {created_by}")
                continue
            
            # Filter by date using timestamp
            timestamp = task.get('timestamp')
            if timestamp:
                try:
                    # Convert timestamp to date
                    if isinstance(timestamp, str):
                        task_datetime = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        # Handle both seconds and milliseconds timestamps
                        if timestamp > 1e12:  # Likely milliseconds
                            task_datetime = datetime.fromtimestamp(timestamp / 1000)
                        else:  # Likely seconds
                            task_datetime = datetime.fromtimestamp(timestamp)
                    
                    task_date = task_datetime.date()
                    
                    # Check if task matches target date
                    if task_date == filter_date:
                        if ctx:
                            await ctx.debug(f"✅ Task {task.get('id', 'unknown')} matches date {filter_date}")
                        filtered_tasks.append(task)
                    else:
                        if ctx:
                            await ctx.debug(f"❌ Task {task.get('id', 'unknown')} date {task_date} != {filter_date}")
                        
                except (ValueError, TypeError) as e:
                    if ctx:
                        await ctx.debug(f"Could not parse timestamp for task {task.get('id', 'unknown')}: {e}")
                    continue
        
        # Limit results to requested limit
        final_results = filtered_tasks[:limit]
        
        if ctx:
            await ctx.info(f"✅ Found {len(filtered_tasks)} tasks matching criteria for {filter_date}, returning {len(final_results)}")
        
        return final_results
        
    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while fetching tasks: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise