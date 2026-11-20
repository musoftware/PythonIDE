"""Small helpers shared by the framework providers (not a provider module: names starting with "_" are skipped
by the loader)."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..project_actions import Field, matches, package_json

IDENT = re.compile(r"[^0-9A-Za-z_]")


def deps(folder) -> dict:
    """dependencies + devDependencies of package.json."""
    pj = package_json(folder)
    out: dict = {}
    for k in ("dependencies", "devDependencies", "peerDependencies"):
        d = pj.get(k)
        if isinstance(d, dict):
            out.update(d)
    return out


def has_dep(folder, *names) -> bool:
    d = deps(folder)
    return any(n in d for n in names)


def has_script(folder, name: str) -> bool:
    s = package_json(folder).get("scripts")
    return isinstance(s, dict) and name in s


def pm(folder) -> str:
    """npm / yarn / pnpm / bun - the package manager of the project (lock file / packageManager)."""
    try:
        from .generic import NodeScripts
        return NodeScripts.manager(Path(folder))
    except Exception:  # noqa: BLE001
        return "npm"


def run_script_or(ctx, script: str, fallback: list, title: str | None = None):
    """``<pm> run <script>`` when package.json has it, else *fallback*."""
    if has_script(ctx.folder, script):
        m = pm(ctx.folder)
        return ctx.run_cli([m, "run", script], title=title or f"{m} run {script}")
    return ctx.run_cli(fallback, title=title)


def studly(name: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", name.strip())
    s = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return s if s and not s[0].isdigit() else ("X" + s if s else "")


def snake(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name.strip())
    return re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_").lower()


def kebab(name: str) -> str:
    return snake(name).replace("_", "-")


def under(rel_folder: str, base: str) -> str:
    """The part of *rel_folder* below *base* ("src/app/users" under "src/app" -> "users"; else "")."""
    r = (rel_folder or "").strip("/")
    b = base.strip("/")
    if matches(r, b + "/**") and len(r) > len(b):
        return r[len(b):].strip("/")
    return ""


def target_folder(ctx, default_rel: str) -> str:
    """The right-clicked folder (relative) when there is one, else *default_rel*."""
    if ctx.target is not None:
        t = Path(ctx.target)
        if t.is_file():
            t = t.parent
        rel = ctx.rel(t)
        if not Path(rel).is_absolute():
            return rel
    return default_rel.strip("/")


def write_new(ctx, rel: str, text: str) -> Path | None:
    """Write a new file of the project (never overwrites: logs and returns None when it exists)."""
    p = ctx.path(rel)
    if p.exists():
        ctx.log(f"*** {rel} already exists - not overwritten")
        ctx.open_file(p)
        return None
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    ctx.log(f"Created {rel}")
    return p


def name_field(default: str, label: str = "Name") -> Field:
    return Field("name", label, default=default)


def which(*names) -> str:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return ""


def first_glob(folder, *patterns) -> Path | None:
    for pat in patterns:
        for p in sorted(Path(folder).glob(pat)):
            return p
    return None


def log_routes(ctx, title: str, routes) -> None:
    """Write a route table (radide.web_site.frameworks Route objects) to the Output window."""
    ctx.log(f"------ {title} routes ------")
    for r in routes or []:
        where = f"    ({ctx.rel(r.file)}:{r.line})" if getattr(r, "file", "") else ""
        ctx.log(f"{r.method:7} {r.path:40} {r.handler or r.name}{where}")
    ctx.log(f"------ {len(routes or [])} route(s) ------")
    try:
        ctx.win.dock_output.show()
        ctx.win.dock_output.raise_()
    except Exception:  # noqa: BLE001
        pass
