// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// AppSettings - reading / writing settings.ini (a code module of the project: compiled with the forms).
#include <fstream>
#include <string>
#include "AppSettings.hpp"

AppSettings settings;

static const char *kFile = "settings.ini";

void AppSettings::load()
{
    std::ifstream in(kFile);
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        size_t eq = line.find('=');
        if (eq == std::string::npos || line[0] == '#' || line[0] == '[') continue;
        std::string key = line.substr(0, eq), value = line.substr(eq + 1);
        if (key == "user") user = value;
        else if (key == "language") language = value;
        else if (key == "font_size") font_size = std::stoi("0" + value);
        else if (key == "formal") formal = value == "1";
    }
    if (font_size < 8 || font_size > 24) font_size = 11;
}

bool AppSettings::save() const
{
    std::ofstream out(kFile);
    if (!out) return false;
    out << "[GreetingCards]\n"
        << "user=" << user << "\n"
        << "language=" << language << "\n"
        << "font_size=" << font_size << "\n"
        << "formal=" << (formal ? 1 : 0) << "\n";
    return true;
}
