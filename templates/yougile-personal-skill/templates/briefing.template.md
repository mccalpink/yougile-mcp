# YouGile Personal Briefing
<!-- Этот файл генерируется через setup_yougile_skill или заполняется вручную.
     Путь установки: ~/.agents/skills/yougile-personal/briefing.md
     Агент читает его при каждой активации skill'а.
     Инструкция по заполнению: в каждой секции есть комментарии <!-- FILL -->. -->

---

## Компании (Workspaces)

<!-- FILL: одна строка на каждый YOUGILE_KEY_<SLUG> в конфиге MCP.
     role: owner | admin | member
     sprints: true | false (есть ли sprint-стикеры в компании)
     CRM: true | false (используете ли CRM-функции YouGile) -->

| slug | label | role | sprints | CRM | notes |
|---|---|---|---|---|---|
| `main` | Личная компания | owner | false | false | |
| `team` | Команда X | member | true | false | |

**Default workspace:** `main`

---

## 🔴 Routing rules (КРИТИЧНО)

<!-- FILL: без этой секции агент будет переспрашивать workspace на каждый запрос.
     Формат: конкретные слова/фразы → slug. НЕ общие описания — конкретные паттерны.
     Примеры ниже — отредактируй под себя. -->

- **Default:** `main` — если явно не указано другое
- **"клиент ACME", "для ACME", "по ACME"** → `client_acme`
- **"в команде", "команда", "team", "рабочее"** → `team`
- **"лично", "себе", "личный проект", "мои задачи"** → `main`
- **Explicit slug в сообщении** ("в main", "workspace team") → используй этот slug
- **Ambiguous** → используй `main`, скажи какой workspace выбрал

---

## Проекты (Project shortcuts)

<!-- FILL: один блок на каждый регулярно используемый проект.
     UUID получи через list_projects / list_boards / list_columns.
     Columns: запиши только те 2-4 колонки, которые нужны в автоматизациях. -->

### `main` / Личные задачи

- aliases: задачи, мои задачи, личные
- `project_id`: `REPLACE_WITH_UUID`
- `board_id`: `REPLACE_WITH_UUID`
- columns:
  - `inbox`: `REPLACE_WITH_UUID`
  - `in_progress`: `REPLACE_WITH_UUID`
  - `done`: `REPLACE_WITH_UUID`

### `team` / Разработка

- aliases: разработка, dev, команда
- `project_id`: `REPLACE_WITH_UUID`
- `board_id`: `REPLACE_WITH_UUID`
- columns:
  - `inbox`: `REPLACE_WITH_UUID`
  - `in_progress`: `REPLACE_WITH_UUID`
  - `done`: `REPLACE_WITH_UUID`
  - `blocked`: `REPLACE_WITH_UUID`

---

## Self user IDs

<!-- FILL: UUID пользователя (тебя) в каждом workspace.
     Один аккаунт → разные UUID в разных компаниях.
     Получи через list_users(workspace=...) → найди себя по email. -->

| workspace | self user_id |
|---|---|
| `main` | `REPLACE_WITH_UUID` |
| `team` | `REPLACE_WITH_UUID` |

---

## Стикеры (Sticker shortcuts)

<!-- FILL: только стикеры, которые используешь в автоматизациях.
     Если стикеры не нужны — удели всю секцию.
     sticker_id: из list_sprint_stickers / list_string_stickers
     state UUIDs: из get_sprint_sticker / get_string_sticker -->

### Priority

- `sticker_id`: `REPLACE_WITH_UUID`
- workspaces: main, team
- states:
  - `low`: `REPLACE_WITH_UUID`
  - `medium`: `REPLACE_WITH_UUID`
  - `high`: `REPLACE_WITH_UUID`
  - `urgent`: `REPLACE_WITH_UUID`

### Sprint (только если sprints: true)

- `sticker_id`: `REPLACE_WITH_UUID`
- текущий спринт: `REPLACE_WITH_UUID` <!-- Обновляй вручную при смене спринта -->
- предыдущий спринт: `REPLACE_WITH_UUID`

---

## Особенности воркфлоу

<!-- FILL: опциональная секция — заполни если есть нестандартные правила -->

- Описания задач: HTML (не Markdown)
- Временная зона для дедлайнов: Europe/Moscow
- Порог массовых операций: 5 (спрашивать OK при > 5 объектах)
- CRM включён только в workspace: `client_acme`

---

## Когда обновлять этот файл

- При добавлении нового workspace (новый YOUGILE_KEY_*)
- При реструктуризации проектов/досок (UUID изменились → 404)
- При смене текущего спринта (обновить Sprint → текущий спринт)
- При изменении routing rules (добавили нового клиента)
