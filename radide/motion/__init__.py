"""Motion for classic forms: animation presets (fade, move, slide, bounce, shake, pulse, rotate, flip, zoom,
colour, typewriter), their model in ``form.extra["animations"]``, ``expand()`` to storyboards + triggers
and the Python runtime (``runtime_py.FX_RT``). See docs/plans/MOTION_VARIANTS_FOLDABLES.md (slice A)."""
from __future__ import annotations

from .expand import expand, sb_name, storyboard_dict  # noqa: F401
from .model import (add, animations, find, has_animations, remove, rename_references,  # noqa: F401
                    validate)
from .presets import CATALOG, GROUPS, Preset, describe, make  # noqa: F401
