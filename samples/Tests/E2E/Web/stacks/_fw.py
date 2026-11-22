# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Helpers shared by the framework stacks (ASP.NET, Spring, Rails, NestJS, Laravel, CodeIgniter)."""
from __future__ import annotations

import e2e_lib as E


def cli(j, win, project, command: str, timeout: float = 900) -> tuple[bool, str]:
    """Site > Framework Tools > CLI / Generators: type *command*, Run, wait. Returns (exit code 0, output)."""
    panel = getattr(win, "framework_panel", None)
    j.check(panel is not None, "no Framework Tools panel")
    win.show_framework_tools(1)
    E.pump(0.3)
    panel.set_project(project, force=True)
    start = panel.out.toPlainText()
    ok = panel.run_command(command)
    j.check(ok, f"the CLI panel did not start {command!r}: {panel.out.toPlainText()[-400:]}")
    E.wait(lambda: panel.proc is None or panel.proc.state().value == 0, timeout, 0.3)
    E.pump(0.3)
    out = panel.out.toPlainText()[len(start):]
    return "exited with code 0" in out, out


def strip_html_attr(text: str) -> str:
    return text
