/* (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * Contacts - a small address book in C (RAD IDE GUI Bridge, radgui.h; Build > Publish = native exe).
 *
 * The "database" is contacts.tsv next to the program: one record per line, fields separated by TAB
 * (id, name, phone, e-mail, group, favourite). It is read at start-up and written after every change,
 * so it can be opened with any spreadsheet. Shows: a ListBox bound to an array, a details GroupBox,
 * ComboBox + CheckBox, add / edit / delete / search, input validation and a status bar.
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "radgui.h"

#define DB_FILE "contacts.tsv"
#define MAX_CONTACTS 500

typedef struct {
    int id;
    char name[80], phone[40], email[80], group[20];
    int favorite;
} Contact;

static Contact db[MAX_CONTACTS];
static int count = 0, next_id = 1;
static int shown[MAX_CONTACTS];     /* list row -> index in db (the list can be filtered) */
static int shown_count = 0;
static int current = -1;            /* index in db of the contact being edited, -1 = new */

/* ------------------------------------------------------------------ storage */
static void copy_field(char *dst, size_t size, const char *src)
{
    size_t i;
    for (i = 0; i + 1 < size && src[i] && src[i] != '\t' && src[i] != '\r' && src[i] != '\n'; i++) dst[i] = src[i];
    dst[i] = 0;
}

static void load_db(void)
{
    FILE *f = fopen(DB_FILE, "r");
    char line[400];
    count = 0;
    if (!f) return;
    while (count < MAX_CONTACTS && fgets(line, sizeof line, f)) {
        char *fields[6] = {0};
        char *p = line;
        int n = 0;
        Contact *c = &db[count];
        while (n < 6) {
            fields[n++] = p;
            p = strchr(p, '\t');
            if (!p) break;
            *p++ = 0;
        }
        if (n < 2 || !isdigit((unsigned char)fields[0][0])) continue;   /* header / broken line */
        memset(c, 0, sizeof *c);
        c->id = atoi(fields[0]);
        copy_field(c->name, sizeof c->name, fields[1]);
        copy_field(c->phone, sizeof c->phone, n > 2 ? fields[2] : "");
        copy_field(c->email, sizeof c->email, n > 3 ? fields[3] : "");
        copy_field(c->group, sizeof c->group, n > 4 ? fields[4] : "Other");
        c->favorite = n > 5 && fields[5][0] == '1';
        if (c->id >= next_id) next_id = c->id + 1;
        count++;
    }
    fclose(f);
}

static int save_db(void)
{
    FILE *f = fopen(DB_FILE, "w");
    int i;
    if (!f) { rad_msgbox("Cannot write " DB_FILE); return 0; }
    fprintf(f, "id\tname\tphone\temail\tgroup\tfavorite\n");
    for (i = 0; i < count; i++)
        fprintf(f, "%d\t%s\t%s\t%s\t%s\t%d\n", db[i].id, db[i].name, db[i].phone, db[i].email, db[i].group,
                db[i].favorite);
    fclose(f);
    return 1;
}

/* ------------------------------------------------------------------ UI */
static int contains_ci(const char *hay, const char *needle)
{
    size_t i, n = strlen(needle);
    if (!n) return 1;
    for (; *hay; hay++) {
        for (i = 0; i < n && hay[i] && tolower((unsigned char)hay[i]) == tolower((unsigned char)needle[i]); i++) {}
        if (i == n) return 1;
    }
    return 0;
}

static void status(const char *text) { rad_set("sbStatus", "Text", text); }

static void fill_list(const char *filter)
{
    int i;
    char row[200], msg[100];
    rad_call("lstContacts", "Clear", "");
    shown_count = 0;
    for (i = 0; i < count; i++) {
        Contact *c = &db[i];
        if (!(contains_ci(c->name, filter) || contains_ci(c->phone, filter) || contains_ci(c->email, filter)
              || contains_ci(c->group, filter)))
            continue;
        snprintf(row, sizeof row, "%s%s  (%s)", c->favorite ? "* " : "", c->name, c->phone);
        rad_call("lstContacts", "AddItem", row);
        shown[shown_count++] = i;
    }
    snprintf(msg, sizeof msg, *filter ? "%d of %d contacts match" : "%d of %d contacts", shown_count, count);
    rad_set("lblCount", "Caption", msg);
}

static void show_contact(int index)
{
    Contact empty = {0, "", "", "", "Family", 0};
    const Contact *c = index >= 0 ? &db[index] : &empty;
    current = index;
    rad_set("txtName", "Text", c->name);
    rad_set("txtPhone", "Text", c->phone);
    rad_set("txtEmail", "Text", c->email);
    rad_set("cboGroup", "Text", c->group);
    rad_set_num("chkFavorite", "Value", c->favorite);
    rad_set("btnDelete", "Enabled", index >= 0 ? "True" : "False");
    rad_set("grpDetails", "Caption", index >= 0 ? "Details" : "New contact");
}

/* ------------------------------------------------------------------ events */
void frmContacts_Load(void)
{
    char msg[200];
    load_db();
    if (count == 0) {                       /* first run: a few sample records */
        Contact samples[] = {{1, "Ahmed Hassan", "010 1234 5678", "ahmed@example.com", "Family", 1},
                             {2, "Sara Ali", "011 2222 3333", "sara@example.com", "Friends", 0},
                             {3, "Musoftware Support", "02 555 0100", "support@example.com", "Work", 0}};
        memcpy(db, samples, sizeof samples);
        count = 3;
        next_id = 4;
        save_db();
    }
    fill_list("");
    show_contact(-1);
    snprintf(msg, sizeof msg, "Database: %s (%d records)", DB_FILE, count);
    status(msg);
}

void lstContacts_SelectedIndexChanged(void)
{
    int row = (int)rad_get_num("lstContacts", "ListIndex");
    if (row >= 0 && row < shown_count) show_contact(shown[row]);
}

void btnNew_Click(void)
{
    show_contact(-1);
    rad_call("txtName", "SetFocus", "");
    status("Type the new contact and press Save");
}

void btnSave_Click(void)
{
    Contact c;
    char msg[200];
    int i, is_new = current < 0;
    memset(&c, 0, sizeof c);
    copy_field(c.name, sizeof c.name, rad_get("txtName", "Text"));
    copy_field(c.phone, sizeof c.phone, rad_get("txtPhone", "Text"));
    copy_field(c.email, sizeof c.email, rad_get("txtEmail", "Text"));
    copy_field(c.group, sizeof c.group, rad_get("cboGroup", "Text"));
    c.favorite = rad_get_num("chkFavorite", "Value") == 1;
    if (!*c.name) { rad_msgbox("Please type a name."); return; }
    if (*c.email && !strchr(c.email, '@')) { rad_msgbox("The e-mail address needs an @."); return; }
    if (!*c.group) strcpy(c.group, "Other");
    if (is_new) {
        if (count >= MAX_CONTACTS) { rad_msgbox("The address book is full."); return; }
        c.id = next_id++;
        current = count++;
    } else {
        c.id = db[current].id;
    }
    db[current] = c;
    if (!save_db()) return;
    fill_list("");
    for (i = 0; i < shown_count; i++)
        if (shown[i] == current) rad_set_num("lstContacts", "ListIndex", i);
    snprintf(msg, sizeof msg, "%s %s", is_new ? "Added" : "Updated", c.name);
    status(msg);
}

void btnDelete_Click(void)
{
    char msg[200], name[80];
    const char *answer;
    if (current < 0) return;
    snprintf(msg, sizeof msg, "Delete %s? Type YES to confirm:", db[current].name);
    answer = rad_input(msg);
    if (!(answer[0] == 'Y' || answer[0] == 'y')) return;
    strcpy(name, db[current].name);
    memmove(&db[current], &db[current + 1], (size_t)(count - current - 1) * sizeof(Contact));
    count--;
    save_db();
    fill_list("");
    show_contact(-1);
    snprintf(msg, sizeof msg, "Deleted %s", name);
    status(msg);
}

void btnFind_Click(void)
{
    char filter[100], msg[200];
    copy_field(filter, sizeof filter, rad_get("txtSearch", "Text"));
    fill_list(filter);
    snprintf(msg, sizeof msg, "Search \"%s\": %d found", filter, shown_count);
    status(msg);
    if (shown_count == 1) {
        rad_set_num("lstContacts", "ListIndex", 0);
        show_contact(shown[0]);
    }
}

void txtSearch_KeyPress(void)
{
    if (strcmp(rad_arg(3), "13") == 0 || strcmp(rad_arg(3), "Return") == 0) btnFind_Click();
}

void btnShowAll_Click(void)
{
    rad_set("txtSearch", "Text", "");
    fill_list("");
    status("All contacts");
}
