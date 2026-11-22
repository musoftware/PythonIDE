# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Greeting Card - two forms: the main window and a modal Settings dialog (frmSettings).

Shows: opening a second form of the project as a modal dialog (Toplevel + grab_set + wait_window) and reading
its result, settings saved as JSON in the user's application data folder (AppSettings.py), switching the
whole UI between English and Arabic at run time - Arabic text is right-aligned and the layout is mirrored
(right-to-left), menus with Arabic captions.
"""
from tkinter import messagebox

from frmMain_designer import frmMainDesigner, EventArgs  # noqa: F401
from frmSettings import frmSettings  # show with: frmSettings(master=self.root)
import AppSettings


class frmMain(frmMainDesigner):
    """Event handlers of the main window."""

    def frmMain_Load(self):
        self.settings = AppSettings.load()
        if self.settings.get("remember") and self.settings.get("name"):
            self.txtName_var.set(self.settings["name"])
        self.txtName.bind("<Return>", lambda _e: self.btnGreet_Click())
        self.apply_settings()

    # ------------------------------------------------------------------ language / look
    def t(self, key, **kw):
        return AppSettings.text(self.settings["language"], key, **kw)

    def apply_settings(self):
        rtl = self.settings["language"] == "ar"
        self.lblTitle.config(text=self.t("title"))
        self.lblPrompt.config(text=self.t("prompt"))
        self.btnGreet.config(text=self.t("greet"))
        self.btnSettings.config(text=self.t("settings"))
        self.lblSettingsFile.config(text=self.t("saved_in", path=AppSettings.path()))
        self.sbInfo.config(text=self.t("status"))
        color = AppSettings.COLORS.get(self.settings["color"], "#FFF8E1")
        self.lblGreeting.config(bg=color, font=("Segoe UI", int(self.settings["font_size"])))
        # right-to-left: right-aligned text and a mirrored layout (x -> form width - x - width)
        anchor, justify = ("e", "right") if rtl else ("w", "left")
        for lbl in (self.lblTitle, self.lblPrompt, self.lblGreeting, self.lblSettingsFile, self.sbInfo):
            lbl.config(anchor=anchor, justify=justify)
        self.txtName.config(justify=justify)
        width = 560
        for name in ("lblPrompt", "txtName", "btnGreet", "btnSettings"):
            place = dict(self._places[name])
            if rtl:
                place["x"] = width - place["x"] - place["width"]
            getattr(self, name).place(**place)
        if self.lblGreeting.cget("text"):
            self.btnGreet_Click()

    # ------------------------------------------------------------------ actions
    def btnGreet_Click(self):
        name = self.txtName_var.get().strip()
        self.lblGreeting.config(text=self.t("hello", name=name) if name else self.t("nobody"))
        if self.settings.get("remember"):
            self.settings["name"] = name
            AppSettings.save(self.settings)

    def btnSettings_Click(self):
        """Show frmSettings as a modal dialog; apply and save what the user chose with OK."""
        dlg = frmSettings(master=self.root)
        dlg.load_from(self.settings)
        dlg.root.transient(self.root)
        dlg.root.grab_set()                    # modal: the main window gets no input meanwhile
        self.root.wait_window(dlg.root)
        if dlg.result is not None:
            self.settings.update(dlg.result)
            if self.settings.get("remember"):
                self.settings["name"] = self.txtName_var.get().strip()
            AppSettings.save(self.settings)
            self.apply_settings()
        return dlg

    def mnuFileSettings_Click(self):
        self.btnSettings_Click()

    def set_language(self, lang):
        self.settings["language"] = lang
        AppSettings.save(self.settings)
        self.apply_settings()

    def mnuLangEn_Click(self):
        self.set_language("en")

    def mnuLangAr_Click(self):
        self.set_language("ar")

    def mnuHelpAbout_Click(self):
        messagebox.showinfo("Greeting Card", self.t("about") + "\n\n(c) 2026 Musoftware - https://musoftwares.com",
                            parent=self.root)

    def mnuFileExit_Click(self):
        self.root.destroy()


if __name__ == "__main__":
    frmMain().show()
