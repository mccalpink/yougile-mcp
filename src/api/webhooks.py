"""YouGile Webhooks API client (3 endpoints)."""

from typing import Dict, Any, List, Optional
from ..core.client import YouGileClient
from ..utils.validation import validate_uuid


async def create_webhook(client: YouGileClient, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create webhook subscription."""
    return await client.post("/webhooks", json=webhook_data)


async def get_webhooks(
    client: YouGileClient,
    include_deleted: bool = False,
) -> List[Dict[str, Any]]:
    """Get list of webhook subscriptions.

    YouGile API supports only `includeDeleted` query parameter — pagination
    (limit/offset) is applied client-side by callers if requested.
    """
    params: Dict[str, Any] = {}
    if include_deleted:
        params["includeDeleted"] = True
    result = await client.get("/webhooks", params=params or None)
    # API responds with a JSON array; httpx returns it as-is.
    if isinstance(result, list):
        return result
    # Defensive fallback in case YouGile wraps the array (matches paginated lists)
    if isinstance(result, dict) and isinstance(result.get("content"), list):
        return result["content"]
    return []


async def update_webhook(
    client: YouGileClient,
    webhook_id: str,
    webhook_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update webhook subscription."""
    return await client.put(
        f"/webhooks/{validate_uuid(webhook_id, 'webhook_id')}", json=webhook_data
    )
