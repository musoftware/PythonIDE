# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Create (or reset) contacts.db next to this file with a few sample contacts.

    python reset_db.py

The Contacts form is bound to this database through the Data Sources window (data source "Contacts",
connection "ContactsDb", path contacts.db relative to the program)."""
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "contacts.db")

ROWS = [
    ("Ahmed Hassan", "+20 100 123 4567", "ahmed@example.com", "Cairo", 1),
    ("Mona Adel", "+20 122 555 0101", "mona@example.com", "Alexandria", 0),
    ("John Smith", "+44 20 7946 0958", "john@example.org", "London", 0),
    ("سارة محمود", "+20 111 222 3333", "sara@example.com", "Giza", 1),
    ("Lina Haddad", "+961 1 234 567", "lina@example.net", "Beirut", 0),
]


def reset(path=DB):
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE Contacts (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Phone TEXT,
        Email TEXT,
        City TEXT,
        Favorite BOOLEAN DEFAULT 0)""")
    con.executemany("INSERT INTO Contacts (Name, Phone, Email, City, Favorite) VALUES (?, ?, ?, ?, ?)", ROWS)
    con.commit()
    con.close()
    return path


if __name__ == "__main__":
    print("created", reset())
