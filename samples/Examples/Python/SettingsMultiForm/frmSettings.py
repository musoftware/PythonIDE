# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""frmSettings - the modal Settings dialog of the Greeting Card sample.

frmMain creates it with frmSettings(master=self.root), calls load_from(settings), waits for the window to
close and reads .result (None = Cancel, else a dict with the chosen values).  The dialog itself follows the
chosen language (Arabic: right-to-left)."""
from frmSettings_designer import frmSettingsDesigner, EventArgs  # noqa: F401
import AppSettings

CODES = ["en", "ar"]
COLORS = list(AppSettings.COLORS)


class frmSettings(frmSettingsDesigner):
    """Event handlers of the Settings dialog."""

    def frmSettings_Load(self):
        self.root.bind("<Escape>", lambda _e: self.btnCancel_Click())
        self.root.bind("<Return>", lambda _e: self.btnOK_Click())

    def load_from(self, settings: dict):
        self.result = None
        self.lang = settings.get("language", "en")
        self.cboLang.current(CODES.index(self.lang) if self.lang in CODES else 0)
        self.cboColor.current(COLORS.index(settings.get("color")) if settings.get("color") in COLORS else 0)
        self.numFontSize_var.set(int(settings.get("font_size", 16)))
        self.chkRemember_var.set(bool(settings.get("remember", True)))
        self.translate()

    def translate(self):
        t = lambda k: AppSettings.text(self.lang, k)          # noqa: E731
        self.root.title(t("settings_title"))
        self.lblLang.config(text=t("lang"))
        self.lblColor.config(text=t("color"))
        self.lblFontSize.config(text=t("font"))
        self.chkRemember.config(text=t("remember"))
        self.btnOK.config(text=t("ok"))
        self.btnCancel.config(text=t("cancel"))
        rtl = self.lang == "ar"
        for lbl in (self.lblLang, self.lblColor, self.lblFontSize):
            lbl.config(anchor="e" if rtl else "w")
        self.chkRemember.config(anchor="e" if rtl else "w")

    def cboLang_SelectedIndexChanged(self):
        self.lang = CODES[self.cboLang.current()]
        self.translate()

    def btnOK_Click(self):
        self.result = {"language": CODES[max(0, self.cboLang.current())],
                       "color": COLORS[max(0, self.cboColor.current())],
                       "font_size": int(self.numFontSize_var.get()),
                       "remember": bool(self.chkRemember_var.get())}
        self.root.destroy()

    def btnCancel_Click(self):
        self.result = None
        self.root.destroy()


if __name__ == "__main__":
    f = frmSettings()
    f.load_from(AppSettings.load())
    f.show()
