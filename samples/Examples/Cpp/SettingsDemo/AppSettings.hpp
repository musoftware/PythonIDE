// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// AppSettings - the settings of the Greeting Cards example, shared by its three forms and kept in
// settings.ini next to the program (key=value lines, UTF-8).
#ifndef APP_SETTINGS_HPP
#define APP_SETTINGS_HPP

#include <string>

struct AppSettings {
    std::string user = "Friend";
    std::string language = "English";   // "English" or "العربية"
    int font_size = 11;
    bool formal = false;

    bool arabic() const { return language != "English"; }
    void load();                        // from settings.ini (defaults when it is missing)
    bool save() const;                  // to settings.ini
};

extern AppSettings settings;            // defined in AppSettings.cpp

void applySettings();                   // frmMain.cpp: show the settings on the main form

#endif
