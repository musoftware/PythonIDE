"""J9: a complete desktop application built entirely through the IDE UI, like a real user: "Customer Manager"
(Python Tkinter) - 3 forms (main list + edit dialog + about), a menu bar made with the Menu Editor, a status bar,
SQLite storage, validation with message boxes, search, CSV export (Arabic text), settings saved as JSON.

Then: F5 and every feature exercised through the running program's own window (Win32 input on the hidden desktop,
PrintWindow screenshots), a breakpoint in a handler (Locals), a deliberate syntax error fixed from the Error List
(double-click jumps to the line), Publish (PyInstaller + Inno Setup), install per user, the installed program
used again on its own, uninstall."""
from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import time
from pathlib import Path

from radauto import Report, check
import e2e_common as C

DB_PY = '''"""Customer storage of Customer Manager: SQLite + CSV export + JSON settings."""
import csv
import json
import os
import re
import sqlite3


def folder():
    d = os.environ.get("CUSTMGR_DIR") or os.path.join(os.environ.get("APPDATA") or ".", "CustomerManagerE2E")
    os.makedirs(d, exist_ok=True)
    return d


def connect():
    con = sqlite3.connect(os.path.join(folder(), "customers.db"))
    con.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                "phone TEXT, city TEXT)")
    return con


def validate(name, phone):
    if not name:
        return "Name is required / الاسم مطلوب"
    if phone and not re.fullmatch(r"[0-9 +-]+", phone):
        return "Phone must contain digits only / رقم الهاتف أرقام فقط"
    return ""


def add(name, phone, city):
    with connect() as con:
        con.execute("INSERT INTO customers (name, phone, city) VALUES (?, ?, ?)", (name, phone, city))


def search(text=""):
    with connect() as con:
        like = f"%{text}%"
        return con.execute("SELECT id, name, phone, city FROM customers WHERE name LIKE ? OR phone LIKE ? "
                           "OR city LIKE ? ORDER BY name", (like, like, like)).fetchall()


def count():
    with connect() as con:
        return con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]


def export_csv():
    path = os.path.join(folder(), "customers.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Phone", "City"])
        for _id, name, phone, city in search(""):
            w.writerow([name, phone, city])
    return path


def load_settings():
    try:
        with open(os.path.join(folder(), "settings.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(data):
    with open(os.path.join(folder(), "settings.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
'''

MAIN_PY = '''from tkinter import messagebox  # noqa: F401

from Form1_designer import Form1Designer, EventArgs  # noqa: F401
from frmEdit import frmEdit
from frmAbout import frmAbout
import db


class Form1(Form1Designer):
    """Customer Manager - main window."""

    def Form1_Load(self):
        self.settings = db.load_settings()
        self.txtSearch_var.set(self.settings.get("search", ""))
        self.refresh()

    def refresh(self):
        rows = db.search(self.txtSearch_var.get().strip())
        self.lstCustomers.delete(0, "end")
        for r in rows:
            self.lstCustomers.insert("end", f"{r[1]}  |  {r[2]}  |  {r[3]}")
        total = db.count()
        self.root.title(f"Customer Manager - {total} customers, {len(rows)} shown")
        self.sbInfo.config(text=f"{len(rows)} / {total}")
        return rows

    def btnSearch_Click(self):
        text = self.txtSearch_var.get().strip()
        rows = self.refresh()
        self.settings["search"] = text
        db.save_settings(self.settings)
        return rows

    def btnAdd_Click(self):
        dlg = frmEdit(master=self.root)
        dlg.root.transient(self.root)
        dlg.root.grab_set()
        self.root.wait_window(dlg.root)
        self.refresh()

    def btnExport_Click(self):
        path = db.export_csv()
        self.sbInfo.config(text=f"exported: {path}")
        self.root.title(self.root.title() + " - exported")

    def btnAbout_Click(self):
        dlg = frmAbout(master=self.root)
        dlg.root.transient(self.root)
        dlg.root.grab_set()
        self.root.wait_window(dlg.root)
%MENU_HANDLERS%

if __name__ == "__main__":
    Form1().show()
'''

EDIT_PY = '''from tkinter import messagebox

from frmEdit_designer import frmEditDesigner, EventArgs  # noqa: F401
import db


class frmEdit(frmEditDesigner):
    """Add a customer (validated)."""

    def btnOK_Click(self):
        name = self.txtName_var.get().strip()
        phone = self.txtPhone_var.get().strip()
        city = self.txtCity_var.get().strip()
        err = db.validate(name, phone)
        if err:
            messagebox.showwarning("Customer", err, parent=self.root)
            return
        db.add(name, phone, city)
        self.root.destroy()

    def btnCancel_Click(self):
        self.root.destroy()
'''

ABOUT_PY = '''from frmAbout_designer import frmAboutDesigner, EventArgs  # noqa: F401


class frmAbout(frmAboutDesigner):
    def btnClose_Click(self):
        self.root.destroy()
'''

AR_NAME, AR_CITY = "أحمد علي", "القاهرة"


def _kids_sorted(ide, hwnd, kind):
    kids = C.find_kids(ide, hwnd)
    if kind == "edit":
        ks = [k for k in kids if k["cls"] == "TkChild" and 16 <= k["rect"][3] <= 30]
    else:
        ks = [k for k in kids if k["cls"].lower() == "button"]
    return sorted(ks, key=lambda k: (k["rect"][1] // 8, k["rect"][0]))


def _type_into(ide, hwnd, text):
    ide.call("win32_click", hwnd=hwnd)
    ide.call("win32_key", hwnd=hwnd, keys="Home, Shift+End, Delete")
    if text:
        ide.call("win32_type", hwnd=hwnd, value=text)


def _msgbox(ide, timeout=15):
    """A Win32 message box (#32770) of the program: (hwnd, its text)."""
    w = ide.wait_for(lambda: next((x for x in ide.call("win32_windows") if x["cls"] == "#32770"), None), timeout,
                     desc="message box")
    texts = [k["text"] for k in C.find_kids(ide, w["hwnd"]) if k["cls"] == "Static" and k["text"]]
    return w, " ".join(texts)


def _close_msgbox(ide, w):
    btn = next((k for k in C.find_kids(ide, w["hwnd"]) if k["cls"].lower() == "button"), None)
    if btn is not None:
        ide.call("win32_click", hwnd=btn["hwnd"], how="bm_click")
    else:
        ide.call("win32_key", hwnd=w["hwnd"], keys="Return")
    ide.wait_for(lambda: not [x for x in ide.call("win32_windows") if x["hwnd"] == w["hwnd"]], 10, desc="box closed")


def menu_click(ide, hwnd, path: str, by_position: str):
    """Menu bar item by text; by position when the toolkit draws its own menu texts (Tk: owner-drawn items)."""
    try:
        return ide.call("win32_menu", hwnd=hwnd, path=path)
    except Exception:  # noqa: BLE001
        return ide.call("win32_menu", hwnd=hwnd, path=by_position)


def exercise_program(ide, rep: Report, P: str, data: Path, pid=None, prefix="F5") -> None:
    """Use every feature of the running Customer Manager through its own window."""
    st = {}

    def main_window():
        w = C.wait_window(ide, "Customer Manager", timeout=240, pid=pid)
        st["w"] = w
        rep.shot(f"{P}{prefix} main window", hwnd=w["hwnd"])
        check("0 customers" in w["text"] or "customers" in w["text"], w["text"])
        return w["text"]
    if not rep.step(f"{P}{prefix}: main window", main_window):
        return
    W = st["w"]["hwnd"]

    def title():
        return ide.call("win32_text", hwnd=W)["text"]

    def edit_window():
        return C.wait_window(ide, "Edit Customer", timeout=20, pid=pid)

    def add_customer(name, phone, city, expect_error=""):
        btns = _kids_sorted(ide, W, "button")              # Search, Add (row 1), Export, About (row 2)
        ide.call("win32_click", hwnd=btns[1]["hwnd"])
        ew = edit_window()
        eds = _kids_sorted(ide, ew["hwnd"], "edit")
        check(len(eds) >= 3, f"edit form fields: {len(eds)}")
        for h, v in zip(eds, (name, phone, city)):
            _type_into(ide, h["hwnd"], v)
        rep.shot(f"{P}{prefix} edit form {name or 'empty'}", hwnd=ew["hwnd"])
        ebtns = _kids_sorted(ide, ew["hwnd"], "button")
        ide.call("win32_click", hwnd=ebtns[0]["hwnd"])        # OK
        if expect_error:
            box, text = _msgbox(ide)
            rep.shot(f"{P}{prefix} validation box", hwnd=box["hwnd"])
            _close_msgbox(ide, box)
            ide.call("win32_click", hwnd=ebtns[1]["hwnd"])    # Cancel
            ide.wait_for(lambda: not ide.call("win32_windows", title="Edit Customer", pid=pid), 15,
                         desc="edit form closed")
            check(expect_error.lower() in text.lower(), f"message box text {text!r}")
            return text
        ide.wait_for(lambda: not ide.call("win32_windows", title="Edit Customer", pid=pid), 15, desc="saved")
        return title()

    rep.step(f"{P}{prefix}: Add with an empty name -> validation message box",
             lambda: add_customer("", "", "", expect_error="Name is required"))
    rep.step(f"{P}{prefix}: Add with letters in the phone -> validation message box",
             lambda: add_customer("Bad Phone", "abc", "", expect_error="digits"))
    rep.step(f"{P}{prefix}: add an Arabic customer through the edit form",
             lambda: check("1 customers" in add_customer(AR_NAME, "0100 123", AR_CITY), title()) and title())
    rep.step(f"{P}{prefix}: add a second customer", lambda: check("2 customers" in add_customer(
        "Sara Ali", "0111", "Giza"), title()) and title())

    def search():
        eds = _kids_sorted(ide, W, "edit")
        _type_into(ide, eds[0]["hwnd"], "Sara")
        ide.call("win32_click", hwnd=_kids_sorted(ide, W, "button")[0]["hwnd"])
        t = C.wait_title(ide, W, "1 shown", 15)
        rep.shot(f"{P}{prefix} search", hwnd=W)
        return t
    rep.step(f"{P}{prefix}: search 'Sara' -> 1 shown", search)

    def export():
        ide.call("win32_click", hwnd=_kids_sorted(ide, W, "button")[2]["hwnd"])
        C.wait_title(ide, W, "exported", 15)
        rows = list(csv.reader((data / "customers.csv").read_text(encoding="utf-8-sig").splitlines()))
        names = [r[0] for r in rows[1:]]
        check(AR_NAME in names and "Sara Ali" in names, f"CSV rows {rows}")
        return f"CSV {len(rows) - 1} rows, Arabic intact: {AR_NAME in names}"
    rep.step(f"{P}{prefix}: Export CSV (UTF-8, Arabic intact)", export)

    def about():
        menu_click(ide, W, "Help/About", "#1/#0")
        a = C.wait_window(ide, "About", timeout=15, pid=pid)
        rep.shot(f"{P}{prefix} about", hwnd=a["hwnd"])
        ide.call("win32_click", hwnd=_kids_sorted(ide, a["hwnd"], "button")[0]["hwnd"])
        ide.wait_for(lambda: not ide.call("win32_windows", title="About Customer Manager", pid=pid), 15,
                     desc="about closed")
        return "menu Help > About -> About form -> Close"
    rep.step(f"{P}{prefix}: menu Help > About opens the About form", about)

    def db_and_settings():
        con = sqlite3.connect(str(data / "customers.db"))
        rows = con.execute("SELECT name, phone, city FROM customers ORDER BY id").fetchall()
        con.close()
        check(rows == [(AR_NAME, "0100 123", AR_CITY), ("Sara Ali", "0111", "Giza")], f"DB rows {rows}")
        s = json.loads((data / "settings.json").read_text(encoding="utf-8"))
        check(s.get("search") == "Sara", f"settings {s}")
        return f"DB {len(rows)} rows (exact Arabic), settings {s}"
    rep.step(f"{P}{prefix}: SQLite rows + settings.json on disk", db_and_settings)

    def close():
        menu_click(ide, W, "File/Exit", "#0/#1")
        ide.wait_for(lambda: not ide.call("win32_windows", title="Customer Manager", pid=pid), 20,
                     desc="program closed")
        return "File > Exit closed it"
    rep.step(f"{P}{prefix}: File > Exit", close)


def _menu(ide, rep, P):
    """MenuStrip + Menu Editor: File (Export CSV, Exit), Help (About) - typed like a user."""
    r = ide.request("designer_place", {"type": "MenuStrip", "x": 0, "y": 0}, async_job=True)   # opens the modal
    job = r["result"]["job"]                                                                  # Menu Editor
    ide.wait_dialog("Menu Editor", timeout=15)

    def add(button, text):
        ide.call("press", button=button, dialog="Menu Editor", async_=False)
        time.sleep(0.3)
        ide.call("type", text=text, clear=True)
        ide.call("key", keys="Return")
        time.sleep(0.2)

    def select(text):
        ide.call("select_item", sel={"cls": "QTreeWidget", "title": "Menu Editor"}, text=text, async_=False)
    add("Add Menu", "&File")
    add("Add Item", "Export CSV")
    select("&File")
    add("Add Item", "Exit")
    add("Add Menu", "&Help")
    add("Add Item", "About")
    tree = ide.call("widget", sel={"cls": "QTreeWidget", "title": "Menu Editor"})["items"]
    rep.shot("menu editor", sel={"dialog": "Menu Editor"})
    ide.call("press", button="OK", dialog="Menu Editor")
    ide.wait_for(lambda: ide.call("job", job=job)["done"], 20, desc="menu strip placed")
    return tree


def _menu_names(ide) -> dict:
    """Text -> handler name of the menu items (as the IDE named them)."""
    ctrls = ide.call("designer_controls", all_props=True)["controls"]
    ms = next(c for c in ctrls if c["type"] == "MenuStrip")
    out = {}

    def walk(items):
        for it in items or []:
            if it.get("Name"):
                out[it.get("Text", "").replace("&", "")] = it["Name"]
            walk(it.get("Items"))
    walk(ms["props"].get("Items"))
    return out


def j9_customer_manager(env: C.Env, rep: Report):
    C.portable_copy(env)
    root = env.scratch / "projects" / "J9"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    data = env.scratch / "j9-data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir(parents=True)
    ide = C.launch(env, "J9")
    rep.ide = ide
    P = "CustomerManager: "
    st: dict = {}

    def create():
        info = ide.call("new_project", language="python-tk", name="CustomerManager", location=str(root))
        st["folder"] = Path(info["folder"])
        ide.call("set_property", name="", prop="Text", value="Customer Manager")
        ide.call("set_property", name="", prop="Width", value="640")
        ide.call("set_property", name="", prop="Height", value="460")
        return info["folder"]
    if not rep.step(P + "new Python Tk project", create, critical=True):
        return

    def main_form():
        tree = _menu(ide, rep, P)
        place = [("TextBox", 16, 40, 300, 24, "txtSearch"), ("Button", 330, 40, 100, 26, "btnSearch"),
                 ("Button", 440, 40, 100, 26, "btnAdd"), ("ListBox", 16, 76, 600, 270, "lstCustomers"),
                 ("Button", 16, 360, 110, 28, "btnExport"), ("Button", 140, 360, 110, 28, "btnAbout"),
                 ("StatusBar", 0, 400, 640, 22, "sbInfo")]
        for t, x, y, w, h, n in place:
            ide.call("designer_place", type=t, x=x, y=y, w=w, h=h, name=n)
        for n, txt in (("btnSearch", "Search / بحث"), ("btnAdd", "Add..."), ("btnExport", "Export CSV"),
                       ("btnAbout", "About")):
            ide.call("set_property", name=n, prop="Text", value=txt)
        rep.shot(P + "main form designed")
        names = [c["name"] for c in ide.call("designer_controls")["controls"]]
        check({"txtSearch", "lstCustomers", "sbInfo"} <= set(names), names)
        st["menu"] = _menu_names(ide)
        return {"menu": tree, "handlers": st["menu"]}
    rep.step(P + "main form: menu (Menu Editor), search box, buttons, list, status bar", main_form)

    def add_form(name, title, controls):
        ide.call("trigger", path="Project/Add Windows Form...")
        d = ide.wait_dialog("Add Windows Form", timeout=15)
        ide.call("set_value", sel={"cls": "QLineEdit", "title": d["title"]}, value=name)
        ide.call("press", button="OK", dialog=d["title"])
        ide.wait_for(lambda: name in (ide.call("project") or {}).get("forms", []), 20, desc=f"{name} added")
        time.sleep(0.5)
        ide.call("set_property", name="", prop="Text", value=title, form=name)
        for t, x, y, w, h, n, txt in controls:
            ide.call("designer_place", type=t, x=x, y=y, w=w, h=h, name=n, form=name)
            if txt:
                ide.call("set_property", name=n, prop="Text", value=txt, form=name)
        rep.shot(P + f"{name} designed")
        return [c["name"] for c in ide.call("designer_controls", form=name)["controls"]]

    rep.step(P + "Project > Add Windows Form: frmEdit (validated edit dialog)", lambda: add_form(
        "frmEdit", "Edit Customer", [
            ("Label", 16, 20, 90, 20, "lblName", "Name / الاسم"), ("TextBox", 120, 18, 220, 24, "txtName", ""),
            ("Label", 16, 60, 90, 20, "lblPhone", "Phone"), ("TextBox", 120, 58, 220, 24, "txtPhone", ""),
            ("Label", 16, 100, 90, 20, "lblCity", "City / المدينة"), ("TextBox", 120, 98, 220, 24, "txtCity", ""),
            ("Button", 120, 150, 90, 28, "btnOK", "OK"), ("Button", 230, 150, 90, 28, "btnCancel", "Cancel")]))
    rep.step(P + "Project > Add Windows Form: frmAbout", lambda: add_form(
        "frmAbout", "About Customer Manager", [
            ("Label", 16, 20, 280, 40, "lblInfo", "Customer Manager 1.0 - مدير العملاء"),
            ("Button", 110, 80, 90, 28, "btnClose", "Close")]))

    def module():
        ide.call("trigger", path="Project/Add Module...")
        d = ide.wait_dialog("Add Module", timeout=15)
        ide.call("set_value", sel={"cls": "QLineEdit", "title": d["title"]}, value="db")
        ide.call("press", button="OK", dialog=d["title"])
        ide.wait_for(lambda: any(m.lower().startswith("db.") for m in (ide.call("project") or {}).get("modules", [])),
                     20, desc="db module")
        ide.call("editor_set_text", text=DB_PY)
        return ide.call("project")["modules"]
    rep.step(P + "Project > Add Module: db (SQLite, CSV, settings)", module)

    def code():
        handlers = []
        names = st.get("menu", {})
        calls = {"Export CSV": "self.btnExport_Click()", "Exit": "self.root.destroy()", "About": "self.btnAbout_Click()"}
        for text, call in calls.items():
            n = names.get(text)
            if n:
                handlers.append(f"\n    def {n}_Click(self):\n        {call}\n")
        check(len(handlers) == 3, f"menu handler names {names}")
        ide.call("open_form", name="Form1", view="code")
        ide.call("editor_set_text", text=MAIN_PY.replace("%MENU_HANDLERS%", "".join(handlers)))
        ide.call("open_form", name="frmEdit", view="code")
        ide.call("editor_set_text", text=EDIT_PY)
        ide.call("open_form", name="frmAbout", view="code")
        ide.call("editor_set_text", text=ABOUT_PY)
        check(ide.call("save_all"), "save failed")
        return "Form1.py, frmEdit.py, frmAbout.py written"
    rep.step(P + "write the code of the three forms", code)

    def check_clean():
        ide.call("output", clear=True)
        ide.call("trigger", path="Project/Check for Errors", async_=False)
        time.sleep(3)
        errs = [e for e in ide.call("errors") if e["kind"].lower().startswith("err")]
        check(not errs, f"errors: {errs[:5]}")
        return "no errors"
    rep.step(P + "Project > Check for Errors: clean", check_clean)

    def error_list():
        ide.call("open_module", filename="db.py")
        t = ide.call("editor_text")["text"]
        ide.call("editor_set_text", text=t + "\n\ndef broken(:\n    pass\n")
        ide.call("save_all")
        bad_line = len((t + "\n\ndef broken(:").splitlines())
        ide.call("trigger", path="Project/Check for Errors", async_=False)
        rows = ide.wait_for(lambda: [e for e in ide.call("errors") if "db.py" in e["file"]], 30, desc="Error List row")
        rep.shot(P + "error list", sel="@error_list")
        ide.call("open_form", name="Form1", view="code")         # somewhere else first
        ide.call("select_item", sel="@error_list", text=rows[0]["description"][:20], column=1, dclick=True,
                 async_=False)
        time.sleep(1)
        tabs = ide.call("tabs")
        cur = ide.call("editor_text")
        check("db.py" in tabs["current_title"], f"double-click opened {tabs['current_title']}")
        check(abs(cur["line"] + 1 - int(rows[0]["line"])) <= 1 and abs(int(rows[0]["line"]) - bad_line) <= 1,
              f"caret line {cur['line'] + 1}, error line {rows[0]['line']}, real {bad_line}")
        ide.call("editor_set_text", text=t)
        ide.call("save_all")
        ide.call("trigger", path="Project/Check for Errors", async_=False)
        time.sleep(3)
        left = [e for e in ide.call("errors") if "db.py" in e["file"]]
        check(not left, f"still errors: {left}")
        return f"{rows[0]['description'][:60]} line {rows[0]['line']} -> jumped, fixed"
    rep.step(P + "deliberate syntax error -> Error List -> double-click jumps to the line -> fix", error_list)

    def run():
        ide.call("set_env", set={"CUSTMGR_DIR": str(data)})
        ide.call("output", clear=True)
        ide.call("activate_tab", title="Form1.form")
        ide.call("key", keys="Ctrl+F5", sel="@tabs", async_=True)          # Start Without Debugging
        return "started"
    if rep.step(P + "Ctrl+F5 (start without debugging)", run):
        exercise_program(ide, rep, P, data)
        if ide.call("run_state")["running"]:
            ide.try_call("trigger", path="Debug/Stop Debugging")

    def debug():
        ide.call("open_form", name="Form1", view="code")
        line = ide.call("editor_find", needle="rows = self.refresh()")[0]
        ide.call("breakpoint", file="Form1.py", line=line, on=True)
        ide.call("key", keys="F5", sel="@tabs", async_=True)
        w = C.wait_window(ide, "Customer Manager", timeout=240)
        eds = _kids_sorted(ide, w["hwnd"], "edit")
        _type_into(ide, eds[0]["hwnd"], "Ahmed")
        ide.call("win32_click", hwnd=_kids_sorted(ide, w["hwnd"], "button")[0]["hwnd"])
        d = ide.wait_for(lambda: (lambda s: s if s.get("paused") else None)(ide.call("debug_state")), 60,
                         desc="breakpoint hit")
        rep.shot(P + "debugger paused")
        check(any("text" in x and "Ahmed" in x for x in d.get("locals") or []), f"Locals {d.get('locals')}")
        ide.call("breakpoint", file="Form1.py", line=line, on=False)
        ide.call("key", keys="F5", sel="@tabs", async_=True)
        time.sleep(1)
        ide.call("trigger", path="Debug/Stop Debugging")
        ide.wait_for(lambda: not ide.call("run_state")["running"], 30, desc="stopped")
        return f"paused at line {line}; locals {[x for x in d['locals'] if 'text' in x][:2]}"
    rep.step(P + "F5 with a breakpoint in btnSearch_Click: Locals show text='Ahmed'", debug)

    def publish():
        ide.call("output", clear=True)
        ide.call("trigger", path="Build/Publish / Create Installer...")
        ide.wait_dialog("Publish", timeout=30)
        ide.call("press", button="Publish", dialog="Publish")
        txt = ide.wait_output(["Publish succeeded", "Publish failed"], timeout=1200)
        import re
        m = re.search(r"Publish succeeded: (.+?\.exe)", txt)
        check(m, "publish failed: " + txt[-2000:])
        st["setup"] = Path(m.group(1).strip())
        return f"{st['setup'].name} ({st['setup'].stat().st_size // 1024} KB)"
    if not rep.step(P + "Build > Publish (PyInstaller + Inno Setup)", publish):
        ide.quit()
        return
    inst = env.scratch / "installed" / "CustomerManager"

    def install():
        import subprocess
        shutil.rmtree(inst, ignore_errors=True)
        r = subprocess.run([str(st["setup"]), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
                            f"/DIR={inst}", "/TASKS=", "/NOICONS"], timeout=600)
        check(r.returncode == 0, f"setup exit {r.returncode}")
        exes = sorted([p for p in inst.rglob("*.exe") if not p.name.lower().startswith("unins")],
                      key=lambda p: (len(p.relative_to(inst).parts), -p.stat().st_size))
        check(exes, "nothing installed")
        st["exe"] = exes[0]
        return str(exes[0].relative_to(inst))
    if rep.step(P + "install the published setup per user", install):
        data2 = env.scratch / "j9-data-installed"
        shutil.rmtree(data2, ignore_errors=True)
        data2.mkdir(parents=True)
        r = ide.call("start_process", argv=[str(st["exe"])], cwd=str(st["exe"].parent),
                     env={"CUSTMGR_DIR": str(data2)})
        exercise_program(ide, rep, P, data2, pid=None, prefix="installed exe")

        def uninstall():
            import subprocess
            if ide.call("process_status", pid=r["pid"])["returncode"] is None:      # still running: close it
                ide.try_call("win32_kill", pid=r["pid"])
                time.sleep(1)
            un = sorted(inst.glob("unins*.exe"))[-1]
            res = subprocess.run([str(un), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300)
            check(res.returncode == 0, f"uninstaller exit {res.returncode}")
            ide.wait_for(lambda: not st["exe"].exists(), 30, desc="files removed")
            return "removed"
        rep.step(P + "uninstall", uninstall)
        st["pid"] = r["pid"]
    rep.step(P + "no internal errors in the IDE", lambda: C.no_internal_errors(ide))
    ide.quit()
