"""Bilingual (English / Arabic) text for messages the service core produces (progress, NRC explanations,
warnings). The IDE's own widgets are translated by radide/i18n; messages that come from the core and from
definition packs carry both languages and are shown in the current UI language."""
from __future__ import annotations


def ui_language() -> str:
    try:
        from ...i18n import language
        return language() or "en"
    except Exception:  # noqa: BLE001 - no Qt / no i18n: English
        return "en"


class BiText:
    """A message in English and Arabic; str() gives the current UI language."""
    __slots__ = ("en", "ar")

    def __init__(self, en: str, ar: str = ""):
        self.en = en or ""
        self.ar = ar or ""

    def get(self, lang: str | None = None) -> str:
        lang = lang or ui_language()
        return (self.ar or self.en) if lang == "ar" else (self.en or self.ar)

    def format(self, *a, **k) -> "BiText":
        return BiText(self.en.format(*a, **k), self.ar.format(*a, **k) if self.ar else "")

    def __add__(self, other) -> "BiText":
        if isinstance(other, BiText):
            return BiText(self.en + other.en, (self.ar or self.en) + (other.ar or other.en))
        return BiText(self.en + str(other), (self.ar or self.en) + str(other))

    def __str__(self) -> str:
        return self.get()

    def __repr__(self) -> str:
        return f"BiText({self.en!r}, {self.ar!r})"

    def to_json(self) -> dict:
        return {"en": self.en, "ar": self.ar}


def bi(en: str, ar: str = "") -> BiText:
    return BiText(en, ar)


def pick(obj: dict, key: str, lang: str | None = None) -> str:
    """`obj[key + "_ar"]` in Arabic (falling back to `obj[key]`), `obj[key]` otherwise."""
    lang = lang or ui_language()
    if lang == "ar":
        return str(obj.get(key + "_ar") or obj.get(key) or "")
    return str(obj.get(key) or obj.get(key + "_ar") or "")


def bi_of(obj: dict, key: str) -> BiText:
    return BiText(str(obj.get(key) or ""), str(obj.get(key + "_ar") or ""))
