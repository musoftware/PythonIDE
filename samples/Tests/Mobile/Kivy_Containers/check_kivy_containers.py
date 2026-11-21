"""Kivy: Column / Row / Card / GroupBox / Stack containers on an ordinary phone form.

KV wants every property of a widget before its child widgets. The generator used to write a container's
children first and its size / position lines (size_hint, size, x, top - added by the parent's placement)
after them, which Kivy's parser rejects. This check

1. builds a phone form with a Column (Label, Button, a nested Row with two buttons), a Row, a Card with a
   Label, a GroupBox with a CheckBox and a Stack with a Label, and writes the Kivy project into Project/;
2. checks statically that in the generated KV no property line follows a child widget of the same widget;
3. loads the KV with kivy's Builder (in a separate process) and runs the app for a few seconds
   (RADKIVY_EXEC): every control exists, the Column's children are inside the Column, the Row lays its
   buttons side by side and the button handler works.

Run:  python samples/Tests/Mobile/Kivy_Containers/check_kivy_containers.py      (SKIPs the run without kivy)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Motion" / "Targets"))

from proj import add, mobile_form, write_project  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:1500]}]"), flush=True)


def build_form():
    f = mobile_form("Form1", "small_phone")
    add(f, "Label", "lblTitle", 16, 16, 300, 30, Text="Containers")
    col = add(f, "Column", "colMain", 16, 56, 320, 200, Spacing=6, Padding=4)
    add(f, "Label", "lblInCol", 0, 0, 200, 30, parent=col.name, Text="In the column")
    add(f, "Button", "btnInCol", 0, 0, 160, 40, parent=col.name, Text="Click me")
    row = add(f, "Row", "rowInner", 0, 0, 300, 44, parent=col.name, Spacing=8)
    add(f, "Button", "btnA", 0, 0, 80, 40, parent=row.name, Text="A")
    add(f, "Button", "btnB", 0, 0, 80, 40, parent=row.name, Text="B")
    row2 = add(f, "Row", "rowMain", 16, 264, 320, 44, Spacing=4)
    add(f, "Button", "btnC", 0, 0, 90, 40, parent=row2.name, Text="C")
    add(f, "Label", "lblD", 0, 0, 90, 40, parent=row2.name, Text="D")
    card = add(f, "Card", "cardInfo", 16, 316, 320, 70)
    add(f, "Label", "lblInCard", 10, 10, 200, 30, parent=card.name, Text="In the card")
    grp = add(f, "GroupBox", "grpOpts", 16, 394, 320, 70, Text="Options")
    add(f, "CheckBox", "chkA", 10, 28, 200, 30, parent=grp.name, Text="Option A")
    stk = add(f, "Stack", "stkBox", 16, 470, 320, 50)
    add(f, "Label", "lblInStack", 4, 4, 200, 30, parent=stk.name, Text="In the stack")
    for c in f.controls:          # children sit in their parent (the generator lays Column / Row out itself)
        if c.props.get("Parent"):
            c.props["Dock"] = "None"
    return f


USER = '''from Form1_designer import Form1Designer


class Form1(Form1Designer):
    def btnInCol_Click(self):
        self.lblTitle.text = "Clicked"


if __name__ == "__main__":
    from radkivy import run_app
    run_app("Form1")
'''


def kv_of(designer: str) -> list[str]:
    a = designer.index("KV = '''") + len("KV = '''")
    b = designer.index("'''", a)
    return designer[a:b].strip("\n").splitlines()


def order_problems(kv: list[str]) -> list[str]:
    """Lines 'name: value' that come after a child widget ('Class:') of the same widget."""
    bad = []
    stack = []        # (indent, saw_child)
    for i, line in enumerate(kv):
        if not line.strip():
            continue
        ind = len(line) - len(line.lstrip())
        s = line.strip()
        while stack and stack[-1][0] >= ind:
            stack.pop()
        is_widget = s.endswith(":") and s[0].isupper() and " " not in s
        is_block = s.endswith(":") and not is_widget          # canvas.before:, Color: ...
        if stack and is_widget:
            stack[-1][1] = True
        elif stack and not is_block and stack[-1][1] and ":" in s and not s.startswith(("#",)):
            bad.append(f"{i + 1}: {s}")
        if is_widget or is_block:
            stack.append([ind, False])
    return bad


EXEC = """
import json
from kivy.clock import Clock
def a(dt):
    R = {}
    ids = ['lblTitle', 'colMain', 'lblInCol', 'btnInCol', 'rowInner', 'btnA', 'btnB', 'rowMain', 'btnC', 'lblD',
           'cardInfo', 'lblInCard', 'grpOpts', 'chkA', 'stkBox', 'lblInStack']
    R['missing'] = [n for n in ids if getattr(scr, n, None) is None]
    R['btn_parent_is_col'] = scr.btnInCol.parent.uid == scr.colMain.uid
    R['a_parent_is_row'] = scr.btnA.parent.uid == scr.rowInner.uid
    R['row_side_by_side'] = scr.btnB.x > scr.btnA.x and abs(scr.btnB.y - scr.btnA.y) < 1
    R['col_top_down'] = scr.btnInCol.top <= scr.lblInCol.y + 1
    R['col_inside'] = scr.colMain.collide_point(*scr.btnInCol.center)
    R['card_child'] = scr.lblInCard.parent.uid == scr.cardInfo.uid
    R['chk_parent'] = scr.chkA.parent.uid == scr.grpOpts.uid
    scr.btnInCol.dispatch('on_release')
    R['clicked'] = scr.lblTitle.text
    open(r'$OUT', 'w').write(json.dumps(R))
Clock.schedule_once(a, 1.5)
"""


def has_kivy() -> bool:
    r = subprocess.run([sys.executable, "-c", "import kivy"], capture_output=True, env=dict(os.environ, KIVY_NO_ARGS="1",
                       KIVY_NO_CONSOLELOG="1"))
    return r.returncode == 0


def main():
    proj = HERE / "Project"
    f = build_form()
    write_project(proj, "kivy", [f], {"Form1": USER}, overwrite_user=True)
    designer = (proj / "Form1_designer.py").read_text(encoding="utf-8")
    kv = kv_of(designer)
    bad = order_problems(kv)
    check("KV: no property after a child widget", not bad, bad[:10])
    # the Column's own size / position come before its first child
    i_col = next(i for i, s in enumerate(kv) if s.strip() == "id: w_colMain")
    i_kid = next(i for i, s in enumerate(kv) if s.strip() == "id: w_lblInCol")
    i_size = next(i for i in range(i_col, len(kv)) if kv[i].strip().startswith("size_hint: None, None"))
    check("KV: Column size / position before its children", i_size < i_kid, (i_col, i_size, i_kid))
    # forms without containers are unchanged: plain controls keep 'class, id, props, geometry'
    i_t = next(i for i, s in enumerate(kv) if s.strip() == "id: w_lblTitle")
    check("KV: plain control lines unchanged", kv[i_t - 1].strip() == "RadLabel:" and
          kv[i_t + 1].strip().startswith("text:"), kv[i_t - 1:i_t + 3])
    if not has_kivy():
        print("SKIP Kivy load/run: kivy is not installed")
    else:
        # 3a. Builder.load_string on the KV alone (the parser is what rejected the old order)
        code = ("import sys; sys.path.insert(0, %r)\n" % str(proj) +
                "from kivy.lang import Builder\nimport radkivy\n"
                "src = open(%r, encoding='utf-8').read()\n" % str(proj / "Form1_designer.py") +
                "a = src.index(\"KV = '''\") + 8; b = src.index(\"'''\", a)\n"
                "Builder.load_string(src[a:b]); print('KV-OK')\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(proj), timeout=120,
                           env=dict(os.environ, KIVY_NO_ARGS="1", KIVY_NO_CONSOLELOG="1"))
        check("Kivy Builder.load_string accepts the KV", "KV-OK" in r.stdout, (r.stdout + r.stderr)[-1500:])
        # 3b. run the app
        out = HERE / "_run.json"
        if out.exists():
            out.unlink()
        env = dict(os.environ, RADKIVY_AUTOSTOP="5", KIVY_NO_ARGS="1", KIVY_NO_CONSOLELOG="1",
                   RADKIVY_EXEC=EXEC.replace("$OUT", str(out).replace("\\", "/")))
        r = subprocess.run([sys.executable, "Form1.py"], cwd=str(proj), env=env, capture_output=True, text=True,
                           timeout=120)
        try:
            R = json.loads(out.read_text(encoding="utf-8"))
            out.unlink()
        except (OSError, ValueError):
            R = {"_error": (r.stdout + r.stderr)[-1500:]}
        check("Kivy app runs; every control exists", R.get("missing") == [], R)
        check("Column children are inside the Column", R.get("btn_parent_is_col") and R.get("col_inside"), R)
        check("Column lays out top-down", R.get("col_top_down"), R)
        check("nested Row: buttons side by side", R.get("a_parent_is_row") and R.get("row_side_by_side"), R)
        check("Card / GroupBox children", R.get("card_child") and R.get("chk_parent"), R)
        check("handler of a button in the Column runs", R.get("clicked") == "Clicked", R)
    ok = sum(1 for _, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed")
    sys.exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
