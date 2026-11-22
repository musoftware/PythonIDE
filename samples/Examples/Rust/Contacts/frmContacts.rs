// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Contacts - an address book in Rust (RAD IDE GUI Bridge: module radgui; Build > Publish makes an exe).
//
// The database is contacts.tsv (one record per line, TAB between the fields), read with std::fs and written
// after every change. Shows: a ListBox filled from a Vec<Contact>, a details GroupBox (TextBox / ComboBox /
// CheckBox), add / edit / delete / search with iterators, validation, io::Result error handling.
use crate::radgui::*;
use std::cell::RefCell;
use std::fs;
use std::io;

const DB_FILE: &str = "contacts.tsv";

#[derive(Clone, Default, PartialEq)]
struct Contact {
    id: u32,
    name: String,
    phone: String,
    email: String,
    group: String,
    favorite: bool,
}

impl Contact {
    fn row(&self) -> String {
        format!("{}{}  ({})", if self.favorite { "* " } else { "" }, self.name, self.phone)
    }

    fn matches(&self, filter: &str) -> bool {
        let f = filter.trim().to_lowercase();
        f.is_empty()
            || [&self.name, &self.phone, &self.email, &self.group].iter().any(|v| v.to_lowercase().contains(&f))
    }
}

#[derive(Default)]
struct Book {
    all: Vec<Contact>,
    shown: Vec<u32>,         // ids of the list rows, in order
    current: Option<u32>,    // id being edited, None = a new contact
}

thread_local! {
    static BOOK: RefCell<Book> = RefCell::new(Book::default());
}

fn clean(s: &str) -> String {
    s.replace(['\t', '\r', '\n'], " ").trim().to_string()
}

// ------------------------------------------------------------------ database
fn load(book: &mut Book) -> io::Result<()> {
    let text = match fs::read_to_string(DB_FILE) {
        Ok(t) => t,
        Err(e) if e.kind() == io::ErrorKind::NotFound => {
            let c = |id, n: &str, p: &str, e: &str, g: &str, f| Contact {
                id, name: n.into(), phone: p.into(), email: e.into(), group: g.into(), favorite: f,
            };
            book.all = vec![
                c(1, "Ahmed Hassan", "010 1234 5678", "ahmed@example.com", "Family", true),
                c(2, "Sara Ali", "011 2222 3333", "sara@example.com", "Friends", false),
                c(3, "Musoftware Support", "02 555 0100", "support@example.com", "Work", false),
            ];
            return save(book);
        }
        Err(e) => return Err(e),
    };
    book.all = text
        .lines()
        .filter_map(|line| {
            let f: Vec<&str> = line.split('\t').collect();
            let id = f.first()?.parse().ok()?;                 // the header line has no number: skipped
            Some(Contact {
                id,
                name: f.get(1).unwrap_or(&"").to_string(),
                phone: f.get(2).unwrap_or(&"").to_string(),
                email: f.get(3).unwrap_or(&"").to_string(),
                group: f.get(4).unwrap_or(&"Other").to_string(),
                favorite: f.get(5) == Some(&"1"),
            })
        })
        .collect();
    Ok(())
}

fn save(book: &Book) -> io::Result<()> {
    let mut out = String::from("id\tname\tphone\temail\tgroup\tfavorite\n");
    for c in &book.all {
        out += &format!("{}\t{}\t{}\t{}\t{}\t{}\n", c.id, c.name, c.phone, c.email, c.group, c.favorite as u8);
    }
    fs::write(DB_FILE, out)
}

// ------------------------------------------------------------------ UI
fn fill_list(book: &mut Book, filter: &str) {
    let mut rows: Vec<&Contact> = book.all.iter().filter(|c| c.matches(filter)).collect();
    rows.sort_by_key(|c| (!c.favorite, c.name.to_lowercase()));
    call("lstContacts", "Clear", &[]);
    for c in &rows {
        call("lstContacts", "AddItem", &[&c.row()]);
    }
    book.shown = rows.iter().map(|c| c.id).collect();
    set("lblCount", "Caption", format!("{} of {} contacts", book.shown.len(), book.all.len()));
}

fn show_contact(book: &mut Book, id: Option<u32>) {
    book.current = id;
    let c = id.and_then(|id| book.all.iter().find(|c| c.id == id).cloned())
              .unwrap_or(Contact { group: "Family".into(), ..Default::default() });
    set("txtName", "Text", &c.name);
    set("txtPhone", "Text", &c.phone);
    set("txtEmail", "Text", &c.email);
    set("cboGroup", "Text", &c.group);
    set("chkFavorite", "Value", c.favorite as u8);
    set("btnDelete", "Enabled", if id.is_some() { "True" } else { "False" });
    set("grpDetails", "Caption", if id.is_some() { "Details" } else { "New contact" });
}

fn select(book: &mut Book, id: u32) {
    if let Some(row) = book.shown.iter().position(|&x| x == id) {
        set("lstContacts", "ListIndex", row);
    }
    show_contact(book, Some(id));
}

fn status(text: &str) {
    set("sbStatus", "Text", text);
}

// ------------------------------------------------------------------ events
pub fn frmContacts_Load() {
    BOOK.with(|b| {
        let mut b = b.borrow_mut();
        if let Err(e) = load(&mut b) {
            msgbox(format!("{} cannot be read: {}", DB_FILE, e));
        }
        fill_list(&mut b, "");
        show_contact(&mut b, None);
        status(&format!("Database: {} ({} records)", DB_FILE, b.all.len()));
    });
}

pub fn lstContacts_SelectedIndexChanged() {
    BOOK.with(|b| {
        let mut b = b.borrow_mut();
        let row = get_num("lstContacts", "ListIndex");
        if row >= 0.0 && (row as usize) < b.shown.len() {
            let id = b.shown[row as usize];
            show_contact(&mut b, Some(id));
        }
    });
}

pub fn btnNew_Click() {
    BOOK.with(|b| show_contact(&mut b.borrow_mut(), None));
    call("txtName", "SetFocus", &[]);
    status("Type the new contact and press Save");
}

pub fn btnSave_Click() {
    let name = clean(&get("txtName", "Text"));
    let email = clean(&get("txtEmail", "Text"));
    if name.is_empty() {
        msgbox("Please type a name.");
        return;
    }
    if !email.is_empty() && !email.contains('@') {
        msgbox("The e-mail address needs an @.");
        return;
    }
    let group = match clean(&get("cboGroup", "Text")) {
        g if g.is_empty() => "Other".to_string(),
        g => g,
    };
    let contact = Contact {
        id: 0,
        name,
        phone: clean(&get("txtPhone", "Text")),
        email,
        group,
        favorite: get_num("chkFavorite", "Value") == 1.0,
    };
    BOOK.with(|b| {
        let mut b = b.borrow_mut();
        let is_new = b.current.is_none();
        let id = match b.current {
            Some(id) => id,
            None => b.all.iter().map(|c| c.id).max().unwrap_or(0) + 1,
        };
        let c = Contact { id, ..contact };
        match b.all.iter_mut().find(|x| x.id == id) {
            Some(existing) => *existing = c.clone(),
            None => b.all.push(c.clone()),
        }
        if let Err(e) = save(&b) {
            msgbox(format!("Save failed: {}", e));
            return;
        }
        fill_list(&mut b, "");
        select(&mut b, id);
        status(&format!("{} {}", if is_new { "Added" } else { "Updated" }, c.name));
    });
}

pub fn btnDelete_Click() {
    let current = BOOK.with(|b| {
        let b = b.borrow();
        b.current.and_then(|id| b.all.iter().find(|c| c.id == id).cloned())
    });
    let Some(c) = current else { return };
    if !input(&format!("Delete {}? Type YES to confirm:", c.name)).to_lowercase().starts_with('y') {
        return;
    }
    BOOK.with(|b| {
        let mut b = b.borrow_mut();
        b.all.retain(|x| x.id != c.id);
        if let Err(e) = save(&b) {
            msgbox(format!("Save failed: {}", e));
        }
        fill_list(&mut b, "");
        show_contact(&mut b, None);
    });
    status(&format!("Deleted {}", c.name));
}

pub fn btnFind_Click() {
    let filter = get("txtSearch", "Text");
    BOOK.with(|b| {
        let mut b = b.borrow_mut();
        fill_list(&mut b, &filter);
        status(&format!("Search \"{}\": {} found", filter, b.shown.len()));
        if b.shown.len() == 1 {
            let id = b.shown[0];
            select(&mut b, id);
        }
    });
}

pub fn txtSearch_KeyPress() {
    if matches!(event_arg(3).as_str(), "Return" | "13") {
        btnFind_Click();
    }
}

pub fn btnShowAll_Click() {
    set("txtSearch", "Text", "");
    BOOK.with(|b| fill_list(&mut b.borrow_mut(), ""));
    status("All contacts");
}
