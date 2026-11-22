VERSION 5.00
Begin {C0E45035-5775-11D0-B388-00A0C9055D8E} deExam 
   ClientHeight    =   6000
   ClientLeft      =   0
   ClientTop       =   0
   ClientWidth     =   8000
   _ExtentX        =   14111
   _ExtentY        =   10583
   FolderFlags     =   1
   TypeLibGuid     =   "{8E4FAD31-5F60-4182-9DCE-3F4051627384}"
   TypeInfoGuid    =   "{8E4FAD32-5F60-4182-9DCE-3F4051627384}"
   TypeInfoCookie  =   0
   Version         =   4
   NumConnections  =   1
   BeginProperty Connection1 
      ConnectionName  =   "conExam"
      ConnDispId      =   1001
      SourceOfData    =   3
      ConnectionSource=   "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=exam.mdb;Persist Security Info=False"
      Expanded        =   -1  'True
      QuoteChar       =   96
      SeparatorChar   =   46
   EndProperty
   NumRecordsets   =   1
   BeginProperty Recordset1 
      CommandName     =   "cmdResults"
      CommDispId      =   1002
      RsDispId        =   1004
      CommandText     =   "SELECT u.FullName, r.TakenOn, r.Correct, r.Score, r.MaxScore, r.PercentScore, r.Passed FROM Results r INNER JOIN Users u ON r.UserName = u.UserName WHERE r.SubjectID = ? ORDER BY r.PercentScore DESC"
      ActiveConnectionName=   "conExam"
      CommandType     =   1
      IsRSReturning   =   -1  'True
      NumParams       =   1
   EndProperty
End
Attribute VB_Name = "deExam"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
' deExam - DataEnvironment: cmdResults (the results of one subject; parameter = SubjectID).
Option Explicit
