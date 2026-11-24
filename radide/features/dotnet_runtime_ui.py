"""Menus of the native runtimes: C# WinForms exes (radide/dotnet/native_project.py, runtime_lib.py) and the native
forms host of every GUI Bridge language (radide/runtimes/native_host.py, radbridge.exe).

Project > Run as Native WinForms exe   (checkable; C# projects with forms) - native mode on / off for the project
Project > Native Forms Host (no Python) (checkable; other GUI Bridge projects with forms) - radbridge.exe or Tk
Tools > RadIDE.Runtime.dll > Copy to Folder (.NET 8 / .NET Framework 4.8)... - the runtime for any C# project
"""
from __future__ import annotations

from pathlib import Path


def _menu(win, title: str):
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == title and a.menu() is not None:
            return a.menu()
    return win.menuBar().addMenu("&" + title)


def _csharp_folder(win) -> Path | None:
    p = getattr(win, "project", None)
    if p is None or getattr(p, "foreign", False) or getattr(p, "language", "") != "csharp-bridge":
        return None
    return Path(p.folder)


def _toggle_native(win, on: bool) -> None:
    folder = _csharp_folder(win)
    if folder is None:
        return
    from ..dotnet import native_project as NP
    try:
        win.save_all()
        NP.set_mode(folder, NP.NATIVE if on else NP.BRIDGE)
        try:                                      # keep the in-memory project in step with the file
            win.project.extra[NP.MODE_KEY] = NP.NATIVE if on else NP.BRIDGE
        except Exception:  # noqa: BLE001
            pass
        from ..languages.csharp_bridge import ensure_build_dir
        ensure_build_dir(folder)                  # the csproj of the new mode (packages kept)
    except Exception as e:  # noqa: BLE001
        win.log(f"*** {e}")
        return
    now = NP.mode(folder)
    if on and now != NP.NATIVE:
        win.log("C#: this project stays on the GUI Bridge (native mode needs a program whose forms are all C#; "
                "class libraries and console programs keep the bridge)")
    else:
        win.log("C#: F5 now runs a native WinForms exe (RadIDE.Runtime.dll)" if now == NP.NATIVE else
                "C#: F5 now runs on the GUI Bridge (the IDE draws the forms)")


def _copy_runtime(win, tfm: str) -> None:
    from PyQt6.QtWidgets import QFileDialog
    dest = QFileDialog.getExistingDirectory(win, f"Copy RadIDE.Runtime.dll ({tfm}) to")
    if not dest:
        return
    from .. import progress
    from ..dotnet import runtime_lib
    lines: list[str] = []

    def work():
        return runtime_lib.export(Path(dest), tfm, log=lines.append)

    def done(p):
        for ln in lines:
            win.log(ln)
        if p is None:
            win.log("*** RadIDE.Runtime.dll could not be built (see above)")
            return
        win.log(f"RadIDE.Runtime: copied to {p}\n  Reference it from a .csproj:\n    "
                f'<Reference Include="RadIDE.Runtime"><HintPath>{p}</HintPath></Reference>\n'
                "  then: Rad.MsgBox(\"Hi\"), Rad.InputBox(\"Name?\") ... (namespace-free class Rad)")

    progress.run_task(work, f"Building RadIDE.Runtime.dll ({tfm})", win, on_done=done,
                      on_error=lambda e: win.log(f"*** RadIDE.Runtime: {e}"), pass_reporter=False)


def install(win) -> None:
    pm = _menu(win, "Project")
    pm.addSeparator()
    act = pm.addAction("Run as &Native WinForms exe")
    act.setCheckable(True)
    act.setToolTip("F5 builds a real WinForms exe against RadIDE.Runtime.dll (off: the IDE draws the forms - "
                   "GUI Bridge)")
    win.a_csharp_native = act

    def refresh():
        folder = _csharp_folder(win)
        act.setVisible(folder is not None)
        if folder is not None:
            from ..dotnet import native_project as NP
            act.blockSignals(True)
            act.setChecked(NP.mode(folder) == NP.NATIVE)
            act.blockSignals(False)
    pm.aboutToShow.connect(refresh)
    act.toggled.connect(lambda on: _toggle_native(win, on))
    act.setVisible(False)

    host = pm.addAction("Native &Forms Host (no Python)")
    host.setCheckable(True)
    host.setToolTip("F5 draws the forms with the native host radbridge.exe (C + radforms, Win32) - every GUI Bridge "
                    "language. Off: the IDE's Python / Tk host. Needs MinGW-w64 (Build > Build Native Exe installs it).")
    win.a_native_host = host

    def host_folder():
        p = getattr(win, "project", None)
        if p is None or getattr(p, "foreign", False):
            return None
        from ..languages import get_plugin
        from ..languages.bridgebase import BridgeLanguagePlugin
        try:
            plugin = get_plugin(p.language)
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(plugin, BridgeLanguagePlugin) or not p.forms:
            return None
        if p.language == "csharp-bridge":
            from ..dotnet import native_project as NP
            if NP.mode(Path(p.folder)) == NP.NATIVE:       # a WinForms exe: no forms host at all
                return None
        return Path(p.folder)

    def host_refresh():
        folder = host_folder()
        host.setVisible(folder is not None)
        if folder is not None:
            from ..runtimes import native_host as NH
            host.blockSignals(True)
            host.setChecked(win.project.extra.get(NH.KEY, True) not in (False, "false", "0", "python"))
            host.blockSignals(False)

    def host_toggle(on: bool):
        folder = host_folder()
        if folder is None:
            return
        import json
        from ..runtimes import native_host as NH
        try:
            win.save_all()
            p = folder / "project.radproj"
            data = json.loads(p.read_text(encoding="utf-8-sig"))
            if on:
                data.pop(NH.KEY, None)
                win.project.extra.pop(NH.KEY, None)
            else:
                data[NH.KEY] = False
                win.project.extra[NH.KEY] = False
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            win.log(f"*** {e}")
            return
        if not on:
            win.log("Forms: F5 uses the IDE's Python / Tk host")
            return
        from ..languages import get_plugin
        why = NH.why_not(folder, win.project, get_plugin(win.project.language))
        win.log("Forms: F5 draws them with the native host (radbridge.exe, no Python)" if not why else
                f"Forms: native host on; this run still uses the Python host: {why}")
    pm.aboutToShow.connect(host_refresh)
    host.toggled.connect(host_toggle)
    host.setVisible(False)
    try:                    # the native forms host is built once, in the background (F5 never waits for it)
        from ..runtimes import native_host as NH
        NH.start_build()
    except Exception as e:  # noqa: BLE001
        win.log(f"[forms host] {e}")

    tm = _menu(win, "Tools").addMenu("RadIDE.&Runtime.dll")
    tm.setToolTip("The RAD IDE WinForms runtime (MsgBox, InputBox, RadControl ...) as a dll for any C# project")
    tm.addAction("Copy to Folder (.NET &8, net8.0-windows)...", lambda: _copy_runtime(win, "net8.0-windows"))
    tm.addAction("Copy to Folder (.NET &Framework 4.8)...", lambda: _copy_runtime(win, "net48"))
