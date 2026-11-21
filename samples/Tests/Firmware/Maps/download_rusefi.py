"""Download open-source rusEFI definitions for the map tests (GPL-3.0, github.com/rusefi/rusefi - official repo).

    python download_rusefi.py [target folder]      (default: %TEMP%/radide-qa/rusefi)

Fetches the generated TunerStudio ini of the f407-discovery board and two small .msq tunes from rusEFI's own test
data. Nothing is committed to RAD IDE; the tests use these files when they are present.
"""
from __future__ import annotations

import os
import sys
import tempfile
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/rusefi/rusefi/master/"
FILES = {
    "rusefi_f407-discovery.ini": "firmware/tunerstudio/generated/rusefi_f407-discovery.ini",
    "batt_lag_prev.msq": "java_console/ui/src/test/java/com/rusefi/maintenance/migration/batt_lag_corr_migration/"
                         "test_data/prev_calibrations.msq",
    "clt_idle_prev.msq": "java_console/ui/src/test/java/com/rusefi/maintenance/migration/clt_idle_corr_migration/"
                         "test_data/prev_calibrations.msq",
}


def default_dir() -> Path:
    return Path(os.environ.get("RUSEFI_DIR") or Path(tempfile.gettempdir()) / "radide-qa" / "rusefi")


def download(target: Path | None = None) -> Path:
    target = Path(target) if target else default_dir()
    target.mkdir(parents=True, exist_ok=True)
    for name, rel in FILES.items():
        dest = target / name
        if dest.is_file() and dest.stat().st_size:
            continue
        req = urllib.request.Request(RAW + rel, headers={"User-Agent": "radide-tests"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
        print("downloaded", dest)
    (target / "LICENSE-NOTE.txt").write_text("Files from https://github.com/rusefi/rusefi (GPL-3.0).\n",
                                             encoding="utf-8")
    return target


if __name__ == "__main__":
    print(download(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
