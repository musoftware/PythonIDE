"""VB6 (BASIC) -> FreeBASIC translator for the native build (radide/deploy/native/vb6_freebasic.py).

    translate.py   the VB6 code of a project (vbparse tree) -> one readable FreeBASIC source file
    forms.py       the .form files -> the vbCtls() table the Win32 forms runtime creates the windows from
    symbols.py     names FreeBASIC / windows.bi already use (renamed in the generated code)
    rt/            the small runtime the generated code includes (MIT): vbrt_core.bi (strings, Variant,
                   Format, dates, files, Collection, errors), vbrt_forms.bi (Win32 forms and controls),
                   vbrt_image.bi (pictures through GDI+)

The forms runtime is reached only through a small interface - VBDefForm / VBDef / VBDefMenu (describe),
VBGetS / VBGetN / VBSetS / VBSetN (properties), VBAddItem ... (methods), VBOn (events) - so that it can
later be backed by another control library without touching the translator.
"""
from .translate import Translation, translate_project

__all__ = ["Translation", "translate_project"]
