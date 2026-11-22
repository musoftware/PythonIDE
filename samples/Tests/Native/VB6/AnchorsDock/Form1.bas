Private Sub cmdRight_Click()
    Me.Width = Me.Width + 100
    Me.Height = Me.Height + 50
    Debug.Print Me.ScaleWidth, Me.ScaleHeight, txtWide.Width, lstFill.Height, cmdCorner.Left, cmdCorner.Top
End Sub
