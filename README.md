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

## Multi-tenant: переменные окружения

Для работы с несколькими YouGile-аккаунтами задайте ключи через env:

```env
# Ключ для каждой компании (slug = часть имени переменной после YOUGILE_KEY_)
YOUGILE_KEY_MAIN=ваш_ключ_личной_компании
YOUGILE_KEY_TEAM=ваш_ключ_командной_компании
YOUGILE_KEY_CLIENT_ACME=ваш_ключ_клиента

# Опционально: человекочитаемые названия (показываются в list_workspaces)
YOUGILE_LABEL_MAIN=Личная компания
YOUGILE_LABEL_TEAM=Команда X
YOUGILE_LABEL_CLIENT_ACME=ACME Corp

# Опционально: UUID компании (для переинициализации /auth/*)
YOUGILE_COMPANY_MAIN=00000000-0000-0000-0000-000000000000
```

Параметр `workspace` во всех тулах принимает slug — строчные буквы части
после `YOUGILE_KEY_` (например `main`, `team`, `client_acme`).

Устаревший формат `YOUGILE_API_KEY` по-прежнему работает и маппится
на слаг `default`.

## HTTP transport (многопользовательский режим)

Запуск stdio на каждую сессию Claude/Cursor стоит ~90 МБ. При 5+ сессиях
одновременно — запустите один долгоживущий HTTP-сервер и подключите к нему всех:

    YOUGILE_TRANSPORT=http python run_server.py
    # или
    python run_server.py --http

По умолчанию: `127.0.0.1:3000/mcp` (переопределяется через `YOUGILE_HOST`,
`YOUGILE_PORT`, `YOUGILE_HTTP_PATH`).

Конфигурация MCP-клиента:

```json
{
  "mcpServers": {
    "yougile": { "url": "http://localhost:3000/mcp" }
  }
}
```

## Несколько компаний (multi-tenant)

Один MCP-сервер может хранить API-ключи для нескольких YouGile-компаний.
Добавьте по одной env-переменной на компанию:

    YOUGILE_KEY_MAIN=xxx           # обязательно, определяет воркспейс 'main'
    YOUGILE_LABEL_MAIN="Личная"    # опционально, человекочитаемое название
    YOUGILE_COMPANY_MAIN=<uuid>    # опционально, для /auth/* переинициализации

    YOUGILE_KEY_TEAM=yyy
    YOUGILE_LABEL_TEAM="Стартап X"

Каждый тул принимает опциональный параметр `workspace` (или используй
`set_active_workspace` один раз в начале сессии).
Используйте `list_workspaces` для получения доступных слагов.

Устаревший формат `YOUGILE_API_KEY` (+ `YOUGILE_COMPANY_ID`) по-прежнему работает
и маппится на слаг `default`.

## Активная компания (per-session)

Чтобы не передавать `workspace` в каждый вызов тула, установи активную компанию
один раз в начале сессии:

```
# MCP вызов
set_active_workspace(slug="main")

# Далее тулы без workspace используют "main"
list_projects()       # → main
list_tasks(...)       # → main
create_task(...)      # → main
```

Для смены компании в рамках сессии — вызови снова:
```
set_active_workspace(slug="client_acme")
```

Для проверки текущего активного workspace:
```
get_active_workspace()
# → {"active_workspace": "main", "effective_workspace": "main", "available_workspaces": [...]}
```

Явный `workspace="X"` в параметре тула всегда побеждает session active:
```
# session active = "main"
list_projects(workspace="team")  # → team (явный override)
```

**Примечание:** Active workspace не персистентен — сбрасывается при перезапуске MCP сервера.

## Безопасность: ограничения upload_file

`upload_file` может читать любой файл на сервере. Чтобы агенты не могли
exfiltrate `.env`, SSH-ключи и другие секреты, пути ограничены домашней
директорией (`~/`) по умолчанию. Переопределить:

    YOUGILE_UPLOAD_ROOTS=/srv/data:/var/uploads

Dotfiles и пути, содержащие `credentials`, `secret`, `password`, `.env`,
`.ssh`, `private_key` (без учёта регистра), всегда заблокированы.

## Управление verbosity ответов

Все read-тулы (`list_*`, `get_*`) принимают параметр `verbosity`:

| Уровень | Поведение | Когда использовать |
|---|---|---|
| `custom` | Только `id`. Остальные поля — явно через `include[]` | Агрегации, подсчёты — минимум токенов |
| `compact` | Core-поля + дешёвые derived-поля + `_hints` о скрытых данных | **По умолчанию.** Стандартная работа |
| `full` | Все поля DTO кроме opt-in (история, raw timestamps) | Отладка, аудит, полный просмотр |

Параметр `include[]` добавляет конкретные поля или группы полей:

```python
# Только ID — для подсчёта completed/not completed
list_tasks(verbosity="custom", include=["completed"])

# Compact + описание (description обычно выключен в list_*)
list_tasks(verbosity="compact", include=["description"])

# Compact + история дедлайна + raw timestamps
get_task(task_id="...", verbosity="compact", include=["deadline_history", "timestamps"])
```

Полный каталог доступных полей и include-ключей — через тул `describe_response`:

```python
# Обзор всех сущностей
describe_response()

# Детальная схема task: типы, verbosity-уровни, include-ключи, quirks
describe_response(entity="task", verbosity="full")
```

Когда поля опущены в compact, ответ содержит `_meta.omitted_fields` и `_hints`:
```json
{
  "_meta": {"verbosity": "compact", "omitted_fields": ["createdBy", "extensionData"]},
  "content": [
    {"id": "...", "title": "...", "_hints": {"has_description": true, "has_checklists": false}}
  ]
}
```

## Персональный скилл для Claude

Шаблон скилла, парный к этому MCP, лежит в
`templates/yougile-personal-skill/` и состоит из `SKILL.md`,
`references/*` и `templates/*`. Скилл даёт Claude per-session контекст:
слаги воркспейсов, UUID проектов, шорткаты стикеров, routing rules.

**Без скилла:** Claude делает 2-3 лишних API-вызова на каждый запрос
(lookup проектов, досок, колонок). **Со скиллом:** UUID уже в
контексте → напрямую к делу.

### Установка через агента (manifest-based)

Сам MCP-сервер на пользовательский диск **не пишет**. Каждый файл
шаблона опубликован как MCP-ресурс — агент читает их через
`resources/read` и записывает локально своим Write-tool (под обычными
permissions клиента, без env-override и без allowlist на стороне
сервера).

```bash
# 1. Тул возвращает манифест: questions + default_target_dir + files[]
#    с (uri, target, sha256) для каждого файла шаблона.
setup_yougile_skill

# 2. Агент читает каждый files[i].uri и пишет в target внутри
#    default_target_dir (или другого места — выбор клиента).
#    Пример URI шаблонных файлов:
#       yougile://skill-template/SKILL.md
#       yougile://skill-template/references/tool-keys.md
#       yougile://skill-template/templates/briefing.template.md
#       (всего 8 файлов в whitelist'е)
```

Манифест включает sha256 каждого файла — агент должен сверить контент
после Write, чтобы исключить случайную переформулировку моделью.

### Ручная установка

Если хотите обойтись без агента:

1. Скопируйте `templates/yougile-personal-skill/SKILL.md`,
   `references/*` и `templates/*` в
   `~/.agents/skills/yougile-personal/` (или другое место, где ваш
   клиент ожидает скиллы; для Claude Code например
   `~/.claude/skills/yougile-personal/`).
2. Заполните плейсхолдеры в `templates/briefing.template.md` (workspace
   slugs, UUID проектов, routing rules) и сохраните результат как
   `briefing.md` рядом с `SKILL.md`.
3. При следующей сессии Claude подхватит скилл автоматически.

### Обновление

Обновляйте `briefing.md` при смене workspace, добавлении новых
проектов или изменении routing rules. `SKILL.md` и `references/*`
переустанавливайте через `setup_yougile_skill` (агент перепишет файлы;
ваш `briefing.md` он не трогает) или вручную перекопируйте из шаблона
после `git pull`.

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