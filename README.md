# YouGile MCP Server

MCP сервер для интеграции с YouGile. Работает с любыми AI помощниками, поддерживающими протокол MCP (Claude Desktop, Continue, Cline и другие). Позволяет AI работать с вашими проектами, задачами и командой в YouGile.

## 🚀 Что умеет

### **Управление проектами**
- ✅ Создание и редактирование проектов
- ✅ Управление досками и колонками
- ✅ Работа с задачами (создание, обновление, комментарии)
- ✅ Управление командой (приглашения, роли)
- ✅ Отчеты и аналитика по проектам

### **Интеграция с AI помощниками**
- ✅ Автоматическое создание задач из разговора
- ✅ Умные отчеты по проектам
- ✅ Планирование спринтов
- ✅ Анализ продуктивности команды

## 📦 Установка

### 1. Скачайте проект
```bash
git clone https://github.com/justrussian/yougile-mcp.git
cd yougile-mcp
```

### 2. Создайте виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Получите данные YouGile

**Найдите свой email и пароль YouGile** - те же, что используете для входа на сайт.

**Получите ID компании:**
1. Войдите в [YouGile](https://yougile.com)
2. Нажмите `Ctrl + ~` для открытия конфигуратора
3. Перейдите во вкладку "Навигатор по объектам" справа
4. Нажмите на иконку информации (ℹ️) справа от названия вашей компании
5. Скопируйте ID компании из открывшегося окна

### 5. Подключите к AI помощнику

**Для Claude Desktop:**

Добавьте в конфигурацию Claude Desktop:
```json
{
  "mcpServers": {
    "yougile": {
      "command": "python",
      "args": ["/полный/путь/к/папке/yougile-mcp/run_server.py"],
      "cwd": "/полный/путь/к/папке/yougile-mcp",
      "env": {
        "PATH": "/полный/путь/к/папке/yougile-mcp/venv/bin:$PATH",
        "YOUGILE_BASE_URL": "https://yougile.com",
        "YOUGILE_EMAIL": "ваш-email@yougile.com",
        "YOUGILE_PASSWORD": "ваш-пароль",
        "YOUGILE_COMPANY_ID": "ваш-company-id"
      }
    }
  }
}
```

**Для других MCP-совместимых AI:**

Используйте аналогичную конфигурацию для Continue, Cline и других MCP-совместимых помощников.

## HTTP transport (multi-client setup)

Running stdio per Claude/Cursor session costs ~90 MB each. For 5+
concurrent sessions, run one long-lived HTTP server and point every
client at its URL:

    YOUGILE_TRANSPORT=http python run_server.py
    # or
    python run_server.py --http

Defaults: `127.0.0.1:3000/mcp` (override via `YOUGILE_HOST`,
`YOUGILE_PORT`, `YOUGILE_HTTP_PATH`).

MCP client config:

```json
{
  "mcpServers": {
    "yougile": { "url": "http://localhost:3000/mcp" }
  }
}
```

## Multi-tenant workspaces

One MCP server can hold API keys for multiple YouGile companies. Add
one env var per company:

    YOUGILE_KEY_MAIN=xxx           # required, defines workspace 'main'
    YOUGILE_LABEL_MAIN="Личная"     # optional, human-readable label
    YOUGILE_COMPANY_MAIN=<uuid>     # optional, for /auth/* re-init

    YOUGILE_KEY_TEAM=yyy
    YOUGILE_LABEL_TEAM="Стартап X"

Every data tool takes a `workspace` parameter (default `"default"`).
Use `list_workspaces` from the LLM to discover configured slugs.

The legacy single-tenant `YOUGILE_API_KEY` (+ optional
`YOUGILE_COMPANY_ID`) still works — it's mapped to slug `default`.

## Security note: upload_file path allowlist

`upload_file` can read any file on the server filesystem. To prevent
agents from exfiltrating `.env`, SSH keys, or other secrets, paths
are restricted by default to the user's home directory (`~/`).
Override with:

    YOUGILE_UPLOAD_ROOTS=/srv/data:/var/uploads

Dotfiles and paths matching `credentials`, `secret`, `password`,
`.env`, `.ssh`, `private_key` (case-insensitive) are always blocked.

## Response verbosity

Read tools (`list_*`, `get_*`) default to `verbosity="compact"` — they strip
timestamps, internal IDs, and empty fields to save tokens (~37% on a
typical session, up to 60% on `list_projects`). When something is dropped,
the response includes a `_meta.omitted_fields` block so the agent knows
what to ask for if it needs the full data:

```json
{
  "_meta": {
    "verbosity": "compact",
    "omitted_fields": ["timestamp", "createdBy", "idTaskCommon", ...],
    "hint": "Pass verbosity='full' to include all fields"
  },
  "id": "...",
  "title": "...",
  ...
}
```

Pass `verbosity="full"` on any read tool to bypass pruning and get the
raw API response (useful for debugging audit history, exact timestamps,
or accessing extension data).

Tools without a `verbosity` parameter return minimal payloads already
(`get_string_sticker_state`, `get_sprint_sticker_state`,
`get_task_chat_subscribers`, `decode_task_stickers`) or are write
operations (`create_*`, `update_*`, `delete_*`, `send_*`).

## Personal Claude skill

A starter skill that pairs with this MCP lives at
`templates/yougile-personal-skill/`. Copy `SKILL.md` to
`~/.claude/skills/yougile-personal/SKILL.md` and fill the
placeholders to give Claude per-session context (workspace slugs,
project shortcuts, sticker maps).

## 🎯 Как использовать с AI помощником

После подключения можно просить AI помощника:

### **Управление задачами**
- "Создай задачу 'Исправить баг с авторизацией' в проекте Мобильное приложение"
- "Покажи все мои задачи на сегодня"
- "Обнови статус задачи на 'В работе'"

### **Работа с проектами**
- "Создай новый проект 'Редизайн сайта'"
- "Покажи статистику по проекту за неделю"
- "Добавь пользователя ivan@company.com в проект"

### **Отчеты и планирование**
- "Сделай отчет по продуктивности команды"
- "Спланируй спринт на 2 недели"
- "Покажи, какие задачи просрочены"

## ⚙️ Диагностика проблем

### Проверка работы сервера
```bash
# Убедитесь что виртуальное окружение активировано
source venv/bin/activate  # На Windows: venv\Scripts\activate

python run_server.py
```
Сервер должен запуститься и подключиться к YouGile автоматически.

### Частые ошибки

**"No module named 'mcp'"** - не активировано виртуальное окружение. Выполните `source venv/bin/activate`

**"No module named 'src'"** - запускайте через `python run_server.py`, не напрямую `src/server.py`

**"HTTP 401"** - неверные данные для входа в YouGile

**"HTTP 403"** - нет доступа к компании

### Получение помощи
Если что-то не работает:
1. Проверьте, что можете войти в YouGile через браузер с теми же данными
2. Убедитесь, что Company ID правильный (см. инструкцию выше)
3. Попробуйте запустить `python run_server.py` напрямую и посмотрите на вывод

## 👨‍💻 Автор

Проект разработан [HeadWise](https://headwise.ru) - Даниил Тарасенко

## 📄 Лицензия

Этот проект является открытым программным обеспечением.