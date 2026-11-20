"""Windows shell integration (radide/shell_integration.py) against a TEST registry root only.

    .venv\\Scripts\\python samples\\Tests\\ShellIntegration\\test_shell_registry.py [scratch folder]

Never touches HKCU\\Software\\Classes: every key goes under HKCU\\Software\\RADIDE-TEST-Shell and the
shortcuts into <scratch>\\shortcuts. Checks every planned key/value, that values RAD IDE does not own
are kept, and that unregister restores exactly the previous state (a full dump of the test tree)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import winreg
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
BASE = "Software\\RADIDE-TEST-Shell"
ROOT = BASE + "\\Classes"
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-shell-test"
SHORTCUTS = SCRATCH / "shortcuts"
os.environ["RADIDE_SHELL_ROOT"] = ROOT
os.environ["RADIDE_SHELL_SHORTCUTS"] = str(SHORTCUTS)

from radide import shell_integration as S  # noqa: E402

HK = winreg.HKEY_CURRENT_USER
results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))


def dump(key: str) -> dict:
    """{subkey path: {value name: (data, type)}} of the whole tree (empty when missing)."""
    out = {}
    try:
        h = winreg.OpenKey(HK, key)
    except OSError:
        return out
    with h:
        vals = {}
        n_sub, n_val, _ = winreg.QueryInfoKey(h)
        for i in range(n_val):
            name, data, typ = winreg.EnumValue(h, i)
            vals[name] = (data, typ)
        out[key] = vals
        subs = [winreg.EnumKey(h, i) for i in range(n_sub)]
    for s in subs:
        out.update(dump(key + "\\" + s))
    return out


def delete_tree(key: str):
    assert key.startswith(BASE), key                      # safety: only the test tree
    try:
        h = winreg.OpenKey(HK, key, 0, winreg.KEY_ALL_ACCESS)
    except OSError:
        return
    with h:
        subs = [winreg.EnumKey(h, i) for i in range(winreg.QueryInfoKey(h)[0])]
    for s in subs:
        delete_tree(key + "\\" + s)
    winreg.DeleteKey(HK, key)


def setv(key, name, data, typ=winreg.REG_SZ):
    with winreg.CreateKeyEx(HK, key, 0, winreg.KEY_WRITE) as h:
        winreg.SetValueEx(h, name, 0, typ, data)


def getv(key, name):
    try:
        with winreg.OpenKey(HK, key) as h:
            return winreg.QueryValueEx(h, name)[0]
    except OSError:
        return None


def real_snapshot():
    """Values of the real locations that a (wrongly targeted) run would create."""
    keys = ["Software\\Classes\\RADIDE.Solution", "Software\\Classes\\*\\shell\\RADIDE",
            "Software\\Classes\\Directory\\shell\\RADIDE", "Software\\RADIDE\\ShellIntegration",
            "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\RADIDE", "Software\\RADIDE\\Capabilities"]
    return {k: dump(k) for k in keys}


def main():
    t = S.Target.from_env()
    check("target is the test root", t.test and t.classes == ROOT and t.manifest_key.startswith(BASE)
          and t.uninstall_key.startswith(BASE) and t.registered_apps_key.startswith(BASE) and not t.notify, repr(t))
    check("real location never targeted", "Software\\Classes" != t.classes)
    real_before = real_snapshot()
    delete_tree(BASE)
    shutil.rmtree(SHORTCUTS, ignore_errors=True)

    # ---- pre-existing state RAD IDE must respect
    setv(ROOT + "\\.radsln", "", "OtherApp.Solution")             # own strong type: replaced, then restored
    setv(ROOT + "\\.form", "", "NetBeans.Form")                   # own weak type: never replaced
    setv(ROOT + "\\.py\\OpenWithProgids", "Python.File", "")      # another program's Open with entry
    setv(ROOT + "\\*\\shell\\Other", "", "Other menu")
    setv(BASE + "\\RegisteredApplications", "Other App", "Software\\Other\\Capabilities")
    (SHORTCUTS / "Desktop").mkdir(parents=True, exist_ok=True)
    dummy = SHORTCUTS / "Desktop" / "RAD IDE.lnk"                  # e.g. an installer's shortcut: kept
    dummy.write_bytes(b"not ours")
    before = dump(BASE)

    opts = {k: True for k in S.OPTIONS}
    planned = S.plan(opts, t)
    st = S.register(opts, t)
    check("register: status registered", st["registered"] and not st["stale"] and st["test"], str(st)[:200])
    m_values = st["values"]
    missing, wrong = [], []
    for key, name, data, overwrite in planned:
        cur = getv(key, name)
        if key == ROOT + "\\.form" and name == "":
            if cur != "NetBeans.Form":
                wrong.append((key, name, cur))
            continue
        if cur is None:
            missing.append((key, name))
        elif cur != data:
            wrong.append((key, name, cur, data))
    check(f"register: every planned value present ({len(planned)} planned, {m_values} written)",
          not missing and not wrong, f"missing={missing[:5]} wrong={wrong[:5]}")
    check(".radsln default = RADIDE.Solution", getv(ROOT + "\\.radsln", "") == "RADIDE.Solution")
    check(".form default kept (NetBeans.Form) + RADIDE.Form in OpenWithProgids",
          getv(ROOT + "\\.form", "") == "NetBeans.Form" and getv(ROOT + "\\.form\\OpenWithProgids", "RADIDE.Form") == "")
    check(".py: no default taken, Open with added, other entry kept",
          getv(ROOT + "\\.py", "") is None and getv(ROOT + "\\.py\\OpenWithProgids", "RADIDE.SourceFile") == ""
          and getv(ROOT + "\\.py\\OpenWithProgids", "Python.File") == "")
    for ext in (".ring", ".bas", ".frm", ".vbp", ".ipynb", ".md", ".json", ".txt", ".sln", ".csproj", ".cs", ".go"):
        if getv(ROOT + f"\\{ext}\\OpenWithProgids", "RADIDE.SourceFile") != "":
            check(f"Open with {ext}", False)
            break
    else:
        check("Open with: language and project extensions", True)
    cmd = getv(ROOT + "\\RADIDE.Solution\\shell\\open\\command", "")
    exe, lead = S.launcher()
    check("open command = pythonw + launch.pyw + \"%1\"", cmd == f'"{exe}" "{lead[0]}" "%1"'
          and exe.lower().endswith("pythonw.exe") and lead[0].endswith("launch.pyw"), cmd)
    check("folder background uses %V", getv(ROOT + "\\Directory\\Background\\shell\\RADIDE\\command", "").endswith('"%V"'))
    check("context menu text", getv(ROOT + "\\*\\shell\\RADIDE", "") == "Open with RAD IDE"
          and getv(ROOT + "\\Directory\\shell\\RADIDE", "") == "Open folder in RAD IDE")
    ico = getv(ROOT + "\\RADIDE.Solution\\DefaultIcon", "")
    check("icons exist", Path(ico).is_file() and Path(S.ICON).is_file(), ico)
    u = BASE + "\\Uninstall\\RADIDE"
    check("uninstall entry", getv(u, "DisplayName") == "RAD IDE" and getv(u, "Publisher") == "Musoftware"
          and getv(u, "URLInfoAbout") == "https://musoftwares.com" and "--unregister" in getv(u, "UninstallString")
          and getv(u, "NoModify") == 1)
    check("RegisteredApplications: ours added, other kept",
          getv(BASE + "\\RegisteredApplications", "RAD IDE") == BASE + "\\RADIDE\\Capabilities"
          and getv(BASE + "\\RegisteredApplications", "Other App") == "Software\\Other\\Capabilities")
    sm = SHORTCUTS / "StartMenu" / "RAD IDE.lnk"
    check("Start Menu shortcut created", sm.is_file() and str(sm) in st["files"])
    check("existing Desktop shortcut not overwritten", dummy.read_bytes() == b"not ours" and str(dummy) not in st["files"])

    # ---- unregister restores exactly
    r = S.unregister(t)
    after = dump(BASE)
    check("unregister: test tree identical to before", after == before,
          f"extra={set(after) - set(before)} missing={set(before) - set(after)}")
    check("unregister: .radsln restored", getv(ROOT + "\\.radsln", "") == "OtherApp.Solution")
    check("unregister: Start Menu shortcut removed, other shortcut kept", not sm.exists() and dummy.exists())
    check("unregister: status not registered", not r["registered"] and r["removed"]["restored"] >= 1, str(r)[:200])

    # ---- re-registration is clean; a value changed by the user afterwards is kept
    S.register(opts, t)
    S.register(opts, t)                         # again: undoes the first one before writing
    setv(ROOT + "\\*\\shell\\RADIDE", "", "Edited by the user")
    S.unregister(t)
    after2 = dump(BASE)
    kept = getv(ROOT + "\\*\\shell\\RADIDE", "") == "Edited by the user"
    extra = {k: v for k, v in after2.items() if k not in before}
    check("value edited by someone else is kept (and only its key)", kept and
          set(extra) == {ROOT + "\\*\\shell\\RADIDE"}, str(extra)[:300])
    winreg.DeleteValue(winreg.OpenKey(HK, ROOT + "\\*\\shell\\RADIDE", 0, winreg.KEY_WRITE), "")
    winreg.DeleteKey(HK, ROOT + "\\*\\shell\\RADIDE")
    check("after removing it: identical to before", dump(BASE) == before)

    # ---- the command line: python -m radide --register / --shell-status / --unregister (test root via env)
    py = str(REPO / ".venv" / "Scripts" / "python.exe")
    env = dict(os.environ)
    p1 = subprocess.run([py, "-m", "radide", "--register"], cwd=REPO, env=env, capture_output=True, text=True, timeout=120)
    p2 = subprocess.run([py, "-m", "radide", "--shell-status"], cwd=REPO, env=env, capture_output=True, text=True, timeout=120)
    ok_reg = p1.returncode == 0 and "registered" in p1.stdout and getv(ROOT + "\\.radproj", "") == "RADIDE.Project"
    p3 = subprocess.run([py, "-m", "radide", "--unregister", "--quiet"], cwd=REPO, env=env, capture_output=True,
                        text=True, timeout=120)
    check("CLI --register / --shell-status / --unregister --quiet", ok_reg and "is registered" in p2.stdout
          and p3.returncode == 0 and p3.stdout == "" and dump(BASE) == before, p1.stdout + p1.stderr + p2.stdout)

    # ---- partial options
    S.register({"file_assoc": False, "open_with": False, "context_menu": True, "start_menu": False,
                "desktop": False, "uninstall_entry": False}, t)
    check("context menus only: no ProgIDs, no Open with, no uninstall entry",
          getv(ROOT + "\\RADIDE.Solution", "") is None and getv(ROOT + "\\.txt\\OpenWithProgids", "RADIDE.SourceFile") is None
          and getv(BASE + "\\Uninstall\\RADIDE", "DisplayName") is None
          and getv(ROOT + "\\Directory\\shell\\RADIDE", "") == "Open folder in RAD IDE")
    S.unregister(t)
    check("partial: identical to before", dump(BASE) == before)

    check("real HKCU locations unchanged", real_snapshot() == real_before)
    inno = "\n".join(S.inno_lines())
    check("installer lines call --register / --unregister", "--register --quiet --no-uninstall-entry" in inno
          and "--unregister --quiet" in inno)
    delete_tree(BASE)
    shutil.rmtree(SHORTCUTS, ignore_errors=True)
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
