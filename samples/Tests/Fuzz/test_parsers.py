"""Parser fuzzing: crash / hang / memory / write-outside safety of RAD IDE's file readers.

Every target of targets.py (.form, .radproj, .radsln, VB6 .frm / .vbp / .bas, the VB interpreter with random
programs, WinForms .Designer.cs / .vb, Delphi .dfm (text and binary) / Lazarus .lfm, PE files + resource
rebuild, PE resource blobs, ROM images, firmware containers (Intel HEX / S-record / ELF / bin), A2L, TunerStudio
ini, Jupyter .ipynb, VS Code package.json and .vsix) gets, in a watchdog'ed worker process:

  1. the regression corpus corpus/<target>/* (minimized inputs of every bug found so far),
  2. its valid seeds (must load without any error),
  3. deep nesting (50 .. 50000 levels), empty / one byte / huge (3 MB) inputs,
  4. N seeded random mutations (bit flips, interesting integers, truncation, chunk duplication = huge sizes,
     splices, invalid UTF-8, number / token / line edits, JSON tree edits) and inputs made from scratch.

An input passes when it loads or raises the target's documented error (ValueError family, VBSyntaxError,
VsixError ...). Anything else is a finding: another exception (crash), no result within the time limit
(hang), more than --mem-mb MB of memory, a file written outside the case folder, or a dead worker.
Findings are shrunk (ddmin) and, with --save, stored as corpus/<target>/<signature>.bin.

Run:  .venv\\Scripts\\python samples\\Tests\\Fuzz\\test_parsers.py [--long] [--cases N] [--seed S]
      [--target NAME ...] [--save] [--no-shrink] [--list]
Quick default: 120 random cases per target (~2-3 min). --long: 3000 per target. Exit code = failures.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import random
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):         # Arabic / emoji test values on a cp1252 console
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import fuzzlib as FL  # noqa: E402
import targets as TG  # noqa: E402

NEST_DEPTHS = (50, 500, 5000, 50000)


def safe_name(sig: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_", sig)[:60]
    return f"{base}_{hashlib.sha1(sig.encode()).hexdigest()[:8]}"


def corpus_files(name: str) -> list[Path]:
    d = FL.CORPUS / name
    return sorted(p for p in d.glob("*") if p.is_file() and p.suffix != ".txt") if d.is_dir() else []


def fuzz_target(t: TG.Target, args, rep: FL.Report, work_root: Path) -> None:
    work = work_root / t.name
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    w = FL.Worker(t.name, work, timeout=t.timeout, mem_mb=args.mem_mb)
    t0 = time.monotonic()
    try:
        w.start()
    except Exception as e:  # noqa: BLE001
        rep.check(f"{t.name}: worker starts", False, e)
        return
    try:
        _fuzz(t, w, args, rep)
    finally:
        w.close()
        print(f"     {t.name}: {time.monotonic() - t0:.1f} s, worker started {w.started}x", flush=True)


def _fuzz(t: TG.Target, w: FL.Worker, args, rep: FL.Report) -> None:
    # 1. regression corpus
    reg = corpus_files(t.name)
    bad = []
    for p in reg:
        r = w.run(p.read_bytes())
        if r.bad:
            bad.append(f"{p.name}: {r.st} {r.sig} {r.msg}")
    rep.check(f"{t.name}: regression corpus ({len(reg)} inputs) loads or fails cleanly", not bad, "; ".join(bad))

    # 2. seeds must load
    seeds = t.seeds()
    bad = []
    for label, data in seeds:
        r = w.run(data)
        if r.st != "ok" and (t.seeds_must_load or r.bad):
            bad.append(f"{label}: {r.st} {r.sig} {r.msg} {r.tb[-600:]}")
    rep.check(f"{t.name}: {len(seeds)} valid seeds load" + (" without error" if t.seeds_must_load else
              " or fail cleanly"), seeds and not bad, "; ".join(bad) or "no seeds found")
    refuse = t.refuse()
    if refuse:
        bad = []
        for label, data in refuse:
            r = w.run(data)
            if r.st != "handled":
                bad.append(f"{label}: {r.st} {r.sig} {r.msg}")
        rep.check(f"{t.name}: {len(refuse)} invalid / malicious inputs are refused with a clean error", not bad,
                  "; ".join(bad))
    seed_bytes = [d for _, d in seeds] or [b""]

    # 3. structural edge cases
    special: list[tuple[str, bytes]] = [("empty", b""), ("one byte", b"\x00"), ("space", b" "),
                                        ("3 MB of seed", (seed_bytes[0] or b"x") * (3_000_000 // max(1, len(seed_bytes[0])) + 1)),
                                        ("3 MB random", random.Random(1).randbytes(3_000_000)),
                                        ("utf-16 seed", seed_bytes[0].decode("latin-1").encode("utf-16"))]
    if t.nest:
        special += [(f"nesting {d}", t.nest(d)) for d in NEST_DEPTHS]
    findings: dict[str, tuple[FL.Result, bytes, str]] = {}
    for label, data in special:
        r = w.run(data[:FL.MAX_SIZE])
        if r.bad and r.sig not in findings:
            findings[r.sig] = (r, data[:FL.MAX_SIZE], label)

    # 4. random mutations / generated inputs
    rng = random.Random(f"{args.seed}:{t.name}")
    n = args.cases
    for i in range(n):
        if t.generate is not None and rng.random() < 0.3:
            data, label = t.generate(rng), f"generated #{i}"
        else:
            base = rng.choice(seed_bytes)
            data, label = FL.mutate(base, rng, t.kind, seed_bytes, t.tokens), f"mutation #{i}"
            if t.kind == "json" and rng.random() < 0.1:
                import json
                data = json.dumps(FL.random_json(rng)).encode()
                label = f"random json #{i}"
        r = w.run(data)
        if r.bad and r.sig not in findings:
            findings[r.sig] = (r, data, label)
            print(f"     finding in {t.name} ({label}): {r.st} {r.sig} {r.msg[:200]}", flush=True)
    # shrink + save
    details = []
    for sig, (r, data, label) in findings.items():
        small = data
        if not args.no_shrink:
            deadline = time.monotonic() + args.shrink_secs

            def still(cand, _r=r, _end=deadline):
                if time.monotonic() > _end:        # time budget of the shrink used up: keep what we have
                    return False
                rr = w.run(cand)
                return rr.st == _r.st and rr.sig == _r.sig
            small = FL.shrink_bytes(data, still, 20 if r.st in ("hang", "oom") else 300)
        where = ""
        if args.save:
            d = FL.CORPUS / t.name
            d.mkdir(parents=True, exist_ok=True)
            f = d / (safe_name(sig if r.st not in ("hang", "oom", "died") else
                                f"{r.st}_{hashlib.sha1(small).hexdigest()[:10]}") + ".bin")
            f.write_bytes(small)
            where = f" -> {f.relative_to(HERE)}"
        else:
            d = Path(args.out) / t.name
            d.mkdir(parents=True, exist_ok=True)
            f = d / (safe_name(sig if r.st not in ("hang", "oom", "died") else
                                f"{r.st}_{hashlib.sha1(small).hexdigest()[:10]}") + ".bin")
            f.write_bytes(small)
            where = f" -> {f}"
        details.append(f"{r.st} {sig} ({label}, {len(data)} -> {len(small)} bytes){where}: {r.msg[:160]}\n"
                       f"{r.tb[-1200:]}")
    rep.check(f"{t.name}: {len(special)} edge cases + {n} random cases without crash / hang / leak",
              not findings, "\n".join(details))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--long", action="store_true", help="deep run: 3000 random cases per target")
    ap.add_argument("--cases", type=int, default=None, help="random cases per target (default 120, --long 3000)")
    ap.add_argument("--seed", default=os.environ.get("RADFUZZ_SEED", "radide"))
    ap.add_argument("--target", action="append", default=[], help="only these targets (repeatable)")
    ap.add_argument("--save", action="store_true", help="store minimized findings in corpus/<target>/")
    ap.add_argument("--no-shrink", action="store_true")
    ap.add_argument("--shrink-secs", type=float, default=60.0, help="time budget to shrink one finding")
    ap.add_argument("--mem-mb", type=int, default=1500)
    ap.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "radide-fuzz-findings"))
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.cases is None:
        args.cases = 3000 if args.long else 120
    if args.list:
        print("\n".join(TG.names()))
        return 0
    names = args.target or TG.names()
    unknown = [n for n in names if n not in TG.TARGETS]
    if unknown:
        print("unknown target(s):", ", ".join(unknown))
        return 1
    rep = FL.Report()
    work_root = Path(tempfile.mkdtemp(prefix="radide-fuzz-"))
    print(f"parser fuzzing: {len(names)} targets, {args.cases} random cases each, seed {args.seed!r}, "
          f"work {work_root}", flush=True)
    try:
        for n in names:
            fuzz_target(TG.TARGETS[n], args, rep, work_root)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
