VERSION 5.00
Begin {C0E45035-5775-11D0-B388-00A0C9055D8E} deBilling 
   ClientHeight    =   6000
   ClientLeft      =   0
   ClientTop       =   0
   ClientWidth     =   8000
   _ExtentX        =   14111
   _ExtentY        =   10583
   FolderFlags     =   1
   TypeLibGuid     =   "{5C2F8B11-3D4E-4F60-9BAC-1D2E3F405162}"
   TypeInfoGuid    =   "{5C2F8B12-3D4E-4F60-9BAC-1D2E3F405162}"
   TypeInfoCookie  =   0
   Version         =   4
   NumConnections  =   1
   BeginProperty Connection1 
      ConnectionName  =   "conBilling"
      ConnDispId      =   1001
      SourceOfData    =   3
      ConnectionSource=   "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=billing.mdb;Persist Security Info=False"
      Expanded        =   -1  'True
      QuoteChar       =   96
      SeparatorChar   =   46
   EndProperty
   NumRecordsets   =   2
   BeginProperty Recordset1 
      CommandName     =   "cmdBill"
      CommDispId      =   1002
      RsDispId        =   1004
      CommandText     =   "SELECT b.BillNo, b.BillDate, c.MeterNo, c.FullName, c.Address, b.Units, b.Energy, b.FixedCharge, b.Tax, b.Total, b.DueDate FROM Bills b INNER JOIN Consumers c ON b.MeterNo = c.MeterNo WHERE b.BillNo = ?"
      ActiveConnectionName=   "conBilling"
      CommandType     =   1
      IsRSReturning   =   -1  'True
      NumFields       =   0
      NumParams       =   1
   EndProperty
   BeginProperty Recordset2 
      CommandName     =   "cmdUnpaid"
      CommDispId      =   1005
      RsDispId        =   1007
      CommandText     =   "SELECT b.BillNo, c.MeterNo, c.FullName, b.Total, b.DueDate FROM Bills b INNER JOIN Consumers c ON b.MeterNo = c.MeterNo WHERE NOT b.Paid ORDER BY b.DueDate"
      ActiveConnectionName=   "conBilling"
      CommandType     =   1
      IsRSReturning   =   -1  'True
   EndProperty
End
Attribute VB_Name = "deBilling"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
' deBilling - DataEnvironment: cmdBill (one bill, parameter = bill number) and cmdUnpaid.
Option Explicit
