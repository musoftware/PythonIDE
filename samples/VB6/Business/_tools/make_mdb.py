# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Build the Access (.mdb, Jet 4.0) databases of the VB6 business samples from their .sql scripts.

    python samples/VB6/Business/_tools/make_mdb.py            # every sample
    python samples/VB6/Business/_tools/make_mdb.py BankManager

Each sample folder has ``<db>.sql`` (Jet SQL: CREATE TABLE / INSERT, statements end with ``;`` at the end of a
line, ``--`` comments).  The .mdb next to it is (re)created with ADOX through the 32-bit Windows Script Host
(``%SystemRoot%\\SysWOW64\\cscript.exe``), because the Jet 4.0 provider exists only as a 32-bit component - the
same route ``radide/runtimes/vbado.py`` uses to run the programs.  All sample data is fictional.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def statements(sql: str) -> list[str]:
    out, cur = [], []
    for line in sql.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        cur.append(s)
        if s.endswith(";"):
            out.append(" ".join(cur)[:-1].strip())
            cur = []
    if cur:
        out.append(" ".join(cur).strip())
    return out


def _vbs_str(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


def build(sql_file: Path, mdb: Path | None = None) -> Path:
    mdb = mdb or sql_file.with_suffix(".mdb")
    if mdb.exists():
        mdb.unlink()
    lines = [
        "On Error Resume Next",
        "Dim cat, cn, cs, failed",
        f"cs = \"Provider=Microsoft.Jet.OLEDB.4.0;Data Source=\" & {_vbs_str(str(mdb))}",
        "Set cat = CreateObject(\"ADOX.Catalog\")",
        "cat.Create cs",
        "If Err.Number <> 0 Then WScript.Echo \"ERR create: \" & Err.Description : WScript.Quit 2",
        "Set cat = Nothing",
        "Set cn = CreateObject(\"ADODB.Connection\")",
        "cn.Open cs",
        "failed = 0",
    ]
    for st in statements(sql_file.read_text(encoding="utf-8")):
        lines += ["Err.Clear", f"cn.Execute {_vbs_str(st)}",
                  f"If Err.Number <> 0 Then WScript.Echo \"ERR \" & Err.Description & \": \" & {_vbs_str(st[:80])}"
                  " : failed = failed + 1"]
    lines += ["cn.Close", "WScript.Quit failed"]
    with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="ascii") as f:
        f.write("\r\n".join(lines))
        script = f.name
    try:
        cscript = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "SysWOW64" / "cscript.exe"
        p = subprocess.run([str(cscript), "//nologo", script], capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(script)
    if p.returncode != 0 or "ERR" in p.stdout:
        raise RuntimeError(f"{sql_file.name}: {p.stdout.strip()} {p.stderr.strip()}")
    return mdb


def main(argv: list[str]) -> int:
    names = argv or [d.name for d in sorted(ROOT.iterdir()) if d.is_dir() and not d.name.startswith("_")]
    for name in names:
        for sql in sorted((ROOT / name).glob("*.sql")):
            print("built", build(sql).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
