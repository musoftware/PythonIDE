"""C# (and Java-free) WinForms code -> python-qt (PySide6) by rules.

QtEmitter is the PySide6 variant of radide/importers/exe/dotnet.PyEmitter (which emits Tkinter code): the C#
parser, statements, expressions, string/number rules and the form structure are shared; only the parts that
touch controls, the form, message boxes and the application are different.
"""
from __future__ import annotations

import re

from ..importers.exe.dotnet import P_ATOM, PyEmitter, Untranslatable, cs_date_format, cs_format_spec, pystr


class CsNumbersMixin:
    """C# prints a double without a format like 100 / 0.1 / 115.25 ("G"); Python's f"{x}" prints 100.0."""

    def fstring(self, parts) -> str:
        out = []
        for p in parts:
            if isinstance(p, str):
                out.append(p.replace("{", "{{").replace("}", "}}").replace("\\", "\\\\").replace("\n", "\n")
                           .replace('"', '\\"'))
                continue
            node, fmt, _raw = p
            if node[0] == "rawexpr":
                raise Untranslatable("interpolated string")
            code, kind = self.ex(node)
            code = code.replace('"', "'")
            spec = cs_format_spec(fmt) if fmt else ""
            if fmt and not spec:
                spec = cs_date_format(fmt) if re.search(r"[yMdHhms]", fmt) else ""
            if not fmt and kind == "float":
                spec = ".15g"
            out.append("{" + code + (":" + spec if spec else "") + "}")
        return 'f"' + "".join(out) + '"'


class TkEmitter(CsNumbersMixin, PyEmitter):
    """python-tk: the .exe importer's emitter + C#-like number formatting."""


class QtEmitter(CsNumbersMixin, PyEmitter):
    """Translate parsed C# statements into Python lines for a python-qt (PySide6) form class."""

    # ------------------------------------------------------------------ setters
    def try_setter(self, target, vcode, vk=None):
        if target[0] == "name" and target[1] in self.FORM_MEMBERS and not self.is_local(target[1]) and \
                target[1] not in self.fields:
            target = ("member", ("name", "this"), target[1], False)
        if target[0] != "member":
            return None
        obj, prop = target[1], target[2]
        if self.is_form(obj) and (prop in self.fields or prop in self.controls or prop in self.methods):
            return None
        if vcode is None:
            return [] if self.ctrl_of(obj) or self.is_form(obj) else None
        if self.is_form(obj):
            return self.form_setter(prop, vcode)
        name = self.ctrl_of(obj)
        if name is None:
            if obj[0] == "member" and obj[2] in ("Font",) and self.ctrl_of(obj[1]):
                raise Untranslatable("font property")
            return None
        t = self.controls[name]
        s = f"self.{name}"
        sv = vcode if vk == "str" or vcode.startswith(('"', "f\"", "str(")) else f"str({vcode})"
        if t == "Timer":
            if prop == "Enabled":
                if vcode in ("True", "False"):
                    return [f"{s}.{'start' if vcode == 'True' else 'stop'}()"]
                return [f"{s}.start() if {vcode} else {s}.stop()"]
            if prop == "Interval":
                return [f"{s}.setInterval(int({vcode}))"]
            return None
        if prop == "Text":
            if t == "TextBox" and name in self.multiline:
                return [f"{s}.setPlainText({sv})"]
            if t == "ComboBox":
                return [f"{s}.setCurrentText({sv})"]
            if t == "GroupBox":
                return [f"{s}.setTitle({sv})"]
            if t in ("ListBox", "NumericUpDown", "TrackBar"):
                raise Untranslatable(f"{t}.Text")
            return [f"{s}.setText({sv})"]
        if prop == "Checked" and t in ("CheckBox", "RadioButton"):
            return [f"{s}.setChecked(bool({vcode}))"]
        if prop == "Value" and t in ("NumericUpDown", "TrackBar", "ProgressBar"):
            return [f"{s}.setValue(int({vcode}))"]
        if prop in ("Maximum", "Minimum") and t in ("NumericUpDown", "TrackBar", "ProgressBar"):
            return [f"{s}.set{prop}(int({vcode}))"]
        if prop == "Enabled":
            return [f"{s}.setEnabled({vcode if vcode in ('True', 'False') else 'bool(' + vcode + ')'})"]
        if prop == "Visible":
            return [f"{s}.setVisible({vcode if vcode in ('True', 'False') else 'bool(' + vcode + ')'})"]
        if prop in ("BackColor", "ForeColor"):
            css = "background-color" if prop == "BackColor" else "color"
            return [f"{s}.setStyleSheet(f\"{css}: {{{vcode}}};\")"]
        if prop in ("Left", "Top"):
            return [f"{s}.move({vcode if prop == 'Left' else s + '.x()'}, {vcode if prop == 'Top' else s + '.y()'})"]
        if prop in ("Width", "Height"):
            return [f"{s}.resize({vcode if prop == 'Width' else s + '.width()'}, "
                    f"{vcode if prop == 'Height' else s + '.height()'})"]
        if prop == "SelectedIndex" and t == "ListBox":
            return [f"{s}.setCurrentRow(int({vcode}))"]
        if prop == "SelectedIndex" and t == "ComboBox":
            return [f"{s}.setCurrentIndex(int({vcode}))"]
        if prop in ("SelectedItem", "SelectedText") and t == "ComboBox":
            return [f"{s}.setCurrentText(str({vcode}))"]
        if prop == "ReadOnly" and t == "TextBox":
            return [f"{s}.setReadOnly(bool({vcode}))"]
        if prop == "PasswordChar" and t == "TextBox":
            return [f"{s}.setEchoMode(QLineEdit.EchoMode.Password if {vcode} else QLineEdit.EchoMode.Normal)"]
        if prop == "Image" and t == "PictureBox":
            raise Untranslatable("images")
        if prop in ("Focus",):
            return None
        raise Untranslatable(f"{t}.{prop}")

    def form_setter(self, prop, vcode):
        if prop == "Text":
            return [f"self.setWindowTitle(str({vcode}))" if not vcode.startswith(('"', 'f"')) else
                    f"self.setWindowTitle({vcode})"]
        if prop == "BackColor":
            return [f"self.setStyleSheet(f\"background-color: {{{vcode}}};\")"]
        if prop == "Width":
            return [f"self.resize({vcode}, self.height())"]
        if prop == "Height":
            return [f"self.resize(self.width(), {vcode})"]
        if prop == "TopMost":
            self.imports.add("from PySide6.QtCore import Qt")
            return [f"self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool({vcode}))", "self.show()"]
        if prop == "Visible":
            return [f"self.setVisible(bool({vcode}))"]
        if prop == "Opacity":
            return [f"self.setWindowOpacity({vcode})"]
        if prop == "WindowState":
            return [f"self.showMaximized() if {vcode} == 'zoomed' else self.showNormal()"]
        raise Untranslatable(f"Form.{prop}")

    # ------------------------------------------------------------------ getters
    def control_get(self, name: str, prop: str):
        t = self.controls[name]
        s = f"self.{name}"
        if t == "Timer":
            if prop == "Enabled":
                return f"{s}.isActive()", "bool"
            if prop == "Interval":
                return f"{s}.interval()", "int"
            return None
        if prop == "Text":
            if t == "TextBox" and name in self.multiline:
                return f"{s}.toPlainText()", "str"
            if t == "ComboBox":
                return f"{s}.currentText()", "str"
            if t == "GroupBox":
                return f"{s}.title()", "str"
            if t == "NumericUpDown":
                return f"str({s}.value())", "str"
            if t == "ListBox":
                return f"({s}.currentItem().text() if {s}.currentItem() else \"\")", "str"
            return f"{s}.text()", "str"
        if prop == "Checked" and t in ("CheckBox", "RadioButton"):
            return f"{s}.isChecked()", "bool"
        if prop == "Value" and t in ("NumericUpDown", "TrackBar", "ProgressBar"):
            return f"{s}.value()", "int"
        if prop in ("Maximum", "Minimum") and t in ("NumericUpDown", "TrackBar", "ProgressBar"):
            return f"{s}.{prop.lower()}()", "int"
        if prop == "SelectedIndex" and t == "ListBox":
            return f"{s}.currentRow()", "int"
        if prop == "SelectedIndex" and t == "ComboBox":
            return f"{s}.currentIndex()", "int"
        if prop in ("SelectedItem", "SelectedValue") and t == "ListBox":
            return f"({s}.currentItem().text() if {s}.currentItem() else None)", None
        if prop in ("SelectedItem", "SelectedValue", "SelectedText") and t == "ComboBox":
            return f"{s}.currentText()", "str"
        if prop == "Enabled":
            return f"{s}.isEnabled()", "bool"
        if prop == "Visible":
            return f"{s}.isVisible()", "bool"
        if prop in ("Width", "Height"):
            return f"{s}.{prop.lower()}()", "int"
        if prop in ("Left", "Top"):
            return f"{s}.{'x' if prop == 'Left' else 'y'}()", "int"
        if prop == "Name":
            return pystr(name), "str"
        if prop == "TextLength":
            return f"len({self.control_get(name, 'Text')[0]})", "int"
        if prop == "Lines" and t == "TextBox":
            return f"{self.control_get(name, 'Text')[0]}.splitlines()", "list"
        if prop == "Focused":
            return f"{s}.hasFocus()", "bool"
        if prop == "ReadOnly" and t == "TextBox":
            return f"{s}.isReadOnly()", "bool"
        return None

    def items_call(self, name: str, method: str, args: list):
        t = self.controls[name]
        s = f"self.{name}"
        a = [self.ex(x)[0] for x in args]
        if t in ("ListBox", "ComboBox"):
            if method == "Add":
                return f"{s}.addItem(str({a[0]}))", None
            if method == "AddRange":
                return f"{s}.addItems([str(x) for x in {a[0]}])", None
            if method == "Clear":
                return f"{s}.clear()", None
            if method == "RemoveAt":
                return (f"{s}.takeItem({a[0]})" if t == "ListBox" else f"{s}.removeItem({a[0]})"), None
            if method == "Insert":
                return f"{s}.insertItem({a[0]}, str({a[1]}))", None
            if method == "Contains":
                return f"(str({a[0]}) in {self.items_get(name)[0]})", "bool"
            if method == "IndexOf":
                return f"{self.items_get(name)[0]}.index(str({a[0]}))", "int"
            if method == "Remove":
                return (f"{s}.takeItem({self.items_get(name)[0]}.index(str({a[0]})))" if t == "ListBox" else
                        f"{s}.removeItem({s}.findText(str({a[0]})))"), None
        raise Untranslatable(f"{t}.Items.{method}")

    def items_get(self, name: str):
        t = self.controls[name]
        s = f"self.{name}"
        if t == "ListBox":
            return f"[{s}.item(i).text() for i in range({s}.count())]", "list"
        if t == "ComboBox":
            return f"[{s}.itemText(i) for i in range({s}.count())]", "list"
        raise Untranslatable(f"{t}.Items")

    def member(self, node):
        obj, prop = node[1], node[2]
        if self.is_form(obj) and prop not in self.controls and prop not in self.fields and prop not in self.methods:
            if prop == "Text":
                return "self.windowTitle()", "str", P_ATOM
            if prop in ("Width", "Height"):
                return f"self.{prop.lower()}()", "int", P_ATOM
        if obj[0] == "member" and obj[2] == "Items" and self.ctrl_of(obj[1]) and prop == "Count":
            return f"self.{self.ctrl_of(obj[1])}.count()", "int", P_ATOM
        if obj[0] == "member" and obj[2] == "SelectedItems" and self.ctrl_of(obj[1]) and prop == "Count":
            return f"len(self.{self.ctrl_of(obj[1])}.selectedItems())", "int", P_ATOM
        return super().member(node)

    # ------------------------------------------------------------------ calls
    def call_stmt_rule(self, e):
        func = e[1]
        if func[0] == "member" and func[2] in ("Show", "ShowDialog") and func[1][0] == "name" and \
                func[1][1] in self.forms:
            f = func[1][1]
            return [f"from {f} import {f}", f"self._{f} = {f}()", f"self._{f}.show()"]
        if func[0] == "member" and func[2] == "AppendText" and self.ctrl_of(func[1]):
            name = self.ctrl_of(func[1])
            arg = self.ex(e[2][0])[0]
            if name in self.multiline:
                return [f"self.{name}.moveCursor(self.{name}.textCursor().MoveOperation.End)",
                        f"self.{name}.insertPlainText(str({arg}))"]
            return [f"self.{name}.setText(self.{name}.text() + str({arg}))"]
        return None

    def call(self, node):
        func = node[1]
        if func[0] == "name" and not self.is_local(func[1]) and func[1] not in self.methods:
            n = func[1]
            if n in ("Close", "Dispose"):
                return "self.close()", None, P_ATOM
            if n == "Hide":
                return "self.hide()", None, P_ATOM
            if n in ("Show", "Activate", "BringToFront"):
                return "self.show()", None, P_ATOM
            if n in ("Refresh", "Invalidate", "Update", "SuspendLayout", "ResumeLayout", "PerformLayout"):
                return "self.update()", None, P_ATOM
        return super().call(node)

    def msgbox(self, args, vb=False):
        self.imports.add("from PySide6.QtWidgets import QMessageBox")
        a = [self.ex(x)[0] for x in args]
        msg = a[0] if a else '""'
        if not args or self.ex(args[0])[1] != "str":
            msg = f"str({msg})"
        title = '""'
        buttons, icon = "", ""
        rest = list(args[1:])
        if vb:
            if rest:
                buttons = self._enum_text(rest[0])
            if len(rest) > 1:
                title = self.ex(rest[1])[0]
        else:
            if rest:
                title = self.ex(rest[0])[0]
            if len(rest) > 1:
                buttons = self._enum_text(rest[1])
            if len(rest) > 2:
                icon = self._enum_text(rest[2])
        b, i = buttons.lower(), icon.lower() + " " + buttons.lower()
        fn = "critical" if any(w in i for w in ("error", "stop", "critical", "hand")) else \
            "warning" if any(w in i for w in ("warning", "exclamation")) else \
            "question" if "question" in i else "information"
        B = "QMessageBox.StandardButton"
        if "yesnocancel" in b:
            return (f"{{{B}.Yes: \"Yes\", {B}.No: \"No\"}}.get(QMessageBox.{fn}(self, {title}, {msg}, "
                    f"{B}.Yes | {B}.No | {B}.Cancel), \"Cancel\")"), "str", P_ATOM
        for key, (yes, no, bb) in {"yesno": ("Yes", "No", f"{B}.Yes | {B}.No"),
                                   "okcancel": ("OK", "Cancel", f"{B}.Ok | {B}.Cancel"),
                                   "retrycancel": ("Retry", "Cancel", f"{B}.Retry | {B}.Cancel")}.items():
            if key in b:
                ok_btn = {"Yes": "Yes", "OK": "Ok", "Retry": "Retry"}[yes]
                return (f"(\"{yes}\" if QMessageBox.{fn}(self, {title}, {msg}, {bb}) == {B}.{ok_btn} "
                        f"else \"{no}\")"), "str", P_ATOM
        return f"QMessageBox.{fn}(self, {title}, {msg})", "str", P_ATOM

    def call_rule(self, obj, method, args):
        n = len(args)
        a = lambda i: self.ex(args[i])[0]   # noqa: E731
        if obj[0] == "member" and obj[2] == "Items" and self.ctrl_of(obj[1]):
            code, kind = self.items_call(self.ctrl_of(obj[1]), method, args)
            return code, kind, P_ATOM
        cname = self.ctrl_of(obj)
        if cname is not None:
            t = self.controls[cname]
            s = f"self.{cname}"
            if method == "Focus" or method == "Select" and n == 0:
                return f"{s}.setFocus()", None, P_ATOM
            if method == "Clear" and t in ("TextBox", "ListBox", "ComboBox"):
                return f"{s}.clear()", None, P_ATOM
            if method == "SelectAll" and t == "TextBox":
                return f"{s}.selectAll()", None, P_ATOM
            if method in ("Start", "Stop") and t == "Timer":
                return f"{s}.{method.lower()}()", None, P_ATOM
            if method == "Hide":
                return f"{s}.hide()", None, P_ATOM
            if method == "Show":
                return f"{s}.show()", None, P_ATOM
            if method in ("Refresh", "Invalidate", "Update"):
                return f"{s}.update()", None, P_ATOM
            if method == "BringToFront":
                return f"{s}.raise_()", None, P_ATOM
            if method == "SendToBack":
                return f"{s}.lower()", None, P_ATOM
            if method == "PerformClick":
                return f"{s}.click()", None, P_ATOM
            if method == "Increment" and t == "ProgressBar":
                return f"{s}.setValue({s}.value() + int({a(0)}))", None, P_ATOM
            if method == "PerformStep" and t == "ProgressBar":
                return f"{s}.setValue({s}.value() + 10)", None, P_ATOM
            if method == "ShowDialog" and t in ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog",
                                                "FolderBrowserDialog"):
                return f"{s}.ShowDialog()", "str", P_ATOM
            if method == "ToString" and n == 0:
                return self.ex(obj)
            raise Untranslatable(f"{t}.{method}()")
        if self.is_form(obj):
            if method in ("Close", "Dispose"):
                return "self.close()", None, P_ATOM
            if method == "Hide":
                return "self.hide()", None, P_ATOM
            if method in self.methods:
                return f"self.{method}({self.arglist(args)})", None, P_ATOM
            if method in ("Show", "Activate", "BringToFront"):
                return "self.show()", None, P_ATOM
            if method in ("Refresh", "Invalidate", "Update"):
                return "self.update()", None, P_ATOM
            raise Untranslatable(f"Form.{method}()")
        return super().call_rule(obj, method, args)

    def static_call(self, obj, method, args):
        cls = None
        if obj[0] == "name" and not self.is_local(obj[1]) and obj[1] not in self.controls and \
                obj[1] not in self.fields:
            cls = obj[1]
        elif obj[0] == "member" and obj[1][0] in ("name", "member"):
            cls = obj[2]
        n = len(args)
        a = lambda i: self.ex(args[i])[0]   # noqa: E731
        if cls == "Application" and method == "Exit":
            self.imports.add("from PySide6.QtWidgets import QApplication")
            return "QApplication.quit()", None, P_ATOM
        if cls == "Application" and method == "DoEvents":
            self.imports.add("from PySide6.QtWidgets import QApplication")
            return "QApplication.processEvents()", None, P_ATOM
        if cls in ("Interaction",) and method == "InputBox":
            self.imports.add("from PySide6.QtWidgets import QInputDialog")
            title = a(1) if n > 1 else '""'
            return f"QInputDialog.getText(self, {title}, {a(0)})[0]", "str", P_ATOM
        return super().static_call(obj, method, args)


def qt_code_fixups(code: str) -> str:
    """Small clean-ups of the python-qt user code produced through translate_form_class."""
    return re.sub(r"\n{3,}(?=    def )", "\n\n", code)


_TRYPARSE_RX = re.compile(r"\b(double|float|decimal|int|long|short|Double|Single|Decimal|Int32|Int64|Int16)"
                          r"\.TryParse\s*\(")


def rewrite_tryparse(src: str) -> tuple[str, int]:
    """C#: ``if (!double.TryParse(s, out double v) || v < 0)`` ->
    ``double v = 0; bool __ok1 = true; try { v = double.Parse(s); } catch (Exception) { __ok1 = false; }``
    + ``if (!__ok1 || v < 0)`` (the translators handle try/catch but not out arguments)."""
    from .vbnet import _close_paren, _split_args
    count = 0
    for _guard in range(50):
        m = _TRYPARSE_RX.search(src)
        if not m:
            break
        close = _close_paren(src, m.end() - 1)
        if close < 0:
            break
        args = _split_args(src[m.end():close])
        if len(args) < 2 or not args[-1].startswith("out "):
            src = src[:m.start()] + m.group(1) + ".TryParse\x01(" + src[m.end():]
            continue
        out = args[-1][4:].strip().split()
        var, typ = out[-1], (out[0] if len(out) > 1 and out[0] != "var" else m.group(1))
        count += 1
        ok = f"_ok{count}"
        line_start = src.rfind("\n", 0, m.start()) + 1
        indent = re.match(r"[ \t]*", src[line_start:]).group(0)
        decl = f"{typ} {var} = 0; " if len(out) > 1 else ""
        pre = (f"{indent}{decl}bool {ok} = true; try {{ {var} = {m.group(1)}.Parse({args[0]}); }} "
               f"catch (Exception) {{ {ok} = false; }}\n")
        src = src[:m.start()] + ok + src[close + 1:]
        src = src[:line_start] + pre + src[line_start:]
    return src.replace(".TryParse\x01(", ".TryParse("), count
