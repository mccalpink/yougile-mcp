# Common Patterns — Tool Chains

15 типичных пользовательских запросов с полными tool chain'ами.
Подгружай когда неочевидна последовательность вызовов.

---

## Pattern 1: Создать задачу в известный проект

**Запрос:** «Создай задачу X в личный проект»

```python
# UUID из briefing.md / shortcuts
create_task(
    workspace="main",
    title="X",
    column_id="<cached inbox UUID>",
    description="<p>...</p>"  # HTML если есть описание
)
```

**Сообщи:** «Помещу в колонку Inbox доски Main Board проекта Личный (main)»

---

## Pattern 2: Найти просроченные задачи

**Запрос:** «Что горит», «просроченные», «overdue»

```python
# Шаг 1: получить задачи с минимальным набором полей
result = list_tasks(
    workspace="main",
    verbosity="custom",
    include=["title", "deadline", "assigned", "columnId"],
    completed=False,
    archived=False
)
# Шаг 2: клиентская фильтрация
import time
now_ms = int(time.time() * 1000)
overdue = [t for t in result["content"]
           if t.get("deadline", {}).get("deadline", 0) < now_ms
           and t.get("deadline", {}).get("deadline", 0) > 0]
```

**Почему не `deadline_to` в API:** YouGile API не поддерживает фильтрацию по deadline_to.

---

## Pattern 3: «Мои задачи» — assign to self

**Запрос:** «Покажи мои задачи», «что на мне»

```python
# self_uuid берёшь из briefing.md → Self user IDs
list_tasks(
    workspace="main",
    verbosity="compact",
    assigned_to="<self_uuid>",
    completed=False
)
```

---

## Pattern 4: Добавить исполнителя (не заменить)

**Запрос:** «Назначь Ивана на задачу X»

```python
# ШАГ 1: найти UUID пользователя
users = list_users(workspace="main", verbosity="custom", include=["realName", "email"])
ivan_uuid = next(u["id"] for u in users["content"] if "Иван" in u.get("realName", ""))

# ШАГ 2: получить текущее assigned (replace-not-append!)
task = get_task(workspace="main", task_id="X", verbosity="compact")
current_assigned = task.get("assigned", [])

# ШАГ 3: обновить
update_task(workspace="main", task_id="X",
            assigned=[ivan_uuid] + current_assigned)
```

---

## Pattern 5: Поставить приоритет через стикер

**Запрос:** «Поставь приоритет High на задачу X»

```python
# UUID из briefing.md → Sticker shortcuts → Priority
update_task(
    workspace="main",
    task_id="X",
    stickers={"<priority_sticker_id>": "<high_state_id>"}
)
```

**Важно:** `stickers` — map полной замены. Если на задаче уже есть другие стикеры:
```python
task = get_task(workspace="main", task_id="X",
                verbosity="compact", include=["stickers"])
existing = task.get("stickers", {})
existing["<priority_sticker_id>"] = "<high_state_id>"
update_task(workspace="main", task_id="X", stickers=existing)
```

---

## Pattern 6: Создать подзадачу

**Запрос:** «Добавь подзадачу к X»

```python
# Шаг 1: создать задачу (без колонки — она будет subtask)
new_task = create_task(workspace="main", title="Подзадача Y")
new_uuid = new_task["id"]

# Шаг 2: прочитать текущие subtasks родителя
parent = get_task(workspace="main", task_id="X", verbosity="compact")
existing_subtasks = parent.get("subtasks", [])

# Шаг 3: добавить
update_task(workspace="main", task_id="X",
            subtasks=[new_uuid] + existing_subtasks)
```

---

## Pattern 7: Работа с чеклистом

**Запрос:** «Добавь пункт в чеклист задачи X»

```python
# Шаг 1: получить текущий чеклист
task = get_task(workspace="main", task_id="X",
                verbosity="full", include=["checklists"])
checklists = task.get("checklists", [])

# Шаг 2: мутировать (добавить пункт в первый чеклист)
if checklists:
    checklists[0]["items"].append({"title": "Новый пункт", "completed": False})

# Шаг 3: обновить
update_task(workspace="main", task_id="X", checklists=checklists)
```

---

## Pattern 8: Загрузить файл и прикрепить к задаче

**Запрос:** «Прикрепи файл /path/to/file.pdf к задаче X»

```python
# Шаг 1: загрузить
upload_result = upload_file(workspace="main", path="/path/to/file.pdf")
file_url = upload_result["url"]

# Шаг 2: embed в description или comment
task = get_task(workspace="main", task_id="X", verbosity="compact",
                include=["description"])
current_desc = task.get("description", "")
new_desc = current_desc + f'<br><a href="{file_url}">file.pdf</a>'
update_task(workspace="main", task_id="X", description=new_desc)
```

---

## Pattern 9: Массовое закрытие задач (с подтверждением)

**Запрос:** «Закрой все задачи в колонке Done»

```python
# Шаг 1: превью — ОБЯЗАТЕЛЬНО перед действием
tasks = list_tasks(workspace="main", column_id="<done_column_uuid>",
                   verbosity="custom", include=["title"], completed=False)
count = tasks["paging"]["totalCount"]
# Сообщи: «Найдено {count} незакрытых задач в Done. Закрыть все?»
# ↑ Дождись явного OK

# Шаг 2 (только после OK):
for task in tasks["content"]:
    update_task(workspace="main", task_id=task["id"], completed=True)
```

---

## Pattern 10: Найти задачу по тексту

**Запрос:** «Найди задачи про интеграцию»

```python
# YouGile не имеет full-text search в API.
# Вариант A: list_tasks + клиентский фильтр по title
tasks = list_tasks(workspace="main", verbosity="custom",
                   include=["title"])
matches = [t for t in tasks["content"]
           if "интеграц" in t.get("title", "").lower()]

# Вариант B: если tasks много — пагинация
# Вариант C: попроси пользователя уточнить project/board для сужения выборки
```

---

## Pattern 11: Webhook без firehose

**Запрос:** «Создай webhook на создание задач»

```python
create_webhook(
    workspace="main",
    url="https://...",
    events=["task-created"],
    filters={"projectId": "<project_uuid>"}  # ОБЯЗАТЕЛЬНО фильтр
)
```

Без `filters` webhook подпишется на **всю компанию** — это anti-pattern #6.

---

## Pattern 12: Работа с CRM-сделкой

**Запрос:** «Покажи сделки по клиенту ACME» (только CRM workspaces)

```python
# Routing: "клиент ACME" → workspace из routing rules
tasks = list_tasks(
    workspace="client_acme",
    verbosity="custom",
    include=["title", "deal", "assigned"]
)
# deal содержит сумму, статус, контакты
```

---

## Pattern 13: Распределение задач по статусам

**Запрос:** «Сколько задач в каждой колонке?»

```python
# verbosity=custom — только id, потом группируем по columnId
tasks = list_tasks(workspace="main", verbosity="custom",
                   include=["columnId"])
from collections import Counter
counts = Counter(t["columnId"] for t in tasks["content"])
# Затем resolve column names из briefing.md shortcuts
```

---

## Pattern 14: Установить дедлайн

**Запрос:** «Дедлайн через 3 дня»

```python
import time
now_ms = int(time.time() * 1000)
deadline_ms = now_ms + 3 * 24 * 60 * 60 * 1000

# Вариант A: хелпер (рекомендуется — авто-корректирует формат)
set_task_deadline(workspace="main", task_id="X", deadline_timestamp=deadline_ms)

# Вариант B: напрямую (не авто-корректирует)
update_task(workspace="main", task_id="X",
            deadline={"deadline": deadline_ms})
```

---

## Pattern 15: Проверить список workspaces

**Запрос:** «Какие workspaces доступны?»

```python
list_workspaces()
# Возвращает: slug, label, is_default для каждого настроенного workspace
# Не требует workspace параметр — читает env-конфигурацию MCP
```

Используй для проверки что workspace настроен, прежде чем сообщать пользователю
«такого workspace нет».
