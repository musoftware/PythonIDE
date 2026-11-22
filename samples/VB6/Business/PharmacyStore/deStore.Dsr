VERSION 5.00
Begin {C0E45035-5775-11D0-B388-00A0C9055D8E} deStore 
   ClientHeight    =   6000
   ClientLeft      =   0
   ClientTop       =   0
   ClientWidth     =   8000
   _ExtentX        =   14111
   _ExtentY        =   10583
   FolderFlags     =   1
   TypeLibGuid     =   "{7D3E9C21-4E5F-4071-8CBD-2E3F40516273}"
   TypeInfoGuid    =   "{7D3E9C22-4E5F-4071-8CBD-2E3F40516273}"
   TypeInfoCookie  =   0
   Version         =   4
   NumConnections  =   1
   BeginProperty Connection1 
      ConnectionName  =   "conStore"
      ConnDispId      =   1001
      SourceOfData    =   3
      ConnectionSource=   "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=pharmacy.mdb;Persist Security Info=False"
      Expanded        =   -1  'True
      QuoteChar       =   96
      SeparatorChar   =   46
   EndProperty
   NumRecordsets   =   1
   BeginProperty Recordset1 
      CommandName     =   "cmdInvoice"
      CommDispId      =   1002
      RsDispId        =   1004
      CommandText     =   "SELECT s.InvoiceNo, s.SaleDate, s.Customer, i.Code, m.MedName, i.Qty, i.UnitPrice, i.Qty * i.UnitPrice AS Amount, s.DiscountPct, s.Total FROM (Sales s INNER JOIN SaleItems i ON s.InvoiceNo = i.InvoiceNo) INNER JOIN Medicines m ON i.Code = m.Code WHERE s.InvoiceNo = ?"
      ActiveConnectionName=   "conStore"
      CommandType     =   1
      IsRSReturning   =   -1  'True
      NumParams       =   1
   EndProperty
End
Attribute VB_Name = "deStore"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
' deStore - DataEnvironment: cmdInvoice (the lines of one invoice; parameter = invoice number).
Option Explicit
