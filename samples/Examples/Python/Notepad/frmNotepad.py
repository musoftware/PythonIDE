# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Notepad - a small Notepad clone made with the RAD IDE designer (python-tk).

Shows: MenuStrip menus, Open/Save/Font common dialogs, the clipboard (cut / copy / paste),
an inline Find bar (a hidden Panel shown on demand), a StatusBar with line / column / word count,
"unsaved changes" questions on New / Open / Exit (FormClosing) and UTF-8 text (Arabic works too).
"""
import os
import time
from tkinter import messagebox

from frmNotepad_designer import frmNotepadDesigner, EventArgs  # noqa: F401

APP = "RAD Notepad"


class frmNotepad(frmNotepadDesigner):
    """Event handlers of the Notepad window."""

    # ------------------------------------------------------------------ start
    def frmNotepad_Load(self):
        self.path = ""                     # file being edited ("" = Untitled)
        self.wrap = True
        self.txtEdit.configure(wrap="word")
        self.txtEdit.place_configure(y=0, height=-22)     # the Find bar starts hidden: use its room
        self.txtEdit.focus_set()
        # live status bar: any key or click in the editor updates line / column / words
        for seq in ("<KeyRelease>", "<ButtonRelease-1>", "<<Modified>>"):
            self.txtEdit.bind(seq, self._on_edit, add="+")
        # common shortcuts (the menu items run the same handlers)
        keys = {"<Control-n>": self.mnuFileNew_Click, "<Control-o>": self.mnuFileOpen_Click,
                "<Control-s>": self.mnuFileSave_Click, "<Control-f>": self.mnuEditFind_Click,
                "<F3>": self.btnFindNext_Click, "<F5>": self.mnuEditTime_Click}
        for seq, fn in keys.items():
            self.root.bind(seq, lambda _e, f=fn: (f(), "break")[1])
        self.txtFind.bind("<Return>", lambda _e: self.btnFindNext_Click())
        self.txtFind.bind("<Escape>", lambda _e: self.btnFindClose_Click())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._update_title()
        self._update_status()

    # ------------------------------------------------------------------ helpers
    def text(self) -> str:
        return self.txtEdit.get("1.0", "end-1c")

    def set_text(self, value: str):
        self.txtEdit.delete("1.0", "end")
        self.txtEdit.insert("1.0", value)
        self.txtEdit.edit_reset()                 # nothing to undo after loading a file
        self.txtEdit.edit_modified(False)
        self._update_title()
        self._update_status()

    @property
    def dirty(self) -> bool:
        return bool(self.txtEdit.edit_modified())

    def _update_title(self):
        name = os.path.basename(self.path) if self.path else "Untitled"
        self.root.title(f"{'*' if self.dirty else ''}{name} - {APP}")

    def _update_status(self, message: str = ""):
        line, col = self.txtEdit.index("insert").split(".")
        text = self.text()
        words = len(text.split())
        self.sbStatus.config(text=message or f"Ln {line}, Col {int(col) + 1}    {words} words, "
                                             f"{len(text)} characters    UTF-8")

    def _on_edit(self, _e=None):
        self._update_title()
        self._update_status()

    def _confirm_discard(self) -> bool:
        """True when it is OK to throw the current text away (asks to save it first)."""
        if not self.dirty:
            return True
        name = os.path.basename(self.path) if self.path else "Untitled"
        answer = messagebox.askyesnocancel(APP, f"Do you want to save changes to {name}?", parent=self.root)
        if answer is None:              # Cancel
            return False
        if answer:
            return self.save()
        return True

    def load(self, path: str):
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            self.set_text(f.read())
        self.path = path
        self._update_title()
        self._update_status(f"Opened {path}")

    def save(self, path: str = "") -> bool:
        path = path or self.path
        if not path:
            if self.dlgSave.ShowDialog() != "OK":
                return False
            path = self.dlgSave.FileName
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(self.text())
        self.path = path
        self.txtEdit.edit_modified(False)
        self._update_title()
        self._update_status(f"Saved {path}")
        return True

    # ------------------------------------------------------------------ File menu
    def mnuFileNew_Click(self):
        if self._confirm_discard():
            self.path = ""
            self.set_text("")

    def mnuFileOpen_Click(self):
        if not self._confirm_discard():
            return
        if self.dlgOpen.ShowDialog() == "OK":
            self.load(self.dlgOpen.FileName)

    def mnuFileSave_Click(self):
        self.save()

    def mnuFileSaveAs_Click(self):
        self.dlgSave.FileName = self.path or "Untitled.txt"
        if self.dlgSave.ShowDialog() == "OK":
            self.save(self.dlgSave.FileName)

    def mnuFileExit_Click(self):
        self._on_close()

    def _on_close(self):                          # also the window's X button
        if self._confirm_discard():
            self.root.destroy()

    # ------------------------------------------------------------------ Edit menu
    def mnuEditUndo_Click(self):
        try:
            self.txtEdit.edit_undo()
        except Exception:                         # nothing to undo
            self.root.bell()
        self._on_edit()

    def mnuEditCut_Click(self):
        self.txtEdit.event_generate("<<Cut>>")
        self._on_edit()

    def mnuEditCopy_Click(self):
        self.txtEdit.event_generate("<<Copy>>")

    def mnuEditPaste_Click(self):
        self.txtEdit.event_generate("<<Paste>>")
        self._on_edit()

    def mnuEditSelectAll_Click(self):
        self.txtEdit.tag_add("sel", "1.0", "end-1c")
        self.txtEdit.mark_set("insert", "end-1c")
        self.txtEdit.focus_set()

    def mnuEditTime_Click(self):
        self.txtEdit.insert("insert", time.strftime("%H:%M %d/%m/%Y"))
        self._on_edit()

    # ------------------------------------------------------------------ Find bar (a Panel shown on demand)
    def mnuEditFind_Click(self):
        self.pnlFind.place(**self._places["pnlFind"])
        self.txtEdit.place_configure(y=34, height=-56)
        sel = self.txtEdit.tag_ranges("sel")
        if sel:
            self.txtFind_var.set(self.txtEdit.get(sel[0], sel[1]))
        self.txtFind.focus_set()
        self.txtFind.select_range(0, "end")

    def btnFindClose_Click(self):
        self.pnlFind.place_forget()
        self.txtEdit.place_configure(y=0, height=-22)
        self.txtEdit.focus_set()

    def btnFindNext_Click(self):
        """Find the next match after the cursor (wraps around); selects it. Returns True when found."""
        what = self.txtFind_var.get()
        if not what:
            self.mnuEditFind_Click()
            return False
        nocase = not self.chkMatchCase_var.get()
        start = self.txtEdit.index("insert")
        pos = self.txtEdit.search(what, start, stopindex="end", nocase=nocase) or \
            self.txtEdit.search(what, "1.0", stopindex=start, nocase=nocase)
        if not pos:
            self._update_status(f'Cannot find "{what}"')
            self.root.bell()
            return False
        end = f"{pos}+{len(what)}c"
        self.txtEdit.tag_remove("sel", "1.0", "end")
        self.txtEdit.tag_add("sel", pos, end)
        self.txtEdit.mark_set("insert", end)
        self.txtEdit.see(pos)
        self._update_status(f'Found "{what}" at {pos.replace(".", ":")}')
        return True

    # ------------------------------------------------------------------ Format / Help
    def mnuFormatWrap_Click(self):
        self.wrap = not self.wrap
        self.txtEdit.configure(wrap="word" if self.wrap else "none")
        self._update_status("Word wrap " + ("on" if self.wrap else "off"))

    def mnuFormatFont_Click(self):
        self.dlgFont.FontName, self.dlgFont.FontSize = "Consolas", 11
        if self.dlgFont.ShowDialog() == "OK":
            self.txtEdit.configure(font=(self.dlgFont.FontName, int(self.dlgFont.FontSize)))

    def mnuHelpAbout_Click(self):
        messagebox.showinfo(APP, "RAD Notepad\nA sample made with RAD IDE (python-tk).\n\n"
                                 "(c) 2026 Musoftware - https://musoftwares.com", parent=self.root)


if __name__ == "__main__":
    frmNotepad().show()
