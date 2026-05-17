"""
YouGile Chat MCP tools.
Communication features: group chats and task messages (8 endpoints).
"""

from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import Context
from ...core import models
from ...core.models import MessageReact
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import chats
from ...utils.validation import validate_uuid, validate_non_empty_string
from ...utils.verbosity import apply_verbosity, Verbosity


# Group Chat Management
async def list_group_chats_tool(
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """Get list of all group chats.

    Args:
        verbosity: 'compact' (default) strips userRoleMap/roleConfigMap;
                   'full' returns raw API payload.
    """
    try:
        await ctx.info("Fetching group chats from YouGile...")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await chats.get_group_chats(client)

        await ctx.info(f"Successfully retrieved {len(result)} group chats")
        return apply_verbosity(result, dto_type="group_chat", verbosity=verbosity, include=include, is_list=True)
        
    except YouGileError as e:
        await ctx.error(f"API error while fetching group chats: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def create_group_chat_tool(
    title: str,
    users: Optional[Dict[str, Dict[str, Any]]] = None,
    user_role_map: Optional[Dict[str, str]] = None,
    role_config_map: Optional[Dict[str, Dict[str, Any]]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Create a new group chat.

    The YouGile CreateGroupChatDto requires ALL of: title, users, userRoleMap,
    roleConfigMap. Calling with only `title` is allowed by this tool but the
    server is likely to reject it — for a functional chat pass all four fields.

    Args:
        title: Chat title (required)
        users: Map {userId: {notified: bool, ...}} listing chat members
        user_role_map: Map {userId: roleSlug} assigning each user to a role
        role_config_map: Map {roleSlug: {editProperties, editAdmins, editUsers,
                         sendMessages, removeMessages, ...}} defining permissions
                         for each role used in user_role_map
    """
    try:
        if ctx:
            await ctx.info(f"Creating group chat: {title}")

        # Validate inputs
        title = validate_non_empty_string(title, "title")

        # Validate user IDs in `users` and `user_role_map` if provided.
        if users is not None:
            if not isinstance(users, dict):
                raise ValidationError("users must be a dict of {userId: {...}}", field="users")
            for user_id in list(users.keys()):
                validate_uuid(user_id, "users.userId")

        if user_role_map is not None:
            if not isinstance(user_role_map, dict):
                raise ValidationError(
                    "user_role_map must be a dict of {userId: roleSlug}",
                    field="user_role_map",
                )
            for user_id in list(user_role_map.keys()):
                validate_uuid(user_id, "user_role_map.userId")

        if role_config_map is not None and not isinstance(role_config_map, dict):
            raise ValidationError(
                "role_config_map must be a dict of {roleSlug: {...}}",
                field="role_config_map",
            )

        chat_data: Dict[str, Any] = {
            "title": title,
        }
        if users is not None:
            chat_data["users"] = users
        if user_role_map is not None:
            chat_data["userRoleMap"] = user_role_map
        if role_config_map is not None:
            chat_data["roleConfigMap"] = role_config_map

        async with YouGileClient(registry.get(workspace)) as client:
            result = await chats.create_group_chat(client, chat_data)

        if ctx:
            await ctx.info(f"Successfully created group chat with ID: {result.get('id')}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while creating group chat: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_group_chat_tool(
    chat_id: str,
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Get detailed information about a specific group chat.

    Args:
        chat_id: Chat UUID.
        verbosity: 'compact' (default) strips userRoleMap/roleConfigMap;
                   'full' returns raw API payload.
    """
    try:
        await ctx.info(f"Fetching group chat details: {chat_id}")

        chat_id = validate_uuid(chat_id, "chat_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await chats.get_group_chat(client, chat_id)

        await ctx.info(f"Successfully retrieved group chat: {result.get('title', chat_id)}")
        return apply_verbosity(result, dto_type="group_chat", verbosity=verbosity, include=include)
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while fetching group chat: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


# Chat Messages (Comments)
async def get_chat_messages_tool(
    chat_id: str,
    limit: int = 50,
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """Get messages from a chat (task comments or group chat messages).

    Args:
        chat_id: ID of the chat (can be task ID for task comments)
        limit: Maximum number of messages to return
        verbosity: 'compact' (default) drops textHtml/editTimestamp/empty reactions;
                   'full' returns raw API payload.
    """
    try:
        await ctx.info(f"Fetching messages from chat: {chat_id}")

        chat_id = validate_uuid(chat_id, "chat_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await chats.get_chat_messages(client, chat_id)

        # Apply limit if needed
        if limit and len(result) > limit:
            result = result[-limit:]  # Get latest messages

        await ctx.info(f"Successfully retrieved {len(result)} messages")
        return apply_verbosity(result, dto_type="message", verbosity=verbosity, include=include, is_list=True)
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while fetching messages: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def send_chat_message_tool(
    chat_id: str,
    text: str,
    text_html: Optional[str] = None,
    label: Optional[str] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Send a message to a chat (add comment to task or send group chat message).

    Args:
        chat_id: ID of the chat (can be task ID for task comments)
        text: Plain-text body of the message
        text_html: HTML version of the message. If omitted, text is auto-wrapped
                   in <p>...</p>. Pass your own HTML to control formatting
                   (<br>, <b>, <i>, lists, etc.). NOT escaped server-side —
                   sanitize untrusted input before passing.
        label: Optional short label / quick link displayed with the message
               (e.g. "Comment", "Update", "Mention"). Defaults to "Comment".
    """
    try:
        if ctx:
            await ctx.info(f"Sending message to chat: {chat_id}")

        # Validate inputs
        chat_id = validate_uuid(chat_id, "chat_id")
        text = validate_non_empty_string(text, "text")

        # Default HTML body wraps plain text in a single paragraph.
        # NOTE: text is NOT html-escaped — callers passing untrusted input must
        # sanitize themselves or pass an explicit text_html.
        effective_html = text_html if text_html is not None else f"<p>{text}</p>"
        effective_label = label if label is not None else "Comment"

        message_data = {
            "text": text,
            "textHtml": effective_html,
            "label": effective_label,
        }

        async with YouGileClient(registry.get(workspace)) as client:
            result = await chats.send_chat_message(client, chat_id, message_data)

        if ctx:
            await ctx.info(f"Successfully sent message with ID: {result.get('id')}")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while sending message: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def get_chat_message_tool(
    chat_id: str,
    message_id: str,
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Get a specific message from a chat.

    Args:
        chat_id: Chat UUID.
        message_id: Message UUID.
        verbosity: 'compact' (default) drops textHtml/editTimestamp/empty reactions;
                   'full' returns raw API payload.
    """
    try:
        await ctx.info(f"Fetching message {message_id} from chat: {chat_id}")

        chat_id = validate_uuid(chat_id, "chat_id")
        message_id = validate_uuid(message_id, "message_id")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await chats.get_chat_message(client, chat_id, message_id)

        await ctx.info(f"Successfully retrieved message")
        return apply_verbosity(result, dto_type="message", verbosity=verbosity, include=include)
        
    except ValidationError as e:
        await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        await ctx.error(f"API error while fetching message: {e.message}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        raise


async def update_chat_message_tool(
    chat_id: str,
    message_id: str,
    label: Optional[str] = None,
    react: Optional[MessageReact] = None,
    delete: bool = False,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Update message metadata: label, admin reaction, or soft-delete.

    Note: the YouGile API does NOT support editing message text — only metadata
    (UpdateChatMessageDto fields: deleted, label, react). To change the body,
    delete and re-send.

    Args:
        chat_id: ID of the chat (or task ID for task comments)
        message_id: ID of the message to update
        label: New label / quick link text for the message
        react: Admin reaction emoji. One of: 👍 👎 👏 🙂 😀 😕 🎉 ❤ 🚀 ✔
        delete: If True, soft-deletes the message
    """
    try:
        if ctx:
            await ctx.info(f"Updating message {message_id} in chat: {chat_id}")

        # Validate inputs
        chat_id = validate_uuid(chat_id, "chat_id")
        message_id = validate_uuid(message_id, "message_id")

        message_data: Dict[str, Any] = {}

        if label is not None:
            message_data["label"] = label

        if react is not None:
            valid_reacts = ("👍", "👎", "👏", "🙂", "😀", "😕", "🎉", "❤", "🚀", "✔")
            if react not in valid_reacts:
                raise ValidationError(
                    f"react must be one of {valid_reacts}, got: {react!r}",
                    field="react",
                )
            message_data["react"] = react

        if delete:
            message_data["deleted"] = True

        if not message_data:
            raise ValidationError(
                "At least one of label, react, delete must be provided",
            )

        async with YouGileClient(registry.get(workspace)) as client:
            result = await chats.update_chat_message(client, chat_id, message_id, message_data)

        if ctx:
            await ctx.info("Successfully updated message metadata")
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while updating message: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise


# Task-specific comment helpers
async def get_task_comments_tool(
    task_id: str,
    limit: int = 50,
    verbosity: Verbosity = "compact",
    include: Optional[List[str]] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """Get comments for a specific task (alias for get_chat_messages with task ID)."""
    if ctx:
        await ctx.info(f"Fetching comments for task: {task_id}")
    return await get_chat_messages_tool(
        task_id, limit, verbosity=verbosity, include=include, workspace=workspace, ctx=ctx,
    )


async def add_task_comment_tool(
    task_id: str,
    comment: str,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Add a comment to a specific task (alias for send_chat_message with task ID)."""
    if ctx:
        await ctx.info(f"Adding comment to task: {task_id}")
    return await send_chat_message_tool(task_id, comment, workspace=workspace, ctx=ctx)