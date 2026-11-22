"""Environment robustness - project folders and user profiles that break real users' machines.

    .venv\\Scripts\\python samples\\Tests\\Robustness\\Environment\\test_env_paths.py [--quick] [--scenarios a,b] [--langs x,y]

Scenarios (each: create a project, open + save it, Publish (native exe where the language has one), start the
published exe, Start Without Debugging the way the IDE does):

  long        project folder deeper than 260 characters (MAX_PATH): builds and runs go through a short junction
              %LOCALAPPDATA%\\RADIDE\\sp\\<hash> (paths.short_alias) - without it CreateProcess fails ("The directory
              name is invalid"), MSVC link LNK1104, fbc / windres / gcc cannot open their files
  unicode     Arabic folder name with spaces, '&' and parentheses (short enough to be used directly)
  arabic-user USERPROFILE / LOCALAPPDATA / APPDATA / TEMP / TMP in an Arabic user name with a space (the
              toolchains and .cargo / .rustup / .nuget / go are junctions into it, like a real Arabic profile)
  unc         the project on \\\\localhost\\C$\\... (network path; skipped when the admin share is not reachable)
  junction    the project opened through a junction (OneDrive / redirected folders are reparse points)
  readonly    the project folder is read-only for the user (ACL deny, no admin): publish to another folder works
              and leaves the project untouched; publishing into the project gives a readable error
Exit code = number of failures. --quick: C, VB6, PyTk only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _envlib as E  # noqa: E402
from _envlib import ok  # noqa: E402

ALL_LANGS = ["VB6", "PyTk", "C", "CSharp", "Rust", "Go", "JS"]
ALL_SCEN = ["long", "unicode", "arabic-user", "unc", "junction", "readonly"]
args = sys.argv[1:]
langs = ["C", "VB6", "PyTk"] if "--quick" in args else ALL_LANGS
scens = ALL_SCEN
if "--langs" in args:
    langs = args[args.index("--langs") + 1].split(",")
if "--scenarios" in args:
    scens = args[args.index("--scenarios") + 1].split(",")
SLOW = {"JS"}                                  # only in the scenarios where it matters (long / unicode)
ROOT = E.scratch("paths")
REAL_LOCAL = Path(os.environ["LOCALAPPDATA"])
REAL_HOME = Path(os.environ["USERPROFILE"])
matrix: dict[tuple[str, str], dict[str, bool | None]] = {}
kinds: dict[tuple[str, str], str] = {}


def junction(link: Path, target: Path) -> bool:
    if not target.exists():
        return False
    link.parent.mkdir(parents=True, exist_ok=True)
    import _winapi
    try:
        _winapi.CreateJunction(str(target), str(link))
        return True
    except OSError:
        return False


def run_child(scen: str, base: Path, ls: list[str], out: str = "-", steps: str = "create,open,publish,exe,f5",
              env: dict | None = None, timeout: float = 3600, record: bool = True) -> list[dict]:
    cmd = [E.PY, str(HERE / "_paths_child.py"), scen, str(base), ",".join(ls), out, steps]
    print(f"-- {scen}: {', '.join(ls)}  ({base})", flush=True)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env or E.child_env())
    res = []
    t0 = time.time()
    for raw in p.stdout:
        line = raw.decode("utf-8", "replace").rstrip()
        if line.startswith("RESULT "):
            r = json.loads(line[7:])
            res.append(r)
            if record:
                ok(f"[{scen}] {r['lang']}: {r['step']} ({r['seconds']} s)", r["ok"], r["detail"])
        elif line.startswith("KIND "):
            _k, lang, kind = line.split(" ", 2)
            kinds[(scen, lang)] = kind
        if time.time() - t0 > timeout:
            E.kill_tree(p)
            break
    p.wait()
    for r in res if record else []:
        matrix.setdefault((scen, r["lang"]), {})[r["step"]] = r["ok"]
    return res


def for_scen(scen: str) -> list[str]:
    return [lg for lg in langs if lg not in SLOW or scen in ("long", "unicode")]


# ------------------------------------------------------------------ long
if "long" in scens:
    base = ROOT / "long" / "/".join(f"deep_folder_segment_{i:02d}" for i in range(1, 13))
    base.mkdir(parents=True, exist_ok=True)
    ok("long: the project folder is deeper than MAX_PATH", len(str(base / "C App" / "Publish" / "build")) > 260,
       len(str(base)))
    run_child("long", base, for_scen("long"))

# ------------------------------------------------------------------ unicode folder
if "unicode" in scens:
    base = ROOT / E.ARABIC / "My App (x86) & Co"
    base.mkdir(parents=True, exist_ok=True)
    ok("unicode: the folder is short enough to be used directly (no alias)", len(str(base)) < 100, len(str(base)))
    run_child("unicode", base, for_scen("unicode"))

# ------------------------------------------------------------------ Arabic user profile
if "arabic-user" in scens:
    user = ROOT / "Users" / f"{E.USER_AR} أحمد"
    local, roaming, temp = user / "AppData" / "Local", user / "AppData" / "Roaming", user / "AppData" / "Local" / "Temp"
    for d in (local, roaming, temp):
        d.mkdir(parents=True, exist_ok=True)
    for sub in ("toolchains", "tools"):          # the IDE's downloaded toolchains, installed for this user
        junction(local / "RADIDE" / sub, REAL_LOCAL / "RADIDE" / sub)
    for sub in (".cargo", ".rustup", ".nuget", "go", ".dotnet"):
        junction(user / sub, REAL_HOME / sub)
    env = E.child_env(USERPROFILE=user, HOMEPATH=str(user)[2:], LOCALAPPDATA=local, APPDATA=roaming, TEMP=temp,
                      TMP=temp, RADIDE_ENV_SCRATCH=ROOT)
    base = ROOT / "arabic-user-projects"
    base.mkdir(parents=True, exist_ok=True)
    res = run_child("arabic-user", base, for_scen("arabic-user"), env=env)
    ok("arabic-user: the IDE's own data went to the Arabic LOCALAPPDATA", (local / "RADIDE").is_dir())

# ------------------------------------------------------------------ UNC path
if "unc" in scens:
    local_dir = ROOT / "unc"
    local_dir.mkdir(parents=True, exist_ok=True)
    drive, rest = str(local_dir.resolve()).split(":", 1)
    unc = Path(f"\\\\localhost\\{drive}$" + rest)
    if unc.is_dir():
        run_child("unc", unc, for_scen("unc"))
    else:
        E.info("unc: \\\\localhost\\C$ is not reachable here - scenario skipped")

# ------------------------------------------------------------------ junction (OneDrive-like reparse point)
if "junction" in scens:
    real = ROOT / "real-onedrive-target"
    real.mkdir(parents=True, exist_ok=True)
    link = ROOT / "OneDrive - Contoso"
    if junction(link, real):
        run_child("junction", link, for_scen("junction"))
        ok("junction: the files really are in the junction's target", (real / f"{for_scen('junction')[0]} App"
                                                                        / "project.radproj").is_file())
    else:
        ok("junction can be created without admin", False)

# ------------------------------------------------------------------ read-only project folder
if "readonly" in scens:
    base = ROOT / "readonly"
    base.mkdir(parents=True, exist_ok=True)
    ro_langs = for_scen("readonly")
    run_child("readonly", base, ro_langs, steps="create")
    snaps = {lg: E.snapshot(base / f"{lg} App") for lg in ro_langs}
    for lg in ro_langs:
        E.deny_write_all(base / f"{lg} App")
    try:
        out = ROOT / "readonly-publish"
        run_child("readonly", base, ro_langs, out=str(out), steps="publish,exe")
        for lg in ro_langs:
            ok(f"[readonly] {lg}: the read-only project folder is unchanged after publishing elsewhere",
               E.snapshot(base / f"{lg} App") == snaps[lg])
        # publishing INTO the read-only folder must fail with a message, not a traceback
        res = run_child("readonly-into", base, ro_langs[:1], steps="publish", record=False)
        for r in res:
            ok(f"[readonly] {r['lang']}: publishing into the read-only folder fails with a clear message",
               not r["ok"] and ("denied" in r["detail"].lower() or "read-only" in r["detail"].lower()
                                or "Errno 13" in r["detail"]), r["detail"][-400:])
    finally:
        for lg in ro_langs:
            E.allow_again(base / f"{lg} App")

# ------------------------------------------------------------------ matrix
steps = ["create", "open", "publish", "exe", "f5"]
print("\nScenario x language matrix (create / open / publish / exe / F5; . = not run):", flush=True)
print(f"{'':14}" + "".join(f"{lg:>12}" for lg in langs))
for sc in [s for s in ALL_SCEN if s in scens]:
    row = f"{sc:14}"
    for lg in langs:
        m = matrix.get((sc, lg), {})
        row += f"{''.join('.' if m.get(s) is None else ('+' if m[s] else 'x') for s in steps):>12}"
    print(row)
print("published kinds: " + ", ".join(f"{k[0]}/{k[1]}={v}" for k, v in sorted(kinds.items())), flush=True)
sys.exit(E.summary("Environment: paths and profiles"))
