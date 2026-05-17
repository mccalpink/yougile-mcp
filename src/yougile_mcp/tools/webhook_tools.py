"""
YouGile Webhook MCP tools.

Subscriptions to company events (3 endpoints):
- POST   /webhooks         create
- GET    /webhooks         list
- PUT    /webhooks/{id}    update / soft-delete
"""

from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from mcp.server.fastmcp import Context
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import webhooks
from ...utils.validation import validate_uuid, validate_non_empty_string
from ...utils.verbosity import apply_verbosity, Verbosity
from ...utils.normalizers import normalize_webhook_filters


def _redact_url(url: str) -> str:
    """Strip path/query/fragment so signed-URL tokens never reach the log."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return "<invalid-url>"
        return f"{parsed.scheme}://{parsed.netloc}/..."
    except Exception:
        return "<unparseable-url>"


def _validate_filters(filters: Any, field: str = "filters") -> List[Dict[str, Any]]:
    """Lightweight validation for the WebhookFilters array.

    YouGile schema marks `filters` as required, but an empty array is allowed
    when the caller wants no filtering. Each item must be a dict with `name`
    and `value` keys. We do not enforce the actual filter-name vocabulary
    (location/title/chat_message) because YouGile may extend it.
    """
    if filters is None:
        filters = []
    if not isinstance(filters, list):
        raise ValidationError(f"{field} must be a list", field=field)
    for i, item in enumerate(filters):
        if not isinstance(item, dict):
            raise ValidationError(f"{field}[{i}] must be an object", field=field)
        if "name" not in item or "value" not in item:
            raise ValidationError(
                f"{field}[{i}] must contain 'name' and 'value' keys",
                field=field,
            )
    return filters


async def list_webhooks_tool(
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False,
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """List configured webhook subscriptions for the workspace.

    **Note:** YouGile API does not support server-side pagination for
    webhooks. The full list is fetched on every call; limit/offset are
    applied client-side. Be mindful with companies that have many webhook
    subscriptions.

    Args:
        verbosity: 'compact' (default) drops lastSuccess/failuresSinceLastSuccess;
                   'full' returns raw API payload.

    RETURNS:
      compact (default): {id, url, event, filters, enabled} per webhook.
        lastSuccess/failuresSinceLastSuccess dropped.
      custom: only {id} per item. Add fields via include=[].
      full: raw API payload.
    Note: workspace must be a resolved string (not None). Caller (server.py) handles session→workspace resolution via _resolve_ws.
    """
    try:
        if ctx:
            await ctx.info(
                f"Fetching webhooks (limit={limit}, offset={offset}, "
                f"include_deleted={include_deleted})..."
            )

        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("limit must be a positive integer", field="limit")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative integer", field="offset")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await webhooks.get_webhooks(client, include_deleted=include_deleted)

        page = result[offset : offset + limit]

        if ctx:
            await ctx.info(
                f"Successfully retrieved {len(page)} webhook(s) (of {len(result)} total)"
            )
        return apply_verbosity(page, dto_type="webhook", verbosity=verbosity, include=include, is_list=True)

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while fetching webhooks: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def create_webhook_tool(
    url: str,
    event: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    allow_unfiltered: bool = False,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Create a webhook subscription.

    Args:
        workspace: workspace slug.
        url: target URL that will receive the event POST.
        event: subscription event, e.g. "task-created", "task-*", ".*".
        filters: list of {name, value} filters narrowing the scope. If empty
            or None, the call fails unless `allow_unfiltered=True` — this
            guards against accidentally creating a firehose webhook that
            receives every event in the company.
        allow_unfiltered: pass True only when you explicitly want a
            company-wide firehose subscription. Default False.
    Note: workspace must be a resolved string (not None). Caller (server.py) handles session→workspace resolution via _resolve_ws.
    """
    try:
        url = validate_non_empty_string(url, "url")
        event = validate_non_empty_string(event, "event")
        filters = _validate_filters(filters)

        if len(filters) == 0 and not allow_unfiltered:
            raise ValidationError(
                "filters is empty — this would create a firehose webhook "
                "for the entire company. If you really want that, pass "
                "allow_unfiltered=True explicitly.",
                field="filters",
            )

        if ctx:
            await ctx.info(
                f"Creating webhook for {_redact_url(url)}, event={event}, "
                f"filters={len(filters)}"
            )

        # Quirk: WebhookFilters.name описан как array в OpenAPI, фактически — строка.
        # Нормализуем до отправки в API.
        if filters:
            filters, filter_meta = normalize_webhook_filters(filters)
            # filter_meta.notes попадут в ответ если нужно

        payload: Dict[str, Any] = {
            "url": url,
            "event": event,
            "filters": filters,
        }

        async with YouGileClient(registry.get(workspace)) as client:
            result = await webhooks.create_webhook(client, payload)

        if ctx:
            await ctx.info(f"Successfully created webhook with ID: {result.get('id')}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while creating webhook: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def update_webhook_tool(
    webhook_id: str,
    url: Optional[str] = None,
    event: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    deleted: bool = False,
    disabled: Optional[bool] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Update or soft-delete a webhook subscription.

    Only the fields explicitly provided are sent to the API. Pass `deleted=True`
    to soft-delete the webhook, `disabled=True` to pause without removing it.
    Note: workspace must be a resolved string (not None). Caller (server.py) handles session→workspace resolution via _resolve_ws.
    """
    try:
        if ctx:
            await ctx.info(f"Updating webhook: {webhook_id}")

        webhook_id = validate_uuid(webhook_id, "webhook_id")

        payload: Dict[str, Any] = {}
        if url is not None:
            payload["url"] = validate_non_empty_string(url, "url")
            if ctx:
                await ctx.debug(f"  new url: {_redact_url(payload['url'])}")
        if event is not None:
            payload["event"] = validate_non_empty_string(event, "event")
        if filters is not None:
            filters = _validate_filters(filters)
            # Quirk: WebhookFilters.name описан как array в OpenAPI, фактически — строка.
            if filters:
                filters, _ = normalize_webhook_filters(filters)
            payload["filters"] = filters
        if disabled is not None:
            payload["disabled"] = bool(disabled)
        if deleted:
            payload["deleted"] = True

        if not payload:
            raise ValidationError(
                "At least one field (url, event, filters, disabled, deleted) must be provided"
            )

        async with YouGileClient(registry.get(workspace)) as client:
            result = await webhooks.update_webhook(client, webhook_id, payload)

        if ctx:
            action = "deleted" if deleted else "updated"
            await ctx.info(f"Successfully {action} webhook: {webhook_id}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while updating webhook: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise
