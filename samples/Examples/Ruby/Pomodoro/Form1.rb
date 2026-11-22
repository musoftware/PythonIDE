# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Pomodoro Timer - event handlers for Form1 (Ruby, GUI Bridge).
# Shows: a Timer (1 s) counting down, ProgressBar, work/break phases, a modal settings dialog
#        (SettingsForm, CALL ShowDialog), settings saved to settings.json, an English/Arabic UI, menus.
require_relative "PomodoroSettings"

$settings = PomodoroSettings.load
$phase = "work"      # "work" or "break"
$left = 0            # seconds left in the phase
$total = 0           # seconds of the whole phase
$sessions = 0

def tr(key)
  PomodoroSettings.t($settings, key)
end

def show_clock
  ui.lblClock.Caption = format("%02d:%02d", $left / 60, $left % 60)
  ui.prgPhase.Value = $total.zero? ? 0 : (100 * ($total - $left) / $total)
end

def start_phase(phase)
  $phase = phase
  $total = $left = $settings[phase] * 60
  ui.lblPhase.Caption = tr(phase)
  show_clock
end

# texts of the controls in the chosen language (called at start and by the settings dialog)
def apply_language
  ui.lblPhase.Caption = tr($phase)
  ui.cmdStart.Caption = tr("start")
  ui.cmdPause.Caption = tr("pause")
  ui.cmdReset.Caption = tr("reset")
  ui.lblDone.Caption = tr("done")
end

def apply_settings
  apply_language
  start_phase($phase) unless ui.tmrTick.Enabled == "True"
end

def Form1_Load(e)
  apply_language
  start_phase("work")
  ui.sbStatus.Text = "Settings: #{$settings['work']} / #{$settings['break']} min"
end

def tmrTick_Tick(e)
  $left -= 1
  if $left.positive?
    show_clock
    return
  end
  if $phase == "work"
    $sessions += 1
    Rad.call("lstSessions", "AddItem", "#{$sessions}. #{Time.now.strftime('%H:%M')}  #{$settings['work']} min")
    msgbox(tr("finished"))
    start_phase("break")
    ui.tmrTick.Enabled = $settings["auto_break"] ? "True" : "False"
  else
    msgbox(tr("back"))
    start_phase("work")
    ui.tmrTick.Enabled = "False"
  end
end

def cmdStart_Click(e)
  ui.tmrTick.Enabled = "True"
  ui.sbStatus.Text = tr("running")
end

def cmdPause_Click(e)
  ui.tmrTick.Enabled = "False"
  ui.sbStatus.Text = tr("paused")
end

def cmdReset_Click(e)
  ui.tmrTick.Enabled = "False"
  start_phase("work")
end

def mnuTimerStart_Click(e) = cmdStart_Click(e)
def mnuTimerPause_Click(e) = cmdPause_Click(e)
def mnuTimerReset_Click(e) = cmdReset_Click(e)

def mnuTimerExit_Click(e)
  Rad.quit
end

def mnuToolsSettings_Click(e)
  Rad.call("SettingsForm", "ShowDialog")       # modal for the user; OK / Cancel are handled in SettingsForm.rb
end
