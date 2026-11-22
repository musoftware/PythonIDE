Attribute VB_Name = "modBilling"
' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' modBilling - the database connection and the tariff calculation of ElectricityBilling.
'
' How a bill is calculated (see CalcBill):
'   units       = current reading - previous reading
'   energy      = the units split over the slabs of the consumer's category (Tariffs table),
'                 e.g. Domestic: first 100 units x 0.50, next 200 x 0.85, the rest x 1.25
'   fixed       = Settings.FixedCharge
'   tax         = (energy + fixed) x Settings.TaxPercent / 100
'   total       = energy + fixed + tax, due Settings.DueDays days after the bill date
Option Explicit

Public cn As New ADODB.Connection
Public gUser As String
Public gRole As String

' One calculated bill (a user-defined type passed around by the forms)
Public Type BillCalc
    Units As Long
    Energy As Currency
    FixedCharge As Currency
    Tax As Currency
    Total As Currency
    Breakdown As String          ' one line per slab, vbCrLf separated
End Type

Public Sub OpenDb()
    If cn.State = adStateOpen Then Exit Sub
    cn.Open "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=" & App.Path & "\billing.mdb"
End Sub

Public Function Q(ByVal s As String) As String
    Q = "'" & Replace(s, "'", "''") & "'"
End Function

Public Function JetDate(ByVal d As Date) As String
    JetDate = "#" & Format$(d, "mm\/dd\/yyyy") & "#"
End Function

Public Function Setting(ByVal Key As String) As String
    Dim rs As ADODB.Recordset
    Set rs = cn.Execute("SELECT SetValue FROM Settings WHERE SetKey = " & Q(Key))
    If Not rs.EOF Then Setting = rs.Fields("SetValue").Value & ""
    rs.Close
End Function

' Units -> money, slab by slab. Breakdown receives a readable explanation.
Public Function EnergyCharge(ByVal Category As String, ByVal Units As Long, Breakdown As String) As Currency
    Dim rs As ADODB.Recordset, inSlab As Long, total As Currency, slabSize As Long
    Set rs = New ADODB.Recordset
    rs.Open "SELECT FromUnit, ToUnit, Rate FROM Tariffs WHERE Category = " & Q(Category) & " ORDER BY FromUnit", _
            cn, adOpenStatic, adLockReadOnly
    Breakdown = ""
    ' note: VB6 evaluates both sides of And, so "Not rs.EOF And Units >= rs!FromUnit" would read
    ' a field past the last record - the slab test is done inside the loop instead
    Do While Not rs.EOF
        If Units < rs!FromUnit Then Exit Do
        slabSize = rs!ToUnit - rs!FromUnit + 1
        inSlab = Units - rs!FromUnit + 1
        If inSlab > slabSize Then inSlab = slabSize
        total = total + inSlab * rs!Rate
        Breakdown = Breakdown & Format$(inSlab, "#,##0") & " units x " & Format$(rs!Rate, "0.00") & " = " & _
                    Format$(inSlab * rs!Rate, "#,##0.00") & vbCrLf
        rs.MoveNext
    Loop
    rs.Close
    EnergyCharge = total
End Function

Public Function CalcBill(ByVal Category As String, ByVal PrevReading As Long, ByVal CurrReading As Long) As BillCalc
    Dim b As BillCalc, text As String
    b.Units = CurrReading - PrevReading
    b.Energy = EnergyCharge(Category, b.Units, text)
    b.FixedCharge = CCur(Val(Setting("FixedCharge")))
    b.Tax = Round((b.Energy + b.FixedCharge) * Val(Setting("TaxPercent")) / 100, 2)
    b.Total = b.Energy + b.FixedCharge + b.Tax
    b.Breakdown = text & "Fixed charge = " & Format$(b.FixedCharge, "0.00") & vbCrLf & _
                  "Tax " & Setting("TaxPercent") & "% = " & Format$(b.Tax, "0.00")
    CalcBill = b
End Function

' Fill a ComboBox with "meter - name" and keep the meter number in ItemData
Public Sub FillConsumers(cbo As ComboBox, Optional ByVal OnlyActive As Boolean = True)
    Dim rs As ADODB.Recordset
    cbo.Clear
    Set rs = cn.Execute("SELECT MeterNo, FullName FROM Consumers" & IIf(OnlyActive, " WHERE Active", "") & _
                        " ORDER BY MeterNo")
    Do Until rs.EOF
        cbo.AddItem rs!MeterNo & " - " & rs!FullName
        cbo.ItemData(cbo.NewIndex) = rs!MeterNo
        rs.MoveNext
    Loop
    rs.Close
End Sub
