"""Download open-source rusEFI firmware (GPL-3.0 with rusEFI's additional terms, github.com/rusefi/rusefi) from its
official GitHub releases into a cache folder OUTSIDE the repository (nothing large is committed).

    python samples/Tests/Firmware/Formats/download_rusefi.py [--dir DIR] [--board f407-discovery]

Writes DIR/rusefi.bin (full image, flash base 0x08000000), DIR/rusefi_update.srec (application image as
Motorola S-record, 0x08008000), DIR/rusefi.ini (TunerStudio definition, used by the map slice) and
DIR/SOURCE.json (release tag, asset URL, SHA-256 of the zip, licence). Default DIR:
%TEMP%/radide-fw-data/rusefi. Returns exit code 2 when offline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

API = "https://api.github.com/repos/rusefi/rusefi/releases?per_page=5"
LICENCE = "GPL-3.0 with rusEFI additional terms (license.txt in github.com/rusefi/rusefi)"
UA = {"User-Agent": "radide-tests", "Accept": "application/vnd.github+json"}


def default_dir() -> Path:
    return Path(os.environ.get("RADIDE_FW_DATA") or Path(tempfile.gettempdir()) / "radide-fw-data") / "rusefi"


def ensure(folder: Path | None = None, board: str = "f407-discovery", timeout: int = 300) -> Path | None:
    """The cache folder with rusefi.bin / rusefi_update.srec, downloading once; None when offline."""
    folder = Path(folder) if folder else default_dir()
    if (folder / "rusefi.bin").is_file() and (folder / "rusefi_update.srec").is_file():
        return folder
    try:
        req = urllib.request.Request(API, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            releases = json.load(r)
    except (OSError, ValueError) as e:
        print(f"offline / GitHub API not reachable: {e}")
        return None
    asset = None
    tag = ""
    for rel in releases:
        for a in rel.get("assets", []):
            if a["name"] == f"rusefi_bundle_{board}_autoupdate.zip":
                asset, tag = a, rel.get("tag_name", "")
                break
        if asset:
            break
    if asset is None:
        print("no rusEFI autoupdate bundle found in the latest releases")
        return None
    url = asset["browser_download_url"]
    if not url.startswith("https://github.com/rusefi/rusefi/releases/download/"):
        print(f"unexpected download URL: {url}")
        return None
    folder.mkdir(parents=True, exist_ok=True)
    zpath = folder / asset["name"]
    print(f"Downloading {url} ({asset.get('size', 0) / 1e6:.1f} MB) ...")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "radide-tests"}),
                                    timeout=timeout) as r, open(zpath, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    except OSError as e:
        print(f"download failed: {e}")
        return None
    sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    digest = (asset.get("digest") or "").replace("sha256:", "")
    if digest and digest != sha:
        print(f"SHA-256 mismatch: {sha} != {digest}")
        return None
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            n = info.filename
            if "/" in n:
                continue
            if n.endswith(".bin"):
                (folder / "rusefi.bin").write_bytes(z.read(info))
            elif n.endswith(".srec"):
                (folder / "rusefi_update.srec").write_bytes(z.read(info))
            elif n.endswith(".ini"):
                (folder / "rusefi.ini").write_bytes(z.read(info))
    (folder / "SOURCE.json").write_text(json.dumps({"project": "rusEFI", "release": tag, "asset": asset["name"],
                                                    "url": url, "sha256": sha, "licence": LICENCE}, indent=2),
                                        encoding="utf-8")
    zpath.unlink(missing_ok=True)
    return folder


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="")
    ap.add_argument("--board", default="f407-discovery")
    a = ap.parse_args()
    f = ensure(Path(a.dir) if a.dir else None, a.board)
    if f is None:
        return 2
    print(f"rusEFI firmware in {f}: " + ", ".join(p.name for p in sorted(f.iterdir())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
