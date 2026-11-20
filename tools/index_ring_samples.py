"""Generate radide/ring_samples/index.json - the Ring Samples gallery index.

    python tools/index_ring_samples.py                 # scan the installed Ring (C:\\ring\\ring)
    python tools/index_ring_samples.py --test          # ... and run every example headless
    python tools/index_ring_samples.py --test --only samples/AQuickStart --jobs 8

The scan reads the samples, applications, extension tutorials, library tests and the code examples of
the Ring documentation (documents/build/html/_sources). Nothing is copied into the repository.

--test runs every example with ring.exe and records the result in the index ("test" of each entry):
  * console examples: stdin gets a few test lines, killed after --timeout seconds;
  * GUI / game examples (RingQt with QT_QPA_PLATFORM=offscreen, RayLib, LibSDL, FreeGLUT ...): started on a
    hidden Windows desktop so no window shows up, killed after --gui-timeout seconds (still running = the
    window opened = ok);
  * status: ok | input (reads the keyboard) | fail (+ reason: missing library, runtime error ...) |
    timeout (console example still busy).
The runs happen in a copy of the example folders (--mirror, default a temp folder) so the Ring folder
itself is never written to by the examples.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from radide import ring_samples as rs  # noqa: E402
from radide.ring_samples import hidden_desktop  # noqa: E402

TEST_INPUT = "5\n3\nRing\n1\n2\n0\nn\nq\nexit\n" * 6


def mirror_tree(ring_root: Path, mirror: Path) -> None:
    for rel, _top, _src in rs.SOURCES:
        src = ring_root / rel
        dst = mirror / rel
        if src.is_dir() and not dst.exists():
            print(f"copying {src} -> {dst}", flush=True)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git"))


_SLOTS = threading.local()
_SLOT_N = [0]
_SLOT_LOCK = threading.Lock()


def _slot() -> int:
    """Each worker thread gets its own hidden desktop (see hidden_desktop.py)."""
    if not hasattr(_SLOTS, "n"):
        with _SLOT_LOCK:
            _SLOTS.n = _SLOT_N[0]
            _SLOT_N[0] += 1
    return _SLOTS.n


def run_one(entry: dict, ring_root: Path, mirror: Path, work: Path, timeout: float, gui_timeout: float) -> dict:
    exe = rs.ring_exe(ring_root)
    expected = None
    if entry["source"] == "docs":
        ex = rs.doc_example(ring_root, entry)
        expected = ex.get("expected") if ex else None
        f = rs.materialize_doc(ring_root, entry, work / "docs" / entry["id"].replace("/", "_"))
    else:
        f = mirror / entry["folder"] / entry["main"]
    kind = entry.get("kind", "console")
    tmo = gui_timeout if kind in ("gui", "game", "web") else timeout
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"          # RingQt honours it; other toolkits use the hidden desktop
    env["SDL_AUDIODRIVER"] = "dummy"
    env.pop("RADDBG_BP", None)
    tag = entry["id"].replace("/", "_").replace(":", "_")[-120:]
    out_path = work / "out" / f"{tag}.txt"
    in_path = work / "stdin.txt"
    t0 = time.time()
    timed_out = False
    try:
        p = hidden_desktop.start([str(exe), f.name], str(f.parent), env, str(out_path), str(in_path),
                                  slot=_slot())
    except OSError as e:
        return {"status": "fail", "reason": f"cannot start ring.exe: {e}", "seconds": 0}
    try:
        try:
            rc = p.wait(tmo)
        except Exception:  # noqa: BLE001 - TimeoutExpired
            timed_out = True
            rc = None
            p.kill()
    finally:
        if hasattr(p, "close"):
            p.close()
    secs = time.time() - t0
    try:
        output = out_path.read_bytes().decode("utf-8", "replace")
    except OSError:
        output = ""
    return rs.classify_run(entry, output, rc, timed_out, secs, expected)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ring", default="", help="Ring folder (default: found automatically)")
    ap.add_argument("--out", default=str(rs.INDEX_FILE))
    ap.add_argument("--test", action="store_true", help="run every example headless and record the result")
    ap.add_argument("--only", default="", help="test only ids starting with this prefix")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--gui-timeout", type=float, default=5.0)
    ap.add_argument("--mirror", default="", help="folder for the copy the tests run in")
    ap.add_argument("--keep-tests", action="store_true",
                    help="keep the test results of the existing index for entries that are not re-tested")
    a = ap.parse_args()
    ring_root = Path(a.ring) if a.ring else rs.find_ring_root()
    if ring_root is None or not ring_root.exists():
        print(rs.INSTALL_HELP)
        return 2
    t0 = time.time()
    entries = rs.scan(ring_root)
    print(f"{len(entries)} examples found in {ring_root} ({time.time() - t0:.1f}s)")
    old = {}
    if a.keep_tests:
        prev = rs.load_index(Path(a.out)) or {}
        old = {e["id"]: e.get("test") for e in prev.get("entries", []) if e.get("test")}
        for e in entries:
            if e["id"] in old:
                e["test"] = old[e["id"]]
    meta = {"ring_root": str(ring_root), "generated": time.strftime("%Y-%m-%d %H:%M"),
            "ring_version": ring_version(ring_root)}
    if a.keep_tests and old:
        for k in ("tested", "test_settings"):
            if k in prev:
                meta[k] = prev[k]
    if a.test:
        mirror = Path(a.mirror) if a.mirror else Path(tempfile.gettempdir()) / "radide_ring_mirror"
        mirror_tree(ring_root, mirror)
        work = mirror / "_work"
        (work / "out").mkdir(parents=True, exist_ok=True)
        (work / "stdin.txt").write_text(TEST_INPUT, encoding="utf-8")
        todo = [e for e in entries if e["id"].startswith(a.only)]
        print(f"testing {len(todo)} examples with {a.jobs} jobs ...", flush=True)
        lock = threading.Lock()
        done = [0]

        def job(e):
            try:
                r = run_one(e, ring_root, mirror, work, a.timeout, a.gui_timeout)
            except Exception as ex:  # noqa: BLE001
                r = {"status": "fail", "reason": f"test error: {ex}", "seconds": 0}
            e["test"] = r
            with lock:
                done[0] += 1
                if done[0] % 50 == 0 or r["status"] == "fail" and done[0] % 10 == 0:
                    print(f"  {done[0]}/{len(todo)}", flush=True)
            return r
        with cf.ThreadPoolExecutor(a.jobs) as pool:
            list(pool.map(job, todo))
        meta["tested"] = time.strftime("%Y-%m-%d %H:%M")
        meta["test_settings"] = {"timeout": a.timeout, "gui_timeout": a.gui_timeout,
                                 "gui": "QT_QPA_PLATFORM=offscreen + hidden Windows desktop"}
    tested = [e for e in entries if e.get("test")]
    if tested:
        meta["summary"] = summary(tested)
    data = {**meta, "count": len(entries), "entries": entries}
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"wrote {a.out} ({Path(a.out).stat().st_size // 1024} KB) in {time.time() - t0:.0f}s")
    if tested:
        print(json.dumps(meta["summary"], indent=1))
    return 0


def summary(tested: list[dict]) -> dict:
    by_status = collections.Counter(e["test"]["status"] for e in tested)
    by_source = collections.defaultdict(collections.Counter)
    for e in tested:
        by_source[e["source"]][e["test"]["status"]] += 1
    reasons = collections.Counter()
    for e in tested:
        if e["test"]["status"] == "fail":
            r = e["test"].get("reason", "")
            key = r.split(":")[0] if r else "unknown"
            if key.startswith("missing"):
                key = r[:90]
            reasons[key] += 1
    doc = [e for e in tested if e["source"] == "docs" and "matches_doc_output" in e["test"]]
    return {"total": len(tested), "status": dict(by_status),
            "by_source": {k: dict(v) for k, v in by_source.items()},
            "fail_reasons": dict(reasons.most_common(25)),
            "docs_output_checked": len(doc),
            "docs_output_matches": sum(1 for e in doc if e["test"]["matches_doc_output"])}


def ring_version(root: Path) -> str:
    import subprocess
    try:
        r = subprocess.run([str(rs.ring_exe(root))], capture_output=True, text=True, timeout=10,
                           stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return next((ln.strip() for ln in (r.stdout or "").splitlines() if "version" in ln.lower()), "")
    except Exception:  # noqa: BLE001
        return ""


if __name__ == "__main__":
    sys.exit(main())
