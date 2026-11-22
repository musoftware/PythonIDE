// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Module ContactsDb - the SQLite part of the Contacts example (Node's built-in node:sqlite).
// Every query uses prepared statements with ? parameters (never string concatenation: no SQL injection).

process.removeAllListeners('warning');           // node:sqlite prints an "experimental" warning on Node 22
const { DatabaseSync } = require('node:sqlite');

let db = null;

function openDatabase(file) {
    db = new DatabaseSync(file);
    db.exec(`CREATE TABLE IF NOT EXISTS contacts (
                 id    INTEGER PRIMARY KEY AUTOINCREMENT,
                 name  TEXT NOT NULL,
                 phone TEXT NOT NULL DEFAULT '',
                 email TEXT NOT NULL DEFAULT '',
                 grp   TEXT NOT NULL DEFAULT 'Other')`);
}

function addContact(c) {
    const r = db.prepare('INSERT INTO contacts (name, phone, email, grp) VALUES (?, ?, ?, ?)')
        .run(c.name, c.phone, c.email, c.grp);
    return Number(r.lastInsertRowid);
}

function updateContact(id, c) {
    db.prepare('UPDATE contacts SET name = ?, phone = ?, email = ?, grp = ? WHERE id = ?')
        .run(c.name, c.phone, c.email, c.grp, id);
}

function deleteContact(id) {
    db.prepare('DELETE FROM contacts WHERE id = ?').run(id);
}

function getContact(id) {
    return db.prepare('SELECT * FROM contacts WHERE id = ?').get(id) || null;
}

/** Contacts whose name, phone, email or group contains `text` (all when text is empty), sorted by name. */
function findContacts(text) {
    const like = `%${String(text || '').trim()}%`;
    return db.prepare(`SELECT * FROM contacts
                       WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? OR grp LIKE ?
                       ORDER BY name COLLATE NOCASE`).all(like, like, like, like);
}

function countContacts() {
    return db.prepare('SELECT COUNT(*) AS n FROM contacts').get().n;
}
