# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Form2 - the modal Settings dialog of Ring Contacts: interface language and the delete confirmation.
# The choices are saved in settings.ini by Form1's SaveSettings() and applied at once.

load "Form2_designer.ring"

# Called by Form1 (button "Settings..." and File > Settings...)
func ShowSettings
    if isNull(Form2) Form2_Create() ok
    Form2.setWindowModality(2)                 # Qt::ApplicationModal - Form1 waits until OK / Cancel
    rdoEnglish.setChecked(cLang != "ar")
    rdoArabic.setChecked(cLang = "ar")
    chkConfirm.setChecked(lConfirm)
    Form2_Show()

# ---------------- Event handlers ----------------

func Form2_Load
    # runs after the form is created

func cmdOK_Click
    if rdoArabic.isChecked() cLang = "ar" else cLang = "en" ok
    lConfirm = chkConfirm.isChecked()
    SaveSettings()
    ApplyLanguage()
    Form2.close()

func cmdCancel_Click
    Form2.close()
