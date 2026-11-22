# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""ContactsDb - the SQLite data layer of the C++ Contacts example.

This Python module is part of the C++ project (a multi-language project): RAD Hub runs it as a worker and the
C++ form calls its functions with rad::invoke("ContactsDb.<function>", {...}). Python's built-in sqlite3 keeps
the records in contacts.db next to the project (a real SQL database you can open in the IDE's Database tools).

Every function returns plain text / numbers, so the C++ side needs no JSON library:
list_contacts() returns one record per line, fields separated by TAB.
"""
import os
import sqlite3

DB = os.path.join(os.environ.get("RAD_PROJECT") or os.path.dirname(os.path.abspath(__file__)), "contacts.db")

SAMPLES = [("Ahmed Hassan", "010 1234 5678", "ahmed@example.com", "Family", 1),
           ("Sara Ali", "011 2222 3333", "sara@example.com", "Friends", 0),
           ("Musoftware Support", "02 555 0100", "support@example.com", "Work", 0)]


def _db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS contacts (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL, phone TEXT, email TEXT, grp TEXT, favorite INTEGER DEFAULT 0)""")
    if con.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 0:
        con.executemany("INSERT INTO contacts (name, phone, email, grp, favorite) VALUES (?, ?, ?, ?, ?)", SAMPLES)
        con.commit()
    return con


def _clean(s):
    return ("" if s is None else str(s)).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def list_contacts(search=""):
    """All contacts (or those matching *search* in any field), ordered by name: 'id\\tname\\tphone\\temail\\tgroup\\tfav' lines."""
    like = f"%{search}%"
    with _db() as con:
        rows = con.execute("""SELECT id, name, phone, email, grp, favorite FROM contacts
                              WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? OR grp LIKE ?
                              ORDER BY favorite DESC, name COLLATE NOCASE""", (like, like, like, like)).fetchall()
    return "\n".join("\t".join(_clean(v) for v in r) for r in rows)


def save_contact(cid, name, phone, email, group, favorite):
    """Insert (cid = 0) or update a contact; returns its id."""
    name = _clean(name)
    if not name:
        raise ValueError("a contact needs a name")
    with _db() as con:
        if int(cid or 0) > 0:
            con.execute("UPDATE contacts SET name=?, phone=?, email=?, grp=?, favorite=? WHERE id=?",
                        (name, _clean(phone), _clean(email), _clean(group), 1 if favorite else 0, int(cid)))
            return int(cid)
        cur = con.execute("INSERT INTO contacts (name, phone, email, grp, favorite) VALUES (?, ?, ?, ?, ?)",
                          (name, _clean(phone), _clean(email), _clean(group), 1 if favorite else 0))
        return cur.lastrowid


def delete_contact(cid):
    with _db() as con:
        return con.execute("DELETE FROM contacts WHERE id=?", (int(cid),)).rowcount


def count():
    with _db() as con:
        return con.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
