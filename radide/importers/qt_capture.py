"""Capture the GUI built by an existing Qt program (PySide6/PySide2/PyQt6/PyQt5).

Usage: python qt_capture.py <script.py> <output.json>
Run with QT_QPA_PLATFORM=offscreen. QApplication.exec() is replaced: when the
program starts its event loop, all visible windows are inspected (real
geometry after layouts) and written as JSON.
"""
import gc
import json
import os
import re
import runpy
import sys
import traceback

BINDINGS = ("PySide6", "PyQt6", "PySide2", "PyQt5")


class _Done(BaseException):
    pass


def _binding_for(source: str):
    for b in BINDINGS:
        if re.search(rf"^\s*(from|import)\s+{b}\b", source, re.M):
            return b
    return None


def main():
    script = os.path.abspath(sys.argv[1])
    out_path = sys.argv[2]
    with open(script, encoding="utf-8-sig", errors="replace") as fh:
        source = fh.read()
    binding = _binding_for(source)
    result = {"windows": [], "error": "", "binding": binding or ""}
    if binding is None:
        result["error"] = "no Qt binding import found"
        return _write(out_path, result)
    try:
        mod = __import__(f"{binding}.QtWidgets", fromlist=["QtWidgets"])
        QtWidgets = mod
        QtCore = __import__(f"{binding}.QtCore", fromlist=["QtCore"])
    except Exception:  # noqa: BLE001
        result["error"] = f"{binding} is not installed for this interpreter ({sys.executable})"
        return _write(out_path, result)

    def fake_exec(*_a, **_k):
        try:
            app = QtWidgets.QApplication.instance()
            for _ in range(3):
                app.processEvents()
            result.update(capture(QtWidgets, QtCore, script))
        except Exception:  # noqa: BLE001
            result["error"] = "capture failed:\n" + traceback.format_exc()
        result["captured"] = True
        raise _Done()
    QtWidgets.QApplication.exec = fake_exec
    if hasattr(QtWidgets.QApplication, "exec_"):
        QtWidgets.QApplication.exec_ = fake_exec
    sys.argv = [script]
    os.chdir(os.path.dirname(script))
    sys.path.insert(0, os.path.dirname(script))
    try:
        runpy.run_path(script, run_name="__main__")
    except (_Done, SystemExit):
        pass
    except BaseException:  # noqa: BLE001
        result["error"] = "the program raised an error:\n" + traceback.format_exc()
    if not result.get("captured"):
        try:
            if QtWidgets.QApplication.instance() is not None:
                result.update(capture(QtWidgets, QtCore, script))
        except Exception:  # noqa: BLE001
            pass
    _write(out_path, result)


def _write(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, default=str)
    os._exit(0)


# ------------------------------------------------------------------ inspection
def _names(QtCore):
    """id(QObject wrapper) -> python name, from instances defined in the script."""
    names = {}
    spaces = []
    main = sys.modules.get("__main__")
    if main is not None:
        spaces.append(("", vars(main)))
    f = sys._getframe()
    while f is not None:
        spaces.append(("", f.f_globals))
        spaces.append(("", f.f_locals))
        f = f.f_back
    for obj in gc.get_objects():
        try:
            if hasattr(obj, "__dict__") and getattr(type(obj), "__module__", "") in ("__main__", "<run_path>"):
                spaces.append(("self.", vars(obj)))
            elif hasattr(obj, "__dict__") and type(obj).__name__.startswith("Ui_"):
                spaces.append(("self.ui.", vars(obj)))      # Qt Designer generated classes
        except Exception:  # noqa: BLE001
            continue
    for prefix, space in spaces:
        try:
            items = list(space.items())
        except Exception:  # noqa: BLE001
            continue
        for k, v in items:
            if k.startswith("__"):
                continue
            if isinstance(v, QtCore.QObject) and id(v) not in names:
                names[id(v)] = prefix + k
    return names


def _font(w):
    f = w.font()
    return {"family": f.family(), "size": f.pointSize() if f.pointSize() > 0 else 9,
            "bold": f.bold(), "italic": f.italic()}


def _style_color(w, prop):
    m = re.search(rf"(?<![-\w]){prop}\s*:\s*(#[0-9A-Fa-f]{{6}})", w.styleSheet() or "")
    return m.group(1).upper() if m else ""


KEEP_CONTAINER = ("QGroupBox", "QTabWidget", "QScrollArea", "QStackedWidget", "QSplitter")
LEAF = ("QPushButton", "QToolButton", "QLabel", "QLineEdit", "QTextEdit", "QPlainTextEdit",
        "QCheckBox", "QRadioButton", "QListWidget", "QListView", "QComboBox", "QSpinBox",
        "QDoubleSpinBox", "QSlider", "QDial", "QProgressBar", "QTableWidget", "QTableView",
        "QTreeWidget", "QTreeView", "QDateEdit", "QTimeEdit", "QDateTimeEdit", "QCalendarWidget",
        "QScrollBar", "QLCDNumber", "QTextBrowser", "QCommandLinkButton", "QKeySequenceEdit")


def _qt_class(QtWidgets, w):
    for cls in type(w).__mro__:
        if cls.__module__.endswith("QtWidgets"):
            return cls.__name__
    return type(w).__name__


def _is_plain_box(QtWidgets, w, qcls):
    """A layout-only QWidget/QFrame (no frame, no style): flattened into its parent."""
    if qcls not in ("QWidget", "QFrame"):
        return False
    if w.styleSheet() or w.autoFillBackground():
        return False
    if qcls == "QFrame":
        shape = w.frameShape()
        shape = getattr(shape, "value", shape)
        if int(shape) != 0:
            return False
    return True


def _widget(QtWidgets, QtCore, w, origin, names, out):
    qcls = _qt_class(QtWidgets, w)
    pos = w.mapTo(origin, QtCore.QPoint(0, 0)) if origin is not w else QtCore.QPoint(0, 0)
    if qcls in ("QMenuBar", "QStatusBar", "QToolBar", "QSizeGrip", "QRubberBand", "QMenu",
                "QTabBar", "QScrollBar") and qcls not in LEAF[:-1]:
        return
    if not w.isVisible() or w.isWindow():
        return
    if _is_plain_box(QtWidgets, w, qcls):
        for c in w.children():
            if isinstance(c, QtWidgets.QWidget):
                _widget(QtWidgets, QtCore, c, origin, names, out)
        return
    d = {"class": qcls, "pyclass": type(w).__name__, "name": names.get(id(w), ""),
         "objectName": w.objectName(), "x": pos.x(), "y": pos.y(),
         "width": w.width(), "height": w.height(), "enabled": w.isEnabled(),
         "tooltip": w.toolTip(), "font": _font(w),
         "bg": _style_color(w, "background-color") or _style_color(w, "background"),
         "fg": _style_color(w, "color")}
    get = lambda m, *a: getattr(w, m)(*a) if hasattr(w, m) else None
    if qcls == "QGroupBox":
        d["text"] = w.title()
    elif hasattr(w, "text") and qcls not in ("QComboBox",):
        try:
            d["text"] = w.text()
        except TypeError:
            pass
    if qcls in ("QTextEdit", "QPlainTextEdit", "QTextBrowser"):
        d["text"] = w.toPlainText()
        d["readonly"] = w.isReadOnly()
    if qcls == "QLineEdit":
        d["password"] = int(w.echoMode().value if hasattr(w.echoMode(), "value") else w.echoMode()) == 2
        d["readonly"] = w.isReadOnly()
        d["maxlength"] = w.maxLength() if w.maxLength() < 32767 else 0
        d["placeholder"] = w.placeholderText()
    if qcls in ("QCheckBox", "QRadioButton"):
        d["checked"] = w.isChecked()
    if qcls == "QComboBox":
        d["items"] = [w.itemText(i) for i in range(w.count())]
        d["editable"] = w.isEditable()
    if qcls == "QListWidget":
        d["items"] = [w.item(i).text() for i in range(w.count())]
    if qcls in ("QSpinBox", "QDoubleSpinBox", "QSlider", "QDial", "QProgressBar"):
        d.update(minimum=get("minimum"), maximum=get("maximum"), value=get("value"))
    if qcls == "QLabel":
        pm = w.pixmap()
        d["has_pixmap"] = bool(pm is not None and not pm.isNull())
        try:
            al = int(w.alignment().value if hasattr(w.alignment(), "value") else w.alignment())
        except Exception:  # noqa: BLE001
            al = 1
        d["align"] = "Center" if al & 0x4 else ("Right" if al & 0x2 else "Left")
    d["children"] = []
    if qcls in ("QGroupBox", "QWidget", "QFrame") or qcls not in LEAF:
        inner = w
        if qcls == "QTabWidget":
            inner = w.currentWidget()
            d["tabs"] = [w.tabText(i) for i in range(w.count())]
        elif qcls == "QScrollArea":
            inner = w.widget()
        elif qcls == "QStackedWidget":
            inner = w.currentWidget()
        if inner is not None:
            kids = inner.children() if inner is not w else w.children()
            for c in kids:
                if isinstance(c, QtWidgets.QWidget):
                    _widget(QtWidgets, QtCore, c, w, names, d["children"])
    out.append(d)


def _menu(QtWidgets, menu, names):
    items = []
    for a in menu.actions():
        if a.isSeparator():
            items.append({"Text": "-"})
        elif a.menu() is not None:
            items.append({"Text": a.text().replace("&", ""), "Items": _menu(QtWidgets, a.menu(), names),
                          "pyname": names.get(id(a), "")})
        else:
            items.append({"Text": a.text().replace("&", ""), "pyname": names.get(id(a), ""),
                          "objectName": a.objectName()})
    return items


def capture(QtWidgets, QtCore, script):
    names = _names(QtCore)
    app = QtWidgets.QApplication.instance()
    tops = [w for w in app.topLevelWidgets() if w.isVisible() and w.isWindow()
            and _qt_class(QtWidgets, w) not in ("QMenu", "QToolTip")]
    windows = []
    for top in tops:
        qcls = _qt_class(QtWidgets, top)
        client = top
        offset_y = 0
        menu = None
        if qcls == "QMainWindow":
            client = top.centralWidget() or top
            if top.menuBar() is not None and top.menuBar().actions():
                menu = _menu(QtWidgets, top.menuBar(), names)
        children = []
        base = client
        for c in (client.children() if client is not top else top.children()):
            if isinstance(c, QtWidgets.QWidget):
                _widget(QtWidgets, QtCore, c, base, names, children)
        geo = client.geometry() if client is not top else top.geometry()
        windows.append({
            "title": top.windowTitle(), "name": names.get(id(top), ""), "class_name": type(top).__name__,
            "qclass": qcls, "width": client.width() if client is not top else top.width(),
            "height": client.height() if client is not top else top.height(),
            "bg": _style_color(top, "background-color"), "menu": menu, "children": children,
            "resizable": [True, True], "offset_y": offset_y, "client_y": geo.y(),
        })
    return {"windows": windows}


if __name__ == "__main__":
    main()
