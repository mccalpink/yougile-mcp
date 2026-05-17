# describe_response — Когда и как использовать

`describe_response` — read-only тул без API-вызовов. Работает со статической схемой.

---

## Когда вызывать

- Перед нестандартным запросом полей: «какой include-ключ для чеклистов?»
- Сомневаешься в структуре ответа конкретного DTO
- Пользователь спрашивает «что вернёт этот тул?»
- Нужно проверить актуальные quirks для entity

## Когда НЕ вызывать

- Стандартный CRUD (create/read/update/delete типичных объектов) — схема уже в tool-keys.md
- Когда уже знаешь нужные поля из briefing.md или предыдущего вызова в сессии

---

## Вызов без entity — обзор всех сущностей

```python
describe_response()
# или
describe_response(verbosity="compact")
```

Возвращает словарь entity → compact_fields count + optins list + предупреждения.
Используй чтобы понять: что вообще есть в API и что "тяжёлое".

---

## Вызов с entity — детальная схема

```python
describe_response(entity="task", verbosity="compact")
```

Возвращает:
- `fields` — список полей с типами, в каких verbosity уровнях присутствуют, include-ключи
- `quirks` — известные расхождения OpenAPI ↔ runtime для этой сущности
- `hints_in_compact` — список hint-ключей в `_hints` блоке

Поддерживаемые entity (case-insensitive):
`task`, `project`, `board`, `column`, `user`, `message`, `group_chat`, `sticker`, `webhook`

---

## Интерпретация поля `quirks` в ответе

```json
"quirks": [
  "SprintStickerState.begin/end: API stores seconds, not ms. MCP auto-converts.",
  "Stopwatch field name mismatch: schema says 'seconds/atMoment', runtime may differ"
]
```

Если quirk говорит «MCP auto-converts» — normalizer уже работает, `_meta.notes`
будет содержать запись о конвертации. Ничего дополнительно делать не нужно.

Если quirk говорит «TBD» или «may differ» — осторожно, поле нестабильно,
используй `get_task(include=["stopwatch"])` и проверяй реальные имена полей в ответе.

---

## Пример: нестандартный запрос полей

```
Пользователь: «Покажи задачи с трекингом времени»

1. Вызови describe_response(entity="task") — убедись в include-ключе
2. Результат: "time_tracking" → поле "timeTracking"
3. Вызов: list_tasks(workspace=..., verbosity="custom",
           include=["title", "time_tracking"])
```
