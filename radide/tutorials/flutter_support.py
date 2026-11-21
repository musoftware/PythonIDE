"""Flutter blocks of the tutorials (guide "flutter-mobile"): projects, headless checks and highlighting.

Block kinds:

* ```` ```flutter run ````   the code file of a phone screen (``lib/main_screen.dart``: ``class MainScreenCode
                             extends MainScreenDesigner { ... }`` with VB-style handlers) -> a Flutter project made
                             like New Project > Mobile > Flutter App.  The screen holds the controls the code uses
                             (VB-prefixed names: lbl, txt, btn, lst, chk, sw, sld, img, prg, tmr, cbo, opt, fab ...)
                             in a column; the hidden test comment can describe them (``controls``) or start from a
                             template (``template``: flutter_app | flutter_tabs | hello_mobile).
* ``flutter exercise`` / ``flutter solution``   as for the other courses.
* ``// #file: lib/edit_screen.dart`` lines split a block: every file with ``class <Name>Code extends
  <Name>Designer`` becomes another screen (form) <Name>; other files are modules under lib/.

Hidden ``<!-- test: {...} -->`` keys used by check() (it runs ``flutter test`` on a generated widget test):
  ``controls``  {"lblTotal": {"Text": "0"}, "tmrClock": {"Interval": 1000}, "lstItems": {"type": "MListView"}}
  ``form``      properties of the start screen, e.g. {"Text": "Counter"}
  ``template``  start from a New Project template (its controls), the block replaces the screen code
  ``do``        steps after the screen has loaded: Dart statements on the current screen's state
                ("txtName.text = 'Sara'", "btnHello_Click()") and commands "@input:<text>" (answer an InputBox),
                "@cancel", "@yes" / "@no" (Confirm), "@wait:<ms>" (let time pass: timers), "@tap:<text>" (a
                real tap on the widget showing that text), "@screen:<Name>" (later steps use that screen),
                "@back" (close the top screen), "@enter:txtName=Sara" (type into a text field like a user: its
                Changed event fires)
  ``expect``    {"Dart expression on the state": "expected text"}, e.g. {"lblResult.text": "Hello, Sara!"}
  ``msgbox`` / ``toast``  the texts of the MsgBox dialogs / Toast messages shown, in order
  ``norun``     only build the project files and analyse nothing (examples that need a real device)
MsgBox dialogs are closed automatically (OK).  print() output is the block's output (```text output).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
MARK = "\u0001RAD "
PREFIXES = (("lbl", "Label"), ("txt", "MTextField"), ("btn", "Button"), ("cmd", "Button"), ("lst", "MListView"),
            ("chk", "CheckBox"), ("sw", "Switch"), ("sld", "MSlider"), ("img", "MImage"), ("prg", "ProgressBar"),
            ("tmr", "Timer"), ("cbo", "ComboBox"), ("opt", "RadioButton"), ("fab", "Fab"), ("ico", "MIcon"))
RX_NAME = re.compile(r"\b(?:" + "|".join(p for p, _t in PREFIXES) + r")[A-Z][A-Za-z0-9]*\b")
RX_SCREEN = re.compile(r"^\s*class\s+(\w+)Code\s+extends\s+(\w+)Designer\b", re.M)
SIZES = {"Label": 32, "MTextField": 56, "Button": 44, "MListView": 240, "CheckBox": 32, "Switch": 32, "MSlider": 40,
         "MImage": 120, "ProgressBar": 20, "ComboBox": 48, "RadioButton": 32, "Fab": 56, "MIcon": 32}


# ===================================================================== toolchain
def flutter() -> str | None:
    try:
        from ..languages.flutter import flutter_exe
        exe = flutter_exe()
        if exe:
            return exe
    except Exception:  # noqa: BLE001
        pass
    return shutil.which("flutter")


def _run(args: list[str], cwd: Path, timeout: int) -> tuple[int, str]:
    exe = flutter()
    if not exe:
        return -1, "Flutter SDK غير موجود (ثبّته من flutter.dev وأضف flutter\\bin إلى PATH)"
    try:
        r = subprocess.run([exe, *args], cwd=str(cwd), capture_output=True, timeout=timeout,
                           creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return -2, "<<انتهت المهلة>>"
    except OSError as e:
        return -1, str(e)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


# ===================================================================== projects
def screen_of(code: str, default: str = "MainScreen") -> str:
    m = RX_SCREEN.search(code)
    return m.group(1) if m else default


def default_file(block) -> str:
    """lib/<screen>.dart of the screen the block's code defines (lib/main_screen.dart by default)."""
    from ..mobile.codegen_common import snake
    return f"lib/{snake(screen_of(block.code))}.dart"


def controls_of(code: str) -> list[tuple[str, str]]:
    """(type, name) of the controls a screen's code uses, in order of first use."""
    out: list[tuple[str, str]] = []
    seen = set()
    for m in RX_NAME.finditer(code):
        n = m.group(0)
        if n in seen:
            continue
        seen.add(n)
        typ = next((t for p, t in PREFIXES if n.startswith(p) and n[len(p):len(p) + 1].isupper()), None)
        if typ:
            out.append((typ, n))
    for n, typ in (("AppBar1", "AppBar"), ("BottomNav1", "BottomNav"), ("Drawer1", "Drawer")):
        if re.search(rf"\b{n}\b", code):
            out.insert(0, (typ, n))
    return out


def _build_form(name: str, code: str, spec: dict, is_start: bool):
    from ..mobile.codegen_templates import _add, _appbar, _form
    form = _form(name, (spec.get("form") or {}).get("Text", name) if is_start else name)
    if is_start:
        for k, v in (spec.get("form") or {}).items():
            form.props[k] = v
    W = int(form.props.get("Width", 412))
    given = dict(spec.get("controls") or {}) if is_start else {}
    found = controls_of(code)
    names = [n for _t, n in found]
    for n, props in given.items():               # controls only the test comment names (no code use)
        if n not in names:
            found.append((props.get("type", next((t for p, t in PREFIXES if n.startswith(p)), "Label")), n))
    y = 8
    for typ, n in found:
        props = {k: v for k, v in (given.get(n) or {}).items() if k != "type"}
        typ = (given.get(n) or {}).get("type", typ)
        if typ == "AppBar":
            c = _appbar(form, props.pop("Title", form.props.get("Text", name)), props.pop("Actions", ""), n)
            c.props.update(props)
            y = max(y, 64)
            continue
        if typ == "Timer":
            c = _add(form, "Timer", n, 0, 0, 0, 0)
            c.props.update({"Interval": 1000, "Enabled": False})
            c.props.update(props)
            continue
        h = int(props.pop("Height", SIZES.get(typ, 40)))
        w = int(props.pop("Width", 56 if typ == "Fab" else W - 32))
        extra = {}
        if typ == "Button":
            extra["Text"] = n[3:]
        elif typ == "Label":
            extra["Text"] = ""
        elif typ == "MTextField":
            extra["Text"], extra["Hint"] = "", n[3:]
        elif typ == "MListView":
            extra["Items"], extra["ItemTemplate"] = "", "title"
        elif typ in ("CheckBox", "RadioButton"):
            extra["Text"] = n[3:]
        extra.update(props)
        _add(form, typ, n, 16 if typ != "Fab" else W - 72, y, w, h, **extra)
        y += h + 12
    return form


def make_project(files: dict[str, str], spec: dict | None, dest: Path, name: str = "Lesson"):
    """A Flutter project in *dest* (already empty) with the screens / modules of *files*."""
    from ..languages import get_plugin
    from ..model import Project
    spec = dict(spec or {})
    plugin = get_plugin("flutter")
    dest = Path(dest)
    screens = [(fn, screen_of(t, "")) for fn, t in files.items() if screen_of(t, "")]
    if spec.get("template"):
        from ..mobile.codegen_templates import build_flutter_project
        project = build_flutter_project(plugin, dest, name, spec["template"])
        for fn, text in files.items():
            scr = screen_of(text, "")
            target = plugin.code_file(scr) if scr in project.forms else ("lib/" + Path(fn).name)
            (dest / target).write_text(text, encoding="utf-8")
            if scr in project.forms:
                from ..model import Form
                form = Form.load(project.form_path(scr))
                (dest / plugin.designer_file(scr)).write_text(plugin.generate_designer(form, text), encoding="utf-8")
            elif target not in project.modules:
                project.modules.append(target)
        project.save()
        plugin.write_project_files(project)
        return project
    (dest / "lib").mkdir(parents=True, exist_ok=True)
    project = Project(dest, name, plugin.id)
    project.extra["mobile"] = {"device": "windows"}
    if not screens:                               # a module only: wrap it in an empty screen
        files = {"lib/main_screen.dart": _empty_screen("MainScreen"), **files}
        screens = [("lib/main_screen.dart", "MainScreen")]
    for i, (fn, scr) in enumerate(screens):
        code = files[fn]
        form = _build_form(scr, code, spec, i == 0)
        form.save(project.form_path(scr))
        (dest / plugin.code_file(scr)).write_text(code, encoding="utf-8")
        (dest / plugin.designer_file(scr)).write_text(plugin.generate_designer(form, code), encoding="utf-8")
        project.forms.append(scr)
    project.startup = screens[0][1]
    for fn, text in files.items():
        if fn in dict(screens):
            continue
        rel = fn if fn.startswith("lib/") else "lib/" + Path(fn).name
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_text(text, encoding="utf-8")
        project.modules.append(rel)
    project.save()
    plugin.write_project_files(project)
    return project


def _empty_screen(name: str) -> str:
    from ..mobile.codegen_common import snake
    return (f"import 'package:flutter/material.dart';\n\nimport 'radapp.dart';\n\npart '{snake(name)}_designer.dart';"
            f"\n\nclass {name}Code extends {name}Designer {{\n}}\n")


# ===================================================================== the widget test
def _dart_str(s: str) -> str:
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$").replace("\n", "\\n") + "'"


TEST_HEAD = r"""// Generated by RAD IDE tutorials (flutter-mobile guide): drives the screen like a user would.
// ignore_for_file: avoid_print, unused_import
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:%(pkg)s/main.dart';
import 'package:%(pkg)s/radapp.dart';

const _m = '\u0001RAD ';
final _seen = <int>{};

String _text(Widget? w) {
  if (w is Text) return w.data ?? w.textSpan?.toPlainText() ?? '';
  return '';
}

Future<void> _settle(WidgetTester t) async {
  try {
    await t.pumpAndSettle(const Duration(milliseconds: 100), EnginePhase.sendSemanticsUpdate,
        const Duration(seconds: 20));
  } catch (_) {
    await t.pump(const Duration(milliseconds: 500));
  }
}

Future<void> _report(WidgetTester t) async {
  for (final e in find.byType(SnackBar).evaluate()) {
    final w = e.widget as SnackBar;
    if (_seen.add(identityHashCode(w))) print('${_m}TOAST ${_text(w.content)}');
  }
  for (var guard = 0; guard < 20; guard++) {
    final dlg = find.byType(AlertDialog);
    if (dlg.evaluate().isEmpty) return;
    final w = dlg.evaluate().last.widget as AlertDialog;
    final ok = find.descendant(of: dlg.last, matching: find.text('OK'));
    final asks = find.descendant(of: dlg.last, matching: find.byType(TextField)).evaluate().isNotEmpty ||
        find.descendant(of: dlg.last, matching: find.text('Yes')).evaluate().isNotEmpty;
    if (_seen.add(identityHashCode(w))) {
      print('${_m}${asks ? "ASK" : "MSGBOX"} ${_text(w.content)}');
    }
    if (asks || ok.evaluate().isEmpty) return;
    await t.tap(ok.last);
    await _settle(t);
  }
}

dynamic _st(WidgetTester t, String screen) =>
    t.state(find.byWidgetPredicate((w) => w.runtimeType.toString() == screen).last);

void main() {
  testWidgets('lesson', (tester) async {
    await tester.binding.setSurfaceSize(const Size(%(w)s, %(h)s));
    await tester.pumpWidget(const RadMobileApp());
    await _settle(tester);
    await _report(tester);
    var screen = '%(screen)s';
    dynamic st = _st(tester, screen);
"""

TEST_TAIL = r"""    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 10));
  });
}
"""


def test_source(pkg: str, screen: str, spec: dict, size=(412, 915)) -> str:
    out = [TEST_HEAD % {"pkg": pkg, "screen": screen, "w": size[0], "h": size[1]}]
    ind = "    "
    for step in spec.get("do") or []:
        step = str(step).strip()
        if step.startswith("@input:"):
            out.append(f"{ind}await tester.enterText(find.descendant(of: find.byType(AlertDialog).last, "
                       f"matching: find.byType(TextField)), {_dart_str(step[7:])});")
            out.append(f"{ind}await tester.tap(find.descendant(of: find.byType(AlertDialog).last, "
                       f"matching: find.text('OK')));")
        elif step in ("@cancel", "@yes", "@no"):
            label = {"@cancel": "Cancel", "@yes": "Yes", "@no": "No"}[step]
            out.append(f"{ind}await tester.tap(find.descendant(of: find.byType(AlertDialog).last, "
                       f"matching: find.text('{label}')));")
        elif step.startswith("@enter:"):
            ctl, _, text = step[7:].partition("=")
            out.append(f"{ind}await tester.enterText(find.byWidgetPredicate((w) => w is TextField && "
                       f"identical(w.controller, st.{ctl.strip()}.controller)), {_dart_str(text)});")
        elif step.startswith("@wait:"):
            out.append(f"{ind}await tester.pump(const Duration(milliseconds: {int(step[6:])}));")
        elif step.startswith("@tap:"):
            out.append(f"{ind}await tester.tap(find.text({_dart_str(step[5:])}).last);")
        elif step.startswith("@screen:"):
            out.append(f"{ind}screen = {_dart_str(step[8:])};")
        elif step == "@back":
            out.append(f"{ind}Navigator.of(st.context as BuildContext).pop();")
        else:
            out.append(f"{ind}st.{step.rstrip(';')};")
        out.append(f"{ind}await _settle(tester);")
        out.append(f"{ind}await _report(tester);")
        out.append(f"{ind}st = _st(tester, screen);")
    for k in (spec.get("expect") or {}):
        out.append(f"{ind}print('${{_m}}VAL ' + {_dart_str(k)} + '=' + '${{st.{k}}}');")
    out.append(TEST_TAIL)
    return "\n".join(out)


def run_check(project_dir: Path, spec: dict, timeout: int = 300) -> dict:
    """flutter test on the generated widget test; {output, msgbox, toast, ask, values, errors, ok}."""
    from ..languages.flutter import package_name
    from ..model import Project
    project_dir = Path(project_dir)
    project = Project.load(project_dir)
    pkg = package_name(project.name)
    (project_dir / "test").mkdir(exist_ok=True)
    wt = project_dir / "test" / "widget_test.dart"
    if wt.exists():
        wt.unlink()                                # the template's smoke test is not needed for the check
    (project_dir / "test" / "rad_lesson_test.dart").write_text(
        test_source(pkg, project.startup, spec), encoding="utf-8")
    res = {"output": "", "msgbox": [], "toast": [], "ask": [], "values": {}, "errors": [], "ok": False}
    if not (project_dir / ".dart_tool" / "package_config.json").exists():
        rc, out = _run(["pub", "get", "--offline"], project_dir, 180)
        if rc != 0:
            rc, out = _run(["pub", "get"], project_dir, 300)
        if rc != 0:
            res["errors"].append("flutter pub get: " + out[-1500:])
            return res
    rc, out = _run(["test", "test/rad_lesson_test.dart", "-r", "json", "--no-pub"], project_dir, timeout)
    lines, success = [], None
    for ln in out.splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            ev = json.loads(ln)
        except ValueError:
            continue
        t = ev.get("type")
        if t == "print":
            msg = ev.get("message", "")
            if msg.startswith(MARK):
                kind, _, rest = msg[len(MARK):].partition(" ")
                if kind == "VAL":
                    k, _, v = rest.partition("=")
                    res["values"][k] = v
                elif kind in ("MSGBOX", "TOAST", "ASK"):
                    res[kind.lower()].append(rest)
            else:
                lines.append(msg)
        elif t == "error":
            res["errors"].append((ev.get("error") or "").strip()[:1500])
        elif t == "testDone" and not ev.get("hidden"):
            success = ev.get("result") == "success"
        elif t == "done" and success is None:
            success = bool(ev.get("success"))
    if success is None and rc != 0:
        res["errors"].append(_compile_errors(out))
    res["output"] = "\n".join(lines)
    res["ok"] = bool(success) and not res["errors"]
    return res


def _compile_errors(out: str) -> str:
    keep = [ln for ln in out.splitlines() if re.search(r"error|Error:", ln) and not ln.startswith("{")]
    return "\n".join(keep[:25]) or out[-1500:]


# ===================================================================== check()
def check(block, code, folder, work: Path, norm, CheckResult):
    """The "تحقق" button / the course checker for a flutter block."""
    from . import _clean, block_files
    target = block.check_target()
    spec = dict(target.spec or {})
    if folder:
        work = Path(folder)
    else:
        _clean(work)
        make_project(block_files(block, code), spec, work)
    if spec.get("norun"):
        return CheckResult(True, "", None, [], "أُنشئ المشروع بنجاح. شغّله بنفسك من «جرّبه».")
    r = run_check(work, spec)
    problems = list(r["errors"])
    expected = target.expected
    if expected is not None and norm(r["output"]) != norm(expected):
        problems.append("المخرجات لا تطابق المطلوب")
    for key, label in (("msgbox", "رسائل MsgBox"), ("toast", "رسائل Toast")):
        if key in spec and r[key] != list(spec[key]):
            problems.append(f"{label}: المتوقع " + " | ".join(spec[key]) + " ، الناتج " + " | ".join(r[key]))
    for k, v in (spec.get("expect") or {}).items():
        got = r["values"].get(k)
        if got != str(v):
            problems.append(f"{k}: المتوقع «{v}» والناتج «{got}»")
    out = r["output"]
    extra = [f"[MsgBox] {m}" for m in r["msgbox"]] + [f"[Toast] {m}" for m in r["toast"]]
    if extra:
        out += ("\n" if out else "") + "\n".join(extra)
    ok = not problems and (r["ok"] or not r["errors"])
    if ok and expected is None and not spec.get("expect") and "msgbox" not in spec and "toast" not in spec:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
    return CheckResult(ok, out, expected, problems)


__all__ = ["check", "controls_of", "make_project", "run_check", "screen_of", "test_source"]
