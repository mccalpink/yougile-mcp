import inspect
import sys; sys.path.insert(0, 'src')
from src.server import mcp

TOOLS_GROUP2 = [
    "list_tasks", "list_task_summaries", "list_projects", "list_string_stickers",
    "list_users", "list_webhooks", "get_tasks_by_date", "decode_task_stickers",
    "get_chat_messages",
]


class TestWorkspaceSignatureGroup2:
    def test_all_tools_have_optional_workspace(self):
        tools = mcp._tool_manager._tools
        for name in TOOLS_GROUP2:
            assert name in tools, f"Тул {name} не найден"
            sig = inspect.signature(tools[name].fn)
            assert 'workspace' in sig.parameters, f"{name}: нет workspace"
            param = sig.parameters['workspace']
            assert param.default is None, (
                f"{name}: workspace default = '{param.default}', ожидалось None"
            )
