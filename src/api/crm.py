"""YouGile CRM API client (2 endpoints implemented)."""

from typing import Dict, Any, Optional

from ..core.client import YouGileClient


async def create_contact_person(
    client: YouGileClient,
    project_id: str,
    title: str,
    fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a CRM contact person inside a CRM project.

    POST /api-v2/crm/contact-persons
    """
    payload: Dict[str, Any] = {
        "projectId": project_id,
        "title": title,
    }
    if fields:
        payload["fields"] = fields
    return await client.post("/crm/contact-persons", json=payload)


async def find_contact_by_external_id(
    client: YouGileClient,
    provider: str,
    chat_id: str,
) -> Dict[str, Any]:
    """Find a CRM contact by external messenger ID.

    GET /api-v2/crm/contacts/by-external-id?provider=...&chatId=...
    """
    return await client.get(
        "/crm/contacts/by-external-id",
        params={"provider": provider, "chatId": chat_id},
    )
