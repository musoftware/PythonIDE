"""Motion for classic forms: animation presets (fade, move, slide, bounce, shake, pulse, rotate, flip, zoom,
colour, typewriter), their model in ``form.extra["animations"]``, ``expand()`` to storyboards + triggers
and the Python runtime (``runtime_py.FX_RT``). See docs/plans/MOTION_VARIANTS_FOLDABLES.md (slice A)."""
from __future__ import annotations

from .expand import expand, sb_name, storyboard_dict
from .model import add, animations, find, has_animations, remove, rename_references, validate
from .presets import CATALOG, GROUPS, Preset, describe, make

__all__ = ["CATALOG", "GROUPS", "Preset", "add", "animations", "describe", "expand", "find", "has_animations",
           "make", "remove", "rename_references", "sb_name", "storyboard_dict", "validate"]
