"""Event semantics matrix: the steps every EventsDemo program is driven through and the event sequence each
family must log (samples/Tests/Events/test_events.py; the projects come from make_projects.py).

Families (docs/EVENTS.md explains every difference):
  vb6       VB6 semantics - the IDE's VB runtime (vbrun, run from the IDE) and the native FreeBASIC exe.
            Mouse: MouseDown, MouseUp, Click (VB6 help, "Click Event": the click follows MouseUp).
            Events raised by code (txtA.Text = ..., chkA.Value = 1, lstA.ListIndex = 2) run at once, nested in the
            handler that caused them. Validate runs before LostFocus; Cancel = True keeps the focus.
            Closing: QueryUnload (UnloadMode 0 = vbFormControlMenu for WM_CLOSE), Unload, Terminate.
  neutral   the neutral event model of the GUI Bridge and of radforms (C, C++, Rust, Go, Lua, JavaScript native
            exes and every bridge client): mouse MouseDown, MouseUp, Click like VB6; events raised by code inside a
            handler are QUEUED and delivered after the handler returns (the program is single-threaded and
            the bridge protocol is request / answer), in the order they were raised.
            Closing: FormClosing (Set("Form1", "Cancel", True) or e.Cancel keeps the form), FormClosed.
  winforms  real WinForms (C# native exe): mouse MouseDown, Click, MouseUp (Control.WmMouseUp / ButtonBase.
            OnMouseUp raise Click before MouseUp); code-raised events nested like VB6.
  swing     the Swing runtime of the Java native exe (RadSwing) - modelled on the neutral contract, code-raised
            events nested (Swing listeners run synchronously).
  tk        a Python Tkinter project: plain Tk widgets; only Tk variable traces react to code (txtA_var.set
            fires TextChanged; BooleanVar.set / Listbox.selection_set raise nothing - Tk semantics).

Canonical log lines (test_events.normalize): mouse "x=<X> y=<Y> b=<L|R|M>", key down / up "key=<letter>",
key press "char=<c>", everything else as logged ("text=..", "value=..", "index=..", "begin" / "end", "mode=0").
"""
from __future__ import annotations

FAMILIES = ("vb6", "neutral", "winforms", "swing", "tk")

# driver operations: ("click", control, x, y) | ("key", control, letter) | ("text", control, value)
#                    | ("close",) | ("wait", seconds) | ("msgbox", control, seconds): click the control, which shows
#                    a message box; close the box after *seconds*
# mode: "exact" - the step logs exactly these lines; "suffix" - the step's lines end with them
STEPS: list[dict] = [
    {"name": "lifecycle_start", "family": "lifecycle", "ops": [], "mode": "exact", "ignore_focus": True,
     "expect": {"*": ["Form1_Load"], "vb6": ["Form_Initialize", "Form_Load"]}},
    {"name": "mouse_button", "family": "mouse", "ops": [("click", "cmdA", 5, 6)], "mode": "exact",
     "expect": {"*": ["cmdA_MouseDown x=5 y=6 b=L", "cmdA_MouseUp x=5 y=6 b=L", "cmdA_Click"],
                "winforms": ["cmdA_MouseDown x=5 y=6 b=L", "cmdA_Click", "cmdA_MouseUp x=5 y=6 b=L"]}},
    {"name": "mouse_label", "family": "mouse", "ops": [("click", "lblA", 7, 8)], "mode": "exact",
     "expect": {"*": ["lblA_MouseDown x=7 y=8 b=L", "lblA_MouseUp x=7 y=8 b=L", "lblA_Click"],
                "winforms": ["lblA_MouseDown x=7 y=8 b=L", "lblA_Click", "lblA_MouseUp x=7 y=8 b=L"]}},
    {"name": "focus_first", "family": "focus", "ops": [("click", "txtA", 5, 5)], "mode": "suffix",
     "expect": {"*": ["txtA_GotFocus"]}},
    {"name": "focus_a_to_b", "family": "focus", "ops": [("click", "txtB", 5, 5)], "mode": "exact",
     "expect": {"*": ["txtA_LostFocus", "txtB_GotFocus"]}},
    {"name": "focus_b_to_a", "family": "focus", "ops": [("click", "txtA", 5, 5)], "mode": "exact",
     "expect": {"*": ["txtB_LostFocus", "txtA_GotFocus"],
                "vb6": ["txtB_Validate text=", "txtB_LostFocus", "txtA_GotFocus"]}},
    {"name": "keys", "family": "keyboard", "ops": [("key", "txtA", "a")], "mode": "exact",
     "expect": {"*": ["txtA_KeyDown key=A", "txtA_KeyPress char=a", "txtA_TextChanged text=a", "txtA_KeyUp key=A"],
                "vb6": ["txtA_KeyDown key=A", "txtA_KeyPress char=a", "txtA_Change text=a", "txtA_KeyUp key=A"]}},
    {"name": "keyascii_cancel", "family": "keyboard", "only": ("vb6",), "ops": [("key", "txtA", "x")],
     "mode": "exact", "read": ("txtA", "a"),
     "expect": {"vb6": ["txtA_KeyDown key=X", "txtA_KeyPress char=x", "txtA_KeyUp key=X"]}},
    {"name": "keyascii_change", "family": "keyboard", "only": ("vb6",), "ops": [("key", "txtA", "b")],
     "mode": "exact", "read": ("txtA", "aB"),
     "expect": {"vb6": ["txtA_KeyDown key=B", "txtA_KeyPress char=b", "txtA_Change text=aB", "txtA_KeyUp key=B"]}},
    {"name": "validate_cancel", "family": "focus", "only": ("vb6",),
     "ops": [("text", "txtB", "stay"), ("click", "txtB", 5, 5), ("wait", 0.3), ("click", "txtA", 5, 5)],
     "mode": "exact", "focus": "txtB",
     "expect": {"vb6": ["txtA_LostFocus", "txtB_GotFocus", "txtB_Validate text=stay"]}},
    {"name": "validate_ok", "family": "focus", "only": ("vb6",),
     "ops": [("text", "txtB", ""), ("wait", 0.3), ("click", "txtA", 40, 6)], "mode": "exact", "focus": "txtA",
     "expect": {"vb6": ["txtB_Validate text=", "txtB_LostFocus", "txtA_GotFocus"]}},
    {"name": "code_changes", "family": "code", "ops": [("click", "cmdCode", 5, 5)], "mode": "exact",
     "ignore_focus": True,
     "expect": {"vb6": ["cmdCode_Click begin", "txtA_Change text=code", "chkA_Click value=1", "lstA_Click index=2",
                        "cmdCode_Click end"],
                "neutral": ["cmdCode_Click begin", "cmdCode_Click end", "txtA_TextChanged text=code",
                            "chkA_CheckedChanged value=1", "lstA_SelectedIndexChanged index=2"],
                "winforms": ["cmdCode_Click begin", "txtA_TextChanged text=code", "chkA_CheckedChanged value=1",
                             "lstA_SelectedIndexChanged index=2", "cmdCode_Click end"],
                "swing": ["cmdCode_Click begin", "txtA_TextChanged text=code", "chkA_CheckedChanged value=1",
                          "lstA_SelectedIndexChanged index=2", "cmdCode_Click end"],
                "tk": ["cmdCode_Click begin", "txtA_TextChanged text=code", "cmdCode_Click end"]}},
    {"name": "timer", "family": "timer", "ops": [("click", "cmdTmr", 5, 5), ("wait", 0.6)], "mode": "exact",
     "ignore_focus": True,
     "expect": {"*": ["cmdTmr_Click", "tmrA_Tick"], "vb6": ["cmdTmr_Click", "tmrA_Timer"]}},
    {"name": "list_user", "family": "selection", "ops": [("click", "lstA", 5, 5)], "mode": "exact",
     "ignore_focus": True,
     "expect": {"*": ["lstA_SelectedIndexChanged index=0"], "vb6": ["lstA_Click index=0"]}},
    {"name": "check_user", "family": "selection", "ops": [("click", "chkA", 5, 5)], "mode": "exact",
     "ignore_focus": True,
     "expect": {"*": ["chkA_CheckedChanged value=0"], "vb6": ["chkA_Click value=0"]}},
    {"name": "doevents", "family": "timer", "only": ("vb6",), "ops": [("click", "cmdDoEv", 5, 5), ("wait", 0.5)],
     "mode": "exact", "ignore_focus": True,
     "expect": {"vb6": ["cmdDoEv_Click begin", "tmrA_Timer", "cmdDoEv_Click end"]}},
    {"name": "timer_in_msgbox", "family": "timer", "only": ("vb6",), "ops": [("msgbox", "cmdMsg", 1.0)],
     "mode": "exact", "ignore_focus": True,
     "expect": {"vb6": ["cmdMsg_Click begin", "tmrA_Timer", "cmdMsg_Click end"]}},
    {"name": "error_in_handler", "family": "lifecycle", "only": ("vb6",), "ops": [("msgbox", "cmdErr", 0.5)],
     "mode": "exact", "ignore_focus": True, "alive": True,
     "expect": {"vb6": ["cmdErr_Click begin"]}},
    {"name": "close_cancel", "family": "lifecycle", "ops": [("close",)], "mode": "exact", "alive": True,
     "ignore_focus": True,
     "expect": {"*": ["Form1_FormClosing"], "vb6": ["Form_QueryUnload mode=0"]}},
    {"name": "close", "family": "lifecycle", "ops": [("close",)], "mode": "exact", "alive": False,
     "ignore_focus": True, "skip": ("vb6",),
     "expect": {"*": ["Form1_FormClosing", "Form1_FormClosed"]}},
    # VB6: Unload Me inside a handler - QueryUnload (UnloadMode 1 = vbFormCode) and Unload run at once, the
    # handler goes on after the statement; Terminate follows when the form object is released
    {"name": "unload_me", "family": "lifecycle", "only": ("vb6",), "ops": [("click", "cmdUnload", 5, 5)],
     "mode": "exact", "alive": False, "ignore_focus": True, "ignore": ("Form_Terminate",), "has": "Form_Terminate",
     "expect": {"vb6": ["cmdUnload_Click begin", "Form_QueryUnload mode=1", "Form_Unload", "cmdUnload_Click end"]}},
]

# lines never compared (they depend on whether the test window is the foreground window)
IGNORED = ("Form1_Activated", "Form_Activate", "Form_Resize", "Form1_Resize")


def expected(step: dict, family: str) -> list[str] | None:
    """The expected lines of *step* for *family* (None: the step does not apply)."""
    if step.get("only") and family not in step["only"] or family in step.get("skip", ()):
        return None
    exp = step["expect"]
    return exp.get(family, exp.get("*"))
