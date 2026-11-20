"""Icon / image editing for RAD IDE (VB / Visual Studio style).

* ``ico``       - read / write .ico and .cur files (multi-size), conversions Pillow <-> QImage.
* ``document``  - the edited image: frames (one per icon size) made of layers, undo / redo, load / save.
* ``canvas``    - the zoomable pixel canvas and its tools (pencil, line, shapes, fill, picker, select, text).
* ``editor``    - the Icon / Image Editor document tab (tools, palette, sizes, layers).
* ``resources`` - the project's resource file (Resources/resources.json) and the generated ``resources.py``.
* ``resource_editor`` - the Resources designer (strings, images, icons, files) and the Select Resource dialog.
"""
from __future__ import annotations

ICON_SIZES = (16, 24, 32, 48, 64, 256)
IMAGE_EXTS = (".ico", ".cur", ".png", ".bmp", ".gif", ".jpg", ".jpeg")
