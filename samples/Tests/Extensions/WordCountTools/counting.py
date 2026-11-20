"""Pure helpers (a sub-module of the extension, imported with a relative import)."""
import re


def count(text: str) -> dict:
    return {"lines": len(text.splitlines()) if text else 0,
            "words": len(re.findall(r"\w+", text or "")),
            "chars": len(text or "")}


def describe(c: dict) -> str:
    return f"{c['lines']} lines, {c['words']} words, {c['chars']} characters"
