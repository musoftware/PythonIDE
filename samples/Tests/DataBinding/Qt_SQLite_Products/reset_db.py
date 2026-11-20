"""Re-creates shop.db with the sample rows (run it to undo your test edits): python reset_db.py"""
import sqlite3
from pathlib import Path

DB = Path(__file__).with_name("shop.db")
SQL = """
DROP TABLE IF EXISTS Products;
DROP TABLE IF EXISTS Categories;
DROP TABLE IF EXISTS Customers;
CREATE TABLE Customers(Id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL, Email TEXT, City TEXT,
                       Active BOOLEAN DEFAULT 1, Balance REAL DEFAULT 0);
INSERT INTO Customers(Name, Email, City, Active, Balance) VALUES
 ('Amira Hassan', 'amira@example.com', 'Cairo', 1, 120.5), ('Omar Khaled', 'omar@example.com', 'Alexandria', 1, 0),
 ('Lina Farouk', 'lina@example.com', 'Giza', 0, 35), ('Youssef Adel', 'youssef@example.com', 'Luxor', 1, 410.75),
 ('Nour Samir', 'nour@example.com', 'Cairo', 1, 15), ('Karim Mostafa', 'karim@example.com', 'Aswan', 0, 0),
 ('Sara Ibrahim', 'sara@example.com', 'Cairo', 1, 77.25);
CREATE TABLE Categories(Id INTEGER PRIMARY KEY, Name TEXT NOT NULL);
INSERT INTO Categories(Id, Name) VALUES (1, 'Books'), (2, 'Music'), (3, 'Toys'), (4, 'Games');
CREATE TABLE Products(Id INTEGER PRIMARY KEY, Name TEXT NOT NULL, CategoryId INTEGER REFERENCES Categories(Id),
                      Price NUMERIC DEFAULT 0, InStock BOOLEAN DEFAULT 1);
INSERT INTO Products(Name, CategoryId, Price, InStock) VALUES
 ('The Nile Novel', 1, 9.5, 1), ('Oud Classics CD', 2, 12, 0), ('Pyramid Puzzle', 3, 4.25, 1),
 ('Chess Set', 4, 22, 1), ('Poetry Collection', 1, 7.75, 1);
"""

if __name__ == "__main__":
    con = sqlite3.connect(DB)
    con.executescript(SQL)
    con.commit()
    con.close()
    print("shop.db re-created:", DB)
