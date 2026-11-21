"""F5 / Ctrl+F5 for Visual Studio solutions: launch profiles and multiple startup projects.

* The active launch profile of the startup project (the drop-down next to the configuration combos,
  like the arrow of VS's Start button) is applied: ``Project`` profiles run the built output (``dotnet
  App.dll`` / ``App.exe``) with the profile's arguments, environment variables (ASPNETCORE_URLS from
  ``applicationUrl``) and working directory (default: the output folder, as Visual Studio does);
  ``Executable`` profiles start ``executablePath``; ``launchBrowser`` opens the URL. With the debugger
  (netcoredbg) the same arguments / environment / working directory go into the launch request.
* "Multiple startup projects" (Solution Property Pages): every project with Action "Start" or
  "Start without debugging" is built first, then started; the first "Start" project gets the
  debugger (F5), the others run next to it with their output in the Output window ("[Name] ...").

``install(win)`` wraps ``radide.foreign.vs_ui.run_session`` (called by VsPlugin.make_session).
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QComboBox, QLabel

from . import launch, ops

OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


# ====================================================================== profiles
def profiles_of(project) -> dict:
    return launch.load(project.folder, project.ms.language)


def active_profile_name(sln, project) -> str:
    data = profiles_of(project)
    names = launch.profile_names(data)
    if not names:
        return ""
    st = ops.load_state(sln) if sln is not None else {}
    chosen = (st.get("launch_profile") or {}).get(ops.rel_key(sln, project.ms.path)) if sln is not None else ""
    return chosen if chosen in names else launch.default_profile(data)


def set_active_profile(sln, project, name: str) -> None:
    st = ops.load_state(sln)
    st.setdefault("launch_profile", {})[ops.rel_key(sln, project.ms.path)] = name
    ops.save_state(sln, st)


def _macros(project, target: str) -> dict:
    t = Path(target) if target else None
    return {"ProjectDir": str(project.folder) + os.sep, "ProjectPath": str(project.ms.path),
            "ProjectName": project.ms.name, "TargetDir": (str(t.parent) + os.sep) if t else "",
            "TargetPath": str(t) if t else "", "TargetName": t.stem if t else "",
            "SolutionDir": ""}


class ProfileStep:
    """The run step of a launch profile: program, arguments and working directory are computed when
    the step starts (the build output is known only after the build step)."""

    def __init__(self, win, project, cfg: str, plat: str, profile: dict, title: str = ""):
        self.win, self.project, self.cfg, self.plat, self.profile = win, project, cfg, plat, profile
        self.title = title
        self._resolved = None
        self.env = {}
        self.env.update(launch.resolve(profile, _macros(project, ""))["env"])

    def resolve(self) -> dict:
        if self._resolved is None:
            from ...foreign import msbuild as MB
            ms = self.project.ms
            props = MB.get_properties(ms, ["TargetPath"], self.cfg, self.plat)
            target = props.get("TargetPath") or str(MB.guess_target_path(ms, self.cfg, self.plat))
            r = launch.resolve(self.profile, _macros(self.project, target))
            if r["command"] == "Executable" and r["executable"]:
                argv = [r["executable"], *r["args"]]
                cwd = r["cwd"] or str(Path(r["executable"]).parent)
            else:
                exe = Path(target)
                apphost = exe.with_suffix(".exe")
                if exe.suffix.lower() == ".dll" and apphost.is_file() and os.name == "nt":
                    argv = [str(apphost), *r["args"]]
                elif exe.suffix.lower() == ".dll":
                    argv = [MB.find_dotnet() or "dotnet", str(exe), *r["args"]]
                else:
                    argv = [str(exe), *r["args"]]
                cwd = r["cwd"] or str(exe.parent)
            r.update(argv=argv, cwd_final=cwd, target=target)
            self.env.update(r["env"])
            self._resolved = r
            ops._log(self.win, f"Launch profile '{self.profile.get('_name', '')}': {' '.join(argv)}"
                               f"  (working directory: {cwd})")
            if r["browser"]:
                url = r["browser"]
                ops._log(self.win, f"Launching browser: {url}")
                if not OFFSCREEN:
                    def go():
                        from PyQt6.QtCore import QUrl
                        from PyQt6.QtGui import QDesktopServices
                        QDesktopServices.openUrl(QUrl(url))
                    QTimer.singleShot(2500, go)
        return self._resolved

    @property
    def cwd(self):
        return Path(self.resolve()["cwd_final"])

    @cwd.setter
    def cwd(self, _v):
        pass

    @property
    def argv(self):
        return self.resolve()["argv"]

    @argv.setter
    def argv(self, _v):
        pass


def apply_profile(win, session, project, sln, debug: bool) -> bool:
    """Put the active launch profile into a run/debug ChainSession of *project*. True = applied."""
    name = active_profile_name(sln, project)
    if not name:
        return False
    prof = dict(profiles_of(project)["profiles"].get(name) or {})
    if prof.get("commandName", "Project") not in ("Project", "Executable"):
        ops._log(win, f"*** launch profile '{name}': {prof.get('commandName')} profiles run in Visual Studio only "
                      "(using the project instead)")
        prof = {"commandName": "Project"}
    prof["_name"] = name
    cfg, plat = sln.project_config(project) if sln is not None else ("Debug", "Any CPU")
    steps = getattr(session, "steps", None)
    if steps is None:
        return False
    factory = getattr(session, "factory", None)
    if debug and factory is not None:
        def patched(orig=factory):
            s = orig()
            if s is None:
                return s
            from ...foreign import msbuild as MB
            props = MB.get_properties(project.ms, ["TargetPath"], cfg, plat)
            target = props.get("TargetPath") or str(MB.guess_target_path(project.ms, cfg, plat))
            r = launch.resolve(prof, _macros(project, target))
            la = getattr(s, "launch_args", None)
            if isinstance(la, dict):
                la["args"] = r["args"]
                la["env"] = {**(la.get("env") or {}), **r["env"]}
                if r["cwd"]:
                    la["cwd"] = r["cwd"]
                if r["command"] == "Executable" and r["executable"]:
                    la["program"] = r["executable"]
            ops._log(win, f"Launch profile '{name}' (debugger): args={r['args']} cwd={la.get('cwd') if la else ''}")
            if r["browser"]:
                ops._log(win, f"Launching browser: {r['browser']}")
                if not OFFSCREEN:
                    from PyQt6.QtCore import QUrl
                    from PyQt6.QtGui import QDesktopServices
                    QTimer.singleShot(2500, lambda: QDesktopServices.openUrl(QUrl(r["browser"])))
            return s
        session.factory = patched
        return True
    if not steps:
        return False
    last = steps[-1]
    argv = [str(a) for a in (last.argv or [])]
    is_run = bool(argv) and (("run" in argv and "--project" in argv) or Path(argv[0]).suffix.lower() == ".exe")
    if not is_run:
        return False
    steps[-1] = ProfileStep(win, project, cfg, plat, prof, last.title)
    return True


# ====================================================================== multiple startup projects
def startup_plan(sln) -> list[tuple[object, str]]:
    """[(VsProject, action)] of the multiple startup configuration (empty when single)."""
    st = ops.load_state(sln)
    if st.get("startup_mode") != "multiple":
        return []
    acts = st.get("startup_actions") or {}
    order = st.get("startup_order") or [e.name.lower() for e in sln.projects]
    out = []
    for key in order + [e.name.lower() for e in sln.projects if e.name.lower() not in order]:
        act = acts.get(key, "None")
        p = sln.project(key)
        if act != "None" and p is not None and not any(x is p for x, _a in out):
            out.append((p, act))
    return out


def _marker(fn, cwd):
    from ...foreign._others_base import LazyStep

    def argv():
        fn()
        return ["cmd.exe", "/d", "/c", "exit", "0"] if os.name == "nt" else ["true"]
    return LazyStep(argv, cwd, {}, "")


def multi_session(orig, win, sln, debug: bool):
    from ...foreign import vs_ui
    from ...foreign._others_base import ChainSession
    plan = startup_plan(sln)
    if not plan:
        return None
    primary_i = next((i for i, (_p, a) in enumerate(plan) if a == "Start"), 0) if debug else 0
    primary, pact = plan[primary_i]
    p_debug = debug and pact == "Start"
    s = orig(win, primary, p_debug, sln)
    apply_profile(win, s, primary, sln, p_debug)
    others = [(p, a) for i, (p, a) in enumerate(plan) if i != primary_i]
    builds = []
    secondaries = []
    for p, act in others:
        cfg, plat = sln.project_config(p)
        st, note = vs_ui._steps_for(p, cfg, plat, "build")
        if note:
            ops._log(win, f"*** {p.name}: {note}")
        builds += st
        if debug and act == "Start":
            ops._log(win, f"{sln.name_of(p)}: started without the debugger (one debugger session at a time)")
        rs = orig(win, p, False, sln)
        apply_profile(win, rs, p, sln, False)
        if getattr(rs, "steps", None):
            secondaries.append((sln.name_of(p), rs.steps[-1]))
    win._vs_secondary_sessions = []

    def start_others():
        for name, step in secondaries:
            cs = ChainSession([step], None, win)
            cs.output.connect(lambda t, n=name: win._append_output("".join(f"[{n}] {ln}\n" for ln in
                                                                           t.rstrip("\n").split("\n")))
                              if hasattr(win, "_append_output") else ops._log(win, t))
            cs.finished.connect(lambda c, n=name: ops._log(win, f"[{n}] exited with code {c}"))
            win._vs_secondary_sessions.append(cs)
            ops._log(win, f"Starting {name} (multiple startup projects)")
            cs.start()
    steps = s.steps
    marker = _marker(start_others, primary.folder)
    if p_debug or not steps:
        s.steps = builds + steps + [marker]
    else:
        s.steps = builds + steps[:-1] + [marker, steps[-1]]
    orig_stop = s.stop

    def stop_all():
        for cs in getattr(win, "_vs_secondary_sessions", []):
            try:
                cs.stop()
            except Exception:  # noqa: BLE001
                pass
        orig_stop()
    s.stop = stop_all
    names = ", ".join(f"{sln.name_of(p)} ({a})" for p, a in plan)
    ops._log(win, f"Multiple startup projects: {names}")
    return s


def wrapped_run_session(orig):
    def run_session(win, project, debug, sln):
        if sln is not None:
            try:
                s = multi_session(orig, win, sln, debug)
                if s is not None:
                    return s
            except Exception as e:  # noqa: BLE001 - never break F5
                ops._log(win, f"*** multiple startup projects: {e}")
        s = orig(win, project, debug, sln)
        try:
            apply_profile(win, s, project, sln, debug)
        except Exception as e:  # noqa: BLE001
            ops._log(win, f"*** launch profile: {e}")
        return s
    run_session._radide_sln_wrapped = True
    return run_session


# ====================================================================== the launch profile drop-down
def install_combo(win) -> None:
    tb = getattr(win, "vs_config_toolbar", None)
    if tb is None or getattr(win, "vs_profile_combo", None) is not None:
        return
    combo = QComboBox()
    combo.setToolTip("Launch profile of the startup project (F5 / Ctrl+F5)")
    combo.setMinimumContentsLength(12)
    tb.addWidget(QLabel("  "))
    win.vs_profile_combo_action = tb.addWidget(combo)
    win.vs_profile_combo = combo

    def picked(_i):
        sln = win.sln
        p = sln.startup_project() if ops.is_vs(sln) else None
        if p is None or getattr(p, "ms", None) is None:
            return
        name = combo.currentText()
        if name == "Open debug launch profiles UI...":
            from .properties import launch_profiles_dialog
            launch_profiles_dialog(win, p)
            refresh_profile_combo(win)
            return
        set_active_profile(sln, p, name)
        ops._log(win, f"{p.name}: launch profile '{name}'")
    combo.activated.connect(picked)


def refresh_profile_combo(win) -> None:
    combo = getattr(win, "vs_profile_combo", None)
    if combo is None:
        return
    try:
        sln = win.sln
        p = sln.startup_project() if ops.is_vs(sln) else None
        combo.blockSignals(True)
        combo.clear()
        if p is None or getattr(p, "ms", None) is None or p.ms.language == "C++":
            win.vs_profile_combo_action.setVisible(False)
            return
        data = profiles_of(p)
        names = launch.profile_names(data) or [p.ms.name]
        combo.addItems(names + ["Open debug launch profiles UI..."])
        cur = active_profile_name(sln, p) or names[0]
        combo.setCurrentText(cur)
        win.vs_profile_combo_action.setVisible(True)
    except RuntimeError:
        return
    finally:
        try:
            combo.blockSignals(False)
        except RuntimeError:
            pass
