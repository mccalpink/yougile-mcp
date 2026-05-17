"""
YouGile Users API client.
User management and invitations (5 endpoints).
"""

from typing import Dict, Any, List
from ..core.client import YouGileClient
from ..utils.validation import validate_uuid, validate_email


async def get_users(client: YouGileClient) -> List[Dict[str, Any]]:
    """Get list of users."""
    response = await client.get("/users")
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