' (c) 2026 Musoftware - https://musoftwares.com - MIT License
'
' Calculator - a VB.NET Windows Forms App (File > New Project > .NET > Windows Forms App, Visual Basic).
' The form was laid out in RAD IDE's WinForms designer (Form1.Designer.vb is the designer's file, like in
' Visual Studio); this file holds the event handlers.
'
' Shows: one handler for many buttons ("Handles btn0.Click, btn1.Click, ..."), keyboard input with KeyPreview +
' KeyPress, Decimal arithmetic, Try / Catch for DivideByZeroException and OverflowException, a memory register.
Public Class Form1
    Private acc As Decimal = 0D
    Private memory As Decimal = 0D
    Private op As Char = Nothing
    Private fresh As Boolean = True
    Private failed As Boolean = False

    Private Sub Form1_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        KeyPreview = True               ' the form sees the keys before its buttons do
        ShowState()
    End Sub

    Private Sub ShowState()
        lblMemory.Text = If(memory <> 0D, "M", "")
    End Sub

    Private ReadOnly Property Value As Decimal
        Get
            Return Decimal.Parse(lblDisplay.Text, Globalization.CultureInfo.InvariantCulture)
        End Get
    End Property

    Private Sub Show(x As Decimal)
        If Math.Abs(x) > 1000000000000000D Then Throw New OverflowException()
        lblDisplay.Text = x.ToString("0.############", Globalization.CultureInfo.InvariantCulture)
    End Sub

    Private Sub Fail(why As String)
        lblDisplay.Text = "Error: " & why
        lblExpr.Text = ""
        failed = True
        op = Nothing
        fresh = True
    End Sub

    ' every action goes through here, so all errors are handled in one place
    Private Sub Act(action As Action)
        Try
            action()
        Catch ex As DivideByZeroException
            Fail("division by zero")
        Catch ex As OverflowException
            Fail("overflow")
        Catch ex As ArgumentException
            Fail(ex.Message)
        End Try
        ShowState()
    End Sub

    Private Sub Digit(d As String)
        If failed Then ClearAll()
        If fresh Then
            lblDisplay.Text = If(d = ".", "0", "")
            fresh = False
        End If
        If d = "." AndAlso lblDisplay.Text.Contains(".") Then Return
        If lblDisplay.Text.Length >= 16 Then Return
        If lblDisplay.Text = "0" AndAlso d <> "." Then lblDisplay.Text = ""
        lblDisplay.Text &= d
    End Sub

    Private Sub Apply()
        Dim x = Value
        Select Case op
            Case "+"c : acc += x
            Case "-"c : acc -= x
            Case "*"c : acc *= x
            Case "/"c : acc /= x                 ' DivideByZeroException for 0
            Case Else : acc = x
        End Select
        Show(acc)
    End Sub

    Private Sub Operation(o As Char)
        If failed Then Return
        If Not fresh OrElse op = Nothing Then Apply()
        op = o
        fresh = True
        lblExpr.Text = acc.ToString(Globalization.CultureInfo.InvariantCulture) & " " & o
    End Sub

    Private Sub Result()
        If failed OrElse op = Nothing Then Return
        Apply()
        op = Nothing
        fresh = True
        lblExpr.Text = ""
    End Sub

    Private Sub ClearAll()
        lblDisplay.Text = "0"
        lblExpr.Text = ""
        acc = 0D
        op = Nothing
        fresh = True
        failed = False
    End Sub

    Private Sub BackSpace()
        If failed OrElse fresh Then Return
        Dim t = lblDisplay.Text.Substring(0, lblDisplay.Text.Length - 1)
        lblDisplay.Text = If(t = "" OrElse t = "-", "0", t)
    End Sub

    ' ------------------------------------------------------------------ buttons
    Private Sub Digit_Click(sender As Object, e As EventArgs) Handles btn0.Click, btn1.Click, btn2.Click, btn3.Click,
            btn4.Click, btn5.Click, btn6.Click, btn7.Click, btn8.Click, btn9.Click, btnDot.Click
        Act(Sub() Digit(DirectCast(sender, Button).Text))
    End Sub

    Private Sub Operator_Click(sender As Object, e As EventArgs) Handles btnAdd.Click, btnSub.Click, btnMul.Click,
            btnDiv.Click
        Act(Sub() Operation(DirectCast(sender, Button).Text(0)))
    End Sub

    Private Sub btnEquals_Click(sender As Object, e As EventArgs) Handles btnEquals.Click
        Act(AddressOf Result)
    End Sub

    Private Sub btnClear_Click(sender As Object, e As EventArgs) Handles btnClear.Click
        Act(AddressOf ClearAll)
    End Sub

    Private Sub btnBack_Click(sender As Object, e As EventArgs) Handles btnBack.Click
        Act(AddressOf BackSpace)
    End Sub

    Private Sub btnSign_Click(sender As Object, e As EventArgs) Handles btnSign.Click
        Act(Sub() If Not failed Then Show(-Value))
    End Sub

    Private Sub btnSqrt_Click(sender As Object, e As EventArgs) Handles btnSqrt.Click
        Act(Sub()
                If failed Then Return
                If Value < 0D Then Throw New ArgumentException("negative square root")
                Show(CDec(Math.Sqrt(CDbl(Value))))
                fresh = True
            End Sub)
    End Sub

    Private Sub btnPercent_Click(sender As Object, e As EventArgs) Handles btnPercent.Click
        Act(Sub() If Not failed Then Show(If(op <> Nothing, acc * Value / 100D, Value / 100D)))
    End Sub

    Private Sub btnMC_Click(sender As Object, e As EventArgs) Handles btnMC.Click
        Act(Sub() memory = 0D)
    End Sub

    Private Sub btnMR_Click(sender As Object, e As EventArgs) Handles btnMR.Click
        Act(Sub()
                If failed Then Return
                Show(memory)
                fresh = True
            End Sub)
    End Sub

    Private Sub btnMPlus_Click(sender As Object, e As EventArgs) Handles btnMPlus.Click
        Act(Sub()
                If failed Then Return
                memory += Value
                fresh = True
            End Sub)
    End Sub

    ' ------------------------------------------------------------------ keyboard (KeyPreview = True)
    Private Sub Form1_KeyPress(sender As Object, e As KeyPressEventArgs) Handles MyBase.KeyPress
        Dim ch = e.KeyChar
        Select Case ch
            Case "0"c To "9"c : Act(Sub() Digit(ch.ToString()))
            Case "."c, ","c : Act(Sub() Digit("."))
            Case "+"c, "-"c, "*"c, "/"c : Act(Sub() Operation(ch))
            Case "="c, ChrW(13) : Act(AddressOf Result)
            Case ChrW(27) : Act(AddressOf ClearAll)
            Case ChrW(8) : Act(AddressOf BackSpace)
            Case Else : Return
        End Select
        e.Handled = True
    End Sub
End Class
