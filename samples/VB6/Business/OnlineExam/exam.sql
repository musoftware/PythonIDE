-- (c) 2026 Musoftware - https://musoftwares.com - MIT License
-- OnlineExam sample database (Jet 4.0, used through DAO). Build exam.mdb with:
--   python samples/VB6/Business/_tools/make_mdb.py OnlineExam
-- The questions were written for this sample; the users are fictional demo accounts.
CREATE TABLE Users (UserName TEXT(20) PRIMARY KEY, Pwd TEXT(20), Role TEXT(10), FullName TEXT(50));
CREATE TABLE Subjects (SubjectID COUNTER PRIMARY KEY, SubjectName TEXT(50));
CREATE TABLE Questions (QID COUNTER PRIMARY KEY, SubjectID LONG, QText MEMO, OptA TEXT(100), OptB TEXT(100),
  OptC TEXT(100), OptD TEXT(100), Correct TEXT(1), Marks INTEGER);
CREATE TABLE Papers (SubjectID LONG PRIMARY KEY, DurationMin INTEGER, PassPercent INTEGER);
CREATE TABLE PaperQuestions (PQID COUNTER PRIMARY KEY, SubjectID LONG, QID LONG, SortNo INTEGER);
CREATE TABLE Results (ResultID COUNTER PRIMARY KEY, UserName TEXT(20), SubjectID LONG, TakenOn DATETIME,
  Answered INTEGER, Correct INTEGER, Score INTEGER, MaxScore INTEGER, PercentScore DOUBLE, Passed BIT);
CREATE TABLE Answers (AnsID COUNTER PRIMARY KEY, ResultID LONG, QID LONG, Chosen TEXT(1));
INSERT INTO Users VALUES ('admin', 'admin', 'admin', 'Demo Examiner');
INSERT INTO Users VALUES ('student1', 'student1', 'student', 'Demo Student One');
INSERT INTO Users VALUES ('student2', 'student2', 'student', 'Demo Student Two');
INSERT INTO Subjects (SubjectName) VALUES ('VB6 basics');
INSERT INTO Subjects (SubjectName) VALUES ('General knowledge');
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (1, 'Which keyword declares a variable in VB6?', 'Dim', 'Var', 'Let', 'Set', 'A', 2);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (1, 'Which control shows a list the user can pick from?', 'Timer', 'ListBox', 'Shape', 'Line', 'B', 2);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (1, 'What does MsgBox show?', 'A message dialog', 'A database', 'A file', 'A menu', 'A', 2);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (1, 'Which event runs when a form is loaded?', 'Click', 'Change', 'Form_Load', 'Timer', 'C', 2);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (1, 'Which operator joins two strings?', '*', '&', '\', 'Mod', 'B', 2);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (2, 'How many days does a leap year have?', '365', '366', '364', '360', 'B', 1);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (2, 'Which planet is closest to the Sun?', 'Venus', 'Earth', 'Mercury', 'Mars', 'C', 1);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (2, 'What is 7 x 8?', '54', '56', '58', '64', 'B', 1);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (2, 'At sea level water boils at (degrees C):', '90', '100', '110', '120', 'B', 1);
INSERT INTO Questions (SubjectID, QText, OptA, OptB, OptC, OptD, Correct, Marks) VALUES (2, 'Which one is a primary colour of light?', 'Red', 'Pink', 'Brown', 'Grey', 'A', 1);
INSERT INTO Papers VALUES (1, 10, 50);
INSERT INTO PaperQuestions (SubjectID, QID, SortNo) VALUES (1, 1, 1);
INSERT INTO PaperQuestions (SubjectID, QID, SortNo) VALUES (1, 2, 2);
INSERT INTO PaperQuestions (SubjectID, QID, SortNo) VALUES (1, 3, 3);
INSERT INTO PaperQuestions (SubjectID, QID, SortNo) VALUES (1, 4, 4);
