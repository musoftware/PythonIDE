VERSION 5.00
Begin {C0E45035-5775-11D0-B388-00A0C9055D8E} DataEnvironment1 
   ClientHeight    =   6000
   ClientLeft      =   0
   ClientTop       =   0
   ClientWidth     =   8000
   _ExtentX        =   14111
   _ExtentY        =   10583
   FolderFlags     =   1
   TypeLibGuid     =   "{6A5E2D11-8D1B-4E73-9C3A-6B1D2F0A9E01}"
   TypeInfoGuid    =   "{6A5E2D12-8D1B-4E73-9C3A-6B1D2F0A9E01}"
   TypeInfoCookie  =   0
   Version         =   4
   NumConnections  =   1
   BeginProperty Connection1 
      ConnectionName  =   "conShop"
      ConnDispId      =   1001
      SourceOfData    =   3
      ConnectionSource=   "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\Shop\shop.mdb;Persist Security Info=False"
      Expanded        =   -1  'True
      QuoteChar       =   96
      SeparatorChar   =   46
   EndProperty
   NumRecordsets   =   2
   BeginProperty Recordset1 
      CommandName     =   "Command1"
      CommDispId      =   1002
      RsDispId        =   1004
      CommandText     =   "select ID, Name, Price, Stock from Products order by ID"
      ActiveConnectionName=   "conShop"
      CommandType     =   1
      IsRSReturning   =   -1  'True
   EndProperty
   BeginProperty Recordset2 
      CommandName     =   "cmdByPrice"
      CommDispId      =   1005
      RsDispId        =   1007
      CommandText     =   "select Name from Products where Price < ? order by Name"
      ActiveConnectionName=   "conShop"
      CommandType     =   1
      IsRSReturning   =   -1  'True
   EndProperty
End
Attribute VB_Name = "DataEnvironment1"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
