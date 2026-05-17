"""
YouGile Projects MCP tools.
Project management and operations (4 endpoints).
"""

from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import Context
from ...core import models
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import projects
from ...utils.validation import validate_uuid, validate_non_empty_string
from ...utils.verbosity import apply_verbosity, Verbosity


async def list_projects_tool(
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """Get list of all projects in the company.

    Args:
        verbosity: 'compact' (default) strips users-role map and timestamp;
                   'full' returns raw API payload.
    """
    try:
        await ctx.info("Fetching projects from YouGile...")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await projects.get_projects(client)

        await ctx.info(f"Successfully retrieved {len(result)} projects")
        return apply_verbosity(result, dto_type="project", verbosity=verbosity, include=include, is_list=True)

    except YouGileError as e:
        await ctx.error(f"API error while fetching projects: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def create_project_tool(
    title: str,
    users: Dict[str, str] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> models.CreatedEntity:
    """Create a new project.

    NOTE: The YouGile CreateProjectDto only accepts `title` and `users` — there
    is no workflow association at create time. Workflow concepts live on
    boards, not projects.
    """
    try:
        await ctx.info(f"Creating project: {title}")

        # Validate inputs
        title = validate_non_empty_string(title, "title")

        project_data = {
            "title": title
        }

        if users is not None:
            # Validate user IDs and roles in the users dict
            validated_users = {}
            for user_id, role in users.items():
                user_id = validate_uuid(user_id, "user_id")
                role = validate_non_empty_string(role, "user_role")
                validated_users[user_id] = role
            project_data["users"] = validated_users

        async with YouGileClient(registry.get(workspace)) as client:
            result = await projects.create_project(client, project_data)
            
        created_entity = models.CreatedEntity(**result)
        
        await ctx.info(f"✅ Successfully created project with ID: {created_entity.id}")
        return created_entity
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while creating project: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_project_tool(
    project_id: str,
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Get detailed information about a specific project.

    Args:
        project_id: Project UUID.
        verbosity: 'compact' (default) strips timestamp and the users-role map;
                   'full' returns raw API payload.
    """
    try:
        await ctx.info(f"Fetching project details: {project_id}")

        project_id = validate_uuid(project_id, "project_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await projects.get_project(client, project_id)

        await ctx.info(f"Successfully retrieved project: {result.get('title', project_id)}")
        return apply_verbosity(result, dto_type="project", verbosity=verbosity, include=include)

    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while fetching project: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def update_project_tool(
    project_id: str,
    title: str = None,
    users: Dict[str, str] = None,
    deleted: bool = None,
    workspace: str = "default",
    ctx: Context = None,
) -> models.Project:
    """Update project information.

    NOTE: The YouGile UpdateProjectDto only accepts `title`, `users`, and
    `deleted`. There is no workflow field — boards carry workflows.
    """
    try:
        await ctx.info(f"Updating project: {project_id}")

        project_id = validate_uuid(project_id, "project_id")

        # Build update data with only provided fields
        project_data = {}

        if title is not None:
            title = validate_non_empty_string(title, "title")
            project_data["title"] = title

        if users is not None:
            # Validate user IDs and roles in the users dict
            validated_users = {}
            for user_id, role in users.items():
                user_id = validate_uuid(user_id, "user_id")
                role = validate_non_empty_string(role, "user_role")
                validated_users[user_id] = role
            project_data["users"] = validated_users

        if deleted is not None:
            project_data["deleted"] = deleted

        if not project_data:
            raise ValidationError("At least one field must be provided for update")
        
        async with YouGileClient(registry.get(workspace)) as client:
            # Update project (returns minimal response with just ID)
            await projects.update_project(client, project_id, project_data)
            
            # Fetch complete project data after update
            result = await projects.get_project(client, project_id)
            
        project = models.Project(**result)
        
        await ctx.info(f"Successfully updated project: {project.title}")
        return project
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while updating project: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise