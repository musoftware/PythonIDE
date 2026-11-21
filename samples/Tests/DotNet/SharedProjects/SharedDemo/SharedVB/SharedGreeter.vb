Public Module SharedGreeter
    Public Function Hello() As String
#If NET8_0_OR_GREATER Then
        Return "Hello from .NET 8+ (shared VB)"
#Else
        Return "Hello from .NET Framework 4.8 (shared VB)"
#End If
    End Function
End Module
