# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module PomodoroSettings - user settings saved in settings.json + the texts of the two UI languages.
require "json"

module PomodoroSettings
  module_function

  FILE = "settings.json"
  DEFAULTS = { "work" => 25, "break" => 5, "lang" => "en", "auto_break" => false }.freeze

  TEXT = {
    "en" => { "work" => "Work", "break" => "Break", "start" => "Start", "pause" => "Pause", "reset" => "Reset",
              "done" => "Completed sessions:", "running" => "Running", "paused" => "Paused",
              "finished" => "Time is up! Take a break.", "back" => "Break is over - back to work." },
    "ar" => { "work" => "عمل", "break" => "استراحة", "start" => "ابدأ", "pause" => "إيقاف مؤقت", "reset" => "إعادة",
              "done" => "الجلسات المكتملة:", "running" => "يعمل", "paused" => "متوقف",
              "finished" => "انتهى الوقت! خذ استراحة.", "back" => "انتهت الاستراحة - عُد إلى العمل." },
  }.freeze

  def load
    return DEFAULTS.dup unless File.exist?(FILE)
    DEFAULTS.merge(JSON.parse(File.read(FILE, encoding: "UTF-8")))
  rescue JSON::ParserError
    DEFAULTS.dup
  end

  def save(settings)
    File.write(FILE, JSON.pretty_generate(settings), encoding: "UTF-8")
  end

  def t(settings, key)
    TEXT.fetch(settings["lang"], TEXT["en"]).fetch(key)
  end
end
