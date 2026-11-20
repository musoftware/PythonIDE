r"""Import a program (.exe / .dll / .jar) into a RAD IDE project from the command line.

Same code path as File > Import > Program (.exe / .dll)... (radide.features.exe_import.import_program).

    ..\..\..\.venv\Scripts\python.exe reimport.py <program> <destination folder> [language]

language: python-tk (default), python-qt, vb-basic, javascript, ...
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]          # samples/Tests/ExeImport -> repo root
sys.path.insert(0, str(REPO))


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    exe, dest = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    lang = sys.argv[3] if len(sys.argv) > 3 else "python-tk"
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtWidgets import QApplication
    QCoreApplication.setOrganizationName("RADIDE-TEST")      # keep the user's IDE settings untouched
    QCoreApplication.setApplicationName("RADIDE-TEST")
    app = QApplication(sys.argv[:1])  # noqa: F841
    try:
        from radide.features.exe_import import import_program
        project, report, result, info = import_program(exe, dest, lang, False, print)
    finally:
        QCoreApplication.setOrganizationName("")
        QCoreApplication.setApplicationName("")
    print("identified as:", getattr(info, "label", info))
    if project is None:
        print("import failed - see the messages above")
        return 1
    print("project:", dest, "forms:", project.forms, "startup:", project.startup)
    return 0


if __name__ == "__main__":
    sys.exit(main())
