"""Tests for the i18n foundation (issue #148, docs/10-stack-tecnologica-e-
estrutura-projeto.md §10.4.1, RF-I18N-01)."""

from pathlib import Path

from django.conf import settings

NATIONAL_LANGUAGE_CODES = ("umb", "kmb", "kon", "cjk", "kua")


def test_six_languages_are_configured():
    """Português + 5 línguas nacionais."""
    codes = {code for code, _label in settings.LANGUAGES}

    assert codes == {"pt", *NATIONAL_LANGUAGE_CODES}


def test_a_catalog_directory_exists_for_each_national_language():
    locale_dir = Path(settings.LOCALE_PATHS[0])

    for code in NATIONAL_LANGUAGE_CODES:
        catalog = locale_dir / code / "LC_MESSAGES" / "django.po"
        assert catalog.is_file(), f"missing catalog for {code}"
