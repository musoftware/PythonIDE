"""Old DOS sources: Open Folder detection (project_detect detector of radide/features/dos_ide.py), compatibility
warnings, and building + running the original old-style samples in samples/Tests/Retro/DOSOldSources
(line-numbered QBasic, Turbo C with BGI and conio, Turbo Pascal with Crt / Dos, MASM / TASM with DOSSEG)."""
from __future__ import annotations

import shutil
import sys

from _common import ROOT, WORK, check, skip, summary

from radide.features.dos_ide import detect_dos_sources
from radide.model import Project
from radide.retro.dos import build as B
from radide.retro.dos import compat, dosbox, toolchain as T

SAMPLES = ROOT / "samples" / "Tests" / "Retro" / "DOSOldSources"
RUNS = {  # folder -> (language, keys, expected output)
    "MoonLander": ("dos-qbasic", "~~~~~~~~~~~~", "CRASH AT 100"),
    "TurboCStars": ("dos-c", "xx", "Stars done."),
    "TurboPascalSort": ("dos-pascal", "", "1.       MONA   95"),
    "TasmCount": ("dos-asm", "", "0123456789"),
}


def main() -> int:
    root = WORK / "old"
    shutil.rmtree(root, ignore_errors=True)
    for name, (lang, keys, want) in RUNS.items():
        folder = root / name
        shutil.copytree(SAMPLES / name, folder)
        cands = detect_dos_sources(folder)
        c = cands[0] if cands else None
        check(f"{name}: Open Folder offers {lang}", c is not None and c.language == lang and c.confidence >= 0.75,
              [(x.language, x.confidence) for x in cands])
        if c is None:
            continue
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        p = Project(folder, name, c.language, [], c.startup, c.modules)
        p.extra.update(c.extra)
        p.save()
        comp = T.COMPILER_FOR_KIND[B.kind_of(p)]
        if not T.ensure_for(comp, log=lambda *_: None, download=False):
            skip(f"{name} build", f"{comp} not installed")
            continue
        ok = B.Builder(folder, log=lambda *_: None).build()
        s = B.settings_for(Project.load(folder))
        diags = B.read_diagnostics(folder)["diags"]
        check(f"{name}: builds {B.output_name(s)} with the free compiler", ok and (folder / B.output_name(s)).is_file(),
              diags)
        check(f"{name}: sources unchanged", all((folder / n).read_bytes() == b for n, b in before.items()))
        if name == "TurboCStars":
            msgs = " | ".join(d["message"] for d in diags)
            check("Turbo C: BGI warning (graphics.h -> RAD IDE BGI subset)", "graphics.h (Borland BGI)" in msgs, msgs)
            check("Turbo C: .BGI path ignored note", 'initgraph path "C:\\TC\\BGI" is ignored' in msgs, msgs)
            check("Turbo C: tcconio.h forced in for clrscr / gotoxy / textcolor", "tcconio.h" in msgs, msgs)
        if name == "MoonLander":
            check("QBasic line numbers note", any("Line-numbered" in d["message"] for d in diags), diags)
        if not T.dosbox_exe():
            skip(f"{name} run", "DOSBox-X not installed")
            continue
        r = dosbox.capture_text(dosbox.DosRun(mounts=[("C", folder)], path=["Z:\\BIN"]), folder, B.output_name(s),
                                keys=keys, timeout=25, log=lambda *_: None)
        text = r["stdout"] + "\n" + r["screen"]
        check(f"{name}: runs in DOSBox-X (\"{want}\")", want in text and not r["timed_out"], repr(text[-400:]))

    # ---- warnings for proprietary pieces
    tp = root / "tpu"
    tp.mkdir(parents=True, exist_ok=True)
    (tp / "GAME.PAS").write_text("program Game;\nuses Crt, Sprites;\nbegin\nend.\n", encoding="ascii")
    (tp / "SPRITES.TPU").write_bytes(b"TPU0")
    notes = compat.scan(tp / "GAME.PAS", (tp / "GAME.PAS").read_text(), "pascal", tp)
    check("Turbo Pascal unit without source (.TPU only) -> warning", any("SPRITES.TPU" in n.message and
                                                                        n.severity == "Warning" for n in notes), notes)
    qb = "10 PLAY \"O3 L8 CDE\"\n20 SOUND 440, 18\n30 ' PLAY in a comment\n"
    notes = compat.scan_qbasic(qb)
    check("QBasic PLAY / SOUND -> warnings (not for comments)", sum("PLAY is not" in n.message for n in notes) == 1
          and any(n.line == 2 and "SOUND" in n.message for n in notes), notes)
    check("TASM IDEAL mode -> warning", compat.scan_asm("IDEAL\nMODEL small\n"))
    # ---- not DOS sources
    vb = root / "vb6"
    vb.mkdir(parents=True, exist_ok=True)
    (vb / "Module1.bas").write_text('Attribute VB_Name = "Module1"\nPublic Sub Main()\nEnd Sub\n', encoding="ascii")
    check("VB6 .bas is not offered as QBasic", not detect_dos_sources(vb))
    dl = root / "delphi"
    dl.mkdir(parents=True, exist_ok=True)
    (dl / "Unit1.pas").write_text("unit Unit1;\ninterface\nuses Windows, SysUtils, Forms;\nimplementation\nend.\n",
                                  encoding="ascii")
    check("Delphi unit is not offered as Turbo Pascal", not detect_dos_sources(dl))
    # ---- project_detect sees the detector once the feature registered it
    from radide import project_detect
    from radide.features.dos_ide import register_detector
    register_detector()
    cands = project_detect.detect_here(root / "MoonLander")
    check("project_detect.detect_here lists the DOS QBasic candidate",
          any(c.language == "dos-qbasic" for c in cands), [(c.language, c.title) for c in cands])
    return summary()


if __name__ == "__main__":
    sys.exit(main())
