Public Class Form1

    Private conversions As Integer = 0

    Private Sub Form1_Load(sender As Object, e As EventArgs) Handles MyBase.Load
        lblOut.Text = "Fahrenheit: -"
    End Sub

    Private Sub btnConvert_Click(sender As Object, e As EventArgs) Handles btnConvert.Click
        Dim c As Double
        If Not Double.TryParse(txtCelsius.Text, c) Then
            MessageBox.Show("Please type a number.", "Temperature", MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        Dim f As Double = c * 9 / 5 + 32
        conversions += 1
        Dim text As String = "Fahrenheit: " & f.ToString("0.0")
        If chkKelvin.Checked Then
            text &= "  Kelvin: " & (c + 273.15).ToString("0.00")
        End If
        lblOut.Text = text
        lstLog.Items.Add(conversions & ": " & c & " C = " & f & " F")
    End Sub

    Private Sub btnClear_Click(sender As Object, e As EventArgs) Handles btnClear.Click
        lstLog.Items.Clear()
        conversions = 0
        lblOut.Text = "Fahrenheit: -"
    End Sub

End Class
