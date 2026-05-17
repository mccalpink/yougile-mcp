# YouGile Custom Filters
<!-- Этот файл читается агентом при активации skill'а.
     Путь: ~/.agents/skills/yougile-personal/filters.md
     Агент предлагает добавить запись когда ты 2+ раза просишь одинаковую выборку.
     Формат записи: см. ниже. Добавляй новые в конец файла. -->

---

## Фильтр: просроченные задачи

- **Хук-фразы:** "просроченные", "что горит", "overdue", "горит", "дедлайн прошёл"
- **Workspace:** main
- **Что делает:** задачи с истёкшим дедлайном, не выполненные, не архивированные
- **Tool chain:**
  - `list_tasks(workspace="main", completed=False, archived=False)`
  - `verbosity="custom"`, `include=["title", "deadline", "assigned", "columnId"]`
  - Клиентский фильтр: `deadline.deadline < now_ms and deadline.deadline > 0`
- **Заметки:** API не поддерживает deadline_to фильтр — фильтрация на стороне клиента.
  Не работает для CRM-задач (deal-задачи не имеют обычного deadline).

---

## Фильтр: мои задачи сегодня

- **Хук-фразы:** "мои задачи", "что на мне", "что делаю сегодня", "мой список"
- **Workspace:** main
- **Что делает:** активные задачи назначенные на меня, с дедлайном сегодня или без
- **Tool chain:**
  - `list_tasks(workspace="main", assigned_to="<self_uuid>", completed=False)`
  - `verbosity="compact"`
- **Заметки:** self_uuid берётся из briefing.md → Self user IDs → main

---

<!-- Добавляй новые фильтры ниже этой строки -->
