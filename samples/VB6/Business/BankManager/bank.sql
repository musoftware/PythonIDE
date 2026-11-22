-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- BankManager sample database (Jet 4.0). Build bank.mdb with: python samples/VB6/Business/_tools/make_mdb.py BankManager
-- Every name and amount below is fictional.
CREATE TABLE Users (UserID COUNTER PRIMARY KEY, UserName TEXT(20) NOT NULL, Pwd TEXT(20), FullName TEXT(50), Role TEXT(10));
CREATE TABLE Customers (AccountNo LONG PRIMARY KEY, FullName TEXT(60) NOT NULL, Phone TEXT(20), Address TEXT(100),
  AccType TEXT(10), Opened DATETIME, Balance CURRENCY);
CREATE TABLE Transactions (TxnID COUNTER PRIMARY KEY, AccountNo LONG, TxnDate DATETIME, TxnType TEXT(10),
  Amount CURRENCY, Mode TEXT(10), Reference TEXT(40));
CREATE TABLE Settings (SetKey TEXT(30) PRIMARY KEY, SetValue TEXT(60));
INSERT INTO Users (UserName, Pwd, FullName, Role) VALUES ('admin', 'admin', 'Demo Administrator', 'admin');
INSERT INTO Users (UserName, Pwd, FullName, Role) VALUES ('teller', 'teller', 'Demo Teller', 'teller');
INSERT INTO Customers VALUES (1001, 'Amira Fathy', '0100-000-1001', '12 Garden St, Demo City', 'Savings', #2025-03-01#, 5200);
INSERT INTO Customers VALUES (1002, 'Karim Lotfy', '0100-000-1002', '7 River Rd, Demo City', 'Current', #2025-06-15#, 12850.5);
INSERT INTO Customers VALUES (1003, 'Nour Samir', '0100-000-1003', '3 Palm Ave, Demo Town', 'Savings', #2026-01-10#, 760);
INSERT INTO Transactions (AccountNo, TxnDate, TxnType, Amount, Mode, Reference) VALUES (1001, #2026-01-05#, 'Deposit', 1200, 'Cash', 'Salary');
INSERT INTO Transactions (AccountNo, TxnDate, TxnType, Amount, Mode, Reference) VALUES (1001, #2026-01-20#, 'Withdraw', 300, 'Cash', 'ATM');
INSERT INTO Transactions (AccountNo, TxnDate, TxnType, Amount, Mode, Reference) VALUES (1002, #2026-02-02#, 'Deposit', 4000, 'Cheque', 'CHQ 77120');
INSERT INTO Settings VALUES ('BankName', 'Musoftware Demo Bank');
INSERT INTO Settings VALUES ('MinBalance', '500');
