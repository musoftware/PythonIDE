"""Toolchain helpers of the slice D checks (Motion/Targets and Variants/Targets check_targets.py).

Every runner returns (ok, detail) or None when the toolchain is missing (the check prints SKIP)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SCRATCH = Path(os.environ.get("RADIDE_TEST_TMP") or tempfile.gettempdir()) / "radide-slice-d"

RESULTS: list[tuple[str, bool]] = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:1500]}]"), flush=True)
    return bool(cond)


def skip(name, why):
    print(f"SKIP {name}: {why}", flush=True)


def summary() -> int:
    bad = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} passed")
    return 1 if bad else 0


def run(cmd, cwd=None, env=None, timeout=600):
    e = dict(os.environ, **(env or {}))
    return subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout,
                          creationflags=NO_WIN, encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ toolchains
def ring_exe() -> str | None:
    for p in (shutil.which("ring"), r"C:\ring\ring\bin\ring.exe", r"C:\ring\bin\ring.exe"):
        if p and Path(p).is_file():
            return p
    return None


def flutter_exe() -> str | None:
    return shutil.which("flutter") or next((p for p in (r"C:\flutter\bin\flutter.bat",) if Path(p).is_file()), None)


def dotnet_exe() -> str | None:
    return shutil.which("dotnet")


def has_kivy() -> bool:
    import importlib.util
    return importlib.util.find_spec("kivy") is not None


def esbuild_exe() -> str | None:
    """esbuild for the React Native checks: RADIDE_ESBUILD, a cached copy, else `npm i esbuild` (network)."""
    env = os.environ.get("RADIDE_ESBUILD")
    if env and Path(env).is_file():
        return env
    tool = SCRATCH / "jstool"
    exe = tool / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    if exe.is_file():
        return str(exe)
    npm = shutil.which("npm")
    if not npm or not shutil.which("node"):
        return None
    tool.mkdir(parents=True, exist_ok=True)
    try:
        run([npm, "i", "esbuild@0.24.0", "--no-audit", "--no-fund", "--silent"], cwd=tool, timeout=240)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return str(exe) if exe.is_file() else None


# ------------------------------------------------------------------ runners
def ring_run(folder: Path, test_code: str, env=None, timeout=90):
    """Runs test.ring (test_code) in a temp copy of a RingQt project; returns its stdout."""
    ring = ring_exe()
    if not ring:
        return None
    dst = SCRATCH / ("ring_" + folder.name)
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(folder, dst, ignore=shutil.ignore_patterns("*.form", "project.radproj"))
    (dst / "test.ring").write_text(test_code, encoding="utf-8")
    r = run([ring, "test.ring"], cwd=dst, env=dict({"QT_QPA_PLATFORM": "offscreen"}, **(env or {})), timeout=timeout)
    return r.stdout + r.stderr


def flutter_check(folder: Path) -> list[tuple[str, bool, str]]:
    fl = flutter_exe()
    if not fl:
        return []
    out = []
    r = run([fl, "pub", "get", "--offline"], cwd=folder)
    if r.returncode != 0:
        r = run([fl, "pub", "get"], cwd=folder)
    out.append(("flutter pub get", r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]))
    r = run([fl, "analyze", "--no-fatal-infos"], cwd=folder)
    out.append(("flutter analyze clean", r.returncode == 0 and "No issues found" in r.stdout, r.stdout[-1500:]))
    r = run([fl, "test"], cwd=folder, timeout=900)
    out.append(("flutter test", r.returncode == 0 and "All tests passed" in r.stdout, r.stdout[-2000:]))
    for d in ("build", ".dart_tool"):
        shutil.rmtree(folder / d, ignore_errors=True)
    return out


def kivy_run(folder: Path, exec_code: str, env=None, secs=6):
    """Runs the Kivy app with RADKIVY_EXEC (scr = the screen); exec_code writes json to $OUT; returns the dict."""
    if not has_kivy():
        return None
    out = SCRATCH / f"kivy_{folder.name}.json"
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    e = {"RADKIVY_AUTOSTOP": str(secs), "KIVY_NO_ARGS": "1", "KIVY_NO_CONSOLELOG": "1",
         "RADKIVY_EXEC": exec_code.replace("$OUT", str(out).replace("\\", "/"))}
    e.update(env or {})
    r = run([sys.executable, "Form1.py"], cwd=folder, env=e, timeout=90)
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"_error": (r.stdout + r.stderr)[-1500:]}


def rn_run(entry: Path):
    """Bundles a Node entry (generated screen + radfx.js + stubs) with esbuild and runs it; returns RESULT dict."""
    eb = esbuild_exe()
    node = shutil.which("node")
    if not eb or not node:
        return None
    stubs = HERE / "rn_harness" / "stubs.js"
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = SCRATCH / (entry.stem + ".bundle.js")
    cmd = [eb, str(entry), "--bundle", "--platform=node", f"--outfile={out}", "--loader:.js=jsx", "--jsx=transform",
           "--log-level=warning"] + [f"--alias:{m}={stubs}" for m in ("react", "react-native", "@expo/vector-icons",
                                                                        "@react-navigation/native")]
    r = run(cmd, cwd=entry.parent)
    if r.returncode != 0:
        return {"_error": (r.stdout + r.stderr)[-1500:]}
    r = run([node, str(out)], timeout=60)
    for line in r.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    return {"_error": (r.stdout + r.stderr)[-1500:]}


def winforms_case(lang: str, build_form, clicks: str = "", resize: str = "", tag: str = ""):
    """Temp copy of samples/Tests/ForeignProjects/WinForms<CS|VB> (never edited in place): load the form, let
    build_form(form) add controls / animations / sizes, save (Designer + .radide.json + Form1.RadFx.*),
    dotnet build, run with RADIDE_FX_SELFTEST. Returns (build ok, build log, {tag: {control: fields}}, save report)."""
    dn = dotnet_exe()
    if not dn:
        return None
    sys.path.insert(0, str(ROOT))
    from radide.foreign import winforms_cs as W
    src = ROOT / "samples" / "Tests" / "ForeignProjects" / ("WinFormsCS" if lang == "cs" else "WinFormsVB")
    dst = SCRATCH / f"wf_{lang}{tag}"
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("bin", "obj", "*.user"))
    f = W.load_form(dst / f"Form1.Designer.{lang}")
    build_form(f)
    report = W.save_form(f)
    r = run([dn, "build", "-nologo", "-v", "q"], cwd=dst, timeout=600)
    ok = r.returncode == 0
    states: dict = {}
    if ok:
        exe = next(dst.glob("bin/**/WinForms*.exe"), None)
        st = dst / "selftest.txt"
        env = {"RADIDE_FX_SELFTEST": str(st), "RADIDE_FX_CLICK": clicks, "RADIDE_FX_RESIZE": resize,
               "RADIDE_REDUCED_MOTION": os.environ.get("RADIDE_REDUCED_MOTION_TEST", "0")}
        if exe is not None:
            try:
                run([str(exe)], cwd=dst, env=env, timeout=60)
            except subprocess.TimeoutExpired:
                pass
        if st.is_file():
            for line in st.read_text(encoding="utf-8").splitlines():
                parts = line.split(" ")
                t, name = parts[0], parts[1]
                d = states.setdefault(t, {})
                if name == "@sizes":
                    d["@sizes"] = parts[2] if len(parts) > 4 else ""
                else:
                    d[name] = {"x": int(parts[2]), "y": int(parts[3]), "w": int(parts[4]), "h": int(parts[5]),
                               "visible": parts[6] == "1", "back": parts[7], "font": float(parts[8]),
                               "text": " ".join(parts[9:]).replace("_", " ")}
    return ok, (r.stdout + r.stderr)[-2000:], states, report, dst
