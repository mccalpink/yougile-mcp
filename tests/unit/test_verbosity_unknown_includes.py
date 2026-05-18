"""Spec §1.3: неизвестные include[] ключи должны попадать в
``_meta.unknown_includes`` на всех формах ответа, где есть место для _meta.

Закрывает review-fixes M4 + N15:
- full + single dict: было — _unknown собирался но терялся
- full + bare list: было — bare list не обрабатывался вообще
- custom + bare list: было — all_unknown_list собирался но терялся
"""
from src.utils.verbosity import apply_verbosity


# ---------- verbosity="full" ----------


def test_full_single_dict_unknown_include_lands_in_meta():
    """M4: full + single dict + неизвестный include → _meta.unknown_includes."""
    raw = {"id": "uuid", "title": "x"}
    result = apply_verbosity(raw, "task", verbosity="full", include=["nope_field"])
    assert "_meta" in result
    assert result["_meta"]["verbosity"] == "full"
    assert "nope_field" in result["_meta"]["unknown_includes"]


def test_full_single_dict_known_include_no_meta():
    """full + single dict + валидный include → _meta НЕ добавляется."""
    raw = {"id": "uuid", "title": "x", "description": "<p>x</p>"}
    result = apply_verbosity(raw, "task", verbosity="full", include=["description"])
    assert "_meta" not in result  # ничего необычного — _meta не нужен


def test_full_bare_list_applies_includes_without_meta():
    """M4: full + bare list — include применяется к items, _meta некуда добавить."""
    raw = [
        {"id": "u1", "title": "x", "description": "<p>x</p>"},
        {"id": "u2", "title": "y", "description": "<p>y</p>"},
    ]
    result = apply_verbosity(raw, "task", verbosity="full", include=["description"])
    assert isinstance(result, list)
    assert len(result) == 2
    # include применился к каждому item
    assert result[0]["description"] == "<p>x</p>"
    assert result[1]["description"] == "<p>y</p>"


def test_full_paging_unknown_include_lands_in_meta():
    """full + paging envelope + неизвестный include → _meta.unknown_includes."""
    raw = {
        "paging": {"totalCount": 1, "offset": 0, "limit": 20},
        "content": [{"id": "uuid", "title": "x"}],
    }
    result = apply_verbosity(
        raw, "task", verbosity="full", include=["nope_field"], is_list=True
    )
    assert "_meta" in result
    assert "nope_field" in result["_meta"]["unknown_includes"]


# ---------- verbosity="custom" ----------


def test_custom_single_dict_unknown_include_lands_in_meta():
    raw = {"id": "uuid", "title": "x"}
    result = apply_verbosity(
        raw, "task", verbosity="custom", include=["nope_field"]
    )
    assert "_meta" in result
    assert "nope_field" in result["_meta"]["unknown_includes"]


def test_custom_bare_list_no_meta_but_does_not_raise():
    """N15: custom + bare list + unknown — не падает, items обработаны,
    unknown_includes теряется (некуда положить — bare list нет _meta)."""
    raw = [{"id": "u1", "title": "x"}, {"id": "u2", "title": "y"}]
    result = apply_verbosity(
        raw, "task", verbosity="custom", include=["nope_field"]
    )
    assert isinstance(result, list)
    assert len(result) == 2
    # В custom only id остаётся
    assert result[0] == {"id": "u1"}
    assert result[1] == {"id": "u2"}
