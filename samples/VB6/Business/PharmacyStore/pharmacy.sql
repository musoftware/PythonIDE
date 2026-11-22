-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- PharmacyStore sample database (Jet 4.0). Build pharmacy.mdb with:
--   python samples/VB6/Business/_tools/make_mdb.py PharmacyStore
-- All products, suppliers and prices are fictional demo data (not medical advice).
-- The StockLog table is NOT created here: the program creates it at start-up (runtime DDL).
CREATE TABLE Users (UserName TEXT(20) PRIMARY KEY, Pwd TEXT(20), FullName TEXT(50));
CREATE TABLE Medicines (Code TEXT(10) PRIMARY KEY, MedName TEXT(60) NOT NULL, Category TEXT(20), UnitPrice CURRENCY,
  Stock LONG, ReorderLevel LONG, Expiry DATETIME, Supplier TEXT(50));
CREATE TABLE Purchases (PurchaseID COUNTER PRIMARY KEY, Code TEXT(10), PurchaseDate DATETIME, Qty LONG,
  UnitCost CURRENCY, Batch TEXT(20), Expiry DATETIME);
CREATE TABLE Sales (InvoiceNo COUNTER PRIMARY KEY, SaleDate DATETIME, Customer TEXT(60), DiscountPct DOUBLE,
  Total CURRENCY);
CREATE TABLE SaleItems (ItemID COUNTER PRIMARY KEY, InvoiceNo LONG, Code TEXT(10), Qty LONG, UnitPrice CURRENCY);
INSERT INTO Users VALUES ('admin', 'admin', 'Demo Pharmacist');
INSERT INTO Medicines VALUES ('M001', 'Pain relief tablets 500 (demo)', 'Tablets', 2.5, 120, 30, #2027-06-30#, 'North Supply (demo)');
INSERT INTO Medicines VALUES ('M002', 'Cough syrup 100ml (demo)', 'Syrup', 4.75, 18, 20, #2026-12-31#, 'North Supply (demo)');
INSERT INTO Medicines VALUES ('M003', 'Vitamin C 1000 (demo)', 'Tablets', 6, 60, 15, #2028-01-31#, 'Delta Health (demo)');
INSERT INTO Medicines VALUES ('M004', 'Antiseptic cream 30g (demo)', 'Cream', 3.2, 9, 10, #2027-03-15#, 'Delta Health (demo)');
INSERT INTO Medicines VALUES ('M005', 'Eye drops 10ml (demo)', 'Drops', 5.4, 25, 10, #2026-12-15#, 'Delta Health (demo)');
