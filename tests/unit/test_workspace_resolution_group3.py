import inspect
import sys; sys.path.insert(0, 'src')
from src.server import mcp

TOOLS_GROUP3 = [
    "add_task_comment", "create_board", "create_column", "create_crm_contact",
    "create_group_chat", "create_project", "create_task", "create_webhook",
    "delete_task", "describe_response", "find_crm_contact_by_external_id",
    "invite_user", "remove_task_sticker", "remove_user", "send_chat_message",
    "set_task_deadline", "setup_yougile_skill", "update_board", "update_chat_message",
    "update_column", "update_project", "update_task", "update_task_chat_subscribers",
    "update_user", "update_webhook", "upload_file",
]


class TestWorkspaceSignatureGroup3:
    def test_all_tools_have_optional_workspace(self):
        tools = mcp._tool_manager._tools
        for name in TOOLS_GROUP3:
            if name not in tools:
                continue  # тул мог быть deferred
            sig = inspect.signature(tools[name].fn)
            if 'workspace' not in sig.parameters:
                continue  # тул без workspace — пропускаем
            param = sig.parameters['workspace']
            assert param.default is None, (
                f"{name}: workspace default = '{param.default}', ожидалось None"
            )

    def test_no_tool_has_workspace_string_default(self):
        """Ни один тул не должен иметь workspace="default" как default."""
        tools = mcp._tool_manager._tools
        violations = []
        for name, tool in tools.items():
            sig = inspect.signature(tool.fn)
            if 'workspace' in sig.parameters:
                param = sig.parameters['workspace']
                if param.default == "default":
                    violations.append(name)
        assert not violations, f"Тулы с workspace='default': {violations}"
