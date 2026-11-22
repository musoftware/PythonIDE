' (c) 2026 Musoftware - https://musoftwares.com - MIT License
' Program - the entry point made by the Windows Forms App template (Visual Basic).
Friend Module Program

    <STAThread()>
    Friend Sub Main(args As String())
        Application.SetHighDpiMode(HighDpiMode.SystemAware)
        Application.EnableVisualStyles()
        Application.SetCompatibleTextRenderingDefault(False)
        Application.Run(New Form1)
    End Sub

End Module
