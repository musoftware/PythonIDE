-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- FinanceLedger sample database (Jet 4.0) - a small savings & loan society.
-- Build finance.mdb with: python samples/VB6/Business/_tools/make_mdb.py FinanceLedger
-- Every name and amount below is fictional.
CREATE TABLE Users (UserName TEXT(20) PRIMARY KEY, Pwd TEXT(20));
CREATE TABLE Members (MemberID TEXT(8) PRIMARY KEY, FullName TEXT(60) NOT NULL, AccType TEXT(10), Joined DATETIME,
  EntryFee CURRENCY, Active BIT);
CREATE TABLE Ledger (EntryID COUNTER PRIMARY KEY, EntryDate DATETIME, MemberID TEXT(8), Category TEXT(20),
  Direction TEXT(2), Amount CURRENCY, PayMode TEXT(10), Narration TEXT(80));
CREATE TABLE Loans (LoanID COUNTER PRIMARY KEY, MemberID TEXT(8), IssueDate DATETIME, Principal CURRENCY,
  RatePct DOUBLE, Repaid CURRENCY, Closed BIT);
CREATE TABLE Cash (ID LONG PRIMARY KEY, CashInHand CURRENCY, BankBalance CURRENCY);
CREATE TABLE Rates (RateID COUNTER PRIMARY KEY, MinDays LONG, RatePct DOUBLE);
INSERT INTO Users VALUES ('admin', 'admin');
INSERT INTO Members VALUES ('S-0001', 'Laila Hassan', 'Saver', #2025-01-15#, 50, -1);
INSERT INTO Members VALUES ('S-0002', 'Tarek Mounir', 'Saver', #2025-04-02#, 50, -1);
INSERT INTO Members VALUES ('C-0001', 'Green Field Co-op (demo)', 'Current', #2025-07-20#, 120, -1);
INSERT INTO Ledger (EntryDate, MemberID, Category, Direction, Amount, PayMode, Narration) VALUES (#2026-01-10#, 'S-0001', 'Savings', 'CR', 2000, 'Cash', 'Monthly saving');
INSERT INTO Ledger (EntryDate, MemberID, Category, Direction, Amount, PayMode, Narration) VALUES (#2026-01-12#, 'S-0002', 'Savings', 'CR', 800, 'Cash', 'Monthly saving');
INSERT INTO Ledger (EntryDate, MemberID, Category, Direction, Amount, PayMode, Narration) VALUES (#2026-02-01#, 'C-0001', 'Share', 'CR', 1500, 'Cheque', 'Share capital');
INSERT INTO Ledger (EntryDate, MemberID, Category, Direction, Amount, PayMode, Narration) VALUES (#2026-02-03#, NULL, 'Expense', 'DR', 120, 'Cash', 'Stationery');
INSERT INTO Ledger (EntryDate, MemberID, Category, Direction, Amount, PayMode, Narration) VALUES (#2026-02-05#, NULL, 'Income', 'CR', 60, 'Cash', 'Passbook fees');
INSERT INTO Cash VALUES (1, 2740, 11500);
INSERT INTO Rates (MinDays, RatePct) VALUES (0, 3);
INSERT INTO Rates (MinDays, RatePct) VALUES (90, 5);
INSERT INTO Rates (MinDays, RatePct) VALUES (365, 7);
