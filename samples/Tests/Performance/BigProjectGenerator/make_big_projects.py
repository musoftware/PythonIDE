"""Generate the performance projects:
perf/BigSite  - static-web website, 5000 files in 100 folders + big50k.js / big50k.py / big50k.html (50k lines)
perf/BigApp   - python-tk app project with 5000 modules listed in project.radproj + big50k.py
"""
import json
import shutil
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "out"
N = 5000


def js(i):
    return "\n".join([f"// module {i}", f"export function func_{i}(a, b) {{"] +
                     [f"  const v{j} = a * {j} + b; // line {j}" for j in range(55)] + ["  return a + b;", "}", ""])


def py(i):
    return "\n".join([f'"""module {i}"""', "", f"def func_{i}(a, b):"] +
                     [f"    v{j} = a * {j} + b  # line {j}" for j in range(55)] + ["    return a + b", ""])


def css(i):
    return "\n".join([f".c{i}-{j} {{ color: #{j:06x}; margin: {j}px; }}" for j in range(60)]) + "\n"


def html(i):
    return "<!doctype html>\n<html><head><title>Page %d</title></head><body>\n" % i + \
        "\n".join(f"<p class='c{i}'>Paragraph {j} of page {i}</p>" for j in range(55)) + "\n</body></html>\n"


def big_py(n=50000):
    out = ['"""a 50k-line Python module"""', "import os", "", "class Big:"]
    k = 0
    while len(out) < n - 10:
        out += [f"    def method_{k}(self, x):", f"        y = x * {k} + len(os.sep)", "        return y", ""]
        k += 1
    out += ["", "b = Big()", "b.method_1(2)", ""]
    return "\n".join(out)


def big_js(n=50000):
    return "\n".join(f"function f{k}(x) {{ return x * {k}; }} // line {k}" for k in range(n)) + "\n"


def big_html(n=50000):
    return "<!doctype html><html><body>\n" + "\n".join(f"<div id='d{k}'>row {k}</div>" for k in range(n)) + \
        "\n</body></html>\n"


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    site = OUT / "BigSite"
    makers = [("js", js), ("py", py), ("css", css), ("html", html)]
    for i in range(N):
        d = site / f"dir{i // 50:03d}"
        d.mkdir(parents=True, exist_ok=True)
        ext, fn = makers[i % 4]
        (d / f"file{i:04d}.{ext}").write_text(fn(i), encoding="utf-8")
    (site / "index.html").write_text(html(-1), encoding="utf-8")
    big = site / "big"
    big.mkdir()
    (big / "big50k.js").write_text(big_js(), encoding="utf-8")
    (big / "big50k.py").write_text(big_py(), encoding="utf-8")
    (big / "big50k.html").write_text(big_html(), encoding="utf-8")
    (site / "project.radproj").write_text(json.dumps({
        "name": "BigSite", "language": "static-web", "forms": [], "startup": "", "modules": [], "kind": "website",
        "web": {"root": ".", "start": "index.html", "port": 0}}, indent=2), encoding="utf-8")
    app = OUT / "BigApp"
    app.mkdir(parents=True)
    mods = []
    for i in range(N):
        (app / f"mod{i:04d}.py").write_text(py(i), encoding="utf-8")
        mods.append(f"mod{i:04d}.py")
    (app / "big50k.py").write_text(big_py(), encoding="utf-8")
    mods.append("big50k.py")
    (app / "project.radproj").write_text(json.dumps({
        "name": "BigApp", "language": "python-tk", "forms": [], "startup": "", "modules": mods}, indent=2),
        encoding="utf-8")
    print("files:", sum(1 for _ in OUT.rglob("*") if _.is_file()))


if __name__ == "__main__":
    sys.exit(main())

