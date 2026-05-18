"""
Нормализаторы для API quirks YouGile.

Каждая функция исправляет конкретное расхождение между OpenAPI-схемой
и реальным поведением API. Все нормализаторы идемпотентны — повторный
вызов с уже нормализованными данными не изменяет результат.

Используется в:
- sticker_tools.py — normalize_sprint_sticker_state
- webhook_tools.py — normalize_webhook_filters
- auth_tools.py    — normalize_company
- apply_verbosity  — при наличии stopwatch-поля в ответе (placeholder)
"""
from __future__ import annotations

from ..core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Quirk 1: SprintStickerState — ms vs seconds
# ---------------------------------------------------------------------------

MS_THRESHOLD = 10 ** 11  # значение > порога — выглядит как миллисекунды


def normalize_sprint_sticker_state(state: dict, direction: str) -> dict:
    """
    Нормализует begin/end в SprintStickerStateDto.

    YouGile хранит begin/end в секундах, хотя все остальные временны́е поля API — мс.
    Источник: dto_map/_ANALYSIS.md §7, п. 9.

    Args:
        state: Словарь с полями begin, end и другими полями состояния стикера.
        direction: "request" — агент→API (конвертируем ms в seconds если нужно);
                   "response" — API→агент (всегда конвертируем seconds в ms).

    Returns:
        Нормализованный словарь. При конвертации request→API добавляет _meta.notes.
    """
    result = dict(state)
    converted = False

    if direction == "request":
        for field in ("begin", "end"):
            val = result.get(field)
            if val is not None and val > MS_THRESHOLD:
                result[field] = val // 1000
                converted = True
        if converted:
            meta = result.setdefault("_meta", {})
            notes = meta.setdefault("notes", [])
            notes.append(
                "SprintStickerState.begin/end auto-converted from ms to seconds "
                f"(value was {state.get('begin')})"
            )

    elif direction == "response":
        # M5: идемпотентность через threshold. Без неё повторный вызов
        # умножал бы уже-ms значение ещё на 1000 (год становился ×1000).
        for field in ("begin", "end"):
            val = result.get(field)
            if val is not None and val < MS_THRESHOLD:
                result[field] = val * 1000

    else:
        raise ValueError(
            f"Unknown direction: {direction!r}. Expected 'request' or 'response'."
        )

    return result


# ---------------------------------------------------------------------------
# Quirk 3: WebhookFilters.name — array vs string
# ---------------------------------------------------------------------------


def normalize_webhook_filters(
    filters: list,
) -> tuple[list, dict]:
    """
    Нормализует WebhookFilters.name — исправляет ошибку кодогенерации OpenAPI.

    Источник: dto_map/_ANALYSIS.md §7, п. 7.
    OpenAPI описывает name как array[location], фактически это строковый enum.

    Args:
        filters: Список объектов WebhookFilter.

    Returns:
        Кортеж (нормализованный список фильтров, meta_dict).
        meta_dict содержит ключ "notes" если была произведена автокоррекция.

    Raises:
        ValidationError: Если name — массив из более чем одного элемента.
    """
    result = []
    notes = []

    for item in filters:
        item = dict(item)
        name = item.get("name")

        if isinstance(name, list):
            if len(name) > 1:
                raise ValidationError(
                    f"WebhookFilters.name cannot be an array with multiple elements. "
                    f"Got {name!r}. YouGile API expects a single string value "
                    f"(e.g. 'location', 'title', 'chat_message').",
                    field="filters.name",
                )
            elif len(name) == 1:
                item["name"] = name[0]
                notes.append(
                    f"WebhookFilters.name auto-corrected: array coerced to string {name[0]!r}"
                )
            # len == 0: оставляем как есть, пусть API вернёт ошибку
        result.append(item)

    meta = {"notes": notes} if notes else {}
    return result, meta


# ---------------------------------------------------------------------------
# Quirk 4: Company — name vs title
# ---------------------------------------------------------------------------


def normalize_company(company: dict) -> dict:
    """
    Выравнивает название компании в единое поле title.

    Источник: dto_map/_ANALYSIS.md §7, п. 8.
    CompanyListDtoBase использует 'name', CompanyDto — 'title'.
    На нашей стороне канонический ключ — title.
    Исходный 'name' сохраняется для backward-compatibility.

    Args:
        company: Словарь одной компании из API.

    Returns:
        Компания с гарантированным полем 'title'.
    """
    result = dict(company)
    if "title" not in result or not result["title"]:
        result["title"] = result.get("name", "")
    return result


def normalize_company_list(companies: list) -> list:
    """
    Нормализует список компаний — применяет normalize_company к каждому элементу.

    Args:
        companies: Список словарей компаний из API.

    Returns:
        Список нормализованных компаний.
    """
    return [normalize_company(c) for c in companies]


# ---------------------------------------------------------------------------
# Quirk 2: Stopwatch — TBD placeholder
# ---------------------------------------------------------------------------

_STOPWATCH_WARNING = (
    "Stopwatch field name mismatch: OpenAPI schema says {running, seconds, atMoment}, "
    "but runtime may expose {running, time, timestamp}. "
    "Field names unverified — see TODO in tests/integration/test_stopwatch_real_field_names.py."
)


def normalize_stopwatch_warning(task: dict) -> dict:
    """
    Заглушка нормализатора для Stopwatch quirk.

    TODO: После прогона tests/integration/test_stopwatch_real_field_names.py
    и фиксации реальных имён полей — заменить на полноценный нормализатор или убрать
    предупреждение если поля совпадают с OpenAPI.

    Источник: dto_map/_ANALYSIS.md §7, п. 5.

    Args:
        task: Словарь задачи из API.

    Returns:
        Задача с предупреждением в _meta.notes если присутствует поле stopwatch.
    """
    if "stopwatch" not in task or task["stopwatch"] is None:
        return task

    result = dict(task)
    meta = result.setdefault("_meta", {})
    notes = meta.setdefault("notes", [])

    # Не дублируем предупреждение при повторном вызове
    if not any("stopwatch" in n.lower() and "mismatch" in n.lower() for n in notes):
        notes.append(_STOPWATCH_WARNING)

    return result
