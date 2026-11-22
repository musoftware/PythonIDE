-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- ClinicManager sample database (Jet 4.0, used through DAO). Build clinic.mdb with:
--   python samples/VB6/Business/_tools/make_mdb.py ClinicManager
-- Every patient, value and medicine name below is fictional demo data, not medical advice.
CREATE TABLE Patients (PatientNo LONG PRIMARY KEY, FullName TEXT(60) NOT NULL, Gender TEXT(1), BirthDate DATETIME,
  Phone TEXT(20), Address TEXT(100), BloodGroup TEXT(3));
CREATE TABLE Visits (VisitID COUNTER PRIMARY KEY, PatientNo LONG, VisitDate DATETIME, WeightKg DOUBLE,
  BloodPressure TEXT(7), Pulse INTEGER, TempC DOUBLE, Diagnosis MEMO, Medicine TEXT(60));
CREATE TABLE Medicines (MedName TEXT(60) PRIMARY KEY);
CREATE TABLE Staff (StaffPin TEXT(6) PRIMARY KEY, FullName TEXT(60));
INSERT INTO Staff VALUES ('1234', 'Demo Receptionist');
INSERT INTO Patients VALUES (1, 'Mona Ibrahim', 'F', #1988-04-12#, '0122-000-0001', '5 Olive St, Demo City', 'A+');
INSERT INTO Patients VALUES (2, 'Youssef Nabil', 'M', #1975-11-30#, '0122-000-0002', '21 Pine Rd, Demo City', 'O-');
INSERT INTO Patients VALUES (3, 'Salma Fouad', 'F', #2012-07-05#, '0122-000-0003', '8 Lake Ave, Demo Town', 'B+');
INSERT INTO Visits (PatientNo, VisitDate, WeightKg, BloodPressure, Pulse, TempC, Diagnosis, Medicine) VALUES (1, #2026-09-14#, 64.5, '118/76', 72, 36.8, 'Routine check-up', 'Vitamin D (demo)');
INSERT INTO Visits (PatientNo, VisitDate, WeightKg, BloodPressure, Pulse, TempC, Diagnosis, Medicine) VALUES (2, #2026-10-02#, 88, '135/88', 80, 37.9, 'Seasonal flu', 'Paracetamol (demo)');
INSERT INTO Visits (PatientNo, VisitDate, WeightKg, BloodPressure, Pulse, TempC, Diagnosis, Medicine) VALUES (2, #2026-10-16#, 87.2, '128/84', 76, 36.9, 'Follow-up', 'None');
INSERT INTO Medicines VALUES ('None');
INSERT INTO Medicines VALUES ('Paracetamol (demo)');
INSERT INTO Medicines VALUES ('Vitamin D (demo)');
INSERT INTO Medicines VALUES ('Cough syrup (demo)');
