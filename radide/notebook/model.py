"""nbformat 4 notebook documents without Qt (load, save, edit, export).

The JSON written is the same as Jupyter's (``indent=1``, sources as lists of lines, nbformat 4.5 cell ids),
so notebooks round-trip with JupyterLab / VS Code without spurious diffs.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

NBFORMAT = 4
NBFORMAT_MINOR = 5

DEFAULT_KERNELSPEC = {"name": "python3", "display_name": "Python 3 (ipykernel)", "language": "python"}


def _join(src) -> str:
    if isinstance(src, list):
        return "".join(s if isinstance(s, str) else json.dumps(s) for s in src)
    if src is None or isinstance(src, str):
        return src or ""
    return json.dumps(src)                  # a number / object where text belongs (hand-edited file)


def _split(text: str) -> list[str]:
    """Jupyter stores multi-line strings as a list of lines that keep their newline."""
    if not text:
        return []
    return text.splitlines(keepends=True)


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class Cell:
    cell_type: str = "code"                 # "code" | "markdown" | "raw"
    source: str = ""
    outputs: list = field(default_factory=list)
    execution_count: int | None = None
    metadata: dict = field(default_factory=dict)
    attachments: dict | None = None
    id: str = field(default_factory=new_id)

    def to_json(self) -> dict:
        d: dict = {"cell_type": self.cell_type, "id": self.id, "metadata": self.metadata,
                   "source": _split(self.source)}
        if self.cell_type == "code":
            d["execution_count"] = self.execution_count
            d["outputs"] = [normalize_output(o, for_save=True) for o in self.outputs]
        elif self.attachments:
            d["attachments"] = self.attachments
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Cell":
        ct = d.get("cell_type", "code")
        cid = str(d.get("id") or new_id())
        if not re.fullmatch(r"[a-zA-Z0-9-_]{1,64}", cid):
            cid = new_id()
        c = cls(cell_type=ct if ct in ("code", "markdown", "raw") else "raw", source=_join(d.get("source")),
                metadata=dict(d.get("metadata") or {}), id=cid, attachments=d.get("attachments"))
        if ct == "code":
            c.execution_count = d.get("execution_count")
            c.outputs = [normalize_output(o) for o in d.get("outputs") or []]
        return c


def normalize_output(o: dict, for_save: bool = False) -> dict:
    """A copy of an nbformat output; multi-line strings joined in memory, split again for saving."""
    o = json.loads(json.dumps(o))
    t = o.get("output_type")
    conv = _split if for_save else _join
    if t == "stream":
        o["text"] = conv(_join(o.get("text")))
    elif t in ("display_data", "execute_result", "update_display_data"):
        data = o.get("data") or {}
        for mime, val in list(data.items()):
            if mime.startswith("text/") or mime == "image/svg+xml" or mime.endswith("+xml"):
                data[mime] = conv(_join(val))
            elif isinstance(val, list):                    # base64 images may be split too
                data[mime] = "".join(val)
        o["data"] = data
        o.setdefault("metadata", {})
        if t == "update_display_data":
            o["output_type"] = "display_data"
        if for_save:
            o.pop("transient", None)
    elif t == "error":
        o.setdefault("ename", "")
        o.setdefault("evalue", "")
        o.setdefault("traceback", [])
    return o


@dataclass
class Notebook:
    cells: list[Cell] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    nbformat: int = NBFORMAT
    nbformat_minor: int = NBFORMAT_MINOR
    path: Path | None = None

    # ------------------------------------------------------------------ io
    @classmethod
    def new(cls, path: Path | None = None, cells: list[Cell] | None = None) -> "Notebook":
        nb = cls(cells=list(cells) if cells is not None else [Cell()], path=path)
        nb.metadata = {"kernelspec": dict(DEFAULT_KERNELSPEC),
                       "language_info": {"name": "python"}}
        return nb

    @classmethod
    def from_json(cls, data: dict, path: Path | None = None) -> "Notebook":
        try:
            return cls._from_json(data, path)
        except (TypeError, AttributeError, KeyError) as e:     # wrong JSON types (hand-edited / corrupted)
            raise ValueError(f"not a valid Jupyter notebook ({type(e).__name__}: {e})") from None

    @classmethod
    def _from_json(cls, data: dict, path: Path | None = None) -> "Notebook":
        if not isinstance(data, dict) or "cells" not in data:
            if isinstance(data, dict) and data.get("nbformat", 4) < 4 and "worksheets" in data:
                cells = []
                for ws in data.get("worksheets") or []:     # nbformat 3: one level of worksheets
                    for c in ws.get("cells") or []:
                        c = dict(c)
                        if c.get("cell_type") == "code":
                            c["source"] = c.get("input", "")
                            c["execution_count"] = c.get("prompt_number")
                            c["outputs"] = []
                        elif c.get("cell_type") == "heading":
                            c = {"cell_type": "markdown",
                                 "source": "#" * int(c.get("level", 1)) + " " + _join(c.get("source"))}
                        cells.append(c)
                data = {"cells": cells, "metadata": data.get("metadata") or {}}
            else:
                raise ValueError("not a Jupyter notebook (no 'cells')")
        nb = cls(cells=[Cell.from_json(c) for c in data.get("cells") or []],
                 metadata=dict(data.get("metadata") or {}), path=path,
                 nbformat=NBFORMAT, nbformat_minor=max(int(data.get("nbformat_minor") or 0), NBFORMAT_MINOR)
                 if data.get("nbformat", 4) == 4 else NBFORMAT_MINOR)
        seen = set()
        for c in nb.cells:                                    # ids must be unique
            while c.id in seen:
                c.id = new_id()
            seen.add(c.id)
        return nb

    @classmethod
    def load(cls, path: Path) -> "Notebook":
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return cls.new(path)
        try:
            data = json.loads(text)
        except RecursionError:                  # JSON nested thousands of levels deep
            raise ValueError(f"{path.name}: not a valid Jupyter notebook (nested too deeply)") from None
        return cls.from_json(data, path)

    def to_json(self) -> dict:
        return {"cells": [c.to_json() for c in self.cells], "metadata": self.metadata,
                "nbformat": self.nbformat, "nbformat_minor": self.nbformat_minor}

    def dumps(self) -> str:
        return json.dumps(self.to_json(), indent=1, ensure_ascii=False) + "\n"

    def save(self, path: Path | None = None) -> Path:
        path = Path(path or self.path)
        text = self.dumps()
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        tmp.replace(path)
        self.path = path
        return path

    def validate(self) -> str | None:
        """nbformat's own schema check when nbformat is installed; None = valid (or not checkable)."""
        try:
            import nbformat
        except ImportError:
            return None
        try:
            nbformat.validate(nbformat.from_dict(self.to_json()))
        except Exception as e:  # noqa: BLE001 - ValidationError and friends
            return str(e).splitlines()[0][:300]
        return None

    # ------------------------------------------------------------------ editing
    def index(self, cell_id: str) -> int:
        for i, c in enumerate(self.cells):
            if c.id == cell_id:
                return i
        return -1

    def cell(self, cell_id: str) -> Cell | None:
        i = self.index(cell_id)
        return self.cells[i] if i >= 0 else None

    def insert(self, index: int, cell: Cell) -> Cell:
        ids = {c.id for c in self.cells}
        while cell.id in ids:
            cell.id = new_id()
        index = max(0, min(index, len(self.cells)))
        self.cells.insert(index, cell)
        return cell

    def remove(self, cell_id: str) -> Cell | None:
        i = self.index(cell_id)
        return self.cells.pop(i) if i >= 0 else None

    def move(self, cell_id: str, delta: int) -> int:
        i = self.index(cell_id)
        j = i + delta
        if i < 0 or not 0 <= j < len(self.cells):
            return i
        self.cells[i], self.cells[j] = self.cells[j], self.cells[i]
        return j

    def clear_outputs(self) -> None:
        for c in self.cells:
            if c.cell_type == "code":
                c.outputs = []
                c.execution_count = None

    @property
    def language(self) -> str:
        li = self.metadata.get("language_info") or {}
        ks = self.metadata.get("kernelspec") or {}
        return (li.get("name") or ks.get("language") or "python").lower()

    # ------------------------------------------------------------------ export
    def to_py(self) -> str:
        """Percent-format script (``# %%`` cells) - runs as plain Python, opens as cells in VS Code / Spyder."""
        out = []
        for c in self.cells:
            if c.cell_type == "code":
                body = "\n".join(_magic_to_comment(line) for line in c.source.splitlines())
                out.append("# %%\n" + body)
            elif c.cell_type == "markdown":
                out.append("# %% [markdown]\n" + "\n".join(("# " + line).rstrip()
                                                           for line in c.source.splitlines()))
            else:
                out.append("# %% [raw]\n" + "\n".join(("# " + line).rstrip() for line in c.source.splitlines()))
        return "\n\n".join(out).rstrip() + "\n"

    def to_html(self, title: str | None = None) -> str:
        from .render import notebook_to_html
        return notebook_to_html(self, title or (self.path.stem if self.path else "Notebook"))

    @classmethod
    def from_py(cls, text: str, path: Path | None = None) -> "Notebook":
        """Import a percent-format script (``# %%`` / ``# %% [markdown]``); a plain script is one cell."""
        cells: list[Cell] = []
        cur: Cell | None = None
        lines: list[str] = []

        def flush():
            if cur is None:
                return
            src = "\n".join(lines).strip("\n")
            if cur.cell_type == "markdown":
                src = "\n".join(re.sub(r"^# ?", "", ln) for ln in src.splitlines())
            cur.source = src
            if src or cur.cell_type == "code":
                cells.append(cur)

        for line in text.splitlines():
            m = re.match(r"^#\s*%%(.*)$", line)
            if m:
                flush()
                tag = m.group(1)
                cur = Cell(cell_type="markdown" if "[markdown]" in tag else ("raw" if "[raw]" in tag else "code"))
                lines = []
            else:
                if cur is None:
                    cur = Cell()
                lines.append(line)
        flush()
        return cls.new(path, cells or [Cell()])


def _magic_to_comment(line: str) -> str:
    s = line.lstrip()
    if s.startswith(("%", "!")):
        return line[:len(line) - len(s)] + "# " + s
    return line


# ---------------------------------------------------------------------- starter templates
def data_science_starter(path: Path | None = None) -> Notebook:
    md = Cell("markdown", "# Data Science starter\n\nA small analysis with **pandas** and **matplotlib**:\n\n"
              "1. load a table (the sample `sales.csv` next to this notebook, or built in code)\n"
              "2. explore it (`head`, `describe`, group by)\n"
              "3. plot it inline\n\nRun a cell with **Shift+Enter**, everything with **Run All**.")
    imports = Cell(source="import pandas as pd\nimport matplotlib.pyplot as plt\n\n"
                   "pd.set_option(\"display.max_rows\", 20)\nprint(\"pandas\", pd.__version__)")
    load = Cell(source="from pathlib import Path\n\n"
                "if Path(\"sales.csv\").exists():\n    df = pd.read_csv(\"sales.csv\")\nelse:\n"
                "    df = pd.DataFrame({\n"
                "        \"month\": [\"Jan\", \"Feb\", \"Mar\", \"Apr\", \"May\", \"Jun\"],\n"
                "        \"region\": [\"North\", \"South\", \"North\", \"South\", \"North\", \"South\"],\n"
                "        \"sales\": [120, 98, 143, 110, 160, 131],\n"
                "        \"cost\": [80, 70, 90, 75, 101, 88],\n    })\n"
                "df[\"profit\"] = df[\"sales\"] - df[\"cost\"]\ndf.head()")
    explore = Cell(source="df.describe()")
    group = Cell(source="df.groupby(\"region\")[[\"sales\", \"profit\"]].sum()")
    plot_md = Cell("markdown", "## Plot\n\nFigures are shown under the cell (matplotlib *inline*).")
    plot = Cell(source="fig, ax = plt.subplots(figsize=(6, 3))\n"
                "ax.plot(df[\"month\"], df[\"sales\"], marker=\"o\", label=\"sales\")\n"
                "ax.bar(df[\"month\"], df[\"profit\"], alpha=0.4, label=\"profit\")\n"
                "ax.set_title(\"Sales and profit\")\nax.legend()\nplt.show()")
    return Notebook.new(path, [md, imports, load, explore, group, plot_md, plot])


SAMPLE_CSV = ("month,region,sales,cost\nJan,North,120,80\nFeb,South,98,70\nMar,North,143,90\n"
              "Apr,South,110,75\nMay,North,160,101\nJun,South,131,88\nJul,North,170,104\nAug,South,125,83\n")
