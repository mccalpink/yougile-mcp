# API Quirks — Известные расхождения YouGile API

Подгружай при работе со стикерами, вебхуками, компаниями, или когда видишь
`_meta.notes` в ответе MCP.

---

## Quirk 1: SprintStickerState.begin/end — секунды, не ms

**Что увидишь:** `SprintStickerStateDto.begin` и `end` в ответе API — числа
порядка 1 748 217 600 (не 1 748 217 600 000).

**Что это значит:** API хранит даты спринта в **секундах** от Epoch, тогда как
все остальные timestamp в YouGile API — в **миллисекундах**.

**Как правильно:**
- MCP auto-converts: request ms→seconds (если > 10¹¹), response seconds→ms
- В `_meta.notes` появится: `"SprintStickerState.begin auto-converted from ms to seconds"`
- Тебе ничего делать не нужно — normalizer работает автоматически
- Если передаёшь напрямую через API без MCP normalizer — дели/умножай на 1000

```python
# Правильно (MCP автоматически конвертирует)
create_sprint_sticker_state(
    workspace="main",
    sticker_id="...",
    begin=1748217600000,  # ms — MCP сконвертирует в секунды
    end=1750809600000
)
```

---

## Quirk 2: Stopwatch — имена полей могут отличаться от схемы

**Что увидишь:** В OpenAPI схеме Stopwatch описан с полями `running`, `seconds`,
`atMoment`. В runtime пример TaskDto показывает `running`, `time`, `timestamp`.

**Что это значит:** Расхождение OpenAPI ↔ runtime. Реальные имена полей TBD
до прогона integration tests (`test_stopwatch_real_field_names.py`).

**Как правильно:**
- Получив задачу с секундомером (`_hints.has_stopwatch: true`), вызови
  `get_task(include=["stopwatch"])` и проверяй реальные ключи в ответе
- Не полагайся на имена из OpenAPI схемы для этого поля
- После прояснения — в `_meta.notes` будет запись если normalizer активирован

---

## Quirk 3: WebhookFilters.name — строка, не массив

**Что увидишь:** В OpenAPI `WebhookFilters.name` описан как `array[location]`.

**Что это значит:** Ошибка кодогенерации. Фактически это строковый enum.

**Как правильно:**
```python
# Правильно
create_webhook(filters={"name": "location", "value": [...]})

# НЕПРАВИЛЬНО (но MCP normalizer исправит)
create_webhook(filters={"name": ["location"], "value": [...]})
# → MCP возьмёт name[0], добавит в _meta.notes предупреждение
```

Если передашь массив из 2+ элементов — MCP вернёт ошибку с ясным текстом.

---

## Quirk 4: Company name — `name` vs `title`

**Что увидишь:** `CompanyListDtoBase` использует поле `name`, `CompanyDto` — `title`.
Два разных имени для одного и того же поля в двух DTO.

**Что это значит:** Расхождение внутри API между list и get ответами.

**Как правильно:**
- MCP нормализует: всегда возвращает `title` как каноническое имя
- Исходное `name` сохраняется для backward-compat
- Прозрачно — `_meta.notes` не пишем

---

## Дополнительные расхождения (из _ANALYSIS.md §7)

| # | Место | Расхождение | Как обрабатывать |
|---|---|---|---|
| 1 | `GET /tasks/{id}/chat-subscribers` | Response schema = none в OpenAPI | MCP возвращает список подписчиков — доверяй ответу |
| 2 | `GET /webhooks` | Schema = одиночный объект, фактически список | MCP нормализует в список |
| 3 | `Deadline.history` | `array[string]` без описания формата | Используй только для просмотра, не парси |
| 4 | `CheckList.items` | `allOf: [CheckListItem]` вместо `array` | Трактуй как array[CheckListItem] |
| 5 | `StringStickerWithStatesDto.limit/offset` | Параметры запроса в response DTO | Игнорируй эти поля в ответе |
| 6 | `TaskPermissionsDto` enum values | Тип `string`, значения не описаны | Используй `describe_response(entity="project")` для актуального списка |

---

## Когда появляется `_meta.notes`

`_meta.notes` — сигнал что MCP auto-heal normalizer что-то поправил:

```json
"_meta": {
  "notes": [
    "SprintStickerState.begin auto-converted from ms to seconds (value was 1748217600000)",
    "WebhookFilters.name auto-corrected: array coerced to string 'location'"
  ]
}
```

При виде этого поля: normalizer сработал корректно, данные в ответе уже в правильном
формате. Логируй для отладки, но не блокируй на этом операцию.
