Option Explicit
' Customers is a data source (Data Sources window). VB code uses it like a BindingSource / TableAdapter:
'   Customers.Fill, Customers.Fill "City = ?", "Cairo", Customers.MoveNext, Customers.Count,
'   Customers.Value("Name"), Customers.SetValue "City", "Giza", Customers.AddNew, Customers.Update

Private Sub Form_Load()
    ShowStatus
End Sub

Private Sub ShowStatus()
    lblStatus.Caption = Customers.Count & " customers - current: " & Customers.Value("Name")
End Sub

Private Sub cmdCairo_Click()
    Customers.Fill "City = ?", "Cairo"
    ShowStatus
End Sub

Private Sub cmdAll_Click()
    Customers.Fill
    ShowStatus
End Sub

Private Sub cmdRich_Click()
    Dim i As Integer, best As Integer
    best = 0
    For i = 0 To Customers.Count - 1
        If Customers.Value("Balance", i) > Customers.Value("Balance", best) Then best = i
    Next i
    Customers.Position = best
    MsgBox Customers.Value("Name") & " has " & Customers.Value("Balance"), vbInformation, "Customers"
    ShowStatus
End Sub
