"""3D games (round 7): .scene3d files open in the 3D scene view - see radide/games3d/ide.py."""
from __future__ import annotations


def install(win) -> None:
    from ..games3d.ide import install as _install
    _install(win)
