"""
YouGile Users API client.
User management and invitations (5 endpoints).
"""

from typing import Dict, Any, List, Optional
from ..core.client import YouGileClient
from ..utils.validation import validate_uuid, validate_email


async def get_users(
    client: YouGileClient,
    limit: int = 50,
    offset: int = 0,
    email: Optional[str] = None,
    project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get list of users with optional filtering.

    Args:
        limit: Page size (max 1000).
        offset: Page offset.
        email: Filter by exact email match (server-side).
        project_id: Filter to users that belong to this project (server-side).

    NOTE: YouGile API v2 does not expose `includeDeleted` for /users.
    """
    params: Dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }
    if email:
        params["email"] = email
    if project_id:
        params["projectId"] = project_id

    response = await client.get("/users", params=params)
    return response.get("content", [])


async def get_me(client: YouGileClient) -> Dict[str, Any]:
    """Get the user account associated with the current API key."""
    return await client.get("/users/me")


async def invite_user(client: YouGileClient, email: str, is_admin: bool = False) -> Dict[str, Any]:
    """Invite user to company.

    API contract (CreateUserDto): required ``email`` only; optional ``isAdmin``.
    Other identity fields (name, departments) are not settable via API v2 —
    they're managed by the invitee or in the YouGile web UI.
    """
    body: Dict[str, Any] = {"email": email}
    if is_admin:
        body["isAdmin"] = True
    return await client.post("/users", json=body)


async def get_user(client: YouGileClient, user_id: str) -> Dict[str, Any]:
    """Get user by ID."""
    user_id = validate_uuid(user_id, "user_id")
    return await client.get(f"/users/{user_id}")


async def update_user(client: YouGileClient, user_id: str, is_admin: bool) -> Dict[str, Any]:
    """Update user.

    API contract (UpdateUserDto): only ``isAdmin`` is settable. Other fields
    silently fall through.
    """
    user_id = validate_uuid(user_id, "user_id")
    return await client.put(f"/users/{user_id}", json={"isAdmin": is_admin})


async def delete_user(client: YouGileClient, user_id: str) -> Dict[str, Any]:
    """Remove user from company."""
    user_id = validate_uuid(user_id, "user_id")
    return await client.delete(f"/users/{user_id}")