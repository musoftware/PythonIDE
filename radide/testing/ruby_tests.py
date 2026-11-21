"""Test Explorer adapters for Ruby: Rails minitest (``bin/rails test``) and RSpec (``bundle exec rspec``).

- **Rails minitest**: discovery reads ``test/**/*_test.rb`` (``class XTest < ...``, ``test "does x" do`` ->
  ``test_does_x``, ``def test_x``); runs go through ``rails_minitest.rb`` (``bin/rails test`` in-process plus a
  reporter that prints one ``@@RADTEST@@{json}`` line per test) after ``bin/rails db:test:prepare`` (the test
  database follows db/schema.rb); a selection runs as ``file:line`` arguments.
- **RSpec**: ``spec/**/*_spec.rb`` (describe / context / it, nesting by indentation); runs
  ``bundle exec rspec --format json --out <tmp> --format progress [file:line ...]``.

Both use the project's Ruby + bundle (``radide/web_site/frameworks/rails.py``: ruby_exe / ruby_env).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import Adapter, Result, RunPlan, Step, _files, _markers, _read, _secs, rel

HERE = Path(__file__).resolve().parent
MINITEST_RUNNER = HERE / "rails_minitest.rb"


def _ruby() -> tuple[str, dict]:
    try:
        from ..web_site.frameworks.rails import ruby_env, ruby_exe
        return ruby_exe(), ruby_env()
    except Exception:  # noqa: BLE001
        return "", {}


def _gems(root: Path) -> str:
    return _read(root / "Gemfile.lock") or _read(root / "Gemfile")


def _bundle_ready(root: Path) -> str:
    if not (root / "Gemfile.lock").is_file():
        return "the gems are not installed: run bundle install (Rails menu > Bundler)"
    cfg = _read(root / ".bundle" / "config")
    if "vendor/bundle" in cfg and not (root / "vendor" / "bundle").is_dir():
        return "the gems are not installed: run bundle install (Rails menu > Bundler)"
    return ""


def minitest_name(title: str) -> str:
    """Rails' ``test "does x" do`` -> the method name minitest reports (``test_does_x``)."""
    return "test_" + re.sub(r"\s+", "_", title)


_CLASS = re.compile(r"^\s*class\s+([\w:]+)\s*<\s*([\w:]+)")
_TEST_BLOCK = re.compile(r"""^\s*test\s*\(?\s*(['"])(.+?)\1\s*\)?\s*(?:do|\{)""")
_TEST_DEF = re.compile(r"^\s*def\s+(test_\w+[?!]?)")


class RailsTestAdapter(Adapter):
    id = "rails-minitest"
    name = "Rails tests (minitest)"
    language = "ruby"

    @classmethod
    def detect(cls, root):
        root = Path(root)
        return (root / "config" / "application.rb").is_file() and (root / "test").is_dir() and \
            bool(cls._test_files(root))

    @staticmethod
    def _test_files(root):
        return [f for f in _files(Path(root) / "test", [r".*_test\.rb"]) if "system" not in f.parts]

    def available(self):
        ruby, _env = _ruby()
        if not ruby:
            return False, "Ruby was not found (toolchains\\ruby)"
        if "rails/test_unit/railtie" in _read(self.root / "config" / "application.rb") and \
                re.search(r"^\s*#\s*require\s+['\"]rails/test_unit/railtie", _read(self.root / "config" /
                                                                                   "application.rb"), re.M):
            return False, "tests are switched off in config/application.rb (Rails menu > Tests > Set Up Tests)"
        why = _bundle_ready(self.root)
        return (False, why) if why else (True, "")

    def discover(self):
        out = []
        for f in self._test_files(self.root):
            cls = ""
            for n, line in enumerate(_read(f).splitlines(), 1):
                m = _CLASS.match(line)
                if m:
                    cls = m.group(1)
                    continue
                m = _TEST_BLOCK.match(line)
                name = minitest_name(m.group(2)) if m else ""
                if not m:
                    d = _TEST_DEF.match(line)
                    name = d.group(1) if d else ""
                if name and cls:
                    title = m.group(2) if m else name
                    out.append(self.item(f"{cls}#{name}", title, f, n, cls))
        return out

    def plan(self, items, coverage=False, debug=False):
        ruby, env = _ruby()
        argv = [ruby or "ruby", str(MINITEST_RUNNER)]
        if items:
            argv += sorted({f"{rel(self.root, i.file)}:{i.line}" for i in items})
        env = dict(env)
        env.pop("RAILS_ENV", None)
        env.update({"RAILS_ENV": "test", "NO_COLOR": "1", "PARALLEL_WORKERS": "1", "DISABLE_SPRING": "1"})

        def parse(text):
            out = []
            for d in _markers(text):
                out.append(Result(id=d.get("id", ""), state=d.get("state", "passed"),
                                  duration=_secs(d.get("duration")), message=d.get("message", ""),
                                  file=d.get("file", ""), line=int(d.get("line") or 0), name=d.get("name", "")))
            return out
        prep = Step([ruby or "ruby", "bin/rails", "db:test:prepare"], self.root, env, "bin/rails db:test:prepare")
        return RunPlan([prep, Step(argv, self.root, env, "bin/rails test")], parse, tmp=self.tmp)


_RSPEC_TEST = re.compile(r"""^(\s*)(it|specify|example|scenario)\s*\(?\s*(['"])(.+?)\3""")
_RSPEC_GROUP = re.compile(r"""^(\s*)(?:RSpec\.)?(describe|context|feature)\s*\(?\s*(['"]?)([\w:]+|.+?)\3\s*"""
                          r"""(?:,.*)?(?:do|\{)""")


def _rspec_scan(path: Path) -> list[tuple[list[str], str, int]]:
    out = []
    stack: list[tuple[int, str]] = []
    for n, line in enumerate(_read(path).splitlines(), 1):
        g = _RSPEC_GROUP.match(line)
        t = _RSPEC_TEST.match(line) if not g else None
        if not (g or t):
            continue
        ind = len((g or t).group(1).expandtabs(4))
        while stack and stack[-1][0] >= ind:
            stack.pop()
        if g:
            stack.append((ind, g.group(4)))
        else:
            out.append(([s for _i, s in stack], t.group(4), n))
    return out


class RSpecAdapter(Adapter):
    id = "rspec"
    name = "RSpec"
    language = "ruby"

    @classmethod
    def detect(cls, root):
        root = Path(root)
        return (root / "spec").is_dir() and "rspec" in _gems(root) and bool(cls._spec_files(root))

    @staticmethod
    def _spec_files(root):
        return _files(Path(root) / "spec", [r".*_spec\.rb"])

    def available(self):
        ruby, _env = _ruby()
        if not ruby:
            return False, "Ruby was not found (toolchains\\ruby)"
        why = _bundle_ready(self.root)
        return (False, why) if why else (True, "")

    def discover(self):
        out = []
        for f in self._spec_files(self.root):
            for groups, title, line in _rspec_scan(f):
                out.append(self.item(f"{rel(self.root, f)}:{line}", title, f, line, " > ".join(groups)))
        return out

    def plan(self, items, coverage=False, debug=False):
        ruby, env = _ruby()
        rep = self.tmp / "rspec.json"
        if rep.exists():
            rep.unlink()
        argv = [ruby or "ruby", "-S", "bundle", "exec", "rspec", "--format", "json", "--out", str(rep),
                "--format", "progress", "--no-color"]
        if items:
            argv += sorted({f"{rel(self.root, i.file)}:{i.line}" for i in items})
        env = dict(env)
        env.update({"RAILS_ENV": "test", "NO_COLOR": "1"})
        root = self.root

        def parse(_text):
            try:
                data = json.loads(rep.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return []
            out = []
            for ex in data.get("examples", []):
                f = str(ex.get("file_path", "")).lstrip("./")
                line = int(ex.get("line_number") or 0)
                st = {"passed": "passed", "failed": "failed", "pending": "skipped"}.get(ex.get("status"), "error")
                exc = ex.get("exception") or {}
                msg = "\n".join(x for x in (exc.get("class", ""), exc.get("message", ""),
                                            "\n".join((exc.get("backtrace") or [])[:5])) if x)
                out.append(Result(id=f"{f}:{line}", state=st, duration=ex.get("run_time"), message=msg,
                                  file=str(root / f), line=line, name=ex.get("description", "")))
            return out
        return RunPlan([Step(argv, self.root, env, "rspec")], parse, tmp=self.tmp)


ADAPTERS = [RailsTestAdapter, RSpecAdapter]

__all__ = ["ADAPTERS", "RSpecAdapter", "RailsTestAdapter", "minitest_name"]
