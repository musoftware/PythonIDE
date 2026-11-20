"""Re-create shop.db (the sample data of the report tests): customers, products, invoices, invoice lines.
Deterministic - running it again gives the same data."""
import os
import random
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
CUSTOMERS = [(1, "Contoso Ltd", "شركة كونتوسو", "Cairo"), (2, "Northwind Traders", "تجار الرياح الشمالية", "Alexandria"),
             (3, "Fabrikam Inc", "فابريكام", "Giza"), (4, "Adventure Works", "أدفنتشر ووركس", "Mansoura"),
             (5, "Tailspin Toys", "ألعاب تيلسبين", "Tanta")]
PRODUCTS = [(1, "Keyboard", "لوحة مفاتيح", "Hardware", 25.0), (2, "Mouse", "فأرة", "Hardware", 12.5),
            (3, "Monitor 24\"", "شاشة 24 بوصة", "Hardware", 189.0), (4, "USB Cable", "كابل يو إس بي", "Accessories", 4.75),
            (5, "Office Suite", "حزمة مكتبية", "Software", 149.0), (6, "Antivirus", "مضاد فيروسات", "Software", 39.9),
            (7, "Headset", "سماعة رأس", "Accessories", 45.0), (8, "Laptop Stand", "حامل حاسوب", "Accessories", 29.0)]


def build(path=os.path.join(HERE, "shop.db")):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE Customers (Id INTEGER PRIMARY KEY, Name TEXT, NameAr TEXT, City TEXT);
    CREATE TABLE Products (Id INTEGER PRIMARY KEY, Name TEXT, NameAr TEXT, Category TEXT, Price REAL);
    CREATE TABLE Invoices (Id INTEGER PRIMARY KEY, CustomerId INTEGER REFERENCES Customers(Id), Date TEXT);
    CREATE TABLE InvoiceLines (Id INTEGER PRIMARY KEY, InvoiceId INTEGER REFERENCES Invoices(Id),
                               ProductId INTEGER REFERENCES Products(Id), Qty INTEGER, Price REAL);
    """)
    db.executemany("INSERT INTO Customers VALUES (?,?,?,?)", CUSTOMERS)
    db.executemany("INSERT INTO Products VALUES (?,?,?,?,?)", PRODUCTS)
    rnd = random.Random(2005)
    inv = 1000
    line = 1
    for cid, *_ in CUSTOMERS:
        for k in range(rnd.randint(2, 4)):
            inv += 1
            db.execute("INSERT INTO Invoices VALUES (?,?,?)", (inv, cid, f"2026-{rnd.randint(1, 10):02d}-{rnd.randint(1, 28):02d}"))
            for pid in rnd.sample(range(1, 9), rnd.randint(2, 6)):
                db.execute("INSERT INTO InvoiceLines VALUES (?,?,?,?,?)",
                           (line, inv, pid, rnd.randint(1, 10), PRODUCTS[pid - 1][4]))
                line += 1
    db.commit()
    db.close()
    return path


if __name__ == "__main__":
    print(build())
