"""Environment robustness - saving under bad conditions and crash safety.

    .venv\\Scripts\\python samples\\Tests\\Robustness\\Environment\\test_env_save_crash.py

1. Atomic saves (radide/safeio.py, used by Form.save / Project.save / Solution.save and the IDE's code-file
   saves): same bytes as Path.write_text; a full disk (ENOSPC injected into the write and into fsync - a real
   tiny VHD needs admin rights) leaves the old file and no temporary file; the message says "disk is full".
2. Locked files: another process holds the .form like Excel (exclusive, and FILE_SHARE_READ) -> a clear
   "locked by another program" error, the file unchanged; after the lock is gone the save works.
   Read-only file attribute, read-only folder (ACL deny on a folder this test owns - no admin) ->
   clear messages / in-place fallback; the previous version is kept as a backup outside the project.
3. Kill during save: a child process saves a big form + project.radproj in a loop, it is killed 25 times at
   random moments -> every time both files are complete (version A or B), never truncated; stale temp files
   are cleaned when the project opens. (Plain write_text is measured for comparison - INFO only.)
4. 1 GB file: check_open_size refuses it (sparse file, no disk space used) and File > Open does not read it.
5. Crash recovery (features/recovery.py) with LOCALAPPDATA / APPDATA / TEMP in an Arabic user folder:
   a real IDE edits a form + code, writes the snapshot and is killed -> the project files are unchanged,
   the next IDE restores the edits as unsaved changes; Save All writes them and removes the snapshot;
   start-up offer opens the crashed project; "Discard" removes the snapshot; a read-only project still
   gets a snapshot; Save All on a full disk fails cleanly (documents stay modified, the close is cancelled).
6. Arabic strings of the new messages.
Exit code = number of failures."""
from __future__ import annotations

import errno
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _envlib as E  # noqa: E402
from _envlib import ok  # noqa: E402

os.environ.update(E.GUI_ENV)
ROOT = E.scratch("save_crash")
# the IDE's user data (recovery, backups) of THIS test: an Arabic user name with a space
USERDIR = ROOT / f"Users {E.USER_AR}"
for sub in ("AppData/Local", "AppData/Roaming", "AppData/Local/Temp"):
    (USERDIR / sub).mkdir(parents=True, exist_ok=True)
os.environ["LOCALAPPDATA"] = str(USERDIR / "AppData/Local")
os.environ["APPDATA"] = str(USERDIR / "AppData/Roaming")
os.environ["TEMP"] = os.environ["TMP"] = str(USERDIR / "AppData/Local/Temp")
os.environ["USERPROFILE"] = str(USERDIR)

from radide import safeio  # noqa: E402
from radide.model import Form, Project  # noqa: E402
from radide.solution import Solution  # noqa: E402
from radide.workspace import create_project  # noqa: E402


def new_project(name: str, parent: Path | None = None, lang: str = "python-tk") -> Path:
    folder = (parent or ROOT) / name
    E.rmtree(folder)
    create_project(folder, name.replace(" ", ""), lang)
    f = Form.load(folder / "Form1.form")
    c = f.add("Button", 16, 16)
    c.props["Name"] = "Button1"
    c.props["Text"] = "OK"
    f.save(folder / "Form1.form")
    return folder


def temps(folder: Path) -> list[str]:
    return [p.name for p in Path(folder).glob(".*" + safeio.TMP_SUFFIX)]


# =================================================================== 1. atomic save + disk full
print("== 1. atomic saves, disk full", flush=True)
d1 = E.scratch("save_crash/atomic")
p = d1 / "a.txt"
txt = "line1\nسطر 2\n"
p.write_text(txt, encoding="utf-8")
ref = p.read_bytes()
safeio.atomic_write_text(p, txt)
ok("atomic_write_text writes the same bytes as Path.write_text (CRLF on Windows)", p.read_bytes() == ref)
safeio.atomic_write_text(p, "new")
ok("atomic replace: new content, no temp file left", p.read_text() == "new" and not temps(d1), temps(d1))

real_fsync, real_open = safeio.os.fsync, open


def enospc(*_a, **_k):
    raise OSError(errno.ENOSPC, "No space left on device")


for where in ("fsync", "write"):
    p.write_text("OLD CONTENT", encoding="utf-8")
    if where == "fsync":
        safeio.os.fsync = enospc
    else:
        import builtins

        class _Full:
            def __init__(self, f):
                self.f = f

            def __enter__(self):
                return self

            def __exit__(self, *a):
                self.f.close()

            def write(self, data):
                self.f.write(data[: len(data) // 2])        # half of it reached the disk, then: full
                raise OSError(errno.ENOSPC, "No space left on device")

            def __getattr__(self, n):
                return getattr(self.f, n)
        builtins.open = lambda f, m="r", *a, **k: _Full(real_open(f, m, *a, **k)) \
            if "w" in m and str(f).endswith(safeio.TMP_SUFFIX) else real_open(f, m, *a, **k)
    try:
        safeio.atomic_write_text(p, "NEW CONTENT " * 1000)
        err = None
    except OSError as e:
        err = e
    finally:
        safeio.os.fsync = real_fsync
        import builtins
        builtins.open = real_open
    ok(f"disk full during {where}: SaveError raised", isinstance(err, safeio.SaveError), repr(err))
    ok(f"disk full during {where}: the old file is intact", p.read_text(encoding="utf-8") == "OLD CONTENT")
    ok(f"disk full during {where}: no partial temp file left", not temps(d1), temps(d1))
    ok(f"disk full during {where}: the message says the disk is full", "disk is full" in str(err), str(err))

# model / solution saves go through safeio as well
proj_dir = new_project("Atomic Proj")
form_path = proj_dir / "Form1.form"
before = {n: (proj_dir / n).read_bytes() for n in ("Form1.form", "project.radproj")}
f = Form.load(form_path)
f.find("Button1").props["Text"] = "changed"
pr = Project.load(proj_dir)
pr.modules.append("x.py")
safeio.os.fsync = enospc
errs = []
for label, fn in (("Form.save", lambda: f.save(form_path)), ("Project.save", pr.save)):
    try:
        fn()
        errs.append((label, None))
    except OSError as e:
        errs.append((label, e))
safeio.os.fsync = real_fsync
for label, e in errs:
    ok(f"{label} on a full disk raises a readable OSError", e is not None and "disk is full" in str(e), repr(e))
ok("Form.save / Project.save on a full disk: .form and project.radproj unchanged",
   all((proj_dir / n).read_bytes() == b for n, b in before.items()))
ok("full disk: no temp files in the project folder", not temps(proj_dir), temps(proj_dir))
f.save(form_path)
ok("Form.save works again when there is space", Form.load(form_path).find("Button1").props["Text"] == "changed")
bk = safeio.recovery_root() / "backups" / safeio.folder_key(proj_dir) / "Form1.form"
ok("the previous version is kept as a backup outside the project folder",
   bk.is_file() and bk.read_bytes() == before["Form1.form"], bk)
ok("backups live under the IDE's user data (Arabic LOCALAPPDATA), not in the project",
   str(bk).startswith(os.environ["LOCALAPPDATA"]) and not list(proj_dir.glob("*.bak")))
s = Solution.implicit_for(proj_dir)
if s is not None:
    safeio.os.fsync = enospc
    try:
        s.save(proj_dir / "Sol.radsln")
        e = None
    except OSError as ex:
        e = ex
    safeio.os.fsync = real_fsync
    ok("Solution.save on a full disk: readable error, no .radsln fragment",
       e is not None and not (proj_dir / "Sol.radsln").exists(), repr(e))

# =================================================================== 2. locks, read-only
print("== 2. locked / read-only files and folders", flush=True)
lock_dir = new_project("Locked Proj")
lf = lock_dir / "Form1.form"
orig = lf.read_bytes()
for share, label in ((0, "exclusive lock"), (1, "Excel-style share-read lock")):
    child = E.lock_in_child(lf, share)
    try:
        t0 = time.time()
        try:
            ff = Form.from_dict(json.loads(orig.decode("utf-8")))
            ff.find("Button1").props["Text"] = "while locked"
            ff.save(lf)
            e = None
        except OSError as ex:
            e = ex
        dt = time.time() - t0
        ok(f"{label}: save fails with a PermissionError", isinstance(e, PermissionError), repr(e))
        ok(f"{label}: the message says the file is locked by another program", "locked by another program" in str(e), str(e))
        ok(f"{label}: gives up quickly (retries < 2 s)", dt < 2.0, f"{dt:.2f}s")
        info_msg = str(e).splitlines()[0] if e else ""
    finally:
        E.kill_tree(child)
    E.info(f"{label}: {info_msg}")
    ok(f"{label}: the file is unchanged and no temp file is left", lf.read_bytes() == orig and not temps(lock_dir),
       temps(lock_dir))
ff = Form.from_dict(json.loads(orig.decode("utf-8")))
ff.find("Button1").props["Text"] = "after unlock"
ff.save(lf)
ok("after the other program closes the file the save works",
   Form.load(lf).find("Button1").props["Text"] == "after unlock")

ro = lock_dir / "Form1.py"
ro_orig = ro.read_bytes()
subprocess.run(["attrib", "+R", str(ro)], capture_output=True)
try:
    from radide.model import write_text_safe
    write_text_safe(ro, "print('x')\n")
    e = None
except OSError as ex:
    e = ex
subprocess.run(["attrib", "-R", str(ro)], capture_output=True)
ok("read-only file attribute: PermissionError with 'read-only' in the message",
   isinstance(e, PermissionError) and "read-only" in str(e), repr(e))
ok("read-only file attribute: unchanged", ro.read_bytes() == ro_orig)

rof = new_project("ReadOnly Folder")
if E.deny_create(rof):
    try:
        try:
            write_text_safe(rof / "Form1.py", "print('in place')\n")
            e = None
        except OSError as ex:
            e = ex
        ok("folder without 'create files' right: an existing file is still saved (in place)",
           e is None and "in place" in (rof / "Form1.py").read_text(encoding="utf-8"), repr(e))
        try:
            write_text_safe(rof / "NewModule.py", "x = 1\n")
            e = None
        except OSError as ex:
            e = ex
        ok("folder without 'create files' right: a new file gives a clear access-denied message",
           isinstance(e, PermissionError) and "access denied" in str(e) and "Save As" in str(e), repr(e))
    finally:
        E.allow_again(rof)
else:
    ok("icacls deny on an own folder works without admin", False)

# =================================================================== 3. kill during save
print("== 3. killing a process in the middle of a save", flush=True)
kd = new_project("Kill Proj")
child_code = str(HERE / "_ide_child.py")
valid, versions, leftovers = 0, set(), 0
rng = random.Random(1234)
for i in range(25):
    p = subprocess.Popen([E.PY, child_code, "save-loop", str(kd)], stdout=subprocess.PIPE, text=True,
                         env=E.child_env())
    if p.stdout.readline().strip() != "READY":
        ok("save-loop child starts", False)
        E.kill_tree(p)
        break
    time.sleep(rng.uniform(0.02, 0.6))
    E.kill_tree(p)                           # TerminateProcess (whole tree): no cleanup, no flush - like a crash
    p.wait(10)
    try:
        fd = json.loads((kd / "Form1.form").read_text(encoding="utf-8"))
        names = {c["props"]["Name"][3] for c in fd["controls"] if c["props"]["Name"].startswith("btn")}
        pd = json.loads((kd / "project.radproj").read_text(encoding="utf-8"))
        if len(names) <= 1 and len(fd["controls"]) in (1, 400) and pd.get("name"):
            valid += 1
            versions |= names
    except (ValueError, KeyError) as ex:
        print("   corrupt after kill", i, ex)
    leftovers = len(temps(kd))
ok("25 kills during saves: .form and project.radproj always complete and parseable", valid == 25, f"{valid}/25")
ok("both versions were seen (the kills really hit the save loop)", versions >= {"A", "B"}, versions)
E.info(f"temp files left by killed saves: {leftovers} (removed when the project is opened)")
for t in kd.glob(".*" + safeio.TMP_SUFFIX):
    os.utime(t, (time.time() - 3600, time.time() - 3600))
n = safeio.clean_stale_temps(kd)
ok("stale temp files of killed saves are cleaned", not temps(kd), f"cleaned {n}, left {temps(kd)}")

# comparison: the old non-atomic write_text
bad = 0
cmp_file = kd / "plain.json"
code = ("import json,sys,pathlib\np=pathlib.Path(sys.argv[1])\nd=json.dumps({'x':['y'*80]*20000})\n"
        "print('READY',flush=True)\nwhile True: p.write_text(d)\n")
for i in range(8):
    p = subprocess.Popen([E.PY, "-c", code, str(cmp_file)], stdout=subprocess.PIPE, text=True)
    p.stdout.readline()
    time.sleep(rng.uniform(0.05, 0.4))
    E.kill_tree(p)
    p.wait(10)
    try:
        json.loads(cmp_file.read_text())
    except ValueError:
        bad += 1
E.info(f"for comparison, plain Path.write_text left a truncated file after {bad}/8 kills")

# =================================================================== 4. 1 GB file
print("== 4. huge files", flush=True)
big = ROOT / "huge.log"
E.make_sparse(big, 1 << 30)
ok("sparse 1 GB test file created", big.stat().st_size == 1 << 30)
t0 = time.time()
try:
    safeio.check_open_size(big)
    e = None
except safeio.SaveError as ex:
    e = ex
ok("check_open_size refuses a 1 GB file quickly with a clear message",
   e is not None and "too large" in str(e) and time.time() - t0 < 0.5, repr(e))
small = ROOT / "small.txt"
small.write_text("ok")
safeio.check_open_size(small)
ok("check_open_size accepts a small file", True)

# =================================================================== 5. crash recovery (real IDE processes)
print("== 5. crash recovery", flush=True)


def run_child(mode: str, folder: Path, answer: str | None = None, timeout: float = 600) -> dict:
    extra = {"RADIDE_TEST_RECOVERY_ANSWER": answer} if answer else {}
    rep, text = E.run_report([E.PY, child_code, mode, str(folder)], E.child_env(**extra), timeout)
    if not rep:
        print(text[-3000:])
    return rep


def crash_session(folder: Path) -> dict:
    p = subprocess.Popen([E.PY, child_code, "edit-and-hang", str(folder)], stdout=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace", env=E.child_env())
    rep = {}
    t0 = time.time()
    while time.time() - t0 < 120:
        ln = p.stdout.readline()
        if not ln:
            break
        if ln.startswith("REPORT "):
            rep = json.loads(ln[7:])
        if ln.strip() == "READY":
            break
    E.kill_tree(p)                              # the IDE "crashes" (TerminateProcess of the tree)
    p.wait(10)
    return rep


rec_dir = new_project("Recover Proj", ROOT / E.ARABIC)
disk_before = E.snapshot(rec_dir)
rep = crash_session(rec_dir)
ok("crashed IDE had unsaved form + code edits", rep.get("dirty") is True, rep)
snap = rep.get("snapshot") or []
ok("recovery snapshot holds the code file and the form", "code/Form1.py" in snap and "forms/Form1.form" in snap
   and "manifest.json" in snap, snap)
from radide.features import recovery  # noqa: E402
sd = recovery.set_dir(rec_dir)
ok("snapshot is under %LOCALAPPDATA%\\RADIDE\\recovery (Arabic user folder)",
   str(sd).startswith(os.environ["LOCALAPPDATA"]) and sd.is_dir(), sd)
ok("the crash did not touch the project files", E.snapshot(rec_dir) == disk_before)
ok("nothing was written into the project folder", not (rec_dir / ".radide_backup").exists())
r2 = run_child("restore", rec_dir, "yes")
ok("next IDE restores the designer edit (Button Text)", r2.get("button_text") == "Edited زر", r2.get("button_text"))
ok("next IDE restores the added Label", len(r2.get("labels") or []) == 1, r2.get("labels"))
ok("next IDE restores the code edit", r2.get("code_has_mark") is True, r2.get("log", "")[-500:])
ok("restored documents are unsaved (modified)", r2.get("doc_modified") and r2.get("code_modified"), r2)
ok("restore did not write the project files", E.snapshot(rec_dir) == disk_before)
r3 = run_child("save-all", rec_dir, "yes")
ok("Save All after a restore succeeds", (r3.get("saved") is True), r3)
ok("Save All removes the recovery snapshot", r3.get("after_save", {}).get("recovery_exists") is False, r3)
ok("the restored edits are now in the files", "recovered-edit" in (rec_dir / "Form1.py").read_text(encoding="utf-8")
   and "Edited" in (rec_dir / "Form1.form").read_text(encoding="utf-8"))

rec2 = new_project("Startup Proj", ROOT / E.ARABIC)
crash_session(rec2)
pend = [m["folder"] for m in recovery.pending()]
ok("pending() lists the crashed project", str(rec2.resolve()) in pend, pend)
r4 = run_child("startup", rec2, "yes")
ok("start-up offer opens the crashed project and restores it", r4.get("opened") and r4.get("code_has_mark")
   and r4.get("button_text") == "Edited زر", {k: r4.get(k) for k in ("opened", "code_has_mark", "button_text")})
r5 = run_child("restore", rec2, "no")
ok("answering No discards the snapshot", r5.get("recovery_exists") is False and not r5.get("code_has_mark"), r5)

rec3 = new_project("Discard Proj")
r6 = run_child("close-discard", rec3)
ok("close with Discard: snapshot existed, then removed", r6.get("before") is True and r6.get("after") is False
   and r6.get("close_allowed") is True, r6)

rec4 = new_project("ReadOnly Recover")
if E.deny_write_all(rec4):
    try:
        rep = crash_session(rec4)
        ok("read-only project folder: the snapshot is still written (not in the project)",
           "code/Form1.py" in (rep.get("snapshot") or []), rep)
    finally:
        E.allow_again(rec4)

rec5 = new_project("Full Disk Proj")
before5 = E.snapshot(rec5)
r7 = run_child("save-full", rec5)
ok("Save All on a full disk returns False", r7.get("saved") is False, r7)
ok("full disk: the documents stay modified", r7.get("doc_modified") and r7.get("code_modified"), r7)
ok("full disk: the Output window says the disk is full", "disk is full" in r7.get("log", ""), r7.get("log", "")[-400:])
ok("full disk: closing the IDE is cancelled (no data loss)", r7.get("close_allowed") is False, r7)
ok("full disk: the project files are unchanged", E.snapshot(rec5) == before5)

# =================================================================== 6. Arabic strings
print("== 6. Arabic UI strings", flush=True)
from radide import i18n  # noqa: E402
i18n.load("ar")
for s_ in ("Recover Unsaved Work", "Open the project and restore the unsaved changes?", "Save failed",
           "Close that program and save again. The file on disk was not changed.",
           "Free some space (or save to another drive) and save again. The file on disk was not changed."):
    t = i18n.tr(s_)
    ok(f"Arabic: {s_[:50]}", t != s_ and any("\u0600" <= ch <= "\u06ff" for ch in t), t)
t = i18n.tr("Could not save C:\\x\\Form1.form: the disk is full.")
ok("Arabic pattern: 'Could not save {}: the disk is full.' keeps the path", "Form1.form" in t and t[0] != "C", t)
i18n.load("en")

E.allow_again(ROOT)
sys.exit(E.summary("Environment: save / crash safety"))
