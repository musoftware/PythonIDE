"""Install / uninstall / update / enable / disable VS Code extensions, with extensionDependencies and
extensionPack resolution. Every function is synchronous and safe to call from a worker thread; the
radide.vsx events are delivered on the GUI thread.

    install_vsix_file(path)                      -> [Extension]   (+ its dependencies from Open VSX)
    install(ext_id, version=None, force=False)   -> [Extension]   from Open VSX (+ dependencies / pack)
    plan(ext_id)                                 -> [(id, entry | None, note)]  what install() would do
    uninstall(ext_id, force=False)               -> [ids removed] (+ orphaned dependencies)
    set_enabled(ext_id, on)                      -> Extension
    check_updates()                              -> [(Extension, entry)]
    update(ext_id) / update_all()
    dependents(ext_id)                           -> installed ids that depend on / pack it
"""
from __future__ import annotations

from pathlib import Path

from . import mark_restart, on_changed, on_enabled, on_installed, on_removed
from . import package as P
from . import registry as R

BUILTIN_NAMESPACES = {"vscode"}          # VS Code built-ins: some exist on Open VSX, the rest are skipped


class InstallError(Exception):
    pass


def _record(ext: P.Extension, **kw) -> None:
    st = P.load_state()
    rec = ext.state_record()
    rec.update(kw)
    st["extensions"][ext.id] = rec
    P.save_state(st)


def _installed_map() -> dict:
    return {e.id: e for e in P.installed()}


def _finish_install(ext: P.Extension, source: str, sha: str, platform: str, dependency_of: str | None,
                    old: P.Extension | None) -> P.Extension:
    """Write the state record (keeping the enabled flag / dependents of a previous version), remove
    the previous version's folder, emit the events."""
    dep_of = list(old.dependency_of) if old else []
    if dependency_of and dependency_of not in dep_of:
        dep_of.append(dependency_of)
    if old and old.source != "dependency":
        source = old.source if source == "dependency" else source
    enabled = old.enabled if old else True
    ext.enabled = enabled
    ext.source = source
    ext.installed_at = P.now_iso()
    ext.sha256 = sha
    ext.target_platform = platform
    ext.dependency_of = dep_of
    _record(ext)
    if old and old.folder and old.folder != ext.folder:
        try:
            P.remove_folder(old.folder)
        except P.VsixError:
            pass
    mark_restart(ext, "installed")
    on_installed.emit(ext)
    on_changed.emit()
    return ext


def install_vsix_file(path, *, with_dependencies: bool = True, progress=None, log=None) -> list[P.Extension]:
    """Install a local .vsix (Install from VSIX...). Missing dependencies come from Open VSX."""
    path = Path(path)
    if not path.is_file():
        raise InstallError(f"file not found: {path}")
    man = P.read_vsix_manifest(path)
    old = P.get_installed(man.id)
    ext = P.unpack_to_root(path)
    out = [_finish_install(ext, "vsix", R._sha256(path), "", None, old)]
    if with_dependencies:
        for dep in ext.extension_dependencies + ext.extension_pack:
            try:
                out += install(dep, dependency_of=ext.id, progress=progress, log=log, _seen={ext.id})
            except (InstallError, R.RegistryError, P.VsixError) as e:
                _log(log, f"dependency {dep}: {e}")
    return out


def _log(log, msg: str) -> None:
    if log:
        try:
            log(msg)
        except Exception:  # noqa: BLE001
            pass


def install(ext_id: str, version: str | None = None, *, force: bool = False, dependency_of: str | None = None,
            progress=None, log=None, _seen: set | None = None) -> list[P.Extension]:
    """Install (or update to) an extension from Open VSX plus its extensionDependencies and extensionPack
    members (recursively, each once). force=True ignores engines.vscode. Returns the installed list."""
    ext_id = ext_id.lower()
    seen = _seen if _seen is not None else set()
    if ext_id in seen:
        return []
    seen.add(ext_id)
    current = P.get_installed(ext_id)
    out: list[P.Extension] = []
    if current is not None and dependency_of and not version:
        # already there: only remember the new dependent
        if dependency_of not in current.dependency_of:
            current.dependency_of.append(dependency_of)
            _record(current)
        return []
    entry = R.pick_version(ext_id, version=version)
    if entry is None and not version:
        if force or dependency_of:
            entry = R.latest_entry(ext_id)
        else:
            latest = R.latest_entry(ext_id)
            if latest is None:
                raise InstallError(f"{ext_id} is not available for {R.target_platform()} on Open VSX")
            raise InstallError(f"{ext_id} {latest.get('version')} needs VS Code "
                               f"{(latest.get('engines') or {}).get('vscode', '?')} and no older version "
                               f"works with the API level {R.api_level()} RAD IDE emulates")
    if entry is None:
        if ext_id.split(".")[0] in BUILTIN_NAMESPACES:
            _log(log, f"{ext_id}: VS Code built-in extension, not on Open VSX - skipped")
            return []
        raise InstallError(f"{ext_id}{' ' + version if version else ''} was not found on Open VSX")
    if current is not None and current.version == entry.get("version"):
        _log(log, f"{ext_id} {current.version} is already installed")
    else:
        _log(log, f"downloading {ext_id} {entry.get('version')} ...")
        vsix, sha = R.download(entry, progress=progress)
        ext = P.unpack_to_root(vsix)
        if ext.id != ext_id:
            _log(log, f"note: {ext_id} unpacked as {ext.id}")
        out.append(_finish_install(ext, "dependency" if dependency_of else "openvsx", sha,
                                   entry.get("targetPlatform") or "universal", dependency_of,
                                   current if current is not None else P.get_installed(ext.id)))
        current = out[-1]
    for dep in current.extension_dependencies + current.extension_pack:
        try:
            out += install(dep, dependency_of=current.id, progress=progress, log=log, _seen=seen)
        except (InstallError, R.RegistryError, P.VsixError) as e:
            _log(log, f"dependency {dep}: {e}")
    return out


def plan(ext_id: str) -> list[tuple[str, dict | None, str]]:
    """What install(ext_id) will fetch: [(id, registry entry or None, note)] - no download."""
    out: list = []
    seen: set = set()
    have = _installed_map()

    def walk(i: str, depth: int):
        i = i.lower()
        if i in seen or depth > 8:
            return
        seen.add(i)
        if depth and i in have:
            out.append((i, None, "installed"))
            return
        try:
            e = R.pick_version(i) or (R.latest_entry(i) if depth else None)
        except R.RegistryError as err:
            out.append((i, None, str(err)))
            return
        if e is None:
            out.append((i, None, "built-in, skipped" if i.split(".")[0] in BUILTIN_NAMESPACES else
                        "not compatible / not found"))
            return
        out.append((i, e, e.get("version", "")))
        try:
            d = R.details(e.get("namespace", ""), e.get("name", ""), e.get("version"))
        except R.RegistryError:
            d = e
        for dep in list(d.get("dependencies") or []) + list(d.get("bundledExtensions") or []):
            did = f"{dep.get('namespace')}.{dep.get('extension') or dep.get('name')}" if isinstance(dep, dict) \
                else str(dep)
            walk(did, depth + 1)
    walk(ext_id, 0)
    return out


def dependents(ext_id: str) -> list[str]:
    ext_id = ext_id.lower()
    return [e.id for e in P.installed()
            if e.id != ext_id and (ext_id in e.extension_dependencies or ext_id in e.extension_pack)]


def uninstall(ext_id: str, *, force: bool = False, remove_orphans: bool = True) -> list[str]:
    """Remove an extension (and the dependencies only it pulled in). Refuses while another installed
    extension depends on it, unless force=True."""
    ext_id = ext_id.lower()
    ext = P.get_installed(ext_id)
    if ext is None:
        raise InstallError(f"{ext_id} is not installed")
    deps = [d for d in dependents(ext_id) if ext_id in (P.get_installed(d).extension_dependencies
                                                         if P.get_installed(d) else [])]
    if deps and not force:
        raise InstallError(f"{ext_id} is needed by {', '.join(deps)}")
    st = P.load_state()
    st["extensions"].pop(ext_id, None)
    for rec in st["extensions"].values():
        if ext_id in (rec.get("dependency_of") or []):
            rec["dependency_of"] = [d for d in rec["dependency_of"] if d != ext_id]
    P.save_state(st)
    P.remove_folder(ext.folder)
    mark_restart(ext, "removed")
    on_removed.emit(ext)
    removed = [ext_id]
    if remove_orphans:
        for child in ext.extension_dependencies + ext.extension_pack:
            c = P.get_installed(child)
            if c is not None and c.source == "dependency" and not c.dependency_of and not dependents(c.id):
                try:
                    removed += uninstall(c.id, remove_orphans=True)
                except InstallError:
                    pass
    on_changed.emit()
    return removed


def set_enabled(ext_id: str, on: bool) -> P.Extension:
    ext_id = ext_id.lower()
    st = P.load_state()
    rec = st["extensions"].get(ext_id)
    if rec is None:
        raise InstallError(f"{ext_id} is not installed")
    rec["enabled"] = bool(on)
    P.save_state(st)
    ext = P.get_installed(ext_id)
    mark_restart(ext, "enabled" if on else "disabled")
    on_enabled.emit(ext, bool(on))
    on_changed.emit()
    return ext


def check_updates(*, refresh: bool = True) -> list[tuple[P.Extension, dict]]:
    """Installed extensions with a newer compatible version on Open VSX (local .vsix installs whose id
    exists on Open VSX are checked too)."""
    out = []
    for ext in P.installed():
        try:
            e = R.pick_version(ext.id, refresh=refresh)
        except R.RegistryError:
            continue
        if e and R.newer(e.get("version", ""), ext.version):
            out.append((ext, e))
    return out


def update(ext_id: str, *, progress=None, log=None) -> list[P.Extension]:
    e = R.pick_version(ext_id, refresh=True)
    cur = P.get_installed(ext_id)
    if e is None or cur is None or not R.newer(e.get("version", ""), cur.version):
        return []
    return install(ext_id, e.get("version"), progress=progress, log=log)


def update_all(*, progress=None, log=None) -> list[P.Extension]:
    out = []
    for ext, e in check_updates():
        try:
            out += install(ext.id, e.get("version"), progress=progress, log=log)
        except (InstallError, R.RegistryError, P.VsixError) as err:
            _log(log, f"update {ext.id}: {err}")
    return out


def support_summary(ext: P.Extension | None = None, contributes: dict | None = None,
                    has_code: bool | None = None) -> list[tuple[str, str, bool, str]]:
    """Which contributions RAD IDE can use: [(point, description, supported, note)]. Works on an
    installed Extension or on a registry manifest (contributes + has_code)."""
    c = contributes if contributes is not None else (ext.contributes if ext else {})
    code = has_code if has_code is not None else (ext.has_code if ext else False)
    host = _host_available()
    rows = []

    def n(v):
        if isinstance(v, dict) and isinstance(v.get("properties"), dict):
            return len(v["properties"])
        return len(v) if isinstance(v, (list, dict)) else (1 if v else 0)
    table = [
        ("themes", "Color themes", True, ""),
        ("iconThemes", "File icon themes", True, ""),
        ("productIconThemes", "Product icon themes", False, "not supported"),
        ("grammars", "TextMate grammars (syntax colouring)", True, ""),
        ("languages", "Languages (extensions, comments, brackets)", True, ""),
        ("snippets", "Snippets", True, ""),
        ("keybindings", "Keyboard shortcuts", True, "for commands RAD IDE knows"),
        ("configuration", "Settings", True, "shown in Tools > Options"),
        ("commands", "Commands", host, "needs the extension host" if not host else "via the extension host"),
        ("menus", "Menus", host, "Command Palette, editor title / context, view title / item menus via the host"),
        ("submenus", "Submenus", host, "inside the menus above"),
        ("debuggers", "Debuggers (DAP)", host, "debug adapters via the host"),
        ("breakpoints", "Breakpoint languages", True, ""),
        ("taskDefinitions", "Task definitions", host, "tasks of task providers run via the host"),
        ("views", "Custom views", host, "tree views and webview views (Activity Bar / Panel / secondary side bar)"),
        ("viewsContainers", "View containers", host, "activitybar, panel and secondarySidebar containers"),
        ("viewsWelcome", "View welcome content", host, "shown while a tree view is empty"),
        ("customEditors", "Custom editors", host, "webview custom editors via the host"),
        ("notebooks", "Notebook types", False, "serializers run; no notebook editor"),
        ("walkthroughs", "Walkthroughs", True, "opened as a Markdown page"),
        ("localizations", "Language packs (UI translation)", False, "RAD IDE has its own UI translation"),
        ("jsonValidation", "JSON schemas", False, "not supported yet"),
        ("semanticTokenTypes", "Semantic token types", False, "not supported"),
        ("problemMatchers", "Problem matchers", False, "not supported"),
        ("terminal", "Terminal profiles", host, "Extensions > New Extension Terminal from Profile..."),
    ]
    known = set()
    for key, label, ok, note in table:
        known.add(key)
        if key in c:
            rows.append((key, f"{label} ({n(c[key])})", ok, note))
    for key in c:
        if key not in known:
            rows.append((key, key, False, "not supported"))
    if code:
        rows.append(("main", "Extension code (Node.js: LSP clients, commands, providers)", host,
                     "runs in the RAD IDE extension host (vscode API shim; not every API exists)" if host
                     else "the extension host is not available - code does not run"))
    return rows


def _host_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("radide.vsx.bridge") is not None
    except Exception:  # noqa: BLE001
        return False
