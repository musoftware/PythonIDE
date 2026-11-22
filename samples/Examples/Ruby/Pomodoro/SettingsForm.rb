# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# SettingsForm - the modal settings dialog of the Pomodoro timer. ShowDialog answers at once (the program keeps
# running), so the result is handled in the dialog's own OK / Cancel handlers.

def SettingsForm_Load(e)
  Rad.set("SettingsForm.nudWork", "Value", $settings["work"])
  Rad.set("SettingsForm.nudBreak", "Value", $settings["break"])
  Rad.set("SettingsForm.cboLang", "ListIndex", $settings["lang"] == "ar" ? 1 : 0)
  Rad.set("SettingsForm.chkAutoBreak", "Value", $settings["auto_break"] ? 1 : 0)
end

def cmdOK_Click(e)
  $settings["work"] = Rad.get_num("SettingsForm.nudWork", "Value").to_i.clamp(1, 90)
  $settings["break"] = Rad.get_num("SettingsForm.nudBreak", "Value").to_i.clamp(1, 30)
  $settings["lang"] = Rad.get_num("SettingsForm.cboLang", "ListIndex") == 1 ? "ar" : "en"
  $settings["auto_break"] = Rad.get("SettingsForm.chkAutoBreak", "Value") == "1"
  PomodoroSettings.save($settings)
  Rad.hide("SettingsForm")
  apply_settings
  Rad.set("Form1.sbStatus", "Text", "Settings: #{$settings['work']} / #{$settings['break']} min")
end

def cmdCancel_Click(e)
  Rad.hide("SettingsForm")
end
