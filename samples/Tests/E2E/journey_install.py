"""J6: the installer and the updater of the REAL release, per user, in <scratch> only.

    install version N silently (/CURRENTUSER /DIR=<scratch> /TASKS= /NOICONS) -> first start of the installed exe
    -> Help > Check for Updates against a local fake release server (RADIDE_UPDATE_API) -> Update Now -> the IDE
    closes, the setup runs, the new version starts by itself with the same settings -> Help > Install Another
    Version (rollback to N) -> the setup of N+1 while an IDE is still running (it must close it and finish) ->
    uninstall.

Isolation: never the user's installation (C:\\Program Files\\RADIDE) or settings: the per-user install goes into
<scratch>\\inst (refused when RAD IDE is already installed for this user elsewhere), the IDE runs with the test
settings organisation RADIDE-TEST-E2E-J6 (registry key removed at the end), LOCALAPPDATA in scratch (downloads,
logs, the pyroot junction), no Start Menu folder, no shell integration tasks.
N+1 is the same build packaged with a higher version (tools/build_ide_release.py --reuse --version X)."""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import re
import shutil
import subprocess
import threading
import time
import winreg
from pathlib import Path

from radauto import IDE, Report, check
import e2e_common as C

APP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{6C2E8F4A-3B71-4D0E-9A5C-7F1D2E8B4A90}_is1"
ORG = "RADIDE-TEST-E2E-J6"


def reg(name: str):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_KEY) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def version_of(p: Path) -> str:
    m = re.search(r"RADIDE-(\d+\.\d+\.\d+)", p.name)
    return m.group(1) if m else ""


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class FakeGitHub:
    def __init__(self, folder: Path, setups: list[Path]):
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        for s in setups:
            dst = folder / s.name
            if not dst.exists():
                try:
                    os.link(s, dst)
                except OSError:
                    shutil.copy2(s, dst)
        (folder / "SHA256SUMS.txt").write_text("".join(f"{sha(s)}  {s.name}\n" for s in setups), encoding="utf-8")
        d = str(folder)

        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=d, **kw)

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        rels = []
        for s in sorted(setups, key=lambda p: [int(x) for x in version_of(p).split(".")], reverse=True):
            v = version_of(s)
            rels.append({"tag_name": f"v{v}", "name": f"RAD IDE {v}", "body": f"## {v}\n- E2E release",
                         "draft": False, "prerelease": False, "published_at": "2026-11-22T00:00:00Z",
                         "html_url": f"{self.base}/v{v}",
                         "assets": [{"name": n, "browser_download_url": f"{self.base}/{n}",
                                     "size": (folder / n).stat().st_size} for n in (s.name, "SHA256SUMS.txt")]})
        (folder / "releases.json").write_text(json.dumps(rels), encoding="utf-8")
        self.api = f"{self.base}/releases.json"

    def close(self):
        self.httpd.shutdown()


def wait_setups_gone(timeout: float = 1200) -> None:
    """No RAD IDE setup (started by the updater) is still running."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout.lower()
        if "radide-" not in out or "setup" not in out:
            return
        if not [ln for ln in out.splitlines() if ln.startswith('"radide-') and "setup" in ln]:
            return
        time.sleep(3)
    raise AssertionError("a RAD IDE setup is still running")


def j6_install_update(env: C.Env, rep: Report):
    new_setup = getattr(env, "next_setup", None)
    old_setup = env.setup
    if not old_setup or not old_setup.is_file():
        rep.skip_rest(["J6 (all steps)"], "no --setup given")
        return
    inst = env.scratch / "inst"
    local = env.scratch / "j6-localappdata"
    existing = reg("InstallLocation")
    if existing and not str(existing).lower().startswith(str(env.scratch).lower()):
        rep.skip_rest(["J6 (all steps)"], f"RAD IDE is installed for this user in {existing}: not touched")
        return
    if (inst / "unins000.exe").is_file():                 # a previous run's leftover in scratch
        subprocess.run([str(inst / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300)
    shutil.rmtree(inst, ignore_errors=True)
    local.mkdir(parents=True, exist_ok=True)
    # "an older release" for Install Another Version: the N build published as 0.0.x (the N+1 package reports the
    # same internal version as N, so N itself is not offered as "another" version by the dialog)
    serve = env.scratch / "j6-serve"
    serve.mkdir(parents=True, exist_ok=True)
    older = serve / "RADIDE-0.0.9-setup-win64.exe"
    if not older.exists():
        try:
            os.link(old_setup, older)
        except OSError:
            shutil.copy2(old_setup, older)
    gh = FakeGitHub(serve, [p for p in (old_setup, new_setup, older) if p and p.is_file()])
    base_env = {"LOCALAPPDATA": str(local), "RADIDE_SETTINGS_ORG": ORG, "RADIDE_UPDATE_API": gh.api,
                "RADIDE_PYTHON": C.real_python()}
    st: dict = {}
    vN, vN1 = version_of(old_setup), version_of(new_setup) if new_setup else ""

    def run_setup(setup: Path, log: str, extra=()):
        r = subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
                            f"/DIR={inst}", "/TASKS=", "/NOICONS", f"/LOG={env.scratch / 'logs' / log}", *extra],
                           timeout=900, env=dict(os.environ, LOCALAPPDATA=str(local)))
        return r.returncode

    def install():
        (env.scratch / "logs").mkdir(parents=True, exist_ok=True)
        t = time.monotonic()
        code = run_setup(old_setup, f"setup-{vN}.log")
        check(code == 0 and (inst / "RADIDE.exe").is_file(), f"setup exit {code}")
        check(reg("DisplayVersion") == vN, f"uninstall entry {reg('DisplayVersion')}")
        check(not (inst / "portable.flag").exists(), "an installed copy must not be portable")
        return f"{time.monotonic() - t:.0f}s into {inst}"
    if not rep.step(f"install {vN} per user (silent)", install, critical=True):
        return

    def launch(tag):
        return C.launch(env, f"J6-{tag}", extra_env=base_env, exe=str(inst / "RADIDE.exe"))

    def first_start():
        ide = launch("first")
        rep.ide = ide
        st["ide"] = ide
        h = ide.call("hello")
        check(h["frozen"] and not h["portable"] and Path(h["install_dir"]) == inst, f"{h}")
        check(h["org"] == ORG, f"settings organisation {h['org']}")
        ide.call("settings", values={"e2e/marker": "keep-me", "options/theme": "Light"})
        time.sleep(4)
        C.no_internal_errors(ide)
        rep.shot("installed first start")
        return f"{h['version']} python={h['python']}"
    if not rep.step("installed IDE starts (frozen, not portable, test settings)", first_start):
        return
    if not new_setup:
        rep.skip_rest(["Check for Updates -> Update Now", "new version starts by itself", "settings kept",
                       "Install Another Version (rollback)", "setup while an old IDE runs"], "no next-version setup")
    else:
        def update():
            ide = st["ide"]
            ide.call("trigger", path="Help/Check for Updates...")
            d = ide.wait_dialog("Update", timeout=60)
            rep.shot("update dialog", sel={"dialog": d["title"]})
            check(vN1 in " ".join(d["labels"]), f"dialog does not offer {vN1}: {d['labels'][:3]}")
            ide.call("press", button="Update Now", dialog=d["title"])
            q = ide.wait_dialog(text="downloaded and checked", timeout=180)
            st["old_pid"] = ide.proc.pid
            ide.call("press", button="Yes", dialog=q["title"])
            ide.close()
            ide.proc.wait(120)
            return f"{q.get('text', q.get('title', ''))[:80]}; old IDE exited"
        if rep.step(f"Help > Check for Updates -> {vN1} -> Update Now -> Yes: the IDE closes", update):
            def relaunched():
                ide = st["ide"]
                t = time.monotonic()
                ide2 = IDE(ide.pipe, ide.token)                # the relaunched IDE inherits the channel settings
                ide2.wait_for(lambda: ide2.try_call("hello"), 1200, step=3, desc="new IDE answers (setup done)")
                wait_setups_gone()
                ver = C.wait_file_text(inst / "VERSION.txt", vN1, 30)
                st["ide"] = ide2
                rep.ide = ide2
                check(reg("DisplayVersion") == vN1, f"uninstall entry {reg('DisplayVersion')}")
                return f"VERSION.txt {ver}; the new IDE answered after {time.monotonic() - t:.0f}s"
            if rep.step("the setup runs and the new version starts by itself", relaunched):
                rep.step("settings kept across the update",
                         lambda: check(st["ide"].call("settings", keys=["e2e/marker"])["e2e/marker"] == "keep-me",
                                       "marker lost") and "e2e/marker = keep-me")

                def rollback():
                    ide = st["ide"]
                    ide.call("trigger", path="Help/Install Another Version...")
                    d = ide.wait_dialog("Version", timeout=60)
                    tree = ide.wait_for(lambda: (lambda w: w if any("0.0.9" in x for x in w.get("items", [])) else None)(
                        ide.call("widget", sel={"cls": "QTreeWidget", "title": d["title"]})), 60,
                        desc="release list")
                    ide.call("select_item", sel={"cls": "QTreeWidget", "title": d["title"]}, text="0.0.9", async_=False)
                    time.sleep(0.5)
                    rep.shot("install another version", sel={"dialog": d["title"]})
                    ide.call("press", button="Install", dialog=d["title"])
                    u = ide.wait_dialog(text="0.0.9", timeout=60)
                    if any("install this version" in b.lower() for b in u["buttons"]):
                        ide.call("press", button="Install This Version", dialog=u["title"])
                        u = ide.wait_dialog(text="downloaded and checked", timeout=180)
                    ide.call("press", button="Yes", dialog=u["title"])
                    ide.close()
                    time.sleep(5)
                    ide3 = IDE(ide.pipe, ide.token)
                    ide3.wait_for(lambda: ide3.try_call("hello"), 1200, step=3, desc="rolled-back IDE answers")
                    wait_setups_gone()
                    ver = C.wait_file_text(inst / "VERSION.txt", vN, 30)
                    st["ide"] = ide3
                    rep.ide = ide3
                    return f"items {tree.get('items', [])[:3]}; VERSION.txt {ver}"
                rep.step("Help > Install Another Version -> an older release (rollback: N+1 -> N files)", rollback)

        def while_running():
            ide = st.get("ide")
            if ide is None or not ide.try_call("hello"):
                ide = launch("running")
                st["ide"] = ide
            pid = ide.call("hello")["pid"]
            t = time.monotonic()
            code = run_setup(new_setup, "setup-while-running.log")
            dt = time.monotonic() - t
            check(code == 0, f"setup exit {code} with an IDE running")
            alive = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True,
                                   text=True).stdout
            check(str(pid) not in alive, "the running IDE was not closed")
            check((inst / "VERSION.txt").read_text().strip() == vN1, "not updated")
            ide.close()
            ide4 = launch("after")
            st["ide"] = ide4
            rep.ide = ide4
            check(ide4.call("settings", keys=["e2e/marker"])["e2e/marker"] == "keep-me", "settings lost")
            return f"setup closed the running IDE and finished in {dt:.0f}s; new IDE starts, settings kept"
        rep.step(f"setup {vN1} while an IDE runs: it closes the IDE, installs, nothing damaged", while_running)

    def uninstall():
        wait_setups_gone()
        if st.get("ide"):
            st["ide"].quit()
            rep.ide = None
        un = inst / "unins000.exe"
        check(un.is_file(), "no uninstaller")
        r = subprocess.run([str(un), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300)
        check(r.returncode == 0, f"uninstaller exit {r.returncode}")
        for _ in range(60):
            if not (inst / "RADIDE.exe").exists() and reg("DisplayVersion") is None:
                break
            time.sleep(1)
        check(not (inst / "RADIDE.exe").exists(), "RADIDE.exe still there")
        check(reg("DisplayVersion") is None, "uninstall entry still there")
        return "removed (folder + uninstall entry)"
    rep.step("uninstall (silent): files and uninstall entry removed", uninstall)
    gh.close()
    try:                                    # the test settings key
        subprocess.run(["reg", "delete", rf"HKCU\Software\{ORG}", "/f"], capture_output=True)
    except OSError:
        pass
