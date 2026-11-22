"""Project file robustness (no GUI): .form / project.radproj / .radsln / .frm / .vbp / .vbproj / .csproj.

* round trips: every sample .form, project.radproj and .radsln opens and saves back byte-identical when
  nothing changed; WinForms Designer files (.vbproj / .csproj) and VB6 projects (.vbp + .frm, ANSI Arabic
  code page included) are written back unchanged;
* format versions: version 1 forms are migrated in memory and stay version 1 on disk until edited; a form of
  a newer version (99) opens with a warning and keeps its unknown top-level / control / property data and
  its version number after an edit;
* encodings: UTF-8 with BOM and UTF-16 (BOM / no BOM) are read and written back in the same encoding; an
  ANSI (Windows-1256 Arabic) .form gives a clear "not UTF-8" error;
* broken files: empty, whitespace, truncated, NUL bytes, binary, JSON of the wrong shape, git merge
  conflict markers, deep nesting -> ProjectFileError with a readable message, never a crash, the file is
  never written;
* read-only: an edited form / project raises PermissionError and leaves the file unchanged; an unchanged
  one saves without error.

Run:  .venv\\Scripts\\python samples/Tests/Robustness/Files/test_files_model.py
"""
import json
import os
import shutil
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _nondef_harness import ROOT, SAMPLES, WORK, check, copy_tree, finish, raises  # noqa: E402

from radide.model import FORM_VERSION, Form, Project, ProjectFileError  # noqa: E402
from radide.solution import Solution, SolutionProject  # noqa: E402

SKIP = ("NetBeansSwingGreeter",)        # a NetBeans Swing .form (XML), not a RAD IDE form


def sample_forms():
    return [p for p in sorted(SAMPLES.rglob("*.form")) if not any(s in p.parts for s in SKIP)]


# =========================================================================== round trips of every sample
n_ok, bad = 0, []
tmp = WORK / "rt"
tmp.mkdir()
forms = sample_forms()
for i, p in enumerate(forms):
    dst = tmp / f"{i}.form"
    shutil.copyfile(p, dst)
    try:
        f = Form.load(dst)
        f.save(dst)
        same = dst.read_bytes() == p.read_bytes()
    except Exception as e:  # noqa: BLE001
        same = False
        bad.append(f"{p}: {type(e).__name__}: {e}")
        continue
    if same:
        n_ok += 1
    else:
        bad.append(str(p))
check(f"every sample .form opens and saves back byte-identical ({n_ok}/{len(forms)})", not bad and n_ok > 300, bad[:5])

projs = [p for p in sorted(SAMPLES.rglob("project.radproj"))]
n_ok, bad = 0, []
for i, p in enumerate(projs):
    d = tmp / f"p{i}"
    d.mkdir()
    shutil.copyfile(p, d / "project.radproj")
    try:
        pr = Project.load(d)
        pr.save()
        if (d / "project.radproj").read_bytes() == p.read_bytes():
            n_ok += 1
        else:
            bad.append(str(p))
    except ProjectFileError as e:
        if "language" in str(e) and "language" not in p.read_text("utf-8", "replace"):
            n_ok += 1                     # a stub "{}" left by another test: a clear error is the right answer
            continue
        bad.append(f"{p}: {e}")
    except (ValueError, OSError) as e:
        bad.append(f"{p}: {type(e).__name__}: {e}")
check(f"every sample project.radproj saves back byte-identical ({n_ok}/{len(projs)})", not bad and n_ok > 100, bad[:5])

slns = sorted(SAMPLES.rglob("*.radsln"))
n_ok, bad = 0, []
for i, p in enumerate(slns):
    d = tmp / f"s{i}"
    d.mkdir()
    q = d / p.name
    shutil.copyfile(p, q)
    try:
        s = Solution.load(q)
        s.save()
        n_ok += q.read_bytes() == p.read_bytes()
        if q.read_bytes() != p.read_bytes():
            bad.append(str(p))
    except Exception as e:  # noqa: BLE001
        bad.append(f"{p}: {e}")
check(f"every sample .radsln saves back byte-identical ({n_ok}/{len(slns)})", not bad and n_ok >= 10, bad[:5])

# =========================================================================== a test project
proj = copy_tree(SAMPLES / "HelloPython", "HelloPython")
fp = proj / "Form1.form"
orig = fp.read_bytes()


def edit_and_save(path: Path, mutate=None) -> Form:
    f = Form.load(path)
    (mutate or (lambda f: f.props.__setitem__("Text", f.props.get("Text", "") + "!")))(f)
    f.save(path)
    return f


# ---- version 1 (older format)
d = json.loads(orig)
check("HelloPython/Form1.form is a version 1 form (older format)", d.get("version") == 1, d.get("version"))
v1 = proj / "V1.form"
d1 = dict(d)
d1["controls"] = list(d["controls"]) + [{"type": "Button", "props": {"Name": "btnOld", "Text": "Old", "TextAlign": "Left",
                                                                      "Left": 5, "Top": 5, "Width": 80, "Height": 25}}]
v1.write_text(json.dumps(d1, indent=2), encoding="utf-8")
raw1 = v1.read_bytes()
f = Form.load(v1)
check("version 1: a Button's old TextAlign 'Left' is migrated to 'Center' in memory",
      f.find("btnOld").props["TextAlign"] == "Center")
f.save(v1)
check("version 1: saved without an edit the file stays byte-identical (still version 1)", v1.read_bytes() == raw1)
f.find("btnOld").props["Text"] = "New"
f.save(v1)
check("version 1: after an edit it is written as the current version", json.loads(v1.read_text("utf-8"))["version"] == FORM_VERSION)
check("version 1: ... and LF/CRLF style of the file is kept",
      (b"\r\n" in v1.read_bytes()) == (b"\r\n" in raw1))

# ---- newer version with unknown data
fut = proj / "Future.form"
dn = json.loads(orig)
dn["version"] = 99
dn["futureTopLevel"] = {"themes": ["dark"], "empty": []}
dn["emptyFuture"] = []
dn["controls"][0]["futureControlKey"] = {"x": 1}
dn["controls"][0]["props"]["FutureProp"] = [1, {"a": "b"}]
fut.write_text(json.dumps(dn, indent=2), encoding="utf-8")
f = Form.load(fut)
check("newer version: the form opens with a warning about the newer format",
      any("newer" in w for w in f.warnings), f.warnings)
f.props["Text"] = "edited"
f.save(fut)
back = json.loads(fut.read_text("utf-8"))
check("newer version: the version number is kept (not downgraded) after an edit", back["version"] == 99, back["version"])
check("newer version: unknown top-level keys are kept (also an empty list)",
      back.get("futureTopLevel") == dn["futureTopLevel"] and back.get("emptyFuture") == [], list(back))
check("newer version: unknown keys of a control entry are kept", back["controls"][0].get("futureControlKey") == {"x": 1},
      back["controls"][0].keys())
check("newer version: unknown properties are kept", back["controls"][0]["props"].get("FutureProp") == [1, {"a": "b"}])

# ---- unknown property of a built-in control (current version)
u = proj / "Unknown.form"
du = json.loads(orig)
du["version"] = FORM_VERSION
du["controls"][0]["props"]["NotAProperty"] = "keep me"
u.write_text(json.dumps(du, indent=2), encoding="utf-8")
edit_and_save(u)
check("unknown property of a built-in control is kept after an edit",
      json.loads(u.read_text("utf-8"))["controls"][0]["props"].get("NotAProperty") == "keep me")

# ---- encodings
arabic_text = "نموذج تجريبي"
for label, enc, bom in (("UTF-8 with BOM", "utf-8-sig", b"\xef\xbb\xbf"), ("UTF-16 LE with BOM", "utf-16", b"\xff\xfe"),
                        ("UTF-16 LE without BOM", "utf-16-le", b""), ("UTF-16 BE without BOM", "utf-16-be", b"")):
    pth = proj / f"Enc_{enc}.form"
    de = json.loads(orig)
    de["props"]["Text"] = arabic_text
    pth.write_bytes(json.dumps(de, indent=2, ensure_ascii=False).encode(enc))
    rawe = pth.read_bytes()
    try:
        f = Form.load(pth)
        loaded = f.props["Text"] == arabic_text
    except Exception as e:  # noqa: BLE001
        loaded, f = False, None
        print("   ", e)
    check(f"{label}: the form opens (Arabic caption read correctly)", loaded)
    if f is None:
        continue
    f.save(pth)
    check(f"{label}: unchanged save is byte-identical", pth.read_bytes() == rawe)
    f.props["Text"] = arabic_text + " 2"
    f.save(pth)
    newraw = pth.read_bytes()
    check(f"{label}: an edited save keeps the encoding" + (" (BOM written)" if bom else ""),
          (not bom or newraw.startswith(bom)) and Form.load(pth).props["Text"] == arabic_text + " 2",
          newraw[:8])

ansi = proj / "Ansi.form"
da = json.loads(orig)
da["props"]["Text"] = arabic_text
ansi.write_bytes(json.dumps(da, indent=2, ensure_ascii=False).encode("cp1256"))
rawa = ansi.read_bytes()
e = raises(lambda: Form.load(ansi), ProjectFileError)
check("ANSI Arabic (Windows-1256) .form: a clear 'not UTF-8 / code page' error", e is not None and "UTF-8" in str(e)
      and "code page" in str(e), e)
check("ANSI Arabic .form: the file is not touched", ansi.read_bytes() == rawa)

# ---- broken files: each gives ProjectFileError with words a user understands, the file is never written
half = orig[: len(orig) // 2]
lines = orig.decode("utf-8").splitlines(keepends=True)
conflict = "".join(lines[:3]) + "<<<<<<< HEAD\n" + lines[3] + "=======\n" + lines[3].replace("Form1", "FormX") + \
    ">>>>>>> feature/x\n" + "".join(lines[4:])
CASES = [
    ("empty file", b"", "empty"),
    ("whitespace only", b"  \r\n\t\r\n", "empty"),
    ("truncated JSON (half the file)", half, "truncated"),
    ("NUL bytes", orig[:40] + b"\x00" * 64, "NUL"),
    ("binary garbage", bytes(range(256)) * 4, None),
    ("a JSON list", b"[1, 2, 3]", "form"),
    ("a JSON string", b"\"hello\"", "form"),
    ("controls is not a list", b'{"version": 2, "props": {"Name": "F"}, "controls": "x"}', "controls"),
    ("props is not an object", b'{"version": 2, "props": [1], "controls": []}', "props"),
    ("control without type", b'{"version": 2, "props": {"Name": "F"}, "controls": [{"props": {}}]}', "type"),
    ("control props not an object", b'{"version": 2, "props": {"Name": "F"}, "controls": [{"type": "Button", "props": 5}]}', "props"),
    ("version is not a number", b'{"version": "two", "props": {"Name": "F"}, "controls": []}', "version"),
    ("git merge conflict markers", conflict.encode("utf-8"), "merge conflict"),
    ("deeply nested JSON", b"[" * 100000 + b"]" * 100000, None),
]
for label, data, word in CASES:
    pth = proj / "Broken.form"
    pth.write_bytes(data)
    e = raises(lambda: Form.load(pth))
    ok = isinstance(e, ProjectFileError) and (word is None or word.lower() in str(e).lower())
    check(f"broken .form ({label}): ProjectFileError with a clear message", ok, f"{type(e).__name__}: {e}")
    check(f"broken .form ({label}): the file is not written", pth.read_bytes() == data)
pth.write_bytes(conflict.encode("utf-8"))
e = raises(lambda: Form.load(pth), ProjectFileError)
check("merge conflict message names the line of the first marker", e is not None and "line 4" in str(e), e)

# repaired entries: missing / duplicate names, non-numeric positions -> warnings, never a crash
rep = proj / "Repair.form"
rep.write_text(json.dumps({"version": 2, "props": {"Name": "Repair"}, "controls": [
    {"type": "Button", "props": {"Name": "Button1", "Left": "abc"}},
    {"type": "Button", "props": {"Name": "Button1"}},
    {"type": "Label", "props": {}}]}), encoding="utf-8")
f = Form.load(rep)
names = [c.name for c in f.controls]
check("repair: duplicate / missing control names get unique names (with warnings)",
      len(set(n.lower() for n in names)) == 3 and len(f.warnings) >= 3, (names, f.warnings))
check("repair: a non-numeric Left goes back to a number", isinstance(f.controls[0].props["Left"], int), f.controls[0].props)
check("repair: abs_pos / ordered work on the repaired form", bool(f.ordered()) and f.abs_pos(f.controls[0]) is not None)

# ---- read-only files
ro = proj / "ReadOnly.form"
shutil.copyfile(fp, ro)
os.chmod(ro, stat.S_IREAD)
raw_ro = ro.read_bytes()
f = Form.load(ro)
e = raises(lambda: f.save(ro))
check("read-only .form: an unchanged save does not fail (nothing to write)", e is None, e)
f.props["Text"] = "changed"
e = raises(lambda: f.save(ro), PermissionError)
check("read-only .form: an edited save raises PermissionError ...", e is not None, e)
check("read-only .form: ... the message says read-only", e is not None and "read-only" in str(e).lower(), e)
check("read-only .form: ... and the file is unchanged", ro.read_bytes() == raw_ro)
alt = proj / "ReadOnly_copy.form"
f.save(alt)
check("read-only .form: Save As to another file works", Form.load(alt).props["Text"] == "changed")
os.chmod(ro, stat.S_IWRITE | stat.S_IREAD)

# ---- project.radproj
pp = proj / "project.radproj"
raw_p = pp.read_bytes()
pr = Project.load(proj)
pr.save()
check("project.radproj: unchanged save is byte-identical", pp.read_bytes() == raw_p)
pr.forms.append("V1")
pr.save()
check("project.radproj: a change is written", "V1" in Project.load(proj).forms)
pp.write_bytes(raw_p)

PCASES = [
    ("empty", b"", "empty"),
    ("JSON list", b"[]", "project"),
    ("forms is a string", b'{"name": "X", "language": "python-tk", "forms": "Form1"}', "forms"),
    ("no language", b'{"name": "X", "forms": []}', "language"),
    ("merge conflict", b'{\n<<<<<<< HEAD\n  "name": "A",\n=======\n  "name": "B",\n>>>>>>> other\n  "language": "python-tk"\n}', "merge conflict"),
    ("truncated", raw_p[:20], "JSON"),
    ("ANSI Arabic", '{"name": "مشروع", "language": "python-tk"}'.encode("cp1256"), "UTF-8"),
]
for label, data, word in PCASES:
    pp.write_bytes(data)
    e = raises(lambda: Project.load(proj))
    check(f"broken project.radproj ({label}): ProjectFileError with a clear message",
          isinstance(e, ProjectFileError) and word.lower() in str(e).lower(), f"{type(e).__name__}: {e}")
    check(f"broken project.radproj ({label}): not written", pp.read_bytes() == data)
pp.write_bytes(b"\xef\xbb\xbf" + raw_p)
e = raises(lambda: Project.load(proj))
check("project.radproj with a UTF-8 BOM opens", e is None, e)
# raw (not escaped) Arabic and LF newlines are kept when the project is changed
pp.write_bytes(json.dumps({"name": "مشروع", "language": "python-tk", "forms": ["Form1"], "startup": "Form1",
                           "modules": [], "futureKey": {"a": 1}}, indent=2, ensure_ascii=False).encode("utf-8"))
pr = Project.load(proj)
pr.modules.append("util.py")
pr.save()
txt = pp.read_bytes()
check("project.radproj: raw Arabic stays raw (not \\u-escaped) and LF stays LF after a change",
      "مشروع".encode("utf-8") in txt and b"\r\n" not in txt, txt[:80])
check("project.radproj: unknown keys are kept", json.loads(txt).get("futureKey") == {"a": 1})
pp.write_bytes(raw_p)
os.chmod(pp, stat.S_IREAD)
pr = Project.load(proj)
check("read-only project.radproj: unchanged save does not fail", raises(pr.save) is None)
pr.forms.append("Zed")
e = raises(pr.save, PermissionError)
check("read-only project.radproj: a change raises PermissionError, file unchanged", e is not None and pp.read_bytes() == raw_p, e)
os.chmod(pp, stat.S_IWRITE | stat.S_IREAD)

# ---- .radsln
sd = WORK / "Sln"
sd.mkdir()
sp = sd / "My.radsln"
sp.write_bytes(b"\xef\xbb\xbf" + json.dumps({"name": "My", "projects": [{"name": "HelloPython", "path": "../HelloPython"}],
                                             "startup": "HelloPython", "futureSln": [1, 2]}, indent=2).encode("utf-8"))
raws = sp.read_bytes()
s = Solution.load(sp)
check(".radsln with a UTF-8 BOM opens", s.names() == ["HelloPython"], s.names())
s.save()
check(".radsln: unchanged save is byte-identical", sp.read_bytes() == raws)
s.projects.append(SolutionProject("Other", "../Other"))
s.save()
back = sp.read_bytes()
check(".radsln: unknown keys are kept after a change (and the BOM)", json.loads(back.decode("utf-8-sig")).get("futureSln") == [1, 2]
      and back.startswith(b"\xef\xbb\xbf"))
for label, data, word in (("empty", b"", "empty"), ("projects is a string", b'{"name": "X", "projects": "a"}', "projects"),
                          ("truncated", raws[:30], "JSON"), ("merge conflict", b'{\n<<<<<<< a\n"name": "x"\n=======\n"name": "y"\n>>>>>>> b\n}', "merge")):
    sp.write_bytes(data)
    e = raises(lambda: Solution.load(sp))
    check(f"broken .radsln ({label}): ProjectFileError with a clear message",
          isinstance(e, ProjectFileError) and word.lower() in str(e).lower(), f"{type(e).__name__}: {e}")
check("a broken .radsln next to a project is skipped by find_for_project (no crash)",
      raises(lambda: Solution.find_for_project(proj)) is None)

# =========================================================================== VB6 .vbp / .frm
from radide.foreign import vb6_project as V  # noqa: E402

vb = copy_tree(SAMPLES / "Tests" / "VB6Compat" / "OcxControls", "OcxControls")
before = {p.name: p.read_bytes() for p in vb.iterdir() if p.is_file()}
mdir, nat = V.build_mirror(vb / "OcxControls.vbp", WORK / "mirror_ocx")
sync = getattr(V, "sync_mirror", None)
if callable(sync):
    try:
        sync(mdir)
    except TypeError:
        sync(mdir, nat)
after = {p.name: p.read_bytes() for p in vb.iterdir() if p.is_file()}
check("VB6 .vbp + .frm: building the mirror and syncing without a change leaves every file byte-identical",
      before == after, [k for k in before if before[k] != after.get(k)])
frm_form = Form.load(Path(mdir) / "frmOcx.form")
types = sorted({c.type for c in frm_form.controls})
check("VB6 OCX controls open (mapped controls / ActiveX placeholders)", len(frm_form.controls) >= 3, types)

# ANSI Arabic VB6 form (Windows-1256): read with the right code page, written back byte-identical
ar = WORK / "VbArabic"
ar.mkdir()
frm = ('VERSION 5.00\r\nBegin VB.Form frmMain \r\n   Caption         =   "نافذة رئيسية"\r\n   ClientHeight    =   3000\r\n'
       '   ClientLeft      =   60\r\n   ClientTop       =   345\r\n   ClientWidth     =   4500\r\n   Begin VB.CommandButton cmdOk \r\n'
       '      Caption         =   "موافق"\r\n      Height          =   495\r\n      Left            =   1200\r\n      TabIndex        =   0\r\n'
       '      Top             =   1200\r\n      Width           =   1215\r\n   End\r\nEnd\r\nAttribute VB_Name = "frmMain"\r\n'
       'Private Sub cmdOk_Click()\r\n    MsgBox "مرحبا"\r\nEnd Sub\r\n')
(ar / "frmMain.frm").write_bytes(frm.encode("cp1256"))
(ar / "Arabic.vbp").write_bytes(b'Type=Exe\r\nForm=frmMain.frm\r\nStartup="frmMain"\r\nName="Arabic"\r\n')
before = {p.name: p.read_bytes() for p in ar.iterdir()}
try:
    mdir2, nat2 = V.build_mirror(ar / "Arabic.vbp", WORK / "mirror_ar")
    ff = Form.load(Path(mdir2) / "frmMain.form")
    caps = {ff.props.get("Text")} | {c.props.get("Text") for c in ff.controls}
    check("VB6 ANSI Arabic .frm: captions decoded with the Arabic code page", {"نافذة رئيسية", "موافق"} <= caps, caps)
    if callable(sync):
        try:
            sync(mdir2)
        except TypeError:
            sync(mdir2, nat2)
    after = {p.name: p.read_bytes() for p in ar.iterdir()}
    check("VB6 ANSI Arabic: an unchanged sync leaves the .frm / .vbp byte-identical", before == after)
except Exception as ex:  # noqa: BLE001
    check("VB6 ANSI Arabic .frm opens", False, f"{type(ex).__name__}: {ex}")

# truncated / empty .frm: an error or an empty form, never a crash of the parser
from radide.importers.vb6_import import parse_frm  # noqa: E402
for label, text in (("empty", ""), ("truncated", frm[:120]), ("no End", frm.replace("End\r\n", "")),
                    ("garbage", "\x00\x01 Begin Begin End End End")):
    e = raises(lambda: parse_frm(text))
    check(f"VB6 .frm parser on a {label} file: no crash", e is None or isinstance(e, ValueError), repr(e))

# =========================================================================== WinForms .vbproj / .csproj
from radide.foreign.vs_solution import load_vs  # noqa: E402

for rel in ("Examples/VBNet/Calculator", "Tests/ForeignProjects/WinFormsVB", "Tests/ForeignProjects/LegacyCsApp",
            "Tests/DotNet/SharedProjects/SharedDemo/WinApp"):
    src = SAMPLES / rel
    if not src.is_dir():
        continue
    dst = copy_tree(src, "vs_" + src.name)
    files = {p: p.read_bytes() for p in dst.rglob("*") if p.is_file()}
    try:
        sln = load_vs(dst)
        n = 0
        for pr in sln.all_projects():
            for name in pr.forms:
                f = Form.load(pr.form_path(name))
                f.save(pr.form_path(name))
                n += 1
        changed = [str(p.relative_to(dst)) for p, b in files.items() if p.is_file() and p.read_bytes() != b]
        check(f"{src.name}: {n} WinForms form(s) open and save back with every project file byte-identical",
              n > 0 and not changed, changed[:5])
    except Exception as ex:  # noqa: BLE001
        check(f"{src.name}: WinForms project opens", False, f"{type(ex).__name__}: {ex}")

finish()
