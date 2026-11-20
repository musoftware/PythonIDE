"""Download the WordPress core files this sample leaves out of git.

The repository keeps only this site's own files (wp-config.php, the SQLite Database
Integration plugin, uploads, the database folder). This script fetches the official
WordPress release from wordpress.org, checks its SHA-1, and extracts everything else
into ./wordpress without overwriting files that already exist (your wp-config.php and
wp-content stay as they are).

Run:  python get_wordpress_core.py            (version 7.1.5, the one the sample was made with)
      python get_wordpress_core.py latest     (newest release)
or double-click get_wordpress_core.bat
"""
from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "7.1.5"
HERE = Path(__file__).resolve().parent
TARGET = HERE / "wordpress"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE-sample"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main(argv: list[str]) -> int:
    version = argv[1] if len(argv) > 1 else VERSION
    name = "latest" if version == "latest" else f"wordpress-{version}"
    url = f"https://wordpress.org/{name}.zip"
    print(f"Downloading {url} ...")
    data = fetch(url)
    expected = fetch(url + ".sha1").decode().split()[0].strip().lower()
    actual = hashlib.sha1(data).hexdigest()
    if actual != expected:
        print(f"SHA-1 mismatch: expected {expected}, got {actual} - nothing was extracted.")
        return 1
    print(f"SHA-1 OK ({actual}), {len(data) / 1e6:.1f} MB")

    added = skipped = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""
            if not rel or info.is_dir():
                continue
            dest = TARGET / rel
            if dest.exists():                 # never overwrite the site's own files
                skipped += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(info))
            added += 1
    print(f"Done: {added} files added, {skipped} already present (kept).")
    print("Open the project in RAD IDE and press F5.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
