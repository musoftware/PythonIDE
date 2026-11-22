VERSION 5.00
Begin {C0E45035-5775-11D0-B388-00A0C9055D8E} deBank 
   ClientHeight    =   6000
   ClientLeft      =   0
   ClientTop       =   0
   ClientWidth     =   8000
   _ExtentX        =   14111
   _ExtentY        =   10583
   FolderFlags     =   1
   TypeLibGuid     =   "{4B1E7A01-2C3D-4E5F-8A9B-0C1D2E3F4A51}"
   TypeInfoGuid    =   "{4B1E7A02-2C3D-4E5F-8A9B-0C1D2E3F4A51}"
   TypeInfoCookie  =   0
   Version         =   4
   NumConnections  =   1
   BeginProperty Connection1 
      ConnectionName  =   "conBank"
      ConnDispId      =   1001
      SourceOfData    =   3
      ConnectionSource=   "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=bank.mdb;Persist Security Info=False"
      Expanded        =   -1  'True
      QuoteChar       =   96
      SeparatorChar   =   46
   EndProperty
   NumRecordsets   =   1
   BeginProperty Recordset1 
      CommandName     =   "cmdBalances"
      CommDispId      =   1002
      RsDispId        =   1004
      CommandText     =   "SELECT AccountNo, FullName, AccType, Balance FROM Customers ORDER BY AccountNo"
      ActiveConnectionName=   "conBank"
      CommandType     =   1
      IsRSReturning   =   -1  'True
   EndProperty
End
Attribute VB_Name = "deBank"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
' deBank - DataEnvironment: connection conBank (bank.mdb in the program folder) and the command
' cmdBalances used by the rptBalances DataReport.
Option Explicit
