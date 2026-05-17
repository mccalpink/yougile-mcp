# YouGile MCP — Tool Keys Reference

Справочник параметров для read-тулов (`list_*`, `get_*`).
Подгружай когда нужно уточнить параметр, include-ключ, формат значения.

---

## Общие параметры (все list_* и get_* тулы)

| Параметр | Тип | Default | Описание |
|---|---|---|---|
| `workspace` | string \| None | None | Slug из таблицы workspaces. **Опционален** — тул использует session active или 'default'. Передавай явно только при override. |
| `verbosity` | "custom"\|"compact"\|"full" | "compact" | Уровень детализации ответа |
| `include` | list[str] \| None | None | Дополнительные поля через opt-in ключи |
| `limit` | int | 20 | Размер страницы (max зависит от тула) |
| `offset` | int | 0 | Смещение для пагинации |

---

## Verbosity уровни

### `custom`
Возвращает **только `id`**. Любые другие поля — явно через `include[]`.
Юзкейс: агрегации, подсчёты — не нужны все поля, только конкретные.

```python
list_tasks(workspace="main", verbosity="custom", include=["title", "completed"])
# → {"id": "...", "title": "...", "completed": false}
```

### `compact` (default)
Core-поля + ISO timestamps + `_hints` о скрытых непустых полях.
Экономит ~60-70% контекста по сравнению с full.

### `full`
Все поля DTO кроме opt-in (history, raw timestamps ms).
Используй только когда реально нужен полный объект.

---

## Include-ключи (opt-in поля)

| Ключ | Поле в DTO | DTO | Когда нужен |
|---|---|---|---|
| `description` | `description` | TaskDto | Полный текст задачи (HTML) |
| `checklists` | `checklists` | TaskDto | Работа с чеклистами |
| `stickers` | `stickers` | TaskDto | Кастомные поля задачи |
| `extension_data` | `extensionData` | TaskDto | Данные интеграций |
| `stopwatch` | `stopwatch` | TaskDto | Секундомер задачи |
| `timer` | `timer` | TaskDto | Таймер задачи |
| `time_tracking` | `timeTracking` | TaskDto | Трекинг времени |
| `deal` | `deal` | TaskDto | CRM-сделка (только CRM workspaces) |
| `deadline_history` | `deadline.history` | TaskDto | Аудит изменений дедлайна |
| `timestamps` | `timestamp`, `archivedTimestamp`, `completedTimestamp` | TaskDto | Raw ms epoch (обычно не нужны — есть ISO в compact) |
| `permissions` | `permissions` | ProjectRoleDto | Полный граф прав роли |
| `sprint_states` | `states` | SprintStickerWithStatesDto | История спринтов |
| `string_states` | `states` | StringStickerWithStatesDto | Все варианты строкового стикера |
| `chat_maps` | `userRoleMap` + `roleConfigMap` | GroupChatDto | Конфигурация ролей чата |
| `crm_fields` | `fields` | ContactPersonEntryDto | Кастомные поля CRM-контакта |
| `all` | Все opt-in поля | — | Полный dump (аналог full++) |

---

## `_hints` в compact list_* ответах

В compact режиме для `list_*` тулов каждый объект содержит `_hints` — сигналы
о скрытых непустых полях. Используй чтобы решить: нужен ли доп. вызов.

```json
"_hints": {
  "has_description": true,
  "has_checklists": false,
  "has_deadline": true,
  "has_extension_data": false,
  "has_stickers": true,
  "has_stopwatch": false,
  "has_timer": false
}
```

Паттерн: `has_description: true` → вызови `get_task(include=["description"])` для
этой конкретной задачи, не для всего списка.

---

## `_meta` в ответах

```json
"_meta": {
  "verbosity": "compact",
  "omitted_fields": ["createdBy", "extensionData", "timestamp"],
  "unknown_includes": ["foo_bar"],
  "notes": ["SprintStickerState.begin auto-converted from ms to seconds"]
}
```

| Поле | Когда присутствует |
|---|---|
| `verbosity` | Всегда |
| `omitted_fields` | Только если что-то реально опущено |
| `unknown_includes` | Только при нераспознанном include-ключе (не ошибка) |
| `notes` | Только если сработал auto-heal normalizer |

---

## Параметры фильтрации (list_tasks)

| Параметр | Тип | Описание |
|---|---|---|
| `column_id` | str \| None | Фильтр по колонке |
| `assigned_to` | str \| None | UUID пользователя |
| `completed` | bool \| None | Статус выполнения |
| `archived` | bool \| None | Статус архивирования |
| `deleted` | bool \| None | Мягкое удаление |

**Важно:** API не поддерживает `deadline_to` напрямую. Фильтрацию по дедлайну
делай на стороне клиента: `list_tasks(verbosity="custom", include=["deadline"])` →
фильтруй `deadline.deadline < now_ms`.

---

## Timestamp форматы

- **compact ответы:** `createdAt`, `completedAt`, `archivedAt` — ISO-8601 строки (`"2026-05-17T15:00:00Z"`)
- **full ответы и include=["timestamps"]:** `timestamp`, `completedTimestamp`, `archivedTimestamp` — ms epoch (integer)
- **Запросы (deadline, startDate):** всегда ms epoch
- **SprintStickerState.begin/end:** **секунды** (не ms) — quirk API, см. quirks.md

---

## Session management

### set_active_workspace

| Поле | Значение |
|---|---|
| Когда | Старт сессии или явная смена компании пользователем |
| Параметры | `slug: str` — slug из настроенных workspaces |
| Возвращает | `active_workspace`, `available_workspaces`, или `error` если slug не найден |

### get_active_workspace

| Поле | Значение |
|---|---|
| Когда | Проверить какой workspace активен, до серии операций |
| Параметры | нет |
| Возвращает | `active_workspace` (null если не установлен), `effective_workspace`, `available_workspaces` |
