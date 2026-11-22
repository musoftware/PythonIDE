-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- ElectricityBilling sample database (Jet 4.0). Build billing.mdb with:
--   python samples/VB6/Business/_tools/make_mdb.py ElectricityBilling
-- Every name, meter and rate below is fictional.
CREATE TABLE Users (UserName TEXT(20) PRIMARY KEY, Pwd TEXT(20), Role TEXT(10));
CREATE TABLE Tariffs (TariffID COUNTER PRIMARY KEY, Category TEXT(20), FromUnit LONG, ToUnit LONG, Rate CURRENCY);
CREATE TABLE Consumers (MeterNo LONG PRIMARY KEY, FullName TEXT(60) NOT NULL, Address TEXT(100), Phone TEXT(20),
  Category TEXT(20), Connected DATETIME, Deposit CURRENCY, Active BIT);
CREATE TABLE Readings (ReadingID COUNTER PRIMARY KEY, MeterNo LONG, ReadDate DATETIME, PrevReading LONG,
  CurrReading LONG, Billed BIT);
CREATE TABLE Bills (BillNo COUNTER PRIMARY KEY, MeterNo LONG, ReadingID LONG, BillDate DATETIME, Units LONG,
  Energy CURRENCY, FixedCharge CURRENCY, Tax CURRENCY, Total CURRENCY, DueDate DATETIME, Paid BIT);
CREATE TABLE Settings (SetKey TEXT(30) PRIMARY KEY, SetValue TEXT(60));
INSERT INTO Users VALUES ('admin', 'admin', 'admin');
INSERT INTO Users VALUES ('reader', 'reader', 'reader');
INSERT INTO Tariffs (Category, FromUnit, ToUnit, Rate) VALUES ('Domestic', 1, 100, 0.50);
INSERT INTO Tariffs (Category, FromUnit, ToUnit, Rate) VALUES ('Domestic', 101, 300, 0.85);
INSERT INTO Tariffs (Category, FromUnit, ToUnit, Rate) VALUES ('Domestic', 301, 999999, 1.25);
INSERT INTO Tariffs (Category, FromUnit, ToUnit, Rate) VALUES ('Commercial', 1, 200, 1.10);
INSERT INTO Tariffs (Category, FromUnit, ToUnit, Rate) VALUES ('Commercial', 201, 999999, 1.60);
INSERT INTO Consumers VALUES (50101, 'Hana Adel', '4 Lotus St, Demo City', '0111-222-0101', 'Domestic', #2024-05-01#, 100, -1);
INSERT INTO Consumers VALUES (50102, 'Omar Zaki', '18 Cedar Rd, Demo City', '0111-222-0102', 'Domestic', #2025-02-11#, 100, -1);
INSERT INTO Consumers VALUES (60201, 'Sunrise Bakery (demo)', '2 Market Sq, Demo Town', '0111-222-0201', 'Commercial', #2023-09-20#, 400, -1);
INSERT INTO Readings (MeterNo, ReadDate, PrevReading, CurrReading, Billed) VALUES (50101, #2026-09-30#, 0, 1180, -1);
INSERT INTO Readings (MeterNo, ReadDate, PrevReading, CurrReading, Billed) VALUES (50101, #2026-10-31#, 1180, 1420, 0);
INSERT INTO Readings (MeterNo, ReadDate, PrevReading, CurrReading, Billed) VALUES (60201, #2026-10-31#, 20500, 21110, 0);
INSERT INTO Bills (MeterNo, ReadingID, BillDate, Units, Energy, FixedCharge, Tax, Total, DueDate, Paid) VALUES (50101, 1, #2026-10-02#, 1180, 1320, 15, 66.75, 1401.75, #2026-10-17#, -1);
INSERT INTO Settings VALUES ('CompanyName', 'Musoftware Demo Power Co.');
INSERT INTO Settings VALUES ('FixedCharge', '15');
INSERT INTO Settings VALUES ('TaxPercent', '5');
INSERT INTO Settings VALUES ('DueDays', '15');
