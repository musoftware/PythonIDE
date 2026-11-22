"""VB6 event names of the neutral events - without tkinter, so the designer of a release build (which does
not bundle tkinter) can use it; radide/runtimes/vbrun.py re-exports it."""
from __future__ import annotations

DIALOGS = ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog", "FolderBrowserDialog")

# neutral event -> VB6 event name, by control type (None = not exposed)
VB_EVENT = {
    "*": {"Click": "Click", "DoubleClick": "DblClick", "MouseDown": "MouseDown", "MouseUp": "MouseUp",
          "MouseMove": "MouseMove", "MouseEnter": "MouseEnter", "MouseLeave": "MouseLeave",
          "MouseWheel": "MouseWheel", "KeyDown": "KeyDown", "KeyUp": "KeyUp", "KeyPress": "KeyPress",
          "GotFocus": "GotFocus", "LostFocus": "LostFocus"},
    "TextBox": {"TextChanged": "Change"},
    "CheckBox": {"CheckedChanged": "Click", "Click": None},
    "RadioButton": {"CheckedChanged": "Click", "Click": None},
    "ListBox": {"SelectedIndexChanged": "Click", "Click": None},
    "ComboBox": {"SelectedIndexChanged": "Click", "TextChanged": "Change", "Click": None},
    "NumericUpDown": {"ValueChanged": "Change"},
    "TrackBar": {"ValueChanged": "Change"},
    "Timer": {"Tick": "Timer"},
    "TabControl": {"SelectedIndexChanged": "Click", "Click": None},
    "TreeView": {"SelectedIndexChanged": "NodeClick", "DoubleClick": "DblClick"},
    "ListView": {"SelectedIndexChanged": "ItemClick", "DoubleClick": "DblClick"},
    "DataGridView": {"SelectedIndexChanged": "SelChange", "CellChanged": "AfterEdit"},
    "DateTimePicker": {"ValueChanged": "Change"},
    "Form": {"Load": "Load", "Activated": "Activate", "Deactivate": "Deactivate", "Resize": "Resize",
             "FormClosing": "Unload", "FormClosed": "Terminate"},
}


def vb_event_name(ctype: str, event: str) -> str | None:
    table = VB_EVENT.get(ctype, {})
    if event in table:
        return table[event]
    if ctype in ("Timer", "MenuStrip", "ToolStrip", *DIALOGS):
        return None
    return VB_EVENT["*"].get(event, event)


__all__ = ["DIALOGS", "VB_EVENT", "vb_event_name"]
