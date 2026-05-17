"""
YouGile Users MCP tools.
User management and invitations (5 endpoints).
"""

from typing import List, Dict, Any
from mcp.server.fastmcp import Context
from ...core import models
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import users
from ...utils.validation import validate_uuid, validate_email


async def list_users_tool(workspace: str = "default", ctx: Context = None) -> List[models.User]:
    """Get list of all users in the company."""
    try:
        await ctx.info("Fetching users from YouGile...")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await users.get_users(client)
            
        user_list = [models.User(**user) for user in result]
        
        await ctx.info(f"Successfully retrieved {len(user_list)} users")
        return user_list
        
    except YouGileError as e:
        await ctx.error(f"API error while fetching users: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def invite_user_tool(
    email: str,
    is_admin: bool = False,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Invite a new user to the company.

    YouGile CreateUserDto accepts only ``email`` (required) and ``isAdmin``
    (optional). Identity fields (first/last name, departments) are NOT
    settable via API v2 — the invitee provides those after accepting the
    invite, or an admin edits them in the web UI.
    """
    try:
        if ctx:
            await ctx.info(f"Inviting user: {email}")

        # Validate inputs
        email = validate_email(email)

        async with YouGileClient(registry.get(workspace)) as client:
            result = await users.invite_user(client, email=email, is_admin=is_admin)

        if ctx:
            await ctx.info(f"Successfully invited user: {email}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while inviting user: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_user_tool(user_id: str, workspace: str = "default", ctx: Context = None) -> models.User:
    """Get detailed information about a specific user."""
    try:
        await ctx.info(f"Fetching user details: {user_id}")

        user_id = validate_uuid(user_id, "user_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await users.get_user(client, user_id)
            
        user = models.User(**result)
        
        await ctx.info(f"Successfully retrieved user: {user.real_name}")
        return user
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while fetching user: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def update_user_tool(
    user_id: str,
    is_admin: bool,
    workspace: str = "default",
    ctx: Context = None,
) -> models.User:
    """Update user admin flag.

    YouGile UpdateUserDto exposes only ``isAdmin``. Other identity fields
    (first/last name, departments, email) are NOT settable via API v2.
    """
    try:
        if ctx:
            await ctx.info(f"Updating user: {user_id}")

        user_id = validate_uuid(user_id, "user_id")

        async with YouGileClient(registry.get(workspace)) as client:
            # Update user (returns minimal response with just ID)
            await users.update_user(client, user_id, is_admin=is_admin)

            # Fetch complete user data after update
            result = await users.get_user(client, user_id)

        user = models.User(**result)

        if ctx:
            await ctx.info(f"Successfully updated user: {user.real_name}")
        return user

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while updating user: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_me_tool(workspace: str = "default", ctx: Context = None) -> Dict[str, Any]:
    """Get the user account associated with the workspace's API key.

    Useful for resolving the current bot/user identity (e.g. to filter tasks
    by `assigned_to=<me>` or `created_by=<me>`).
    """
    try:
        if ctx:
            await ctx.info(f"Fetching current user for workspace '{workspace}'...")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await users.get_me(client)

        if ctx:
            await ctx.info(
                f"Successfully retrieved current user: "
                f"{result.get('realName') or result.get('email') or result.get('id')}"
            )
        return result

    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while fetching current user: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def remove_user_tool(user_id: str, workspace: str = "default", ctx: Context = None) -> Dict[str, Any]:
    """Remove user from the company."""
    try:
        await ctx.info(f"Removing user: {user_id}")

        user_id = validate_uuid(user_id, "user_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await users.delete_user(client, user_id)
            
        await ctx.info(f"Successfully removed user: {user_id}")
        return {"success": True, "message": "User removed successfully", "user_id": user_id}
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while removing user: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise