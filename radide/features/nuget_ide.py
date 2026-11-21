"""NuGet like Visual Studio 2022 (radide/dotnet/nuget): menus, the Package Manager Console tool window and
the Options page.

* Tools > NuGet Package Manager > Package Manager Console / Manage NuGet Packages for Solution... /
  Package Manager Settings; View > Other Windows > Package Manager Console.
* Project > Manage Packages... and the Solution Explorer commands open the NuGet document for .NET
  projects (Visual Studio solutions and RAD IDE's C# GUI-Bridge projects); other languages keep their
  own package managers (radide/features/packages.py).
* Tools > Options > NuGet Package Manager (General, Package Sources).
"""
from __future__ import annotations


def _menu(win, title: str):
    return next((a.menu() for a in win.menuBar().actions() if a.menu() is not None and
                 a.text().replace("&", "") == title), None)


def show_console(win):
    dock = getattr(win, "dock_nuget_console", None)
    if dock is None:
        from ..dotnet.nuget.console_ui import install_dock
        dock = install_dock(win)
    dock.show()
    dock.raise_()
    win.nuget_console.refresh_context()
    win.nuget_console.text.setFocus()
    return win.nuget_console


def manage_solution(win):
    from ..dotnet.nuget.ui import open_manager
    return open_manager(win, solution=True)


def manage_project(win, project=None):
    from ..dotnet.nuget.ui import open_manager
    return open_manager(win, project)


def settings(win):
    from ..dotnet.nuget.context import solution_folder
    from ..dotnet.nuget.options_ui import package_sources_dialog
    return package_sources_dialog(win, solution_folder(win), tab=0)


def restore_solution(win):
    """Solution Explorer > Restore NuGet Packages (dotnet restore / packages.config restore) in the background."""
    from ..dotnet.nuget import context as CX
    from ..dotnet.nuget.projects import restore_all
    from ..dotnet.nuget.qtasync import run_async, thread_log
    projects = CX.dotnet_projects(win)
    if not projects:
        win.log("No .NET project is open.")
        return
    log = thread_log(win.log)
    win.log("========== Restore NuGet packages ==========")
    run_async(restore_all, lambda ok, err: win.log(f"*** {err}" if err else ""), projects, CX.solution_file(win), log)


def install(win) -> None:
    tools = _menu(win, "Tools")
    if tools is not None:
        sub = tools.addMenu("NuGet Package Manager")
        sub.setObjectName("menuNuGet")
        a = sub.addAction("Package Manager Console", lambda: show_console(win))
        a.setObjectName("actNuGetConsole")
        b = sub.addAction("Manage NuGet Packages for Solution...", lambda: manage_solution(win))
        b.setObjectName("actNuGetSolution")
        sub.addSeparator()
        sub.addAction("Package Manager Settings", lambda: settings(win))
        win.nuget_menu = sub

        def update():
            from ..dotnet.nuget.context import is_dotnet
            try:
                b.setEnabled(is_dotnet(win))
            except Exception:  # noqa: BLE001
                b.setEnabled(True)
        sub.aboutToShow.connect(update)
    view = _menu(win, "View")
    if view is not None:
        other = next((a.menu() for a in view.actions() if a.menu() is not None and
                      a.text().replace("&", "").startswith("Other Windows")), None)
        (other or view).addAction("Package Manager Console", lambda: show_console(win))
    try:
        from . import settings as S
        from ..dotnet.nuget.options_ui import options_page
        if options_page not in S.PAGE_HOOKS:
            S.PAGE_HOOKS.append(options_page)
    except Exception as e:  # noqa: BLE001
        win.log(f"[nuget] Options page: {e}")


__all__ = ["show_console", "manage_solution", "manage_project", "settings", "restore_solution", "install"]
