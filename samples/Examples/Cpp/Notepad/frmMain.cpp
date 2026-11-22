// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Notepad - a text editor in C++ (RAD IDE GUI Bridge, radgui.hpp; Build > Publish makes a native exe).
//
// Shows: menus, OpenFileDialog / SaveFileDialog / FontDialog, std::ifstream / std::ofstream, the Windows
// clipboard (Win32 API), Find / Find Next / Replace with SelStart / SelLength / SelText, a status bar,
// "discard changes?" questions, multi-line text through the bridge, std::string algorithms.
#include <ctime>
#include <fstream>
#include <sstream>
#include <string>
#ifdef _WIN32
#include <windows.h>
#endif
#include "radgui.hpp"

namespace {

const size_t kMaxText = 60000;      // a GUI Bridge answer is one line of at most 64 KB
std::string file_name;              // "" = Untitled
std::string find_what;
bool dirty = false, loading = false;

std::string base_name(const std::string &path)
{
    size_t p = path.find_last_of("\\/");
    return p == std::string::npos ? path : path.substr(p + 1);
}

void updateTitle()
{
    rad::set("frmMain", "Caption", (dirty ? "*" : "") + (file_name.empty() ? std::string("Untitled")
                                                                           : base_name(file_name)) + " - Notepad");
}

void status(const std::string &s) { rad::set("sbStatus", "Text", s); }

// SelStart / SelLength count characters; std::string holds UTF-8 bytes
int chars_in(const std::string &s, size_t bytes)
{
    int n = 0;
    for (size_t i = 0; i < bytes && i < s.size(); i++)
        if ((static_cast<unsigned char>(s[i]) & 0xC0) != 0x80) n++;
    return n;
}

size_t bytes_for(const std::string &s, int chars)
{
    size_t i = 0;
    for (int c = 0; i < s.size() && c < chars; c++) {
        i++;
        while (i < s.size() && (static_cast<unsigned char>(s[i]) & 0xC0) == 0x80) i++;
    }
    return i;
}

bool confirm_discard()
{
    if (!dirty) return true;
    std::string a = rad::input("The text has changed. Type YES to discard the changes (or Cancel to keep them):");
    return !a.empty() && (a[0] == 'Y' || a[0] == 'y');
}

void set_text(const std::string &text)
{
    loading = true;
    rad::set("txtDoc", "Text", text);
    loading = false;
}

bool write_file(const std::string &path)
{
    std::string text = rad::get("txtDoc", "Text");
    std::ofstream out(path, std::ios::binary);
    if (!out) { rad::msgbox("Cannot write " + path); return false; }
    out << text;
    file_name = path;
    dirty = false;
    updateTitle();
    status("Saved " + base_name(path) + " (" + std::to_string(text.size()) + " bytes)");
    return true;
}

void open_file(const std::string &path)
{
    std::ifstream in(path, std::ios::binary);
    if (!in) { rad::msgbox("Cannot open " + path); return; }
    std::ostringstream ss;
    ss << in.rdbuf();
    std::string raw = ss.str(), text;
    bool cut = raw.size() > kMaxText;
    if (cut) raw.resize(kMaxText);
    if (raw.compare(0, 3, "\xEF\xBB\xBF") == 0) raw.erase(0, 3);          // UTF-8 BOM
    for (size_t i = 0; i < raw.size(); i++) {                               // LF -> CR LF
        if (raw[i] == '\n' && (i == 0 || raw[i - 1] != '\r')) text += '\r';
        text += raw[i];
    }
    set_text(text);
    file_name = path;
    dirty = false;
    updateTitle();
    status("Opened " + base_name(path) + (cut ? " (only the first 60000 bytes)" : ""));
}

#ifdef _WIN32
void clipboard_put(const std::string &utf8)
{
    int n = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, nullptr, 0);
    HGLOBAL mem = GlobalAlloc(GMEM_MOVEABLE, static_cast<SIZE_T>(n) * sizeof(wchar_t));
    if (!mem) return;
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, static_cast<wchar_t *>(GlobalLock(mem)), n);
    GlobalUnlock(mem);
    if (OpenClipboard(nullptr)) {
        EmptyClipboard();
        SetClipboardData(CF_UNICODETEXT, mem);
        CloseClipboard();
    } else {
        GlobalFree(mem);
    }
}

std::string clipboard_get()
{
    std::string out;
    if (!OpenClipboard(nullptr)) return out;
    if (HANDLE h = GetClipboardData(CF_UNICODETEXT)) {
        const wchar_t *w = static_cast<const wchar_t *>(GlobalLock(h));
        int n = WideCharToMultiByte(CP_UTF8, 0, w, -1, nullptr, 0, nullptr, nullptr);
        out.resize(n > 0 ? n - 1 : 0);
        if (n > 1) WideCharToMultiByte(CP_UTF8, 0, w, -1, &out[0], n, nullptr, nullptr);
        GlobalUnlock(h);
    }
    CloseClipboard();
    return out;
}
#else
void clipboard_put(const std::string &) {}
std::string clipboard_get() { return ""; }
#endif

bool find_next()
{
    if (find_what.empty()) return false;
    std::string text = rad::get("txtDoc", "Text");
    int from = (int)rad::get_num("txtDoc", "SelStart") + (int)rad::get_num("txtDoc", "SelLength");
    size_t hit = text.find(find_what, bytes_for(text, from));
    if (hit == std::string::npos) hit = text.find(find_what);              // wrap around
    if (hit == std::string::npos) { status("Cannot find \"" + find_what + "\""); return false; }
    rad::set("txtDoc", "SelStart", chars_in(text, hit));
    rad::set("txtDoc", "SelLength", chars_in(find_what, find_what.size()));
    rad::call("txtDoc", "SetFocus");
    status("Found \"" + find_what + "\" at character " + std::to_string(chars_in(text, hit) + 1));
    return true;
}

}  // namespace

// ------------------------------------------------------------------ events
void frmMain_Load()
{
    updateTitle();
    status("Ready - File > Open to load a text file");
}

void txtDoc_TextChanged()
{
    if (loading || dirty) return;
    dirty = true;
    updateTitle();
}

void mnuNew_Click()
{
    if (!confirm_discard()) return;
    set_text("");
    file_name.clear();
    dirty = false;
    updateTitle();
    status("New document");
}

void mnuOpen_Click()
{
    if (!confirm_discard()) return;
    if (rad::call("dlgOpen", "ShowOpen") != "OK") return;
    std::string path = rad::get("dlgOpen", "FileName");
    if (!path.empty()) open_file(path);
}

void mnuSaveAs_Click()
{
    rad::set("dlgSave", "FileName", file_name.empty() ? std::string("Untitled.txt") : base_name(file_name));
    if (rad::call("dlgSave", "ShowSave") != "OK") return;
    std::string path = rad::get("dlgSave", "FileName");
    if (!path.empty()) write_file(path);
}

void mnuSave_Click()
{
    if (file_name.empty()) mnuSaveAs_Click();
    else write_file(file_name);
}

void mnuExit_Click()
{
    if (confirm_discard()) rad::end();
}

void mnuCut_Click()
{
    std::string sel = rad::get("txtDoc", "SelText");
    if (sel.empty()) return;
    clipboard_put(sel);
    rad::set("txtDoc", "SelText", "");
    status("Cut to the clipboard");
}

void mnuCopy_Click()
{
    std::string sel = rad::get("txtDoc", "SelText");
    if (sel.empty()) { status("Nothing selected"); return; }
    clipboard_put(sel);
    status("Copied to the clipboard");
}

void mnuPaste_Click()
{
    std::string clip = clipboard_get();
    if (clip.empty()) { status("The clipboard has no text"); return; }
    rad::set("txtDoc", "SelText", clip);
    status("Pasted");
}

void mnuSelectAll_Click()
{
    std::string text = rad::get("txtDoc", "Text");
    rad::set("txtDoc", "SelStart", 0);
    rad::set("txtDoc", "SelLength", chars_in(text, text.size()));
    rad::call("txtDoc", "SetFocus");
}

void mnuFind_Click()
{
    std::string w = rad::input("Find what:");
    if (w.empty()) return;
    find_what = w;
    rad::set("txtDoc", "SelLength", 0);
    find_next();
}

void mnuFindNext_Click()
{
    if (find_what.empty()) mnuFind_Click();
    else find_next();
}

void mnuReplace_Click()
{
    std::string what = rad::input("Replace what:");
    if (what.empty()) return;
    std::string with = rad::input("Replace with:");
    std::string text = rad::get("txtDoc", "Text");
    int count = 0;
    for (size_t p = text.find(what); p != std::string::npos; p = text.find(what, p + with.size())) {
        text.replace(p, what.size(), with);
        count++;
    }
    if (count) rad::set("txtDoc", "Text", text);
    status(std::to_string(count) + " replacement(s)");
}

void mnuTimeDate_Click()
{
    char buf[64];
    std::time_t now = std::time(nullptr);
    std::strftime(buf, sizeof buf, "%H:%M %Y-%m-%d", std::localtime(&now));
    rad::set("txtDoc", "SelText", buf);
}

void mnuFont_Click()
{
    rad::set("dlgFont", "FontName", rad::get("txtDoc", "FontName"));
    rad::set("dlgFont", "FontSize", rad::get("txtDoc", "FontSize"));
    if (rad::call("dlgFont", "ShowFont") != "OK") return;
    rad::set("txtDoc", "FontName", rad::get("dlgFont", "FontName"));
    rad::set("txtDoc", "FontSize", rad::get("dlgFont", "FontSize"));
    status("Font: " + rad::get("txtDoc", "FontName") + " " + rad::get("txtDoc", "FontSize") + " pt");
}

void mnuWordCount_Click()
{
    std::string text = rad::get("txtDoc", "Text");
    std::istringstream in(text);
    std::string word;
    int words = 0, lines = text.empty() ? 0 : 1;
    while (in >> word) words++;
    for (char ch : text)
        if (ch == '\n') lines++;
    int chars = chars_in(text, text.size()) - (lines > 0 ? 2 * (lines - 1) : 0);   // without CR LF
    std::string msg = std::to_string(words) + " words, " + std::to_string(lines) + " lines, " +
                      std::to_string(chars) + " characters";
    status(msg);
    rad::msgbox(msg);
}

void mnuAbout_Click()
{
    rad::msgbox("Notepad - a RAD IDE example in C++\n(c) 2026 Musoftware - MIT License");
}
