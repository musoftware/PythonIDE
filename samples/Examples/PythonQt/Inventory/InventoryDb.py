# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""InventoryDb - SQLite storage of the Inventory sample (sqlite3 from the standard library, no UI).

The database lives in the user's application data folder (a published program may not write next to
itself):  %APPDATA%\\RADExamples\\Inventory\\inventory.db  - or the file named by RADEX_INVENTORY_DB."""
import os
import sqlite3

LOW_STOCK = 5
SEED = [("HW-001", "Hammer", "Hardware", 12, 9.5), ("HW-002", "Screwdriver set", "Hardware", 3, 14.0),
        ("OF-010", "A4 paper (500)", "Office", 40, 4.25), ("OF-011", "Stapler", "Office", 2, 6.75),
        ("FD-100", "Dates (1 kg)", "Food", 25, 3.2), ("TY-007", "Puzzle 1000", "Toys", 6, 11.9)]


def db_path() -> str:
    p = os.environ.get("RADEX_INVENTORY_DB")
    if not p:
        root = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
        p = os.path.join(root, "RADExamples", "Inventory", "inventory.db")
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    return p


class Inventory:
    def __init__(self, path: str = ""):
        self.path = path or db_path()
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("""CREATE TABLE IF NOT EXISTS Items (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SKU TEXT NOT NULL UNIQUE,
            Name TEXT NOT NULL,
            Category TEXT DEFAULT 'Other',
            Qty INTEGER NOT NULL DEFAULT 0 CHECK (Qty >= 0),
            Price REAL NOT NULL DEFAULT 0 CHECK (Price >= 0))""")
        if self.con.execute("SELECT COUNT(*) FROM Items").fetchone()[0] == 0:
            self.con.executemany("INSERT INTO Items (SKU, Name, Category, Qty, Price) VALUES (?, ?, ?, ?, ?)", SEED)
        self.con.commit()

    def items(self, search: str = "", low_only: bool = False) -> list[dict]:
        sql, args = "SELECT * FROM Items WHERE 1=1", []
        if search:
            sql += " AND (SKU LIKE ? OR Name LIKE ? OR Category LIKE ?)"
            args += [f"%{search}%"] * 3
        if low_only:
            sql += " AND Qty < ?"
            args.append(LOW_STOCK)
        return [dict(r) for r in self.con.execute(sql + " ORDER BY SKU", args)]

    def get(self, item_id: int) -> dict | None:
        r = self.con.execute("SELECT * FROM Items WHERE Id = ?", (item_id,)).fetchone()
        return dict(r) if r else None

    def add(self, item: dict) -> int:
        cur = self.con.execute("INSERT INTO Items (SKU, Name, Category, Qty, Price) VALUES (?, ?, ?, ?, ?)",
                               (item["SKU"], item["Name"], item["Category"], item["Qty"], item["Price"]))
        self.con.commit()
        return cur.lastrowid

    def update(self, item_id: int, item: dict):
        self.con.execute("UPDATE Items SET SKU = ?, Name = ?, Category = ?, Qty = ?, Price = ? WHERE Id = ?",
                         (item["SKU"], item["Name"], item["Category"], item["Qty"], item["Price"], item_id))
        self.con.commit()

    def delete(self, item_id: int):
        self.con.execute("DELETE FROM Items WHERE Id = ?", (item_id,))
        self.con.commit()

    def sku_taken(self, sku: str, except_id: int | None = None) -> bool:
        r = self.con.execute("SELECT Id FROM Items WHERE SKU = ? COLLATE NOCASE", (sku,)).fetchone()
        return r is not None and r[0] != except_id

    def totals(self) -> tuple[int, int, float]:
        n, qty, value = self.con.execute("SELECT COUNT(*), COALESCE(SUM(Qty), 0), "
                                         "COALESCE(SUM(Qty * Price), 0) FROM Items").fetchone()
        return n, qty, value
