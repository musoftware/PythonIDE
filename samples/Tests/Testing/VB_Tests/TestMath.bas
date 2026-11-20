' Test module: file name starts with "Test", every Sub Test...() is a test.
Public Sub TestAdd()
    AssertEqual 5, AddNumbers(2, 3)
End Sub

Public Sub TestGreeting()
    AssertEqual "Hello Ali", Greeting("Ali")
End Sub

Public Sub TestFailsOnPurpose()
    AssertEqual 5, AddNumbers(2, 2), "2 + 2"
End Sub
