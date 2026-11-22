"""DOS Batch (.BAT) - New Project > DOS. Runs in DOSBox-X; the build checks GOTO / CALL targets."""
from __future__ import annotations

from ..retro.dos.plugin import DosPluginBase
from ..retro.dos.reference import BATCH


class DosBatchPlugin(DosPluginBase):
    id = "dos-batch"
    display_name = "DOS Batch (.BAT)"
    code_ext = ".bat"
    kind = "batch"
    project_name_base = "BatchApp"
    line_comments = ["REM ", "::"]
    block_comment = None
    string_quotes = ['"']
    string_escapes = False
    keywords = sorted({k.lower() for k in BATCH} | {"errorlevel", "exist", "not", "in", "do", "on", "off"})
    builtins = []
    supports_debug = False

    def module_template(self, name: str) -> str:
        return f"@ECHO OFF\r\nREM {name}.BAT - CALL {name} from MAIN.BAT\r\n"


PLUGIN = DosBatchPlugin()
