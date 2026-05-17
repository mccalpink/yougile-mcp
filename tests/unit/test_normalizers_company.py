from src.utils.normalizers import normalize_company


def test_company_with_only_title_unchanged():
    """CompanyDto уже имеет title — не трогаем."""
    company = {"id": "uuid-1", "title": "My Company", "deleted": False}
    result = normalize_company(company)
    assert result["title"] == "My Company"


def test_company_with_only_name_adds_title():
    """CompanyListDtoBase имеет name — добавляем title = name."""
    company = {"id": "uuid-1", "name": "My Company", "deleted": False}
    result = normalize_company(company)
    assert result["title"] == "My Company"


def test_company_name_preserved_for_backward_compat():
    """Исходное name сохраняется для backward-compatibility."""
    company = {"id": "uuid-1", "name": "My Company", "deleted": False}
    result = normalize_company(company)
    assert result["name"] == "My Company"


def test_company_with_both_name_and_title_keeps_title():
    """Если оба поля есть — title приоритетнее."""
    company = {"id": "uuid-1", "name": "Name", "title": "Title", "deleted": False}
    result = normalize_company(company)
    assert result["title"] == "Title"


def test_normalize_company_list():
    """Нормализация списка компаний."""
    from src.utils.normalizers import normalize_company_list
    companies = [
        {"id": "1", "name": "A"},
        {"id": "2", "title": "B"},
    ]
    result = normalize_company_list(companies)
    assert result[0]["title"] == "A"
    assert result[1]["title"] == "B"


def test_company_no_name_no_title_returns_empty_title():
    """Если ни name, ни title нет — title = '' (не падаем)."""
    company = {"id": "uuid-1"}
    result = normalize_company(company)
    assert "title" in result
