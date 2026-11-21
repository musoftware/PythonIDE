Option Explicit

Private Sub Form_Load()

End Sub

Private Sub rateFood_ValueChanged()
    lblResult.Caption = "Food " & rateFood.Value & "/" & rateFood.MaxStars & " - Service " & rateService.Value & "/" & rateService.MaxStars

End Sub

Private Sub rateService_ValueChanged()
    lblResult.Caption = "Food " & rateFood.Value & "/" & rateFood.MaxStars & " - Service " & rateService.Value & "/" & rateService.MaxStars

End Sub

Private Sub btnReset_Click()
    rateFood.Reset
    rateService.SetValue 1

End Sub
