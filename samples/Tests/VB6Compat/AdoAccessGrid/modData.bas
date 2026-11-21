Attribute VB_Name = "modData"
Option Explicit
Public cn As New ADODB.Connection

Sub Main()
    ' the path of the developer's old PC: not found -> shop.mdb next to the program is used
    cn.Provider = "Microsoft.Jet.OLEDB.4.0"
    cn.ConnectionString = "D:\OldPc\Shop\shop.mdb"
    cn.Open
    SelfTest
    frmGrid.Show
End Sub

Sub SelfTest()
    Dim rs As New ADODB.Recordset, n As Long, total As Currency, x As Variant
    rs.Open "select * from Products order by ID", cn, adOpenKeyset, adLockOptimistic
    Debug.Print "rows=" & rs.RecordCount & " fields=" & rs.Fields.Count & " first=" & rs.Fields(1).Name
    Do While Not rs.EOF
        total = total + rs!Price * rs("Stock")
        rs.MoveNext
    Loop
    Debug.Print "stock value=" & Format(total, "0.00")
    rs.AddNew
    rs!Name = "Webcam"
    rs!Price = 45
    rs.Fields("Stock").Value = 5
    rs!Added = DateSerial(2026, 4, 1)
    rs.Update
    Debug.Print "added " & rs!Name & " id>3: " & (rs!ID > 3)
    With rs
        .MoveFirst
        .Find "Name = 'Mouse'"
        If Not .EOF Then
            !Stock = !Stock + 1
            .Update
        End If
    End With
    rs.Filter = "Price > 20"
    Debug.Print "filtered=" & rs.RecordCount
    rs.Filter = ""
    rs.Close
    Set rs = cn.Execute("select Stock from Products where Name='Mouse'")
    x = rs!Stock
    rs.Close
    Debug.Print "mouse stock=" & x & " IsNull=" & IsNull(x)
    cn.Execute "DELETE FROM Products WHERE Name='Webcam'", n
    cn.Execute "UPDATE Products SET Stock = 40 WHERE Name='Mouse'"
    Debug.Print "deleted=" & n
    Dim cmd As New ADODB.Command
    Set cmd.ActiveConnection = cn
    cmd.CommandText = "select Name from Products where Price < ? order by Name"
    cmd.Parameters.Append cmd.CreateParameter("p", adCurrency, adParamInput, , 30)
    Set rs = cmd.Execute
    Debug.Print "cheap: " & rs.GetString(adClipString, , ",", ";")
    On Error Resume Next
    cn.Execute "select * from NoSuchTable"
    Debug.Print "error trapped: " & (Err.Number <> 0)
    On Error GoTo 0
End Sub
