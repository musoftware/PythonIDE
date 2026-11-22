# HandlesAbi

A plain C program (no IDE project) for the **radforms ABI**: the form description is given in memory
(`rad_forms_load`), events come through `rf_run_events(callback, user)` with numeric ids, a control class module
(ButtonX, `radforms/controls/rf_buttonx.c`) is registered with `rfmod_buttonx()`, a control is made at run time
(`rf_create`), a custom event is raised (`rf_raise`), the theme switches to Dark and the first FormClosing is
cancelled. Linked against `libradforms.a` (MinGW) and `radforms.lib` (MSVC) by
`samples/Tests/Native/test_native_c.py`. See docs/NATIVE_BUILD.md.

*Origin:* native C / C++ / Fortran builder agent (radforms).
