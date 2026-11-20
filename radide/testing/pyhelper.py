"""Test helper run INSIDE the project's Python (stand-alone: no radide imports).

    python pyhelper.py probe
    python pyhelper.py collect <root>                    -> JSON on the last line (marker @@RADTEST@@)
    python pyhelper.py pytest <root> <out.json> [ids...]  -> results file
    python pyhelper.py unittest <root> <out.json> [ids...]

Collection/results use pytest when it is importable, else unittest (standard library).
Results: [{"id", "state": passed|failed|skipped|error, "duration": s, "message", "output", "file", "line"}].
Used by radide/testing (Test Explorer); "coverage run ... pyhelper.py pytest ..." measures coverage and
debugpy launches this same script to debug one test.
"""
import inspect
import io
import json
import os
import sys
import time
import traceback

MARK = "@@RADTEST@@"


def _emit(obj):
    sys.stdout.write("\n" + MARK + json.dumps(obj) + "\n")
    sys.stdout.flush()


def _has(mod):
    try:
        import importlib.util
        return importlib.util.find_spec(mod) is not None
    except Exception:  # noqa: BLE001
        return False


def probe():
    _emit({"pytest": _has("pytest"), "coverage": _has("coverage"), "debugpy": _has("debugpy"),
           "python": sys.version.split()[0], "executable": sys.executable})


# ------------------------------------------------------------------ pytest
class _Collector:
    def __init__(self):
        self.items = []
        self.errors = []

    def pytest_collectreport(self, report):
        if report.failed:
            self.errors.append({"id": report.nodeid or "<collection>", "message": str(report.longrepr)[-4000:],
                                "file": str(getattr(report, "fspath", "") or "")})

    def pytest_collection_finish(self, session):
        for it in session.items:
            loc = it.location
            path = str(getattr(it, "path", "") or getattr(it, "fspath", ""))
            cls = getattr(it, "cls", None)
            self.items.append({"id": it.nodeid, "file": path, "line": (loc[1] or 0) + 1, "name": it.name,
                               "cls": cls.__name__ if cls is not None else ""})


class _Reporter:
    def __init__(self):
        self.results = {}

    def pytest_runtest_logreport(self, report):
        r = self.results.setdefault(report.nodeid, {"id": report.nodeid, "state": "passed", "duration": 0.0,
                                                    "message": "", "output": ""})
        r["duration"] += float(getattr(report, "duration", 0.0) or 0.0)
        loc = getattr(report, "location", None)
        if loc:
            r["line"] = (loc[1] or 0) + 1
        if report.passed and report.when == "call" and getattr(report, "wasxfail", None) is not None:
            r["state"] = "failed"
            r["message"] = "XPASS (strict)"
        if report.failed:
            r["state"] = "failed" if report.when == "call" else "error"
            r["message"] = (report.longreprtext or "")[-8000:]
        elif report.skipped and r["state"] == "passed":
            r["state"] = "skipped"
            lr = report.longrepr
            r["message"] = lr[2] if isinstance(lr, tuple) and len(lr) > 2 else str(lr or "")
        out = ""
        for name, text in getattr(report, "sections", []):
            if text and ("stdout" in name or "stderr" in name or "log" in name):
                out += "--- %s ---\n%s\n" % (name, text)
        if out:
            r["output"] += out


def collect(root):
    os.chdir(root)
    if _has("pytest"):
        import pytest
        c = _Collector()
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = pytest.main(["--collect-only", "-q", "-p", "no:cacheprovider", root], plugins=[c])
        finally:
            sys.stdout = old
        _emit({"framework": "pytest", "items": c.items, "errors": c.errors, "code": int(code),
               "log": buf.getvalue()[-4000:]})
        return
    items, errors = _unittest_collect(root)
    _emit({"framework": "unittest", "items": items, "errors": errors, "code": 0, "log": ""})


def run_pytest(root, out, ids):
    os.chdir(root)
    import pytest
    rep = _Reporter()
    args = ["-q", "-p", "no:cacheprovider", "-rN"] + (list(ids) or [root])
    code = pytest.main(args, plugins=[rep])
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"framework": "pytest", "code": int(code), "results": list(rep.results.values())}, f)


# ------------------------------------------------------------------ unittest
def _iter_tests(suite):
    for t in suite:
        if hasattr(t, "__iter__"):
            yield from _iter_tests(t)
        else:
            yield t


def _where(test):
    cls = type(test)
    meth = getattr(cls, getattr(test, "_testMethodName", ""), None)
    try:
        f = inspect.getsourcefile(meth or cls)
        line = inspect.getsourcelines(meth or cls)[1]
    except (TypeError, OSError):
        f, line = "", 1
    return f or "", line


def _unittest_collect(root):
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(root, pattern="test*.py", top_level_dir=root)
    items, errors = [], []
    for t in _iter_tests(suite):
        tid = t.id()
        if type(t).__name__ in ("_FailedTest", "ModuleImportFailure"):
            msg = str(getattr(t, "_exception", "")) or tid
            errors.append({"id": tid, "message": msg})
            continue
        f, line = _where(t)
        items.append({"id": tid, "file": f, "line": line, "name": tid.rsplit(".", 1)[-1],
                      "cls": type(t).__name__})
    for e in getattr(loader, "errors", []):
        errors.append({"id": "<import>", "message": str(e)[-4000:]})
    return items, errors


def run_unittest(root, out, ids):
    import unittest
    os.chdir(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(ids) if ids else loader.discover(root, pattern="test*.py", top_level_dir=root)
    results = {}

    class R(unittest.TestResult):
        def startTest(self, test):
            super().startTest(test)
            self._t0 = time.perf_counter()
            self._buf = io.StringIO()
            self._old = (sys.stdout, sys.stderr)
            sys.stdout = sys.stderr = self._buf
            f, line = _where(test)
            results[test.id()] = {"id": test.id(), "state": "passed", "duration": 0.0, "message": "",
                                  "output": "", "file": f, "line": line}

        def stopTest(self, test):
            sys.stdout, sys.stderr = self._old
            r = results[test.id()]
            r["duration"] = time.perf_counter() - self._t0
            r["output"] = self._buf.getvalue()
            super().stopTest(test)

        def addFailure(self, test, err):
            results[test.id()].update(state="failed", message=self._exc_info_to_string(err, test))

        def addError(self, test, err):
            results[test.id()].update(state="error", message=self._exc_info_to_string(err, test))

        def addSkip(self, test, reason):
            results[test.id()].update(state="skipped", message=reason)

        def addUnexpectedSuccess(self, test):
            results[test.id()].update(state="failed", message="unexpected success")
    suite.run(R())
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"framework": "unittest", "code": 0, "results": list(results.values())}, f)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    try:
        if cmd == "probe":
            probe()
        elif cmd == "collect":
            root = os.path.abspath(argv[1])
            if root not in sys.path:
                sys.path.insert(0, root)
            collect(root)
        elif cmd == "pytest":
            run_pytest(os.path.abspath(argv[1]), argv[2], argv[3:])
        elif cmd == "unittest":
            run_unittest(os.path.abspath(argv[1]), argv[2], argv[3:])
        else:
            print("unknown command " + cmd)
            return 2
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 - report everything to the IDE
        _emit({"fatal": traceback.format_exc()[-6000:]})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
