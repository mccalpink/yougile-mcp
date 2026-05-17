# yougile-personal — SKILL Template

Шаблон персонального skill'а для YouGile MCP.
Для разработчика и продвинутого пользователя — не для агента.

---

## Что это

Папка содержит SKILL.md и вспомогательные файлы для personalizing YouGile workflow.

- **SKILL.md** — главный файл, загружается Claude Code как skill context
- **references/** — справочники, подгружаются агентом по необходимости
- **templates/** — шаблоны для пользовательских файлов (briefing.md, filters.md)

Пользовательские данные (briefing.md, filters.md) хранятся в `~/.agents/skills/yougile-personal/`
— вне репозитория. SKILL.md — шаблон в репозитории.

---

## Быстрый старт

### 1. MCP сервер уже запущен?

Проверь что `yougile-mcp` настроен в Claude Code:
```bash
claude mcp list
# или
cat ~/.claude.json | grep yougile
```

### 2. Первый запуск — setup через тул

В Claude Code запроси:
```
запусти setup_yougile_skill
```

Или прочитай шаблон напрямую через MCP resource:
```
yougile://skill-template
```

### 3. Ручная установка SKILL.md

```bash
# Копировать SKILL.md в директорию skill'а
cp templates/yougile-personal-skill/SKILL.md \
   ~/.agents/skills/yougile-personal/SKILL.md

# Убедиться что симлинки работают
ls -la ~/.claude/skills/yougile-personal/
ls -la ~/.claude-work/skills/yougile-personal/
```

### 4. Заполнить briefing.md

```bash
cp templates/yougile-personal-skill/templates/briefing.template.md \
   ~/.agents/skills/yougile-personal/briefing.md
# Отредактируй — замени все REPLACE_WITH_UUID реальными значениями
```

UUID проектов, досок, колонок — из тулов `list_projects`, `list_boards`, `list_columns`.

---

## Структура папки

```
templates/yougile-personal-skill/
├── SKILL.md                      # Главный skill файл (≤250 строк)
├── README.md                     # Этот файл
├── references/
│   ├── tool-keys.md              # Параметры read-тулов, include-ключи
│   ├── describe-response.md      # Когда/как использовать describe_response
│   ├── common-patterns.md        # 15 паттернов tool chains
│   ├── custom-filters.md         # Система именованных фильтров
│   └── quirks.md                 # API gotchas (ms vs sec, field mismatches)
└── templates/
    ├── briefing.template.md      # Шаблон персонального briefing.md
    └── filters.template.md       # Шаблон файла именованных фильтров
```

---

## Когда обновлять SKILL.md

- При добавлении новых тулов в MCP (новые паттерны → common-patterns.md)
- При обнаружении нового API quirk (→ quirks.md)
- При изменении verbosity API (новые include-ключи → tool-keys.md)
- После прогона eval-viewer и выявлении проблем с routing/anti-patterns

После изменения SKILL.md — скопируй в установленную директорию:
```bash
cp templates/yougile-personal-skill/SKILL.md \
   ~/.agents/skills/yougile-personal/SKILL.md
```

---

## Eval-viewer тестирование

Для тестирования SKILL через side-by-side сравнение — см. `evals/` директорию
и `scripts/run_skill_eval.sh` (или Phase VII плана реализации).
