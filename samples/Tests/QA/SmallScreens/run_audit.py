"""Run the small-screen audit for several simulated screens and print a summary table.

    python run_audit.py [--quick] [--shots] [--out DIR] [--only TAG,...] [--parallel N]

Each configuration runs audit.py in its own process with the Qt "offscreen" platform plugin
configured to a screen of the given size (screen.json), optionally with QT_SCALE_FACTOR to
simulate Windows display scaling. The screen height is the *available* height (the taskbar,
40 px, already subtracted). --quick skips the walk over every menu command (main window only).
"""
import argparse, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
TASKBAR = 40
# tag, physical width, physical height, scale, language
CONFIGS = [
    ("1024x600-en", 1024, 600, 1.0, "en"),
    ("1024x600-ar", 1024, 600, 1.0, "ar"),
    ("1280x720-en", 1280, 720, 1.0, "en"),
    ("1280x720-ar", 1280, 720, 1.0, "ar"),
    ("1366x768-en", 1366, 768, 1.0, "en"),
    ("1366x768-ar", 1366, 768, 1.0, "ar"),
    ("1920x1080@150-en", 1920, 1080, 1.5, "en"),
    ("1920x1080@150-ar", 1920, 1080, 1.5, "ar"),
    ("1920x1080@175-en", 1920, 1080, 1.75, "en"),
    ("1920x1080-en", 1920, 1080, 1.0, "en"),
    ("1280x720-ar-dark", 1280, 720, 1.0, "ar", {"SS_THEME": "Dark"}),
    ("1366x768-savedbig-en", 1366, 768, 1.0, "en", {"SS_SAVED_BIG": "1"}),
]


def run(cfg, args):
    tag, w, h, scale, lang = cfg[:5]
    extra = cfg[5] if len(cfg) > 5 else {}
    cdir = tempfile.mkdtemp(prefix="radide-ss-")
    with open(os.path.join(cdir, "screen.json"), "w") as f:
        json.dump({"screens": [{"name": "SmallScreen", "x": 0, "y": 0, "width": w,
                                "height": h - int(TASKBAR * scale), "logicalDpi": 96,
                                "logicalBaseDpi": 96, "dpr": 1}]}, f)
    env = dict(os.environ)
    env.update({"QT_QPA_PLATFORM": "offscreen:configfile=screen.json",   # relative: "C:" would split the option
                "SS_TAG": tag, "SS_OUT": args.out, "SS_LANG": lang, "SS_THEME": args.theme,
                "SS_DIALOGS": "0" if args.quick else "1", "RADIDE_NO_BROWSER": "1", "SS_MATCH": args.match, "SS_SHOTS": "1" if args.shots else "0"})
    env.update(extra)
    if scale != 1.0:
        env["QT_SCALE_FACTOR"] = str(scale)
    else:
        env.pop("QT_SCALE_FACTOR", None)
    p = subprocess.run([sys.executable, os.path.join(HERE, "audit.py")], cwd=cdir, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1500)
    open(os.path.join(args.out, tag + ".log"), "w", encoding="utf-8").write(p.stdout + "\n---stderr---\n" + p.stderr[-20000:])
    tail = [ln for ln in p.stdout.splitlines() if ln.startswith("[")]
    if p.returncode:
        print(f"!! {tag} exit {p.returncode}\n{p.stderr[-2000:]}")
    return tag, tail


def summary(out):
    rows = []
    for name in sorted(os.listdir(out)):
        if not name.endswith(".json"):
            continue
        r = json.load(open(os.path.join(out, name), encoding="utf-8"))
        m = r["main"]
        cut = sum(t["cut_off"] for t in r["toolbars"])
        rows.append((r["tag"], f"{m['avail'][2]}x{m['avail'][3]}", f"{m['min_needed'][0]}x{m['min_needed'][1]}",
                     "yes" if m["min_needed"][0] > m["avail"][2] or m["min_needed"][1] > m["avail"][3] else "no",
                     "yes" if m["offscreen"] else "no", cut, len(r.get("windows", [])),
                     len(r.get("windows_too_big", [])), len(r.get("windows_exceeding", []))))
    hdr = ("config", "avail", "main min", "main>scr", "main off", "tb cut", "windows", "min>scr", "shown>scr")
    print("  ".join(f"{h:>16}" for h in hdr))
    for row in rows:
        print("  ".join(f"{str(c):>16}" for c in row))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--shots", action="store_true")
    ap.add_argument("--theme", default="Light")
    ap.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "radide-smallscreens"))
    ap.add_argument("--only", default="")
    ap.add_argument("--match", default="", help="walk only the menu commands whose path contains one of these (comma list)")
    ap.add_argument("--parallel", type=int, default=1)   # one IDE at a time: the machine stays usable
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    cfgs = [c for c in CONFIGS if not args.only or c[0] in args.only.split(",")]
    with ThreadPoolExecutor(args.parallel) as ex:
        for tag, tail in ex.map(lambda c: run(c, args), cfgs):
            print("\n".join(tail) or f"{tag}: no result")
    summary(args.out)
    print("reports:", args.out)


if __name__ == "__main__":
    main()
