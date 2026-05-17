"""
MCP resource для шаблона персонального скилла YouGile.

Resource возвращает содержимое templates/yougile-personal-skill/SKILL.md —
шаблон для настройки персонального workflow агента.

Использование агентом: прочитать ресурс перед setup_yougile_skill,
чтобы понять структуру briefing.md до его создания.
"""
from pathlib import Path


# Путь к шаблону относительно корня репозитория MCP
_SKILL_TEMPLATE_PATH = Path(__file__).parents[4] / "templates" / "yougile-personal-skill" / "SKILL.md"


def get_skill_template_content() -> str:
    """
    Читает содержимое SKILL.md из templates/yougile-personal-skill/.

    Returns:
        Содержимое файла как строка, или описание ошибки если файл не найден.
    """
    try:
        return _SKILL_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            f"# Error: SKILL.md template not found\n\n"
            f"Expected at: `{_SKILL_TEMPLATE_PATH}`\n\n"
            f"Run `setup_yougile_skill` to initialize the skill, or manually copy "
            f"`templates/yougile-personal-skill/SKILL.md` to your skills directory."
        )
    except Exception as e:
        return f"# Error reading SKILL.md template\n\n{e}"
