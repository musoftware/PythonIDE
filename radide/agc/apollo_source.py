"""Download the Apollo flight software source on request (Tools > Apollo AGC > Open Apollo Source...).

The AGC programs were written by the MIT Instrumentation Laboratory under NASA contract; they are believed to
be in the public domain (US government work). The transcriptions from the original printed listings are by the
Virtual AGC project (https://www.ibiblio.org/apollo, https://github.com/virtualagc/virtualagc). RAD IDE never
bundles them: the files go into a folder the user chooses, with a licence note, and become an
"Apollo AGC Program" project that builds with yaYUL.

    download("Comanche055", Path("D:/Apollo"))      # -> D:/Apollo/Comanche055 (project.radproj, *.agc)
"""
from __future__ import annotations

import json
from pathlib import Path

from . import toolchain

PROGRAMS = {
    "Comanche055": ("Apollo 11 Command Module - Colossus 2A (Comanche 55)", "برنامج مركبة القيادة في أبولو 11"),
    "Luminary099": ("Apollo 11 Lunar Module - Luminary 1A (Luminary 99)", "برنامج المركبة القمرية في أبولو 11"),
}
MIRRORS = [("virtualagc/virtualagc", toolchain.COMMIT, "{name}"), ("chrislgarry/Apollo-11", "master", "{name}")]

NOTE = """{name} - {title}

Source: https://github.com/{repo}/tree/{ref}/{folder}
Downloaded by RAD IDE on request.

Licence / origin
----------------
The Apollo Guidance Computer software was written by the MIT Instrumentation Laboratory (now Draper) for
NASA. As a work produced for the US government it is believed to be in the public domain. The transcription
from the scanned original listings is the work of the Virtual AGC project (Ron Burkey and volunteers,
https://www.ibiblio.org/apollo); please credit them when you share it.

Build it in RAD IDE with yaYUL (Tools > Apollo AGC > Virtual AGC Toolchain...). The flight program uses
interpretive code, which RAD IDE's built-in assembler does not handle. Run it in yaAGC with RAD IDE's DSKY
panel (Project > Properties: "agc": {{"run": "yaagc"}}).
"""


def download(name: str, dest: Path, log=print) -> Path:
    """Fetch every .agc file of *name* (Comanche055 / Luminary099) into dest/<name>; returns that folder."""
    if name not in PROGRAMS:
        raise ValueError(f"unknown program {name}")
    folder = Path(dest) / name
    last_error = None
    for repo, ref, path in MIRRORS:
        try:
            entries = [e for e in toolchain.list_dir(path.format(name=name), ref, repo)
                       if e["type"] == "file" and e["name"].lower().endswith((".agc", ".binsource"))]
        except Exception as e:  # noqa: BLE001 - try the next mirror
            last_error = e
            log(f"{repo}: {e}")
            continue
        if not entries:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        hashes = {}
        for i, e in enumerate(entries, 1):
            hashes[e["name"]] = toolchain.fetch_file(e, folder / e["name"], ref, repo)
            if i % 10 == 0 or i == len(entries):
                log(f"  {i}/{len(entries)} files")
        (folder / "README_RADIDE.txt").write_text(NOTE.format(name=name, title=PROGRAMS[name][0], repo=repo,
                                                              ref=ref, folder=path.format(name=name)),
                                                  encoding="utf-8")
        (folder / "manifest_radide.json").write_text(json.dumps({"repo": repo, "ref": ref, "sha256": hashes},
                                                                indent=1), encoding="utf-8")
        make_project(folder, name)
        return folder
    raise RuntimeError(f"could not download {name}: {last_error}")


def make_project(folder: Path, name: str) -> Path:
    """project.radproj for a downloaded flight program (assembler: yaYUL, run: yaAGC)."""
    proj = folder / "project.radproj"
    if not proj.exists():
        modules = sorted(p.name for p in folder.glob("*.agc"))
        modules.sort(key=lambda n: (n.upper() != "MAIN.AGC", n))
        proj.write_text(json.dumps({"name": name, "language": "agc-yul", "forms": [], "startup": "MAIN",
                                    "modules": modules, "agc": {"assembler": "yayul", "run": "yaagc"}},
                                   indent=2), encoding="utf-8")
    return proj


__all__ = ["PROGRAMS", "download", "make_project"]
