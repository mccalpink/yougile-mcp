---
name: yougile-personal
description: >
  Персональный workflow-контекст для YouGile MCP.
  Активируется при любой операции с YouGile — создание/обновление/закрытие задач,
  просмотр проектов/досок/колонок, работа со спринтами, CRM-сделками, чатами задач.
  Триггеры на русские фразы: "задача", "канбан", "доска", "колонка", "проект",
  "спринт", "дедлайн", "сделка", "клиент", "горит", "просроченные".
  Слэш-команды: /yougile /задача /спринт.
  НЕ активировать для общих вопросов о project management без реальных операций с данными.
---

# YouGile — Personal Workflow Skill

Этот skill сообщает ассистенту: какие workspace'ы настроены, где обычно работает
пользователь, какие UUID проектов/досок/колонок кэшированы (без лишних round-trip
вызовов), и какие паттерны предпочитает пользователь.

Инструменты MCP: `yougile_*` (например, `yougile_list_projects`, `yougile_create_task`).
Каждый тул принимает `workspace` — slug из таблицы ниже. Передавай явно, даже если
воркспейс один.

---

## Алгоритм при активации (выполнять по порядку)

1. **Прочитай `briefing.md`** — путь: `~/.agents/skills/yougile-personal/briefing.md`
   (или `$YOUGILE_USER_MEMORY_DIR/briefing.md` если переменная задана).
   Из него берёшь: routing rules, UUID-кэш, workspace slugs.
   **Если файл не существует** → предложи: «Хотите настроить персональный брифинг?
   Я задам 5 вопросов.» Шаблон: `templates/briefing.template.md`.

2. **Прочитай `filters.md`** — тот же каталог. Именованные фильтры пользователя.
   Если файл отсутствует — пропусти (не обязателен).

3. **Подгружай references/** по необходимости (не все сразу):
   - Нестандартный набор полей → `references/describe-response.md`
   - Стикеры, вебхуки, компании → `references/quirks.md`
   - Неочевидный tool chain → `references/common-patterns.md`
   - Работа с фильтрами / сохранение фильтра → `references/custom-filters.md`
   - Параметры тулов, include-ключи → `references/tool-keys.md`

4. **Если пользователь 2+ раз просит одинаковую нестандартную выборку** →
   предложи сохранить в `filters.md` по шаблону `templates/filters.template.md`.

---

## Workspaces

<!-- Заполни после запуска setup_yougile_skill или вручную -->

| slug | label | role | sprints | CRM | notes |
|---|---|---|---|---|---|
| `{{SLUG_1}}` | {{LABEL_1}} | {{ROLE_1}} | false | false | |
| `{{SLUG_2}}` | {{LABEL_2}} | {{ROLE_2}} | false | false | |

**Default workspace:** `{{DEFAULT_SLUG}}`

---

## Routing rules (КРИТИЧНО — читай первым)

Без этой секции агент будет переспрашивать workspace на каждый запрос.

<!-- Заполни конкретными паттернами — не общими словами -->

- **Default:** `{{DEFAULT_SLUG}}` — если явно не указано другое
- **"клиент {{CLIENT_NAME}}", "для {{CLIENT_NAME}}", "по {{CLIENT_NAME}}"** → `{{CLIENT_SLUG}}`
- **"в команде", "команда", "team"** → `{{TEAM_SLUG}}`
- **"лично", "себе", "личный проект", "мои задачи"** → `{{PERSONAL_SLUG}}`
- **Explicit slug в сообщении** ("в main", "workspace team") → используй этот slug
- **Ambiguous** → используй default, **явно скажи** какой workspace выбрал, чтобы пользователь мог поправить

---

## Project / board / column shortcuts

Когда пользователь называет проект словами — маппируй на UUID ниже.
Пропускаешь цепочку `list_projects` → `list_boards` → `list_columns`.
Если UUID вернул 404 — перечитай через API и сообщи пользователю что нужно обновить.

<!-- Один блок на каждый регулярно используемый проект -->

### `{{SLUG_1}}` / {{PROJECT_NAME_1}}

- aliases: {{ALIAS_1A}}, {{ALIAS_1B}}
- `project_id`: `{{UUID}}`
- `board_id`: `{{UUID}}`
- columns:
  - `inbox`: `{{UUID}}`
  - `in_progress`: `{{UUID}}`
  - `done`: `{{UUID}}`

### `{{SLUG_2}}` / {{PROJECT_NAME_2}}

- aliases: {{ALIAS_2A}}
- `project_id`: `{{UUID}}`
- `board_id`: `{{UUID}}`
- columns:
  - `inbox`: `{{UUID}}`
  - `done`: `{{UUID}}`

---

## Sticker shortcuts

YouGile stickers — кастомные поля компании. Установка значения на задаче требует
двух UUID: sticker_id + state_id. Кэш ниже экономит N+1 вызовы (rate limit 50/min).

<!-- Заполни только используемые в автоматизациях стикеры -->

### Priority

- `sticker_id`: `{{UUID}}`
- workspaces: {{SLUG_LIST}}
- states: `low`: `{{UUID}}` | `medium`: `{{UUID}}` | `high`: `{{UUID}}` | `urgent`: `{{UUID}}`

### Sprint (только если sprints_enabled)

- `sticker_id`: `{{UUID}}`
- текущий спринт: `{{STATE_UUID}}` (обновлять вручную или через `yougile_get_sprint_sticker`)

---

## Self user IDs

Для «мои задачи» / «назначь на меня» — UUID пользователя разный в каждой компании.

| workspace | self user_id |
|---|---|
| `{{SLUG_1}}` | `{{UUID}}` |
| `{{SLUG_2}}` | `{{UUID}}` |

---

## Operational rules (всегда)

1. **Show before mutate при высоких ставках.** Перед `deleted=True`, `remove_user`,
   массовой операцией (> 5 объектов) — объяви что собираешься делать, жди OK.
   «Я найду 17 задач и заархивирую» — это **превью**, не действие.

2. **Replace-not-append для массивов.** `assigned`, `subtasks`, `stickers`, `checklists` —
   поля полной замены. Алгоритм: `get_task` → мутируй массив → передай полный массив
   в `update_task`. Никогда не отправляй одноэлементный массив в надежде на merge.

3. **HTML, не Markdown, не plain text.** YouGile рендерит описания и комментарии как HTML.
   `<br>` вместо `\n`, `<b>`/`<i>` вместо `**`/`*`, `<a href="">` для ссылок.

4. **Миллисекунды для timestamp.** `deadline.deadline`, sticker timestamps — всегда ms.
   SprintStickerState.begin/end — исключение: API хранит **секунды** (quirk, см. quirks.md).

5. **Workspace передавай явно.** Даже если один workspace — пиши `workspace="slug"`.

6. **Confirm destination при создании.** При создании задачи скажи:
   «Помещу в {{column}} на доске {{board}} проекта {{project}} ({{workspace}}).»

---

## Per-workspace flags

<!-- Обнови после setup_yougile_skill -->

- `crm_enabled`: если false — не предлагай CRM-операции в этом workspace
- `sprints_enabled`: если false — не ищи sprint-стикеры в списках задач
- `mass_op_threshold`: порог подтверждения массовых операций (default: 5)

---

## Cheat-sheet (типичные запросы → tool chain)

| Пользователь говорит | Tool chain |
|---|---|
| «Создай задачу X» | `create_task(workspace=default, title=X, column_id=cached.inbox, description=html)`. Скажи куда кладёшь. |
| «Создай задачу X в проекте Y» | UUID из shortcuts выше. Если нет — `list_projects` + fuzzy, спроси при ambiguity. |
| «Покажи мои задачи на сегодня» | `list_tasks(workspace, assigned_to=self_uuid, verbosity="custom", include=["title","deadline","columnId"])` + фильтр по deadline |
| «Что горит» / «просроченные» | Именованный фильтр из `filters.md` если есть. Иначе: `list_tasks(completed=false)`, клиентский фильтр `deadline.deadline < now_ms` |
| «Отметь X как сделано» | `update_task(task_id=X, completed=true)`. Перемести в done-колонку только если есть конвенция. |
| «Дедлайн через N дней» | `set_task_deadline(task_id, deadline=now_ms + N*86400000)` |
| «Назначь на Иван» | `list_users` → найди по realName → `get_task` → `update_task(assigned=[ivan_uuid, *existing])` |
| «Создай подзадачу» | `create_task` (без column_id) → `get_task(parent)` → `update_task(parent, subtasks=[new, *existing])` |
| «Прокомментируй задачу X» | `add_task_comment(task_id=X, comment="<p>...</p>")` |
| «Поставь приоритет High» | Sticker UUID из shortcuts → `update_task(stickers={priority_id: high_state_id})` |
| «Что сделал вчера» | `list_tasks(assigned_to=self, completed=true)` + фильтр по completedAt |
| «Удали задачу X» | **Confirm first.** `update_task(deleted=true)`. Упомяни что soft-delete, обратимо. |
| «Загрузи файл к задаче» | `upload_file(path="/abs/path")` → url → embed в description или comment |
| «Задачи по клиенту ACME» | routing → client_acme workspace (из briefing), не переспрашивай |
| «Поставь стикер Sprint» | `sticker_id` + текущий `STATE_UUID` из shortcuts → `update_task(stickers={...})` |

---

## Anti-patterns (запрещено)

1. Молча выбирать workspace при неоднозначном запросе — всегда говори какой выбрал.
2. Использовать plain newlines в description/комментариях — только HTML.
3. Передавать timestamps в секундах — только ms (кроме SprintStickerState, см. quirks.md).
4. Отправлять `assigned`/`subtasks`/`stickers`/`checklists` без чтения текущего состояния.
5. Редактировать текст чат-сообщения через `update_chat_message` — API запрещает (только label/react/delete). Объясни пользователю.
6. Создавать webhook без `filters` — станет firehose на всю компанию.
7. Массово архивировать/удалять без явного OK пользователя.
8. Вызывать `decode_task_stickers` для задач с > 3 стикерами без кэша — N+1 проблема.
9. Предлагать CRM-операции в workspace с `crm_enabled=false`.
10. Молча повторять запрос на 429 — rate limit 50 req/min, сообщи пользователю.

---

## References index

Подгружай по необходимости — не все сразу:

| Файл | Когда читать |
|---|---|
| `references/tool-keys.md` | Нужен параметр тула, include-ключ, формат значения |
| `references/describe-response.md` | Перед нестандартным запросом полей; когда сомневаешься какие поля вернёт тул |
| `references/common-patterns.md` | Сложная tool-chain, нет уверенности в порядке вызовов |
| `references/custom-filters.md` | Пользователь 2+ раз просит одинаковую выборку; работа с `filters.md` |
| `references/quirks.md` | Стикеры/спринты (ms vs sec), вебхуки, компании; видишь `_meta.notes` в ответе |
