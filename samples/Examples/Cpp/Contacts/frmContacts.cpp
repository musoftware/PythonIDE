// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Contacts - an address book in C++ whose data lives in SQLite (RAD IDE GUI Bridge, radgui.hpp).
//
// A multi-language project: the form code is C++, the data layer is the Python module ContactsDb.py
// (Python's sqlite3). RAD Hub (started by the IDE for every Run) runs ContactsDb.py as a worker and
// rad::invoke("ContactsDb.<function>", {...}) calls it - the C++ program needs no database library.
// Shows: ListBox + details GroupBox, ComboBox, CheckBox, add / edit / delete / search, validation,
// cross-language calls with error handling (std::runtime_error), std::vector / std::string.
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "radgui.hpp"

namespace {

struct Contact {
    int id = 0;
    std::string name, phone, email, group = "Family";
    bool favorite = false;
};

std::vector<Contact> shown;     // the rows of the list, in order
int current = -1;               // index in `shown` being edited, -1 = a new contact

std::vector<std::string> split(const std::string &s, char sep)
{
    std::vector<std::string> out;
    std::string item;
    std::istringstream in(s);
    while (std::getline(in, item, sep)) out.push_back(item);
    return out;
}

void status(const std::string &text) { rad::set("sbStatus", "Text", text); }

// load the list from the database (search = "" for all)
void fill_list(const std::string &search)
{
    shown.clear();
    rad::call("lstContacts", "Clear");
    std::string rows = rad::invoke("ContactsDb.list_contacts", {rad::to_json(search)}).str();
    for (const std::string &line : split(rows, '\n')) {
        std::vector<std::string> f = split(line, '\t');
        if (f.size() < 6) continue;
        Contact c;
        c.id = std::stoi(f[0]);
        c.name = f[1];
        c.phone = f[2];
        c.email = f[3];
        c.group = f[4];
        c.favorite = f[5] == "1";
        shown.push_back(c);
        rad::call("lstContacts", "AddItem", (c.favorite ? "* " : "") + c.name + "  (" + c.phone + ")");
    }
    int total = (int)rad::invoke("ContactsDb.count", {}).num();
    rad::set("lblCount", "Caption", std::to_string(shown.size()) + " of " + std::to_string(total) + " contacts");
}

void show_contact(int row)
{
    Contact empty;
    const Contact &c = row >= 0 ? shown[row] : empty;
    current = row;
    rad::set("txtName", "Text", c.name);
    rad::set("txtPhone", "Text", c.phone);
    rad::set("txtEmail", "Text", c.email);
    rad::set("cboGroup", "Text", c.group);
    rad::set("chkFavorite", "Value", c.favorite ? 1 : 0);
    rad::set("btnDelete", "Enabled", row >= 0 ? "True" : "False");
    rad::set("grpDetails", "Caption", row >= 0 ? "Details" : "New contact");
}

void select_id(int id)
{
    for (size_t i = 0; i < shown.size(); i++)
        if (shown[i].id == id) {
            rad::set("lstContacts", "ListIndex", (int)i);
            show_contact((int)i);
        }
}

}  // namespace

// ------------------------------------------------------------------ events
void frmContacts_Load()
{
    try {
        fill_list("");
        show_contact(-1);
        status("SQLite database contacts.db via ContactsDb.py (RAD Hub)");
    } catch (const std::exception &e) {
        rad::msgbox(std::string("The database is not available:\n") + e.what());
    }
}

void lstContacts_SelectedIndexChanged()
{
    int row = (int)rad::get_num("lstContacts", "ListIndex");
    if (row >= 0 && row < (int)shown.size()) show_contact(row);
}

void btnNew_Click()
{
    show_contact(-1);
    rad::call("txtName", "SetFocus");
    status("Type the new contact and press Save");
}

void btnSave_Click()
{
    Contact c;
    c.id = current >= 0 ? shown[current].id : 0;
    c.name = rad::get("txtName", "Text");
    c.phone = rad::get("txtPhone", "Text");
    c.email = rad::get("txtEmail", "Text");
    c.group = rad::get("cboGroup", "Text");
    c.favorite = rad::get_num("chkFavorite", "Value") == 1;
    if (c.name.empty()) { rad::msgbox("Please type a name."); return; }
    if (!c.email.empty() && c.email.find('@') == std::string::npos) {
        rad::msgbox("The e-mail address needs an @.");
        return;
    }
    try {
        int id = (int)rad::invoke("ContactsDb.save_contact",
                                  {rad::to_json(c.id), rad::to_json(c.name), rad::to_json(c.phone),
                                   rad::to_json(c.email), rad::to_json(c.group), rad::to_json(c.favorite)}).num();
        fill_list("");
        select_id(id);
        status((c.id ? "Updated " : "Added ") + c.name);
    } catch (const std::exception &e) {
        rad::msgbox(std::string("Save failed: ") + e.what());
    }
}

void btnDelete_Click()
{
    if (current < 0) return;
    std::string name = shown[current].name;
    std::string answer = rad::input("Delete " + name + "? Type YES to confirm:");
    if (answer.empty() || (answer[0] != 'Y' && answer[0] != 'y')) return;
    rad::invoke("ContactsDb.delete_contact", {rad::to_json(shown[current].id)});
    fill_list("");
    show_contact(-1);
    status("Deleted " + name);
}

void btnFind_Click()
{
    std::string search = rad::get("txtSearch", "Text");
    fill_list(search);
    status("Search \"" + search + "\": " + std::to_string(shown.size()) + " found");
    if (shown.size() == 1) {
        rad::set("lstContacts", "ListIndex", 0);
        show_contact(0);
    }
}

void txtSearch_KeyPress()
{
    if (rad::arg(3) == "Return") btnFind_Click();
}

void btnShowAll_Click()
{
    rad::set("txtSearch", "Text", "");
    fill_list("");
    status("All contacts");
}
