"""Localized labels and dates used by exported documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

__all__ = ["ExportLabels", "export_labels", "format_lesson_date", "primary_language"]


@dataclass(frozen=True, slots=True)
class ExportLabels:
    """The human-readable labels one exported document needs."""

    recordings: str
    duration: str
    reference_documents: str
    pages: str
    glossary: str
    generated_notice: str
    page_abbreviation: str


_LABELS_BY_LANGUAGE = {
    "en": ExportLabels(
        recordings="Recordings",
        duration="Duration",
        reference_documents="Reference documents",
        pages="Pages",
        glossary="Glossary",
        generated_notice=("These notes were generated automatically - double-check them."),
        page_abbreviation="p.",
    ),
    "it": ExportLabels(
        recordings="Registrazioni",
        duration="Durata",
        reference_documents="Documenti di riferimento",
        pages="Pagine",
        glossary="Glossario",
        generated_notice=("Questi appunti sono stati generati automaticamente - ricontrollali."),
        page_abbreviation="p.",
    ),
    "tr": ExportLabels(
        recordings="Kayıtlar",
        duration="Süre",
        reference_documents="Referans belgeler",
        pages="Sayfa",
        glossary="Sözlük",
        generated_notice="Bu notlar otomatik olarak oluşturuldu - bir kontrol et.",
        page_abbreviation="s.",
    ),
}

_MONTHS_BY_LANGUAGE = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "it": (
        "gennaio",
        "febbraio",
        "marzo",
        "aprile",
        "maggio",
        "giugno",
        "luglio",
        "agosto",
        "settembre",
        "ottobre",
        "novembre",
        "dicembre",
    ),
    "tr": (
        "Ocak",
        "Şubat",
        "Mart",
        "Nisan",
        "Mayıs",
        "Haziran",
        "Temmuz",
        "Ağustos",
        "Eylül",
        "Ekim",
        "Kasım",
        "Aralık",
    ),
}


def primary_language(language: str | None) -> str:
    """Extracts the normalized leading subtag of a BCP 47 language tag."""
    subtag = (language or "en").replace("_", "-").split("-", 1)[0].strip().lower()
    return subtag or "en"


def export_labels(language: str | None) -> ExportLabels:
    """Resolves export labels, falling back to English."""
    return _LABELS_BY_LANGUAGE.get(primary_language(language), _LABELS_BY_LANGUAGE["en"])


def format_lesson_date(lesson_date: date, language: str | None) -> str:
    """Formats a calendar date for the supported export language."""
    selected_language = primary_language(language)
    months = _MONTHS_BY_LANGUAGE.get(selected_language, _MONTHS_BY_LANGUAGE["en"])
    month = months[lesson_date.month - 1]
    if selected_language == "en":
        return f"{month} {lesson_date.day}, {lesson_date.year}"
    return f"{lesson_date.day} {month} {lesson_date.year}"
