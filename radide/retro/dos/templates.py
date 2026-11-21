"""New Project templates of the DOS project kinds (no Qt in here).

    for_kind("pascal") -> [Template, ...]        BY_ID["dostp_menu"] -> Template
    create_files(folder, name, template)        writes the files (CRLF, plain ASCII) and returns their names

Every template is original RAD IDE code (templates_basic / _pascal / _c / _asm / _batch). A file whose text is
``@include/NAME`` is copied from radide/retro/dos/include (tcconio.h / tcgraph.h).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import templates_asm, templates_basic, templates_batch, templates_c, templates_pascal

INCLUDE_DIR = Path(__file__).resolve().parent / "include"

ICONS = {"hello": "rad:console", "menu": "SP_FileDialogListView", "mode13": "SP_DesktopIcon",
         "speaker": "SP_MediaVolume", "mouse": "SP_ArrowRight", "lines": "SP_FileDialogDetailedView",
         "com": "SP_ComputerIcon", "bgi": "SP_DesktopIcon", "launcher": "SP_MediaPlay"}


@dataclass(frozen=True)
class Template:
    id: str
    kind: str
    title: str
    description: str
    files: dict
    settings: dict = field(default_factory=dict)

    @property
    def icon(self) -> str:
        return ICONS.get(self.id.split("_", 1)[-1], "rad:console")

    @property
    def main(self) -> str:
        return next(iter(self.files))


def _collect() -> list[Template]:
    out: list[Template] = []
    for kind, mod in (("qbasic", templates_basic), ("pascal", templates_pascal), ("c", templates_c),
                      ("asm", templates_asm), ("batch", templates_batch)):
        for row in mod.TEMPLATES:
            tid, title, desc, files = row[:4]
            settings = row[4] if len(row) > 4 else {}
            out.append(Template(tid, kind, title, desc, dict(files), dict(settings)))
    return out


TEMPLATES = _collect()
BY_ID = {t.id: t for t in TEMPLATES}


def for_kind(kind: str) -> list[Template]:
    return [t for t in TEMPLATES if t.kind == kind]


def identifier(name: str) -> str:
    ident = re.sub(r"\W", "_", name) or "Program1"
    return ident if not ident[0].isdigit() else "P" + ident


def dos_name(name: str, default: str = "PROGRAM") -> str:
    """An 8.3 base name (upper case, at most 8 letters / digits / _-) for *name*."""
    s = re.sub(r"[^A-Za-z0-9_-]", "", name or "").upper()[:8]
    return s or default


def text_for(template_text: str, name: str) -> str:
    if template_text.startswith("@include/"):
        return (INCLUDE_DIR / template_text[len("@include/"):]).read_text(encoding="ascii")
    return template_text.replace("{name}", name).replace("{ident}", identifier(name))


def write_dos_text(path: Path, text: str) -> None:
    """DOS sources: CRLF line ends, code page 437 (characters CP437 lacks become '?')."""
    data = text.replace("\r\n", "\n").replace("\n", "\r\n")
    Path(path).write_bytes(data.encode("cp437", "replace"))


def create_files(folder: Path, name: str, template: Template) -> list[str]:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for fname, text in template.files.items():
        p = folder / fname
        if not p.exists():
            write_dos_text(p, text_for(text, name))
        written.append(fname)
    return written


__all__ = ["BY_ID", "INCLUDE_DIR", "TEMPLATES", "Template", "create_files", "dos_name", "for_kind", "identifier",
           "text_for", "write_dos_text"]
