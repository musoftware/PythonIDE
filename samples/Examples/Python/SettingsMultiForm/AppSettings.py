# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""AppSettings - the program's settings as JSON in the user's application data folder.

    %APPDATA%\\RADExamples\\SettingsMultiForm\\settings.json      (Windows)
    ~/.config/RADExamples/SettingsMultiForm/settings.json        (elsewhere)

Set RADEX_SETTINGS_DIR to use another folder (the tests do).  Also holds the English / Arabic texts."""
import json
import os

DEFAULTS = {"language": "en", "color": "Cream", "font_size": 16, "remember": True, "name": ""}
COLORS = {"Cream": "#FFF8E1", "Mint": "#E0F7EF", "Sky": "#E3F2FD", "Rose": "#FDE7EF"}

TEXTS = {
    "en": {"title": "Welcome", "prompt": "Your name:", "greet": "Greet", "settings": "Settings...",
           "hello": "Hello, {name}!\nHave a wonderful day.", "nobody": "Please type your name first.",
           "saved_in": "Settings file: {path}", "about": "Greeting Card - a multi-form RAD IDE sample.",
           "lang": "Language:", "color": "Card color:", "font": "Font size:", "remember": "Remember my name",
           "ok": "OK", "cancel": "Cancel", "settings_title": "Settings", "status": "Language: English"},
    "ar": {"title": "أهلاً وسهلاً", "prompt": "اسمك:", "greet": "ترحيب", "settings": "الإعدادات...",
           "hello": "أهلاً يا {name}!\nنتمنى لك يوماً سعيداً.", "nobody": "من فضلك اكتب اسمك أولاً.",
           "saved_in": "ملف الإعدادات: {path}", "about": "بطاقة ترحيب - مثال متعدد النماذج من RAD IDE.",
           "lang": "اللغة:", "color": "لون البطاقة:", "font": "حجم الخط:", "remember": "تذكر اسمي",
           "ok": "موافق", "cancel": "إلغاء", "settings_title": "الإعدادات", "status": "اللغة: العربية"},
}
LANG_NAMES = {"en": "English", "ar": "العربية"}


def folder() -> str:
    base = os.environ.get("RADEX_SETTINGS_DIR")
    if not base:
        root = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
        base = os.path.join(root, "RADExamples", "SettingsMultiForm")
    os.makedirs(base, exist_ok=True)
    return base


def path() -> str:
    return os.path.join(folder(), "settings.json")


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        with open(path(), encoding="utf-8") as f:
            stored = json.load(f)
        data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass                                   # first start or a broken file: the defaults
    return data


def save(data: dict) -> str:
    clean = {k: data.get(k, v) for k, v in DEFAULTS.items()}
    if not clean["remember"]:
        clean["name"] = ""
    with open(path(), "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    return path()


def text(lang: str, key: str, **kw) -> str:
    return TEXTS.get(lang, TEXTS["en"])[key].format(**kw)
