"""
YouGile CRM MCP tools.

CRM directories (2 endpoints):
- POST /crm/contact-persons             create contact person
- GET  /crm/contacts/by-external-id     find contact by messenger ID
"""

from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError, NotFoundError
from ...api import crm
from ...utils.validation import validate_uuid, validate_non_empty_string


# ContactFieldsDto allowed keys (from OpenAPI: ContactFieldsDto / CreateContactPersonDto.fields)
_CONTACT_FIELD_KEYS = {"position", "phone", "additionalPhone", "email", "address"}


async def create_crm_contact_tool(
    project_id: str,
    title: str,
    position: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    additional_phone: Optional[str] = None,
    address: Optional[str] = None,
    fields_extra: Optional[Dict[str, Any]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Create a CRM contact person inside a CRM project.

    Convenience fields (position/phone/email/additional_phone/address) are
    merged into the `fields` payload. Use `fields_extra` for any keys not
    exposed as named arguments — it is merged last and wins on conflict.
    """
    try:
        if ctx:
            await ctx.info(f"Creating CRM contact '{title}' in project {project_id}")

        project_id = validate_uuid(project_id, "project_id")
        title = validate_non_empty_string(title, "title")

        fields: Dict[str, Any] = {}
        if position is not None:
            fields["position"] = position
        if phone is not None:
            fields["phone"] = phone
        if email is not None:
            fields["email"] = email
        if additional_phone is not None:
            fields["additionalPhone"] = additional_phone
        if address is not None:
            fields["address"] = address

        if fields_extra:
            if not isinstance(fields_extra, dict):
                raise ValidationError(
                    "fields_extra must be a dict", field="fields_extra"
                )
            # Warn if caller mixes unknown keys — accepted but logged for visibility.
            unknown = set(fields_extra.keys()) - _CONTACT_FIELD_KEYS
            if unknown and ctx:
                await ctx.debug(
                    f"fields_extra contains keys not in ContactFieldsDto: "
                    f"{sorted(unknown)} — sending as-is"
                )
            fields.update(fields_extra)

        async with YouGileClient(registry.get(workspace)) as client:
            result = await crm.create_contact_person(
                client, project_id, title, fields or None
            )

        if ctx:
            await ctx.info(
                f"Successfully created CRM contact with ID: {result.get('id')}"
            )
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while creating CRM contact: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def find_crm_contact_by_external_id_tool(
    provider: str,
    chat_id: str,
    workspace: str = "default",
    ctx: Context = None,
) -> Optional[Dict[str, Any]]:
    """Find a CRM contact by external messenger ID.

    Returns the contact dict if found, or None if the contact does not exist
    (YouGile responds 404 in that case).
    """
    try:
        if ctx:
            await ctx.info(
                f"Searching CRM contact by external ID: provider='{provider}', chat_id='{chat_id}'"
            )

        provider = validate_non_empty_string(provider, "provider")
        chat_id = validate_non_empty_string(chat_id, "chat_id")

        async with YouGileClient(registry.get(workspace)) as client:
            try:
                result = await crm.find_contact_by_external_id(client, provider, chat_id)
            except NotFoundError:
                if ctx:
                    await ctx.info("No CRM contact found for the given external ID")
                return None

        if ctx:
            await ctx.info(f"Found CRM contact: {result.get('id')}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while searching CRM contact: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise
