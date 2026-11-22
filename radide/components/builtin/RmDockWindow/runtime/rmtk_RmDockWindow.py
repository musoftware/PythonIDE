"""RmDockWindow - python-tk runtime of the RmDockWindow component package (the classes live in ../../_rmkit/rmkit_tk.py,
shared by every Rm* package). Also used for VB6 forms and every GUI Bridge language run inside the IDE."""
import os as _os
import sys as _sys

_KIT = _os.path.normpath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "_rmkit"))
if _KIT not in _sys.path:
    _sys.path.append(_KIT)

from rmkit_tk import RmDockWindow  # noqa: E402

__all__ = ["RmDockWindow"]
