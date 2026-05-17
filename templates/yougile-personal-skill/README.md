# yougile-personal — Claude skill template

This is a starting point for a personal Claude skill that loads YouGile context
into the assistant — workspace slugs, project/board/column UUIDs, sticker maps,
routing rules, your own user IDs. It's the counterpart to the `yougile-mcp`
server: the MCP exposes generic tools, the skill tells the model what
*your* setup looks like so it doesn't have to discover everything per session.

## Why bother

Without a personal context skill, the model spends ~3 tool calls
(`list_projects` → `list_boards` → `list_columns`) every time you say
"create a task in project X". With cached UUIDs in the skill you get
to one `create_task` call. The skill also encodes operational rules that
otherwise have to be re-explained every session ("HTML, not Markdown",
"replace-not-append for arrays", "ms not seconds").

## How to use

1. **Pick the install path.** Claude Code reads skills from:
   - `~/.claude/skills/<name>/SKILL.md` (personal profile)
   - `~/.claude-work/skills/<name>/SKILL.md` (work profile if you use one)
   - or a plugin-bundled location

   For most setups: `~/.claude/skills/yougile-personal/SKILL.md`.

2. **Copy `SKILL.md` into place.**
   ```bash
   mkdir -p ~/.claude/skills/yougile-personal
   cp SKILL.md ~/.claude/skills/yougile-personal/SKILL.md
   ```

3. **Fill the placeholders.** Every `{{TOKEN}}` and every `<!-- FILL: ... -->`
   block needs your input. The fastest path is to ask an assistant to walk
   you through it: open Claude Code, point it at the file, and say "fill
   this YouGile skill for me — start by asking what workspaces I have set
   up in `YOUGILE_KEY_*` env vars". It will then ask you per section.

4. **Verify env on the MCP server.** The slugs in the skill must match
   `YOUGILE_KEY_<SLUG>` env vars on the MCP server. If you say `team` in
   the skill but env has `YOUGILE_KEY_WORK`, tool calls will fail.

5. **First-run test.** Ask the assistant "list my YouGile workspaces" —
   it should call `yougile_list_workspaces` and the result should match
   your skill table. If not, fix the smaller of the two until they agree.

## What to fill in (priority order)

| Section | When to fill | Notes |
|---|---|---|
| Workspaces table | always | The most important table — slugs, labels, flags |
| Default workspace | always | One slug. Where ambiguous requests land |
| Self user IDs | always | One UUID per workspace — fetch via `yougile_get_me(workspace)` |
| Project shortcuts | if you have > 1 project you work on regularly | Pure speed-up; can be empty initially |
| Sticker shortcuts | only if you actually use stickers | Skip the whole section otherwise |
| Routing rules | if you have > 1 workspace | Plain-language → workspace mapping |
| Operational rules | already pre-filled | Edit if you want different defaults |
| Style | already pre-filled | Match your communication style |

## Refreshing UUIDs

Project / board / column UUIDs change when the workspace gets restructured
(rare but real). When a cached UUID returns 404, the assistant will
prompt you to update the skill. There's no automatic refresh yet — that
might land later as a `yougile_refresh_workspace_index` tool.

## License

Whatever license the parent `yougile-mcp` repository uses applies. This
template is purely yours to edit.
