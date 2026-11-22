' ============================================================================================
' vbrt_core.bi - RAD IDE VB6 runtime for FreeBASIC: strings (UTF-8), numbers, Variant, errors,
' Format, dates, text files, Collection.  Part of RAD IDE (MIT licence).
'
' Every routine is Private: with -gen gcc the C compiler drops what a program does not use,
' so a small program gets a small exe.
' Strings are UTF-8 inside FreeBASIC Strings; Len/Mid/Left/Right/InStr count characters.
' ============================================================================================
#include once "windows.bi"
#include once "crt/stdio.bi"
#include once "crt/stdlib.bi"
#include once "crt/math.bi"

Type VBBool As Long                 ' VB Boolean: True = -1, False = 0
#define VBTrue (-1)
#define VBFalse 0

' ------------------------------------------------------------------------------ errors
Type VBErrObject
    Number As Long
    Description As String
    Source As String
    LastDllError As Long
End Type
Dim Shared VBErr As VBErrObject
Dim Shared vbErrPending As Long        ' an error is on its way to a handler (polled after statements)
Dim Shared vbErrLine As Long           ' VB source line of the first check that saw it
Dim Shared vbErrFile As String
Dim Shared vbAppTitle As String
Dim Shared vbAppPath As String

Private Function VBErrMsg(ByVal n As Long) As String
    Select Case n
    Case 3: Return "Return without GoSub"
    Case 5: Return "Invalid procedure call or argument"
    Case 6: Return "Overflow"
    Case 7: Return "Out of memory"
    Case 9: Return "Subscript out of range"
    Case 10: Return "This array is fixed or temporarily locked"
    Case 11: Return "Division by zero"
    Case 13: Return "Type mismatch"
    Case 20: Return "Resume without error"
    Case 28: Return "Out of stack space"
    Case 35: Return "Sub or Function not defined"
    Case 52: Return "Bad file name or number"
    Case 53: Return "File not found"
    Case 54: Return "Bad file mode"
    Case 55: Return "File already open"
    Case 57: Return "Device I/O error"
    Case 58: Return "File already exists"
    Case 61: Return "Disk full"
    Case 62: Return "Input past end of file"
    Case 67: Return "Too many files"
    Case 70: Return "Permission denied"
    Case 75: Return "Path/File access error"
    Case 76: Return "Path not found"
    Case 91: Return "Object variable or With block variable not set"
    Case 92: Return "For loop not initialized"
    Case 94: Return "Invalid use of Null"
    Case 380: Return "Invalid property value"
    Case 424: Return "Object required"
    Case 438: Return "Object doesn't support this property or method"
    Case 449: Return "Argument not optional"
    Case 457: Return "This key is already associated with an element of this collection"
    Case 32755: Return "Cancel was selected."
    End Select
    Return "Application-defined or object-defined error"
End Function

Private Sub VBRaise(ByVal n As Long, ByRef desc As String = "")
    VBErr.Number = n
    VBErr.Description = IIf(Len(desc) = 0, VBErrMsg(n), desc)
    vbErrPending = 1
    vbErrLine = 0
End Sub

Private Sub VBErrClear()
    VBErr.Number = 0
    VBErr.Description = ""
    VBErr.Source = ""
End Sub

Private Sub VBErrSetNumber(ByVal n As Long)
    VBErr.Number = n
    If n <> 0 AndAlso Len(VBErr.Description) = 0 Then VBErr.Description = VBErrMsg(n)
End Sub

' called by the first error check that sees a pending error: remembers where it happened
Private Sub VBErrAt(ByVal ln As Long, ByVal f As ZString Ptr)
    If vbErrLine = 0 Then
        vbErrLine = ln
        vbErrFile = *f
    End If
End Sub

' ------------------------------------------------------------------------------ UTF-8 <-> UTF-16
Private Function VBWide(ByRef s As String) As WString Ptr       ' Deallocate the result
    Dim n As Long = MultiByteToWideChar(CP_UTF8, 0, StrPtr(s), Len(s), 0, 0)
    Dim w As WString Ptr = Allocate((n + 1) * 2)
    If n > 0 Then MultiByteToWideChar(CP_UTF8, 0, StrPtr(s), Len(s), w, n)
    (*w)[n] = 0
    Return w
End Function

Private Function VBFromWide(ByVal w As Const WString Ptr, ByVal n As Long = -1) As String
    If w = 0 Then Return ""
    If n < 0 Then n = lstrlenW(w)
    If n = 0 Then Return ""
    Dim k As Long = WideCharToMultiByte(CP_UTF8, 0, w, n, 0, 0, 0, 0)
    Dim r As String = Space(k)
    WideCharToMultiByte(CP_UTF8, 0, w, n, StrPtr(r), k, 0, 0)
    Return r
End Function

Private Function VBIsAscii(ByRef s As String) As Long
    For i As Long = 0 To Len(s) - 1
        If s[i] >= 128 Then Return 0
    Next
    Return -1
End Function

' byte offset (0-based) of character ci (0-based)
Private Function VBU8Off(ByRef s As String, ByVal ci As Long) As Long
    Dim As Long i = 0, n = Len(s), c = 0
    While i < n AndAlso c < ci
        Dim b As UByte = s[i]
        If b < &hC0 Then
            i += 1
        ElseIf b < &hE0 Then
            i += 2
        ElseIf b < &hF0 Then
            i += 3
        Else
            i += 4
        End If
        c += 1
    Wend
    If i > n Then i = n
    Return i
End Function

Private Function VBU8Chars(ByRef s As String, ByVal nbytes As Long) As Long   ' characters in the first n bytes
    Dim c As Long = 0
    If nbytes > Len(s) Then nbytes = Len(s)
    For i As Long = 0 To nbytes - 1
        If (s[i] And &hC0) <> &h80 Then c += 1
    Next
    Return c
End Function

Private Function VBEncodeCP(ByVal cp As Long) As String
    If cp < 0 Then VBRaise(5): Return ""
    If cp < &h80 Then Return Chr(cp)
    If cp < &h800 Then Return Chr(&hC0 Or (cp Shr 6), &h80 Or (cp And &h3F))
    If cp < &h10000 Then Return Chr(&hE0 Or (cp Shr 12), &h80 Or ((cp Shr 6) And &h3F), &h80 Or (cp And &h3F))
    Return Chr(&hF0 Or (cp Shr 18), &h80 Or ((cp Shr 12) And &h3F), &h80 Or ((cp Shr 6) And &h3F), &h80 Or (cp And &h3F))
End Function

Private Function VBDecodeFirst(ByRef s As String) As Long
    If Len(s) = 0 Then Return 0
    Dim b As Long = s[0]
    If b < &h80 OrElse Len(s) < 2 Then Return b
    If b < &hE0 Then Return ((b And &h1F) Shl 6) Or (s[1] And &h3F)
    If b < &hF0 AndAlso Len(s) >= 3 Then Return ((b And &h0F) Shl 12) Or ((s[1] And &h3F) Shl 6) Or (s[2] And &h3F)
    If Len(s) >= 4 Then Return ((b And &h07) Shl 18) Or ((s[1] And &h3F) Shl 12) Or ((s[2] And &h3F) Shl 6) Or (s[3] And &h3F)
    Return b
End Function

' ------------------------------------------------------------------------------ string functions
Private Function VBLen(ByRef s As String) As Long
    Dim c As Long = 0
    For i As Long = 0 To Len(s) - 1
        If (s[i] And &hC0) <> &h80 Then c += 1
    Next
    Return c
End Function

Private Function VBLeft(ByRef s As String, ByVal n As Long) As String
    If n < 0 Then VBRaise(5): Return ""
    If VBIsAscii(s) Then Return Left(s, n)
    Return Left(s, VBU8Off(s, n))
End Function

Private Function VBRight(ByRef s As String, ByVal n As Long) As String
    If n < 0 Then VBRaise(5): Return ""
    If VBIsAscii(s) Then Return Right(s, n)
    Dim total As Long = VBLen(s)
    If n >= total Then Return s
    Return Mid(s, VBU8Off(s, total - n) + 1)
End Function

Private Function VBMid(ByRef s As String, ByVal start As Long, ByVal n As Long = -1) As String
    If start < 1 Then VBRaise(5): Return ""
    If VBIsAscii(s) Then
        If n < 0 Then Return Mid(s, start)
        Return Mid(s, start, n)
    End If
    Dim a As Long = VBU8Off(s, start - 1)
    If a >= Len(s) Then Return ""
    If n < 0 Then Return Mid(s, a + 1)
    Dim b As Long = a + VBU8Off(Mid(s, a + 1), n)
    Return Mid(s, a + 1, b - a)
End Function

' Mid(s, start, n) = repl
Private Sub VBMidSet(ByRef s As String, ByVal start As Long, ByVal n As Long, ByRef repl As String)
    If start < 1 Then VBRaise(5): Exit Sub
    Dim total As Long = VBLen(s)
    If start > total Then Exit Sub
    Dim k As Long = VBLen(repl)
    If n < 0 OrElse n > k Then n = k
    If n > total - start + 1 Then n = total - start + 1
    s = VBLeft(s, start - 1) & VBLeft(repl, n) & VBMid(s, start + n)
End Sub

Private Function VBUCase(ByRef s As String) As String
    If VBIsAscii(s) Then Return UCase(s)
    Dim w As WString Ptr = VBWide(s)
    CharUpperW(w)
    Function = VBFromWide(w)
    Deallocate(w)
End Function

Private Function VBLCase(ByRef s As String) As String
    If VBIsAscii(s) Then Return LCase(s)
    Dim w As WString Ptr = VBWide(s)
    CharLowerW(w)
    Function = VBFromWide(w)
    Deallocate(w)
End Function

Private Function VBInStr(ByVal start As Long, ByRef s As String, ByRef sub_ As String, ByVal cmp As Long = 0) As Long
    If start < 1 Then VBRaise(5): Return 0
    Dim As String a = s, b = sub_
    If cmp = 1 Then a = VBLCase(a): b = VBLCase(b)
    If Len(b) = 0 Then
        If start <= VBLen(a) + 1 Then Return start
        Return 0
    End If
    If VBIsAscii(a) Then Return InStr(start, a, b)
    Dim off As Long = VBU8Off(a, start - 1)
    Dim p As Long = InStr(off + 1, a, b)
    If p = 0 Then Return 0
    Return VBU8Chars(a, p - 1) + 1
End Function

Private Function VBInStrRev(ByRef s As String, ByRef sub_ As String, ByVal start As Long = -1, ByVal cmp As Long = 0) As Long
    Dim As String a = s, b = sub_
    If cmp = 1 Then a = VBLCase(a): b = VBLCase(b)
    Dim total As Long = VBLen(a)
    Dim e As Long = IIf(start = -1, total, start)
    If e > total Then e = total
    If e < 0 Then Return 0
    Dim hay As String = VBLeft(a, e)
    If Len(b) = 0 Then Return e + 1
    Dim As Long p = 0, q = InStr(hay, b)
    While q > 0
        p = q
        q = InStr(q + 1, hay, b)
    Wend
    If p = 0 Then Return 0
    Return VBU8Chars(hay, p - 1) + 1
End Function

Private Function VBReplace(ByRef s As String, ByRef f As String, ByRef r As String) As String
    If Len(f) = 0 Then Return s
    Dim As String out_
    Dim As Long i = 1, p = InStr(s, f)
    While p > 0
        out_ &= Mid(s, i, p - i) & r
        i = p + Len(f)
        p = InStr(i, s, f)
    Wend
    Return out_ & Mid(s, i)
End Function

Private Function VBChr(ByVal n As Long) As String
    Return VBEncodeCP(n)
End Function

Private Function VBAsc(ByRef s As String) As Long
    Return VBDecodeFirst(s)
End Function

Private Function VBStringN(ByVal n As Long, ByRef c As String) As String
    If n < 0 Then VBRaise(5): Return ""
    Dim ch As String = VBLeft(c, 1)
    Dim r As String
    For i As Long = 1 To n
        r &= ch
    Next
    Return r
End Function

Private Function VBStrReverse(ByRef s As String) As String
    If VBIsAscii(s) Then
        Dim r As String = s
        Dim n As Long = Len(s)
        For i As Long = 0 To n - 1
            r[i] = s[n - 1 - i]
        Next
        Return r
    End If
    Dim r As String
    Dim As Long i = 0, n = Len(s)
    While i < n
        Dim k As Long = 1
        While i + k < n AndAlso (s[i + k] And &hC0) = &h80
            k += 1
        Wend
        r = Mid(s, i + 1, k) & r
        i += k
    Wend
    Return r
End Function

Private Function VBFixStr(ByRef s As String, ByVal n As Long) As String    ' String * n
    Dim k As Long = VBLen(s)
    If k >= n Then Return VBLeft(s, n)
    Return s & Space(n - k)
End Function

Private Function VBSpace(ByVal n As Long) As String
    If n < 0 Then VBRaise(5): Return ""
    Return Space(n)
End Function

Private Function VBStrComp(ByRef a As String, ByRef b As String, ByVal cmp As Long = 0) As Long
    Dim As String x = a, y = b
    If cmp = 1 Then x = VBLCase(x): y = VBLCase(y)
    If x < y Then Return -1
    If x > y Then Return 1
    Return 0
End Function

Private Function VBProperCase(ByRef s As String) As String
    ' Python str.title(): upper after a non-letter, lower otherwise (ASCII letters)
    Dim r As String = s
    Dim prev As Long = 0
    For i As Long = 0 To Len(r) - 1
        Dim c As Long = r[i]
        Dim isl As Long = (c >= 65 AndAlso c <= 90) OrElse (c >= 97 AndAlso c <= 122)
        If isl Then
            If prev Then
                If c >= 65 AndAlso c <= 90 Then r[i] = c + 32
            Else
                If c >= 97 AndAlso c <= 122 Then r[i] = c - 32
            End If
        End If
        prev = isl OrElse c >= 128
    Next
    Return r
End Function

Private Function VBStrConv(ByRef s As String, ByVal mode As Long) As String
    Select Case mode
    Case 1: Return VBUCase(s)
    Case 2: Return VBLCase(s)
    Case 3: Return VBProperCase(s)
    End Select
    Return s
End Function

' ------------------------------------------------------------------------------ numbers <-> text
' Python repr() of a double: shortest digits that read back the same number
Private Sub VBShortest(ByVal x As Double, ByRef digits As String, ByRef e10 As Long)
    Dim buf As ZString * 40
    For p As Long = 1 To 17
        sprintf(@buf, "%.*e", p - 1, Abs(x))
        If strtod(@buf, 0) = Abs(x) Then Exit For
    Next
    Dim t As String = buf
    Dim ep As Long = InStr(t, "e")
    e10 = ValInt(Mid(t, ep + 1))
    digits = Left(t, 1) & Mid(t, 3, ep - 3)
    If ep = 2 Then digits = Left(t, 1)
    While Len(digits) > 1 AndAlso Right(digits, 1) = "0"
        digits = Left(digits, Len(digits) - 1)
    Wend
End Sub

Private Function VBRepr(ByVal x As Double) As String
    If x <> x Then Return "nan"
    If x = 0 Then Return IIf(1 / x < 0, "-0.0", "0.0")
    If Abs(x) > 1.7976931348623157e308 Then Return IIf(x < 0, "-inf", "inf")
    Dim digits As String
    Dim e As Long
    VBShortest(x, digits, e)
    Dim sg As String = IIf(x < 0, "-", "")
    Dim n As Long = Len(digits)
    If e >= -4 AndAlso e < 16 Then
        If e >= 0 Then
            If n <= e + 1 Then Return sg & digits & String(e + 1 - n, "0") & ".0"
            Return sg & Left(digits, e + 1) & "." & Mid(digits, e + 2)
        End If
        Return sg & "0." & String(-e - 1, "0") & digits
    End If
    Dim m As String = Left(digits, 1)
    If n > 1 Then m &= "." & Mid(digits, 2)
    Dim es As String = Str(Abs(e))
    If Len(es) < 2 Then es = "0" & es
    Return sg & m & "e" & IIf(e < 0, "-", "+") & es
End Function

Private Function VBStrL(ByVal x As LongInt) As String
    Return Str(x)
End Function

' VB / interpreter number to text: whole numbers without decimals, else up to 15 decimals
Private Function VBStrD(ByVal x As Double) As String
    If x = Int(x) AndAlso Abs(x) < 1e15 Then Return Str(CLngInt(x))
    Dim r As String = VBRepr(x)
    If InStr(r, "e") OrElse InStr(r, "n") Then Return r
    Dim buf As ZString * 400
    sprintf(@buf, "%.15f", x)
    r = VBRepr(strtod(@buf, 0))
    If InStr(r, "e") = 0 Then
        r = RTrim(r, "0")
        r = RTrim(r, ".")
    End If
    Return r
End Function

Private Function VBStrB(ByVal b As Long) As String
    Return IIf(b, "True", "False")
End Function

' Str(): a leading space for positive numbers
Private Function VBStrFn(ByVal x As Double) As String
    Return IIf(x >= 0, " ", "") & VBStrD(x)
End Function

Private Function VBIsSpace(ByVal c As Long) As Long
    Return c = 32 OrElse c = 9 OrElse c = 10 OrElse c = 13 OrElse c = 11 OrElse c = 12
End Function

' text -> number like the interpreter's to_num (error 13 when it is not a number)
Private Function VBTryNum(ByRef s As String, ByRef v As Double) As Long
    Dim t As String = s
    Dim As Long a = 0, b = Len(t) - 1
    While a <= b AndAlso VBIsSpace(t[a])
        a += 1
    Wend
    While b >= a AndAlso VBIsSpace(t[b])
        b -= 1
    Wend
    If b < a Then Return 0
    t = Mid(t, a + 1, b - a + 1)
    If Len(t) > 2 AndAlso (Left(t, 2) = "&h" OrElse Left(t, 2) = "&H") Then
        Dim r As LongInt = 0
        For i As Long = 2 To Len(t) - 1
            Dim c As Long = t[i]
            Select Case c
            Case 48 To 57: r = r * 16 + (c - 48)
            Case 65 To 70: r = r * 16 + (c - 55)
            Case 97 To 102: r = r * 16 + (c - 87)
            Case Else: Return 0
            End Select
        Next
        v = r
        Return -1
    End If
    t = VBReplace(t, "_", "")
    Dim ep As ZString Ptr
    v = strtod(StrPtr(t), @ep)
    If ep = StrPtr(t) OrElse (*ep)[0] <> 0 Then Return 0
    Return -1
End Function

Private Function VBNumS(ByRef s As String) As Double
    Dim v As Double
    If VBTryNum(s, v) = 0 Then
        If Len(Trim(s, Any Chr(32, 9, 10, 13))) = 0 Then VBRaise(13, "Type mismatch") Else VBRaise(13, "Type mismatch: """ & s & """ is not a number")
        Return 0
    End If
    Return v
End Function

Private Function VBIsNumericS(ByRef s As String) As Long
    Dim v As Double
    Return VBTryNum(s, v)
End Function

Private Function VBBoolS(ByRef s As String) As Long
    Dim l As String = LCase(s)
    If l = "true" Then Return -1
    If l = "false" Then Return 0
    Return VBNumS(s) <> 0
End Function

Private Function VBVal(ByRef s As String) As Double
    Dim t As String = VBReplace(s, " ", "")
    t = VBReplace(t, Chr(9), "")
    Dim i As Long = 0
    Dim n As Long = Len(t)
    Dim st As Long = 0
    If i < n AndAlso (t[i] = 45 OrElse t[i] = 43) Then i += 1
    Dim d0 As Long = i
    While i < n AndAlso t[i] >= 48 AndAlso t[i] <= 57
        i += 1
    Wend
    If i < n AndAlso t[i] = 46 Then
        i += 1
        While i < n AndAlso t[i] >= 48 AndAlso t[i] <= 57
            i += 1
        Wend
    End If
    If i = d0 OrElse (i = d0 + 1 AndAlso t[d0] = 46) Then Return 0
    If i < n AndAlso (t[i] = 69 OrElse t[i] = 101) Then
        Dim j As Long = i + 1
        If j < n AndAlso (t[j] = 45 OrElse t[j] = 43) Then j += 1
        If j < n AndAlso t[j] >= 48 AndAlso t[j] <= 57 Then
            While j < n AndAlso t[j] >= 48 AndAlso t[j] <= 57
                j += 1
            Wend
            i = j
        End If
    End If
    Dim num As String = Left(t, i)
    Return strtod(StrPtr(num), 0)
End Function

Private Function VBRound(ByVal x As Double, ByVal nd As Long = 0) As Double
    If nd = 0 Then Return CLngInt(x)
    Dim buf As ZString * 400
    sprintf(@buf, "%.*f", nd, x)
    Return strtod(@buf, 0)
End Function

Private Function VBIDiv(ByVal a As Double, ByVal b As Double) As LongInt
    Dim d As LongInt = CLngInt(b)
    If d = 0 Then VBRaise(11): Return 0
    Return CLngInt(a) \ d
End Function

Private Function VBMod(ByVal a As Double, ByVal b As Double) As LongInt
    Dim d As LongInt = CLngInt(b)
    If d = 0 Then VBRaise(11): Return 0
    Return CLngInt(a) Mod d
End Function

Private Function VBDiv(ByVal a As Double, ByVal b As Double) As Double
    If b = 0 Then VBRaise(11): Return 0
    Return a / b
End Function

Private Function VBSqr(ByVal x As Double) As Double
    If x < 0 Then VBRaise(5): Return 0
    Return Sqr(x)
End Function

Private Function VBLog(ByVal x As Double) As Double
    If x <= 0 Then VBRaise(5): Return 0
    Return Log(x)
End Function

Private Function VBHex(ByVal x As LongInt) As String
    If x < 0 Then Return "-" & Hex(-x)
    Return Hex(x)
End Function

Private Function VBOct(ByVal x As LongInt) As String
    If x < 0 Then Return "-" & Oct(-x)
    Return Oct(x)
End Function

Private Function VBSgn(ByVal x As Double) As Long
    Return IIf(x > 0, 1, IIf(x < 0, -1, 0))
End Function

Dim Shared vbRndSeed As ULong = 327680
Private Function VBRnd() As Double
    vbRndSeed = vbRndSeed * 1103515245 + 12345
    Return (vbRndSeed Shr 8) / 16777216.0
End Function
Private Sub VBRandomize()
    vbRndSeed = GetTickCount() Xor (GetCurrentProcessId() Shl 16)
End Sub

' index check of an array subscript (VB: error 9)
Private Function VBIxChk(ByVal i As Double, ByVal lo As Long, ByVal hi As Long) As Long
    Dim k As Long = CLng(i)
    If k < lo OrElse k > hi Then
        VBRaise(9)
        Return lo
    End If
    Return k
End Function
#define VBIX(arr, d, i) VBIxChk(i, LBound(arr, d), UBound(arr, d))

' ------------------------------------------------------------------------------ dates (serial days since 30/12/1899)
Private Function VBDaysFromCivil(ByVal y As Long, ByVal m As Long, ByVal d As Long) As Long
    ' days since 1970-01-01 (H. Hinnant's algorithm), m may be outside 1..12
    y += (m - 1) \ 12
    m = ((m - 1) Mod 12)
    If m < 0 Then m += 12: y -= 1
    m += 1
    If m <= 2 Then y -= 1
    Dim era As Long = IIf(y >= 0, y, y - 399) \ 400
    Dim yoe As Long = y - era * 400
    Dim mp As Long = (m + 9) Mod 12
    Dim doy As Long = (153 * mp + 2) \ 5 + d - 1
    Dim doe As Long = yoe * 365 + yoe \ 4 - yoe \ 100 + doy
    Return era * 146097 + doe - 719468
End Function

Private Sub VBCivilFromDays(ByVal z As Long, ByRef y As Long, ByRef m As Long, ByRef d As Long)
    z += 719468
    Dim era As Long = IIf(z >= 0, z, z - 146096) \ 146097
    Dim doe As Long = z - era * 146097
    Dim yoe As Long = (doe - doe \ 1460 + doe \ 36524 - doe \ 146096) \ 365
    y = yoe + era * 400
    Dim doy As Long = doe - (365 * yoe + yoe \ 4 - yoe \ 100)
    Dim mp As Long = (5 * doy + 2) \ 153
    d = doy - (153 * mp + 2) \ 5 + 1
    m = IIf(mp < 10, mp + 3, mp - 9)
    If m <= 2 Then y += 1
End Sub

Private Function VBDateSerial(ByVal y As Long, ByVal m As Long, ByVal d As Long) As Double
    Return VBDaysFromCivil(y, m, 1) + (d - 1) + 25569
End Function

Private Function VBTimeSerial(ByVal h As Long, ByVal n As Long, ByVal s As Long) As Double
    Return (h * 3600 + n * 60 + s) / 86400.0
End Function

Private Sub VBDateParts(ByVal dt As Double, ByRef y As Long, ByRef m As Long, ByRef d As Long, _
                        ByRef hh As Long, ByRef nn As Long, ByRef ss As Long)
    Dim days As Long = Int(dt)
    Dim ms As LongInt = CLngInt((dt - days) * 86400000.0)
    If ms >= 86400000 Then days += 1: ms -= 86400000
    VBCivilFromDays(days - 25569, y, m, d)
    Dim secs As Long = ms \ 1000
    hh = secs \ 3600
    nn = (secs \ 60) Mod 60
    ss = secs Mod 60
End Sub

Private Function VBNow() As Double
    Dim st As SYSTEMTIME
    GetLocalTime(@st)
    Return VBDateSerial(st.wYear, st.wMonth, st.wDay) + VBTimeSerial(st.wHour, st.wMinute, st.wSecond)
End Function

Private Function VBToday() As Double
    Return Int(VBNow())
End Function

Private Function VBTimeNow() As Double
    Dim n As Double = VBNow()
    Return n - Int(n)
End Function

Private Function VBTimer() As Double
    Dim st As SYSTEMTIME
    GetLocalTime(@st)
    Return CLngInt((st.wHour * 3600 + st.wMinute * 60 + st.wSecond + st.wMilliseconds / 1000.0) * 100) / 100.0
End Function

Private Function VBYear(ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Return y
End Function
Private Function VBMonth(ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Return m
End Function
Private Function VBDay(ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Return d
End Function
Private Function VBHour(ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Return h
End Function
Private Function VBMinute(ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Return n
End Function
Private Function VBSecond(ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Return s
End Function
Private Function VBWeekday(ByVal dt As Double) As Long     ' 1 = Sunday
    Dim w As Long = (Int(dt) - 1) Mod 7                     ' serial 1 (31/12/1899) was a Sunday
    If w < 0 Then w += 7
    Return w + 1
End Function
Private Function VBDayOfYear(ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Return Int(dt) - CLng(VBDateSerial(y, 1, 1)) + 1
End Function

Private Function VBMonthName(ByVal m As Long, ByVal abbr As Long = 0) As String
    Static names(1 To 12) As String * 9 = {"January", "February", "March", "April", "May", "June", "July", _
                                          "August", "September", "October", "November", "December"}
    If m < 1 OrElse m > 12 Then VBRaise(5): Return ""
    Dim r As String = names(m)
    Return IIf(abbr, Left(r, 3), r)
End Function

Private Function VBWeekdayName(ByVal w As Long, ByVal abbr As Long = 0) As String
    Static names(1 To 7) As String * 9 = {"Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}
    If w < 1 OrElse w > 7 Then VBRaise(5): Return ""
    Dim r As String = names(w)
    Return IIf(abbr, Left(r, 3), r)
End Function

Private Function VB2(ByVal n As Long) As String
    Return IIf(n < 10, "0", "") & Str(n)
End Function

Private Function VBDateStr(ByVal dt As Double) As String       ' interpreter: dd/mm/yyyy [hh:mm:ss]
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Dim r As String = VB2(d) & "/" & VB2(m) & "/" & Right("000" & Str(y), 4)
    If h <> 0 OrElse n <> 0 OrElse s <> 0 Then r &= " " & VB2(h) & ":" & VB2(n) & ":" & VB2(s)
    Return r
End Function

Private Function VBDateAdd(ByRef iv As String, ByVal n As Double, ByVal dt As Double) As Double
    Dim As Long y, m, d, h, mi, s
    Select Case LCase(iv)
    Case "d", "y", "w": Return dt + n
    Case "ww": Return dt + n * 7
    Case "h": Return dt + n / 24
    Case "n": Return dt + n / 1440
    Case "s": Return dt + n / 86400
    Case "m", "q", "yyyy"
        Dim months As Long = Fix(n) * IIf(LCase(iv) = "q", 3, IIf(LCase(iv) = "yyyy", 12, 1))
        VBDateParts(dt, y, m, d, h, mi, s)
        Dim t As Long = (m - 1) + months
        Dim ny As Long = y + IIf(t >= 0, t \ 12, -((11 - t) \ 12))
        Dim nm As Long = t - (ny - y) * 12 + 1
        Dim last As Long = VBDateSerial(ny, nm + 1, 1) - VBDateSerial(ny, nm, 1)
        If d > last Then d = last
        Return VBDateSerial(ny, nm, d) + (dt - Int(dt))
    End Select
    VBRaise(5)
    Return dt
End Function

Private Function VBDateDiff(ByRef iv As String, ByVal a As Double, ByVal b As Double) As LongInt
    Dim As Long y1, m1, d1, h1, n1, s1, y2, m2, d2, h2, n2, s2
    Dim secs As Double = CLngInt((b - a) * 86400)
    Dim floordiv As Double
    Select Case LCase(iv)
    Case "d", "y", "w": Return Int(secs / 86400)
    Case "ww": Return Int(Int(secs / 86400) / 7)
    Case "h": Return Int(secs / 3600)
    Case "n": Return Int(secs / 60)
    Case "s": Return secs
    Case "m", "yyyy", "q"
        VBDateParts(a, y1, m1, d1, h1, n1, s1)
        VBDateParts(b, y2, m2, d2, h2, n2, s2)
        If LCase(iv) = "yyyy" Then Return y2 - y1
        Dim mm As Long = (y2 - y1) * 12 + m2 - m1
        If LCase(iv) = "m" Then Return mm
        Return Int(mm / 3)
    End Select
    VBRaise(5)
    Return 0
End Function

Private Function VBDatePart(ByRef iv As String, ByVal dt As Double) As Long
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Select Case LCase(iv)
    Case "yyyy": Return y
    Case "q": Return (m - 1) \ 3 + 1
    Case "m": Return m
    Case "y": Return VBDayOfYear(dt)
    Case "d": Return d
    Case "w": Return VBWeekday(dt)
    Case "ww"
        Dim jan1 As Double = VBDateSerial(y, 1, 1)
        Return (VBDayOfYear(dt) + VBWeekday(jan1) - 2) \ 7 + 1
    Case "h": Return h
    Case "n": Return n
    Case "s": Return s
    End Select
    Return 0
End Function

' text -> date (the interpreter's formats: m/d/yyyy, d/m/yyyy, yyyy-mm-dd, times)
Private Function VBTryDate(ByRef s0 As String, ByRef v As Double) As Long
    Dim s As String = Trim(s0)
    Dim nums(0 To 6) As Long
    Dim seps As String
    Dim cnt As Long = 0
    Dim pm As Long = -1
    Dim i As Long = 0
    Dim n As Long = Len(s)
    Dim us As String = UCase(s)
    If Right(us, 2) = "PM" Then pm = 1: s = RTrim(Left(s, n - 2)): n = Len(s)
    If Right(us, 2) = "AM" AndAlso pm = -1 Then pm = 0: s = RTrim(Left(s, n - 2)): n = Len(s)
    While i < n
        If s[i] >= 48 AndAlso s[i] <= 57 Then
            If cnt > 6 Then Return 0
            Dim k As Long = 0
            While i < n AndAlso s[i] >= 48 AndAlso s[i] <= 57
                k = k * 10 + (s[i] - 48)
                i += 1
            Wend
            nums(cnt) = k
            cnt += 1
        Else
            seps &= Chr(s[i])
            i += 1
        End If
    Wend
    Dim As Long y, m, d, hh, nn, ss
    If cnt = 0 Then Return 0
    If Left(seps, 2) = "//" OrElse Left(seps, 2) = "--" Then
        If InStr(seps, "-") AndAlso nums(0) > 31 Then
            y = nums(0): m = nums(1): d = nums(2)
        Else
            m = nums(0): d = nums(1): y = nums(2)
            If m > 12 Then Swap m, d
        End If
        If m < 1 OrElse m > 12 OrElse d < 1 OrElse d > 31 Then Return 0
        hh = nums(3): nn = nums(4): ss = nums(5)
        If cnt < 3 OrElse (cnt > 3 AndAlso cnt < 5) Then Return 0
        If pm = 1 AndAlso hh < 12 Then hh += 12
        If pm = 0 AndAlso hh = 12 Then hh = 0
        v = VBDateSerial(y, m, d) + VBTimeSerial(hh, nn, ss)
        Return -1
    End If
    If Left(seps, 1) = ":" AndAlso (cnt = 2 OrElse cnt = 3) Then
        hh = nums(0): nn = nums(1): ss = IIf(cnt = 3, nums(2), 0)
        If pm = 1 AndAlso hh < 12 Then hh += 12
        If pm = 0 AndAlso hh = 12 Then hh = 0
        If hh > 23 OrElse nn > 59 OrElse ss > 59 Then Return 0
        v = VBTimeSerial(hh, nn, ss)
        Return -1
    End If
    Return 0
End Function

Private Function VBDateS(ByRef s As String) As Double
    Dim v As Double
    If VBTryDate(s, v) = 0 Then VBRaise(13, "Type mismatch"): Return 0
    Return v
End Function

' ------------------------------------------------------------------------------ Variant
Enum VBVarType
    vbvEmpty = 0
    vbvNull = 1
    vbvLong = 3
    vbvDouble = 5
    vbvDate = 7
    vbvString = 8
    vbvBoolean = 11
End Enum

Type RVar
    vt As Long
    n As Double
    s As String
    p As Any Ptr          ' vt = 9: an object (class instance)
End Type

Private Function RV_Empty() As RVar
    Dim r As RVar
    Return r
End Function
Private Function RV_L(ByVal x As LongInt) As RVar
    Dim r As RVar
    r.vt = vbvLong: r.n = x
    Return r
End Function
Private Function RV_D(ByVal x As Double) As RVar
    Dim r As RVar
    r.vt = vbvDouble: r.n = x
    Return r
End Function
Private Function RV_S(ByRef x As String) As RVar
    Dim r As RVar
    r.vt = vbvString: r.s = x
    Return r
End Function
Private Function RV_B(ByVal x As Long) As RVar
    Dim r As RVar
    r.vt = vbvBoolean: r.n = IIf(x, -1, 0)
    Return r
End Function
Private Function RV_Dt(ByVal x As Double) As RVar
    Dim r As RVar
    r.vt = vbvDate: r.n = x
    Return r
End Function
Private Function RV_Null() As RVar
    Dim r As RVar
    r.vt = vbvNull
    Return r
End Function

Private Function RV_Obj(ByVal p As Any Ptr) As RVar
    Dim r As RVar
    r.vt = 9: r.p = p
    Return r
End Function

Private Function RV_ToObj(ByRef v As RVar) As Any Ptr
    If v.vt = 9 Then Return v.p
    If v.vt <> vbvEmpty Then VBRaise(13)
    Return 0
End Function

Private Function RV_Missing() As RVar           ' an Optional Variant argument that was not passed
    Dim r As RVar
    r.vt = 10
    Return r
End Function

Private Function RV_IsNum(ByRef v As RVar) As Long
    Select Case v.vt
    Case vbvLong, vbvDouble, vbvBoolean: Return -1
    Case vbvString: Return VBIsNumericS(v.s)
    End Select
    Return 0
End Function

Private Function RV_ToD(ByRef v As RVar) As Double
    Select Case v.vt
    Case vbvString: Return VBNumS(v.s)
    Case vbvNull: VBRaise(94): Return 0
    End Select
    Return v.n
End Function

Private Function RV_ToL(ByRef v As RVar) As LongInt
    Return CLngInt(RV_ToD(v))
End Function

Private Function RV_ToS(ByRef v As RVar) As String
    Select Case v.vt
    Case vbvString: Return v.s
    Case vbvLong, vbvDouble: Return VBStrD(v.n)
    Case vbvBoolean: Return VBStrB(v.n)
    Case vbvDate: Return VBDateStr(v.n)
    End Select
    Return ""
End Function

Private Function RV_ToB(ByRef v As RVar) As Long
    If v.vt = vbvString Then Return VBBoolS(v.s)
    Return RV_ToD(v) <> 0
End Function

Private Function RV_ToDate(ByRef v As RVar) As Double
    Select Case v.vt
    Case vbvString: Return VBDateS(v.s)
    Case vbvEmpty: Return 0
    End Select
    Return v.n
End Function

Private Function RV_Num(ByVal x As Double, ByVal whole As Long) As RVar
    If whole AndAlso x = Int(x) AndAlso Abs(x) < 9e15 Then Return RV_L(x)
    Return RV_D(x)
End Function

Private Function RV_IsWhole(ByRef v As RVar) As Long
    Select Case v.vt
    Case vbvEmpty, vbvLong, vbvBoolean: Return -1
    Case vbvString
        Dim d As Double
        If VBTryNum(v.s, d) Then Return InStr(v.s, ".") = 0 AndAlso InStr(LCase(v.s), "e") = 0 AndAlso d = Int(d)
    End Select
    Return 0
End Function

Private Function RV_Add(ByRef a As RVar, ByRef b As RVar) As RVar
    If a.vt = vbvString AndAlso b.vt = vbvString Then Return RV_S(a.s & b.s)
    If a.vt = vbvDate OrElse b.vt = vbvDate Then Return RV_Dt(RV_ToD(a) + RV_ToD(b))
    If (a.vt = vbvString AndAlso RV_IsNum(a) = 0) OrElse (b.vt = vbvString AndAlso RV_IsNum(b) = 0) Then
        Return RV_S(RV_ToS(a) & RV_ToS(b))
    End If
    Return RV_Num(RV_ToD(a) + RV_ToD(b), RV_IsWhole(a) AndAlso RV_IsWhole(b))
End Function

Private Function RV_Sub(ByRef a As RVar, ByRef b As RVar) As RVar
    If a.vt = vbvDate AndAlso b.vt = vbvDate Then Return RV_D(a.n - b.n)
    If a.vt = vbvDate Then Return RV_Dt(a.n - RV_ToD(b))
    Return RV_Num(RV_ToD(a) - RV_ToD(b), RV_IsWhole(a) AndAlso RV_IsWhole(b))
End Function

Private Function RV_Mul(ByRef a As RVar, ByRef b As RVar) As RVar
    Return RV_Num(RV_ToD(a) * RV_ToD(b), RV_IsWhole(a) AndAlso RV_IsWhole(b))
End Function

Private Function RV_Div(ByRef a As RVar, ByRef b As RVar) As RVar
    Dim d As Double = RV_ToD(b)
    If d = 0 Then VBRaise(11): Return RV_Empty()
    Return RV_Num(RV_ToD(a) / d, -1)
End Function

Private Function RV_IDiv(ByRef a As RVar, ByRef b As RVar) As RVar
    Return RV_L(VBIDiv(RV_ToD(a), RV_ToD(b)))
End Function

Private Function RV_Mod(ByRef a As RVar, ByRef b As RVar) As RVar
    Return RV_L(VBMod(RV_ToD(a), RV_ToD(b)))
End Function

Private Function RV_Pow(ByRef a As RVar, ByRef b As RVar) As RVar
    Return RV_Num(RV_ToD(a) ^ RV_ToD(b), -1)
End Function

Private Function RV_Neg(ByRef a As RVar) As RVar
    Return RV_Num(-RV_ToD(a), RV_IsWhole(a))
End Function

Private Function RV_Cat(ByRef a As RVar, ByRef b As RVar) As RVar
    Return RV_S(RV_ToS(a) & RV_ToS(b))
End Function

' -1 / 0 / 1 like the interpreter's vb_compare
Private Function RV_Cmp(ByRef a As RVar, ByRef b As RVar, ByVal textmode As Long = 0) As Long
    Dim As String x, y
    If a.vt = vbvString AndAlso b.vt = vbvString Then
        x = a.s: y = b.s
        If textmode Then x = VBLCase(x): y = VBLCase(y)
        Return IIf(x < y, -1, IIf(x > y, 1, 0))
    End If
    If (a.vt = vbvEmpty AndAlso b.vt = vbvString) OrElse (b.vt = vbvEmpty AndAlso a.vt = vbvString) Then
        x = RV_ToS(a): y = RV_ToS(b)
        Return IIf(x < y, -1, IIf(x > y, 1, 0))
    End If
    If (a.vt = vbvString AndAlso RV_IsNum(a) = 0) OrElse (b.vt = vbvString AndAlso RV_IsNum(b) = 0) Then
        x = RV_ToS(a): y = RV_ToS(b)
        Return IIf(x < y, -1, IIf(x > y, 1, 0))
    End If
    Dim As Double p = RV_ToD(a), q = RV_ToD(b)
    Return IIf(p < q, -1, IIf(p > q, 1, 0))
End Function

Private Function RV_And(ByRef a As RVar, ByRef b As RVar) As RVar
    If a.vt = vbvBoolean AndAlso b.vt = vbvBoolean Then Return RV_B(a.n <> 0 AndAlso b.n <> 0)
    Return RV_L(CLngInt(RV_ToD(a)) And CLngInt(RV_ToD(b)))
End Function
Private Function RV_Or(ByRef a As RVar, ByRef b As RVar) As RVar
    If a.vt = vbvBoolean AndAlso b.vt = vbvBoolean Then Return RV_B(a.n <> 0 OrElse b.n <> 0)
    Return RV_L(CLngInt(RV_ToD(a)) Or CLngInt(RV_ToD(b)))
End Function
Private Function RV_Xor(ByRef a As RVar, ByRef b As RVar) As RVar
    If a.vt = vbvBoolean AndAlso b.vt = vbvBoolean Then Return RV_B((a.n <> 0) <> (b.n <> 0))
    Return RV_L(CLngInt(RV_ToD(a)) Xor CLngInt(RV_ToD(b)))
End Function
Private Function RV_Not(ByRef a As RVar) As RVar
    If a.vt = vbvBoolean Then Return RV_B(a.n = 0)
    Return RV_L(Not CLngInt(RV_ToD(a)))
End Function

Private Function RV_TypeName(ByRef v As RVar) As String
    Select Case v.vt
    Case vbvEmpty: Return "Empty"
    Case vbvNull: Return "Null"
    Case vbvLong: Return IIf(Abs(v.n) > 32767, "Long", "Integer")
    Case vbvDouble: Return "Double"
    Case vbvDate: Return "Date"
    Case vbvString: Return "String"
    Case vbvBoolean: Return "Boolean"
    Case 9: Return IIf(v.p, "Object", "Nothing")
    End Select
    Return "Variant"
End Function

Private Function RV_VarType(ByRef v As RVar) As Long
    If v.vt = vbvLong AndAlso Abs(v.n) <= 32767 Then Return 2
    Return v.vt
End Function

Private Function RV_IIf(ByVal c As Long, ByRef a As RVar, ByRef b As RVar) As RVar
    If c Then Return a
    Return b
End Function

' ------------------------------------------------------------------------------ Format()
Private Function VBDecRound(ByVal x As Double, ByVal nd As Long) As String
    ' Decimal(repr(abs(x))).quantize(10^-nd, ROUND_HALF_UP) as "123.45"
    x = Abs(x)
    If x = 0 Then
        If nd > 0 Then Return "0." & String(nd, "0")
        Return "0"
    End If
    Dim digits As String
    Dim e As Long
    VBShortest(x, digits, e)
    Dim pnt As Long = e + 1                        ' digits before the decimal point
    If pnt <= 0 Then digits = String(1 - pnt, "0") & digits: pnt = 1
    If Len(digits) < pnt + nd + 1 Then digits &= String(pnt + nd + 1 - Len(digits), "0")
    Dim keep As String = Left(digits, pnt + nd)
    If digits[pnt + nd] >= 53 Then                   ' >= "5": round half up
        Dim i As Long = Len(keep) - 1
        Do
            If i < 0 Then keep = "1" & keep: pnt += 1: Exit Do
            If keep[i] = 57 Then
                keep[i] = 48
                i -= 1
            Else
                keep[i] += 1
                Exit Do
            End If
        Loop
    End If
    Dim ip As String = Left(keep, pnt)
    While Len(ip) > 1 AndAlso ip[0] = 48
        ip = Mid(ip, 2)
    Wend
    If nd > 0 Then Return ip & "." & Mid(keep, pnt + 1, nd)
    Return ip
End Function

Private Function VBFmtSplit(ByRef f As String, secs() As String) As Long
    Dim As String cur
    Dim As Long i = 0, q = 0, n = 0
    ReDim secs(0 To 0)
    While i < Len(f)
        Dim c As String = Chr(f[i])
        If c = """" Then
            q = Not q
        ElseIf c = "\" AndAlso q = 0 AndAlso i + 1 < Len(f) Then
            cur &= Mid(f, i + 1, 2)
            i += 2
            Continue While
        ElseIf c = ";" AndAlso q = 0 Then
            secs(n) = cur
            cur = ""
            n += 1
            ReDim Preserve secs(0 To n)
            i += 1
            Continue While
        End If
        cur &= c
        i += 1
    Wend
    secs(n) = cur
    Return n + 1
End Function

' tokens of a format section: kinds "c" (one character) / "l" (literal text)
Private Function VBFmtTokens(ByRef sec As String, kinds() As String, texts() As String) As Long
    Dim As Long i = 0, n = 0
    ReDim kinds(0 To Len(sec) + 1)
    ReDim texts(0 To Len(sec) + 1)
    While i < Len(sec)
        Dim c As String = Chr(sec[i])
        If c = """" Then
            Dim j As Long = InStr(i + 2, sec, """")
            If j = 0 Then j = Len(sec) + 1
            kinds(n) = "l": texts(n) = Mid(sec, i + 2, j - i - 2): n += 1
            i = j
        ElseIf c = "\" AndAlso i + 1 < Len(sec) Then
            kinds(n) = "l": texts(n) = Mid(sec, i + 2, 1): n += 1
            i += 2
        ElseIf (c = "*" OrElse c = "_") AndAlso i + 1 < Len(sec) Then
            i += 2
        Else
            kinds(n) = "c": texts(n) = c: n += 1
            i += 1
        End If
    Wend
    Return n
End Function

Private Function VBFmtUnquoted(ByRef sec As String) As String
    Dim As String k(), t()
    Dim n As Long = VBFmtTokens(sec, k(), t())
    Dim r As String
    For i As Long = 0 To n - 1
        If k(i) = "c" Then r &= t(i)
    Next
    Return r
End Function

Private Function VBFmtIsDate(ByRef sec As String) As Long
    Dim p As String = LCase(VBFmtUnquoted(sec))
    If InStr(p, Any "0#@&") Then Return 0
    p = VBReplace(VBReplace(p, "am/pm", ""), "a/p", "")
    Return InStr(p, Any "dmyhnswqtc") > 0
End Function

Private Function VBFmtNumSec(ByVal num As Double, ByRef sec As String, ByVal signed As Long) As String
    Dim As String k(), t()
    Dim n As Long = VBFmtTokens(sec, k(), t())
    Dim As Long expAt = -1, i
    For i = 0 To n - 2
        If k(i) = "c" AndAlso (t(i) = "e" OrElse t(i) = "E") AndAlso k(i + 1) = "c" AndAlso (t(i + 1) = "+" OrElse t(i + 1) = "-") Then
            expAt = i
            Exit For
        End If
    Next
    Dim mantEnd As Long = IIf(expAt < 0, n, expAt)
    Dim dotAt As Long = -1
    For i = 0 To mantEnd - 1
        If k(i) = "c" AndAlso t(i) = "." Then dotAt = i: Exit For
    Next
    Dim intEnd As Long = IIf(dotAt < 0, mantEnd, dotAt)
    Dim As String intPh, decPh
    Dim As Long pct = 0, firstPh = -1, lastPh = -1
    For i = 0 To intEnd - 1
        If k(i) = "c" AndAlso (t(i) = "0" OrElse t(i) = "#") Then
            intPh &= t(i)
            If firstPh < 0 Then firstPh = i
            lastPh = i
        End If
    Next
    If dotAt >= 0 Then
        For i = dotAt + 1 To mantEnd - 1
            If k(i) = "c" AndAlso (t(i) = "0" OrElse t(i) = "#") Then decPh &= t(i)
        Next
    End If
    If Len(intPh) = 0 AndAlso Len(decPh) = 0 Then
        Dim r As String
        For i = 0 To n - 1
            r &= t(i)
        Next
        Return r
    End If
    For i = 0 To mantEnd - 1
        If k(i) = "c" AndAlso t(i) = "%" Then pct += 1
    Next
    Dim As Long thousands = 0, scale = 0
    For i = 0 To intEnd - 1
        If k(i) = "c" AndAlso t(i) = "," Then
            If firstPh >= 0 AndAlso firstPh < i AndAlso lastPh >= 0 AndAlso i < lastPh Then
                thousands = -1
            ElseIf lastPh >= 0 AndAlso i > lastPh Then
                scale += 1
            End If
        End If
    Next
    Dim x As Double = num * (100 ^ pct) / (1000 ^ scale)
    Dim nd As Long = Len(decPh)
    Dim expTxt As String
    If expAt >= 0 Then
        Dim eChar As String = t(expAt), eSign As String = t(expAt + 1)
        Dim As Long eZeros = 0
        Dim restLits As String
        For i = expAt + 2 To n - 1
            If k(i) = "c" AndAlso (t(i) = "0" OrElse t(i) = "#") Then
                If t(i) = "0" Then eZeros += 1
            Else
                restLits &= t(i)
            End If
        Next
        Dim lead As Long = IIf(Len(intPh) > 1, Len(intPh), 1)
        Dim ee As Long = 0
        If x <> 0 Then ee = Int(Log(Abs(x)) / Log(10.0) + 1e-12) - (lead - 1)
        Dim mm As Double = IIf(x <> 0, Abs(x) / (10 ^ ee), 0)
        If x <> 0 AndAlso Val(VBDecRound(mm, nd)) >= 10 ^ lead Then ee += 1: mm = Abs(x) / (10 ^ ee)
        x = IIf(x >= 0, mm, -mm)
        Dim es As String = Str(Abs(ee))
        If Len(es) < eZeros Then es = String(eZeros - Len(es), "0") & es
        expTxt = eChar & IIf(ee < 0, "-", IIf(eSign = "+", "+", "")) & es & restLits
    End If
    Dim dtxt As String = VBDecRound(x, nd)
    Dim ip As String, dp As String
    Dim pp As Long = InStr(dtxt, ".")
    If pp Then ip = Left(dtxt, pp - 1): dp = Mid(dtxt, pp + 1) Else ip = dtxt
    Dim isZero As Long = (Val(dtxt) = 0)
    If ip = "0" AndAlso InStr(intPh, "0") = 0 Then ip = ""
    Dim minInt As Long = 0
    For i = 0 To Len(intPh) - 1
        If intPh[i] = 48 Then minInt += 1
    Next
    If Len(ip) < minInt Then ip = String(minInt - Len(ip), "0") & ip
    Dim keep As Long = 0
    For i = 0 To Len(decPh) - 1
        If decPh[i] = 48 Then keep = i + 1
    Next
    dp = Left(dp, nd)
    While Len(dp) > keep AndAlso Right(dp, 1) = "0"
        dp = Left(dp, Len(dp) - 1)
    Wend
    Dim r As String
    Dim L As Long = Len(ip)
    Dim nInt As Long = Len(intPh)
    Dim kph As Long = 0
    #define VBDIGIT(rr) (Mid(ip, L - (rr), 1) & IIf(thousands AndAlso (rr) > 0 AndAlso ((rr) Mod 3) = 0, ",", ""))
    For i = 0 To intEnd - 1
        If k(i) = "c" AndAlso (t(i) = "0" OrElse t(i) = "#") Then
            Dim rpos As Long = nInt - 1 - kph
            If kph = 0 AndAlso L > nInt Then
                For rr As Long = L - 1 To nInt Step -1
                    r &= VBDIGIT(rr)
                Next
            End If
            If rpos < L Then r &= VBDIGIT(rpos)
            kph += 1
        ElseIf k(i) = "c" AndAlso t(i) = "," Then
        Else
            r &= t(i)
        End If
    Next
    If nInt = 0 AndAlso L > 0 Then
        Dim pre As String
        For rr As Long = L - 1 To 0 Step -1
            pre &= VBDIGIT(rr)
        Next
        r = pre & r
    End If
    If dotAt >= 0 Then
        r &= "."
        Dim j As Long = 0
        For i = dotAt + 1 To mantEnd - 1
            If k(i) = "c" AndAlso (t(i) = "0" OrElse t(i) = "#") Then
                If j < Len(dp) Then r &= Mid(dp, j + 1, 1)
                j += 1
            ElseIf k(i) = "c" AndAlso t(i) = "," Then
            Else
                r &= t(i)
            End If
        Next
    End If
    r &= expTxt
    If signed AndAlso x < 0 AndAlso (isZero = 0 OrElse expAt >= 0) Then r = "-" & r
    Return r
End Function

Private Function VBFmtNumber(ByVal x As Double, ByRef f As String) As String
    Dim secs() As String
    Dim n As Long = VBFmtSplit(f, secs())
    If x = 0 AndAlso n > 2 AndAlso Len(secs(2)) Then Return VBFmtNumSec(0, secs(2), 0)
    If x < 0 AndAlso n > 1 AndAlso Len(secs(1)) Then Return VBFmtNumSec(-x, secs(1), 0)
    Return VBFmtNumSec(x, secs(0), -1)
End Function

Private Function VBFmtDate(ByVal dt As Double, ByRef f As String) As String
    Dim As Long y, mo, d, h, mi, s
    VBDateParts(dt, y, mo, d, h, mi, s)
    ' tokens: kind l (literal), a (am/pm pattern), c (run of one letter)
    Dim kinds(0 To Len(f) + 1) As String
    Dim texts(0 To Len(f) + 1) As String
    Dim As Long i = 0, n = 0, hasAmpm = 0
    While i < Len(f)
        Dim c As String = Chr(f[i])
        If c = """" Then
            Dim j As Long = InStr(i + 2, f, """")
            If j = 0 Then j = Len(f) + 1
            kinds(n) = "l": texts(n) = Mid(f, i + 2, j - i - 2): n += 1
            i = j
            Continue While
        End If
        If c = "\" AndAlso i + 1 < Len(f) Then
            kinds(n) = "l": texts(n) = Mid(f, i + 2, 1): n += 1
            i += 2
            Continue While
        End If
        Dim matched As String
        If Mid(f, i + 1, 5) = "AM/PM" OrElse Mid(f, i + 1, 5) = "am/pm" Then
            matched = Mid(f, i + 1, 5)
        ElseIf Mid(f, i + 1, 3) = "A/P" OrElse Mid(f, i + 1, 3) = "a/p" Then
            matched = Mid(f, i + 1, 3)
        ElseIf UCase(Mid(f, i + 1, 4)) = "AMPM" Then
            matched = "AMPM"
        End If
        If Len(matched) Then
            kinds(n) = "a": texts(n) = matched: n += 1
            hasAmpm = -1
            i += Len(matched)
            Continue While
        End If
        Dim lc As Long = Asc(LCase(c))
        If lc >= 97 AndAlso lc <= 122 Then
            Dim j As Long = i
            While j < Len(f) AndAlso Asc(LCase(Chr(f[j]))) = lc
                j += 1
            Wend
            kinds(n) = "c": texts(n) = Mid(f, i + 1, j - i): n += 1
            i = j
        Else
            kinds(n) = "l": texts(n) = c: n += 1
            i += 1
        End If
    Wend
    Dim hour12 As Long = IIf(hasAmpm, IIf(h Mod 12 = 0, 12, h Mod 12), h)
    Dim r As String
    For i = 0 To n - 1
        If kinds(i) = "l" Then r &= texts(i): Continue For
        If kinds(i) = "a" Then
            Dim am As Long = h < 12
            Select Case texts(i)
            Case "AM/PM", "AMPM": r &= IIf(am, "AM", "PM")
            Case "am/pm": r &= IIf(am, "am", "pm")
            Case "A/P": r &= IIf(am, "A", "P")
            Case Else: r &= IIf(am, "a", "p")
            End Select
            Continue For
        End If
        Dim low As String = LCase(texts(i))
        Dim ln As Long = Len(low)
        Select Case low[0]
        Case Asc("m")
            Dim As String prv, nxt
            For j As Long = i - 1 To 0 Step -1
                If kinds(j) = "c" Then prv = LCase(texts(j)): Exit For
            Next
            For j As Long = i + 1 To n - 1
                If kinds(j) = "c" Then nxt = LCase(texts(j)): Exit For
            Next
            If ln <= 2 AndAlso (Left(prv, 1) = "h" OrElse Left(nxt, 1) = "s") Then
                r &= IIf(ln = 2, VB2(mi), Str(mi))
            ElseIf ln = 1 Then
                r &= Str(mo)
            ElseIf ln = 2 Then
                r &= VB2(mo)
            Else
                r &= VBMonthName(mo, ln = 3)
            End If
        Case Asc("d")
            Select Case ln
            Case 1: r &= Str(d)
            Case 2: r &= VB2(d)
            Case 3: r &= VBWeekdayName(VBWeekday(dt), -1)
            Case 4: r &= VBWeekdayName(VBWeekday(dt))
            Case 5: r &= VBFmtDate(dt, "dd/mm/yyyy")
            Case Else: r &= VBFmtDate(dt, "dddd, d mmmm yyyy")
            End Select
        Case Asc("y")
            If ln = 1 Then
                r &= Str(VBDayOfYear(dt))
            ElseIf ln = 2 Then
                r &= VB2(y Mod 100)
            Else
                r &= Str(y)
            End If
        Case Asc("h"): r &= IIf(ln = 1, Str(hour12), VB2(hour12))
        Case Asc("n"): r &= IIf(ln = 1, Str(mi), VB2(mi))
        Case Asc("s"): r &= IIf(ln = 1, Str(s), VB2(s))
        Case Asc("w")
            If ln = 1 Then r &= Str(VBWeekday(dt)) Else r &= Str(VBDatePart("ww", dt))
        Case Asc("q"): r &= Str((mo - 1) \ 3 + 1)
        Case Asc("t")
            If ln = 5 Then r &= VBFmtDate(dt, "hh:nn:ss") Else r &= texts(i)
        Case Asc("c")
            If ln = 1 Then
                If h = 0 AndAlso mi = 0 AndAlso s = 0 Then
                    r &= VBFmtDate(dt, "dd/mm/yyyy")
                ElseIf Int(dt) = 0 Then
                    r &= VBFmtDate(dt, "hh:nn:ss")
                Else
                    r &= VBFmtDate(dt, "dd/mm/yyyy hh:nn:ss")
                End If
            Else
                r &= texts(i)
            End If
        Case Else
            r &= texts(i)
        End Select
    Next
    Return r
End Function

Private Function VBGeneralDate(ByVal dt As Double) As String
    If dt = Int(dt) Then Return VBFmtDate(dt, "dd/mm/yyyy")
    If Int(dt) = 0 Then Return VBFmtDate(dt, "hh:nn:ss")
    Return VBFmtDate(dt, "dd/mm/yyyy hh:nn:ss")
End Function

Private Function VBFmtString(ByRef s0 As String, ByRef f As String) As String
    Dim secs() As String
    Dim ns As Long = VBFmtSplit(f, secs())
    Dim sec As String = IIf(Len(s0) <> 0 OrElse ns < 2, secs(0), secs(1))
    Dim As String k(), t()
    Dim n As Long = VBFmtTokens(sec, k(), t())
    Dim As Long upper_ = 0, lower_ = 0, ltr = 0, nph = 0, i
    For i = 0 To n - 1
        If k(i) = "c" Then
            Select Case t(i)
            Case ">": upper_ = -1
            Case "<": lower_ = -1
            Case "!": ltr = -1
            Case "@", "&": nph += 1
            End Select
        End If
    Next
    Dim s As String = s0
    If upper_ Then s = VBUCase(s) Else If lower_ Then s = VBLCase(s)
    Dim r As String
    If nph = 0 Then
        r = s
        For i = 0 To n - 1
            If Not (k(i) = "c" AndAlso (t(i) = "<" OrElse t(i) = ">" OrElse t(i) = "!")) Then r &= t(i)
        Next
        Return r
    End If
    Dim total As Long = VBLen(s)
    Dim fill(0 To n) As String
    Dim has(0 To n) As Long
    Dim As String before, after
    If ltr Then
        Dim pos_ As Long = 1
        For i = 0 To n - 1
            If k(i) = "c" AndAlso (t(i) = "@" OrElse t(i) = "&") Then
                If pos_ <= total Then fill(i) = VBMid(s, pos_, 1): has(i) = -1
                pos_ += 1
            End If
        Next
        If pos_ <= total Then after = VBMid(s, pos_)
    Else
        Dim pos_ As Long = total
        For i = n - 1 To 0 Step -1
            If k(i) = "c" AndAlso (t(i) = "@" OrElse t(i) = "&") Then
                If pos_ >= 1 Then fill(i) = VBMid(s, pos_, 1): has(i) = -1
                pos_ -= 1
            End If
        Next
        If pos_ >= 1 Then before = VBLeft(s, pos_)
    End If
    r = before
    For i = 0 To n - 1
        If k(i) = "c" AndAlso (t(i) = "@" OrElse t(i) = "&") Then
            If has(i) Then r &= fill(i) Else If t(i) = "@" Then r &= " "
        ElseIf k(i) = "c" AndAlso (t(i) = "<" OrElse t(i) = ">" OrElse t(i) = "!") Then
        Else
            r &= t(i)
        End If
    Next
    Return r & after
End Function

Private Function VBFormat(ByRef v As RVar, ByRef f As String = "") As String
    Dim low As String = LCase(Trim(f))
    If v.vt = vbvNull Then
        Dim secs() As String
        Dim ns As Long = VBFmtSplit(f, secs())
        If ns > 3 Then Return secs(3)
    End If
    If v.vt = vbvEmpty AndAlso Len(f) = 0 Then Return ""
    If v.vt = vbvDate Then
        If Len(f) = 0 OrElse low = "general date" Then Return VBGeneralDate(v.n)
        Select Case low
        Case "long date": Return VBFmtDate(v.n, "dddd, d mmmm yyyy")
        Case "medium date": Return VBFmtDate(v.n, "dd-mmm-yy")
        Case "short date": Return VBFmtDate(v.n, "dd/mm/yyyy")
        Case "long time": Return VBFmtDate(v.n, "hh:nn:ss")
        Case "medium time": Return VBFmtDate(v.n, "hh:nn AM/PM")
        Case "short time": Return VBFmtDate(v.n, "hh:nn")
        End Select
        Dim secs() As String
        VBFmtSplit(f, secs())
        If VBFmtIsDate(secs(0)) Then Return VBFmtDate(v.n, f)
    End If
    If Len(f) = 0 Then Return RV_ToS(v)
    If low = "yes/no" OrElse low = "true/false" OrElse low = "on/off" Then
        Dim isOn As Long
        If RV_IsNum(v) OrElse v.vt = vbvDate Then isOn = RV_ToD(v) <> 0 Else isOn = Len(RV_ToS(v)) > 0
        Select Case low
        Case "yes/no": Return IIf(isOn, "Yes", "No")
        Case "true/false": Return IIf(isOn, "True", "False")
        Case Else: Return IIf(isOn, "On", "Off")
        End Select
    End If
    If low = "general number" Then Return VBStrD(RV_ToD(v))
    Dim named As String
    Select Case low
    Case "currency": named = "#,##0.00;(#,##0.00)"
    Case "fixed": named = "0.00"
    Case "standard": named = "#,##0.00"
    Case "percent": named = "0.00%"
    Case "scientific": named = "0.00E+00"
    End Select
    If Len(named) Then
        If RV_IsNum(v) = 0 AndAlso v.vt <> vbvDate AndAlso v.vt <> vbvEmpty Then Return RV_ToS(v)
        Return VBFmtNumber(RV_ToD(v), named)
    End If
    Select Case low
    Case "long date", "medium date", "short date", "long time", "medium time", "short time", "general date"
        Dim dt As Double = RV_ToDate(v)
        Return VBFormat(RV_Dt(dt), f)
    End Select
    Dim secs() As String
    VBFmtSplit(f, secs())
    Dim plain As String = VBFmtUnquoted(secs(0))
    Dim hasDigits As Long = InStr(plain, Any "0#") > 0
    If v.vt = vbvString AndAlso InStr(plain, Any "@&<>!") > 0 AndAlso hasDigits = 0 Then Return VBFmtString(v.s, f)
    If VBFmtIsDate(secs(0)) Then
        Dim dv As Double
        If v.vt = vbvString Then
            If VBTryDate(v.s, dv) = 0 Then Return RV_ToS(v)
        Else
            dv = RV_ToD(v)
        End If
        Return VBFmtDate(dv, f)
    End If
    If InStr(plain, Any "@&") > 0 AndAlso hasDigits = 0 Then Return VBFmtString(RV_ToS(v), f)
    If RV_IsNum(v) = 0 AndAlso v.vt <> vbvEmpty AndAlso v.vt <> vbvDate Then Return RV_ToS(v)
    Return VBFmtNumber(RV_ToD(v), f)
End Function

Private Function VBFormatNumber(ByVal x As Double, ByVal nd As Long = 2) As String
    Return VBFmtNumber(x, "#,##0" & IIf(nd > 0, "." & String(nd, "0"), ""))
End Function

' ------------------------------------------------------------------------------ Debug.Print / console
Dim Shared vbDebugPending As String
Private Sub VBDebugOut(ByRef s As String, ByVal newline As Long = -1)
    If newline = 0 Then vbDebugPending &= s: Exit Sub
    Dim t As String = vbDebugPending & s & Chr(13, 10)
    vbDebugPending = ""
    Dim h As HANDLE = GetStdHandle(STD_OUTPUT_HANDLE)
    If h <> 0 AndAlso h <> INVALID_HANDLE_VALUE Then
        Dim written As DWORD
        WriteFile(h, StrPtr(t), Len(t), @written, 0)
    End If
End Sub

Private Function VBTabTo(ByRef sofar As String, ByVal col As Long) As String
    ' Tab(n) inside Debug.Print (n < 1 = next 14-column zone)
    Dim nl As Long = InStrRev(sofar, Chr(10))
    Dim c As Long = VBLen(vbDebugPending) + VBLen(Mid(sofar, nl + 1))
    If col < 1 Then Return Space(14 - (c Mod 14))
    If col - 1 - c > 0 Then Return Space(col - 1 - c)
    Return ""
End Function

' ------------------------------------------------------------------------------ text files (Open / Print # / Input #)
Type VBFile
    used As Long
    mode As Long          ' 1 input, 2 output, 3 append
    h As HANDLE
    text As String        ' input: the whole file (\r\n -> \n)
    pos_ As Long          ' input: 0-based byte position
    col As Long           ' output: current column (Print zones)
End Type
Dim Shared vbFiles(1 To 511) As VBFile

Private Function VBAnsiToUtf8(ByRef s As String) As String
    Dim n As Long = MultiByteToWideChar(CP_ACP, 0, StrPtr(s), Len(s), 0, 0)
    Dim w As WString Ptr = Allocate((n + 1) * 2)
    MultiByteToWideChar(CP_ACP, 0, StrPtr(s), Len(s), w, n)
    Function = VBFromWide(w, n)
    Deallocate(w)
End Function

Private Function VBFullPath(ByRef p As String) As String
    Return p
End Function

Private Sub VBOpen(ByRef path As String, ByVal mode As Long, ByVal num As Long)
    If num < 1 OrElse num > 511 Then VBRaise(52): Exit Sub
    If vbFiles(num).used Then VBRaise(55): Exit Sub
    Dim w As WString Ptr = VBWide(path)
    Dim h As HANDLE
    Select Case mode
    Case 1: h = CreateFileW(w, GENERIC_READ, FILE_SHARE_READ Or FILE_SHARE_WRITE, 0, OPEN_EXISTING, 0, 0)
    Case 2: h = CreateFileW(w, GENERIC_WRITE, FILE_SHARE_READ, 0, CREATE_ALWAYS, 0, 0)
    Case Else: h = CreateFileW(w, GENERIC_WRITE, FILE_SHARE_READ, 0, OPEN_ALWAYS, 0, 0)
    End Select
    Deallocate(w)
    If h = INVALID_HANDLE_VALUE Then
        Dim e As DWORD = GetLastError()
        If e = ERROR_FILE_NOT_FOUND Then
            VBRaise(53)
        ElseIf e = ERROR_PATH_NOT_FOUND Then
            VBRaise(76)
        ElseIf e = ERROR_ACCESS_DENIED OrElse e = ERROR_SHARING_VIOLATION Then
            VBRaise(70)
        Else
            VBRaise(75)
        End If
        Exit Sub
    End If
    With vbFiles(num)
        .used = -1: .mode = mode: .h = h: .pos_ = 0: .col = 0: .text = ""
        If mode = 1 Then
            Dim size As DWORD = GetFileSize(h, 0)
            Dim raw As String = Space(size)
            Dim got As DWORD
            If size > 0 Then ReadFile(h, StrPtr(raw), size, @got, 0)
            CloseHandle(h)
            .h = 0
            If Len(raw) >= 3 AndAlso raw[0] = &hEF AndAlso raw[1] = &hBB AndAlso raw[2] = &hBF Then raw = Mid(raw, 4)
            If MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, StrPtr(raw), Len(raw), 0, 0) = 0 AndAlso Len(raw) > 0 Then
                raw = VBAnsiToUtf8(raw)
            End If
            .text = VBReplace(raw, Chr(13, 10), Chr(10))
        ElseIf mode = 3 Then
            SetFilePointer(h, 0, 0, FILE_END)
        End If
    End With
End Sub

Private Function VBFileOk(ByVal num As Long) As Long
    If num < 1 OrElse num > 511 Then VBRaise(52): Return 0
    If vbFiles(num).used = 0 Then VBRaise(52): Return 0
    Return -1
End Function

Private Sub VBClose(ByVal num As Long)
    If num < 1 OrElse num > 511 Then Exit Sub
    With vbFiles(num)
        If .used = 0 Then Exit Sub
        If .h Then CloseHandle(.h)
        .used = 0: .h = 0: .text = ""
    End With
End Sub

Private Sub VBCloseAll()
    For i As Long = 1 To 511
        VBClose(i)
    Next
End Sub

Private Function VBFreeFile() As Long
    For i As Long = 1 To 511
        If vbFiles(i).used = 0 Then Return i
    Next
    VBRaise(67)
    Return 0
End Function

Private Sub VBFWrite(ByVal num As Long, ByRef s As String)
    If VBFileOk(num) = 0 Then Exit Sub
    With vbFiles(num)
        If .mode = 1 Then VBRaise(54): Exit Sub
        Dim t As String = VBReplace(VBReplace(s, Chr(13, 10), Chr(10)), Chr(10), Chr(13, 10))
        Dim written As DWORD
        If Len(t) Then WriteFile(.h, StrPtr(t), Len(t), @written, 0)
        Dim nl As Long = InStrRev(s, Chr(10))
        If nl Then .col = VBLen(Mid(s, nl + 1)) Else .col += VBLen(s)
    End With
End Sub

Private Sub VBFZone(ByVal num As Long)
    If VBFileOk(num) = 0 Then Exit Sub
    VBFWrite(num, Space(14 - vbFiles(num).col Mod 14))
End Sub

Private Sub VBFTab(ByVal num As Long, ByVal col As Long)
    If VBFileOk(num) = 0 Then Exit Sub
    col = IIf(col < 1, 0, col - 1)
    If col < vbFiles(num).col Then VBFWrite(num, Chr(10))
    VBFWrite(num, Space(col - vbFiles(num).col))
End Sub

' Print # numbers: leading space for the sign and a trailing space
Private Function VBPrintNum(ByVal x As Double) As String
    Dim s As String = VBStrD(x)
    Return IIf(Left(s, 1) = "-", s, " " & s) & " "
End Function

Private Function VBPrintV(ByRef v As RVar) As String
    Select Case v.vt
    Case vbvLong, vbvDouble: Return VBPrintNum(v.n)
    Case vbvNull: Return "Null"
    End Select
    Return RV_ToS(v)
End Function

' Write # field
Private Function VBWriteS(ByRef s As String) As String
    Return """" & s & """"
End Function
Private Function VBWriteDate(ByVal dt As Double) As String
    Dim As Long y, m, d, h, n, s
    VBDateParts(dt, y, m, d, h, n, s)
    Dim r As String = "#" & Str(y) & "-" & VB2(m) & "-" & VB2(d)
    If h <> 0 OrElse n <> 0 OrElse s <> 0 OrElse Int(dt) = 0 Then r &= " " & VB2(h) & ":" & VB2(n) & ":" & VB2(s)
    Return r & "#"
End Function
Private Function VBWriteV(ByRef v As RVar) As String
    Select Case v.vt
    Case vbvBoolean: Return IIf(v.n, "#TRUE#", "#FALSE#")
    Case vbvLong, vbvDouble: Return VBStrD(v.n)
    Case vbvDate: Return VBWriteDate(v.n)
    Case vbvNull: Return "#NULL#"
    Case vbvEmpty: Return ""
    End Select
    Return VBWriteS(v.s)
End Function

Private Function VBFInputReady(ByVal num As Long) As Long
    If VBFileOk(num) = 0 Then Return 0
    If vbFiles(num).mode <> 1 Then VBRaise(54): Return 0
    Return -1
End Function

Private Function VBLineInput(ByVal num As Long) As String
    If VBFInputReady(num) = 0 Then Return ""
    With vbFiles(num)
        If .pos_ >= Len(.text) Then VBRaise(62): Return ""
        Dim e As Long = InStr(.pos_ + 1, .text, Chr(10))
        If e = 0 Then e = Len(.text) + 1
        Function = Mid(.text, .pos_ + 1, e - .pos_ - 1)
        .pos_ = e
    End With
End Function

' next Input # field; quoted tells whether it was "quoted"
Private Function VBInputField(ByVal num As Long, ByRef quoted As Long) As String
    quoted = 0
    If VBFInputReady(num) = 0 Then Return ""
    With vbFiles(num)
        Dim t As String Ptr = @.text
        Dim n As Long = Len(.text)
        While .pos_ < n AndAlso ((*t)[.pos_] = 32 OrElse (*t)[.pos_] = 9 OrElse (*t)[.pos_] = 10)
            .pos_ += 1
        Wend
        If .pos_ >= n Then VBRaise(62): Return ""
        If (*t)[.pos_] = 34 Then
            Dim e As Long = InStr(.pos_ + 2, .text, """")
            If e = 0 Then e = n + 1
            Function = Mid(.text, .pos_ + 2, e - .pos_ - 2)
            .pos_ = e
            While .pos_ < n AndAlso ((*t)[.pos_] = 32 OrElse (*t)[.pos_] = 9)
                .pos_ += 1
            Wend
            If .pos_ < n AndAlso ((*t)[.pos_] = 44 OrElse (*t)[.pos_] = 10) Then .pos_ += 1
            quoted = -1
            Exit Function
        End If
        Dim e As Long = .pos_
        While e < n AndAlso (*t)[e] <> 44 AndAlso (*t)[e] <> 10
            e += 1
        Wend
        Function = Trim(Mid(.text, .pos_ + 1, e - .pos_))
        .pos_ = e + 1
    End With
End Function

Private Function VBFieldNum(ByRef s As String) As Double
    If Len(s) = 0 Then Return 0
    If UCase(s) = "#TRUE#" Then Return -1
    If UCase(s) = "#FALSE#" Then Return 0
    Return VBNumS(s)
End Function

Private Function VBFieldV(ByRef s As String, ByVal quoted As Long) As RVar
    If quoted Then Return RV_S(s)
    Dim u As String = UCase(s)
    If u = "#TRUE#" Then Return RV_B(-1)
    If u = "#FALSE#" Then Return RV_B(0)
    If u = "#NULL#" Then Return RV_Null()
    If Len(s) = 0 Then Return RV_Empty()
    If Len(s) > 2 AndAlso Left(s, 1) = "#" AndAlso Right(s, 1) = "#" Then
        Dim dv As Double
        Dim inner As String = Mid(s, 2, Len(s) - 2)
        If Mid(inner, 5, 1) = "-" Then
            Dim dd As Double = VBDateSerial(ValInt(Left(inner, 4)), ValInt(Mid(inner, 6, 2)), ValInt(Mid(inner, 9, 2)))
            If Len(inner) >= 19 Then dd += VBTimeSerial(ValInt(Mid(inner, 12, 2)), ValInt(Mid(inner, 15, 2)), ValInt(Mid(inner, 18, 2)))
            Return RV_Dt(dd)
        End If
        Return RV_S(s)
    End If
    Dim v As Double
    If VBTryNum(s, v) Then Return RV_Num(v, InStr(s, ".") = 0 AndAlso InStr(LCase(s), "e") = 0)
    Return RV_S(s)
End Function

Private Function VBInputChars(ByVal n As Long, ByVal num As Long) As String
    If VBFInputReady(num) = 0 Then Return ""
    With vbFiles(num)
        Dim rest As String = Mid(.text, .pos_ + 1)
        If VBLen(rest) < n Then VBRaise(62): Return ""
        Function = VBLeft(rest, n)
        .pos_ += VBU8Off(rest, n)
    End With
End Function

Private Function VBEOF(ByVal num As Long) As Long
    If VBFileOk(num) = 0 Then Return -1
    With vbFiles(num)
        If .mode = 1 Then Return .pos_ >= Len(.text)
    End With
    Return -1
End Function

Private Function VBLOF(ByVal num As Long) As Long
    If VBFileOk(num) = 0 Then Return 0
    With vbFiles(num)
        If .mode = 1 Then Return Len(.text)
        Return GetFileSize(.h, 0)
    End With
End Function

' ------------------------------------------------------------------------------ file system
Private Sub VBFileErr()
    Dim e As DWORD = GetLastError()
    Select Case e
    Case ERROR_FILE_NOT_FOUND: VBRaise(53)
    Case ERROR_PATH_NOT_FOUND: VBRaise(76)
    Case ERROR_ACCESS_DENIED, ERROR_SHARING_VIOLATION: VBRaise(70)
    Case ERROR_ALREADY_EXISTS, ERROR_FILE_EXISTS: VBRaise(58)
    Case Else: VBRaise(75)
    End Select
End Sub

Private Sub VBKill(ByRef p As String)
    Dim w As WString Ptr = VBWide(p)
    If DeleteFileW(w) = 0 Then VBFileErr()
    Deallocate(w)
End Sub

Private Sub VBMkDir(ByRef p As String)
    Dim w As WString Ptr = VBWide(p)
    If CreateDirectoryW(w, 0) = 0 Then VBFileErr()
    Deallocate(w)
End Sub

Private Sub VBRmDir(ByRef p As String)
    Dim w As WString Ptr = VBWide(p)
    If RemoveDirectoryW(w) = 0 Then VBFileErr()
    Deallocate(w)
End Sub

Private Sub VBChDir(ByRef p As String)
    Dim w As WString Ptr = VBWide(p)
    If SetCurrentDirectoryW(w) = 0 Then VBFileErr()
    Deallocate(w)
End Sub

Private Function VBCurDir() As String
    Dim buf As WString * 1024
    GetCurrentDirectoryW(1024, @buf)
    Return VBFromWide(@buf)
End Function

Private Sub VBFileCopy(ByRef a As String, ByRef b As String)
    Dim As WString Ptr wa = VBWide(a), wb = VBWide(b)
    If CopyFileW(wa, wb, 0) = 0 Then VBFileErr()
    Deallocate(wa): Deallocate(wb)
End Sub

Private Sub VBName(ByRef a As String, ByRef b As String)
    Dim As WString Ptr wa = VBWide(a), wb = VBWide(b)
    If MoveFileW(wa, wb) = 0 Then VBFileErr()
    Deallocate(wa): Deallocate(wb)
End Sub

Private Function VBFileLen(ByRef p As String) As LongInt
    Dim w As WString Ptr = VBWide(p)
    Dim fa As WIN32_FILE_ATTRIBUTE_DATA
    Dim ok As Long = GetFileAttributesExW(w, GetFileExInfoStandard, @fa)
    Deallocate(w)
    If ok = 0 Then VBRaise(53): Return 0
    Return (CLngInt(fa.nFileSizeHigh) Shl 32) Or fa.nFileSizeLow
End Function

Dim Shared vbDirHandle As HANDLE
Dim Shared vbDirAttr As Long
Private Function VBDirNext() As String
    Dim fd As WIN32_FIND_DATAW
    Do
        If vbDirHandle = 0 OrElse vbDirHandle = INVALID_HANDLE_VALUE Then Return ""
        If FindNextFileW(vbDirHandle, @fd) = 0 Then FindClose(vbDirHandle): vbDirHandle = 0: Return ""
        Dim nm As String = VBFromWide(@fd.cFileName)
        If nm = "." OrElse nm = ".." Then Continue Do
        If (fd.dwFileAttributes And FILE_ATTRIBUTE_DIRECTORY) AndAlso (vbDirAttr And 16) = 0 Then Continue Do
        If (fd.dwFileAttributes And FILE_ATTRIBUTE_HIDDEN) AndAlso (vbDirAttr And 2) = 0 Then Continue Do
        Return nm
    Loop
End Function

Private Function VBDir(ByRef pattern As String, ByVal attr As Long = 0) As String
    If vbDirHandle <> 0 AndAlso vbDirHandle <> INVALID_HANDLE_VALUE Then FindClose(vbDirHandle)
    vbDirAttr = attr
    Dim fd As WIN32_FIND_DATAW
    Dim w As WString Ptr = VBWide(pattern)
    vbDirHandle = FindFirstFileW(w, @fd)
    Deallocate(w)
    If vbDirHandle = INVALID_HANDLE_VALUE Then vbDirHandle = 0: Return ""
    Dim nm As String = VBFromWide(@fd.cFileName)
    If nm = "." OrElse nm = ".." OrElse ((fd.dwFileAttributes And FILE_ATTRIBUTE_DIRECTORY) AndAlso (attr And 16) = 0) _
       OrElse ((fd.dwFileAttributes And FILE_ATTRIBUTE_HIDDEN) AndAlso (attr And 2) = 0) Then Return VBDirNext()
    Return nm
End Function

Private Function VBEnviron(ByRef nm As String) As String
    Dim w As WString Ptr = VBWide(nm)
    Dim buf As WString * 4096
    Dim n As Long = GetEnvironmentVariableW(w, @buf, 4096)
    Deallocate(w)
    If n = 0 OrElse n > 4096 Then Return ""
    Return VBFromWide(@buf, n)
End Function

Private Function VBCommand() As String
    Return VBEnviron("RAD_COMMAND")
End Function

Private Function VBShell(ByRef cmd As String, ByVal style As Long = 1) As Long
    Dim si As STARTUPINFOW
    Dim pi As PROCESS_INFORMATION
    si.cb = SizeOf(si)
    si.dwFlags = STARTF_USESHOWWINDOW
    si.wShowWindow = IIf(style = 0, SW_HIDE, SW_SHOWNORMAL)
    Dim w As WString Ptr = VBWide(cmd)
    Dim ok As Long = CreateProcessW(0, w, 0, 0, 0, 0, 0, 0, @si, @pi)
    Deallocate(w)
    If ok = 0 Then VBRaise(53): Return 0
    CloseHandle(pi.hThread)
    CloseHandle(pi.hProcess)
    Return pi.dwProcessId
End Function

' ------------------------------------------------------------------------------ Split / Join
Private Sub VBSplit(ByRef s As String, ByRef d As String, arr() As String, ByVal limit As Long = -1)
    Dim As Long n = 0, i = 1, p
    If Len(d) = 0 Then
        ReDim arr(0 To 0)
        arr(0) = s
        Exit Sub
    End If
    ReDim arr(0 To 15)
    Do
        p = InStr(i, s, d)
        If p = 0 OrElse (limit > 0 AndAlso n = limit - 1) Then Exit Do
        If n > UBound(arr) Then ReDim Preserve arr(0 To n * 2)
        arr(n) = Mid(s, i, p - i)
        n += 1
        i = p + Len(d)
    Loop
    If n > UBound(arr) Then ReDim Preserve arr(0 To n)
    arr(n) = Mid(s, i)
    ReDim Preserve arr(0 To n)
End Sub

Private Function VBJoin(arr() As String, ByRef d As String = " ") As String
    Dim r As String
    For i As Long = LBound(arr) To UBound(arr)
        If i > LBound(arr) Then r &= d
        r &= arr(i)
    Next
    Return r
End Function

Private Function VBJoinV(arr() As RVar, ByRef d As String = " ") As String
    Dim r As String
    For i As Long = LBound(arr) To UBound(arr)
        If i > LBound(arr) Then r &= d
        r &= RV_ToS(arr(i))
    Next
    Return r
End Function

' ------------------------------------------------------------------------------ Like
Private Function VBLikeAt(ByRef s As String, ByVal i As Long, ByRef p As String, ByVal j As Long) As Long
    While j < Len(p)
        Dim c As Long = p[j]
        If c = 42 Then                                       ' *
            For k As Long = Len(s) To i Step -1
                If VBLikeAt(s, k, p, j + 1) Then Return -1
            Next
            Return 0
        End If
        If i >= Len(s) Then Return 0
        If c = 63 Then                                       ' ?
            i += 1
            While i < Len(s) AndAlso (s[i] And &hC0) = &h80
                i += 1
            Wend
            j += 1
        ElseIf c = 35 Then                                   ' #
            If s[i] < 48 OrElse s[i] > 57 Then Return 0
            i += 1: j += 1
        ElseIf c = 91 Then                                   ' [...]
            Dim e As Long = InStr(j + 1, p, "]")
            If e = 0 Then Return 0
            Dim body As String = Mid(p, j + 2, e - j - 2)
            Dim neg As Long = 0
            If Left(body, 1) = "!" Then neg = -1: body = Mid(body, 2)
            Dim ch As Long = s[i]
            Dim hit As Long = 0
            Dim q As Long = 0
            While q < Len(body)
                If q + 2 < Len(body) AndAlso body[q + 1] = 45 Then
                    If ch >= body[q] AndAlso ch <= body[q + 2] Then hit = -1
                    q += 3
                Else
                    If ch = body[q] Then hit = -1
                    q += 1
                End If
            Wend
            If hit = neg Then Return 0
            i += 1
            j = e
        Else
            If s[i] <> c Then Return 0
            i += 1: j += 1
        End If
    Wend
    Return i = Len(s)
End Function

Private Function VBLike(ByRef s As String, ByRef p As String) As Long
    Return VBLikeAt(s, 0, p, 0)
End Function

' ------------------------------------------------------------------------------ Collection
Type VBCollection
    count As Long
    items(Any) As RVar
    keys(Any) As String
End Type

Private Function VBColIndex(ByRef c As VBCollection, ByRef k As RVar) As Long   ' 0-based, -1 = error raised
    If k.vt = vbvString Then
        Dim lk As String = LCase(k.s)
        For i As Long = 0 To c.count - 1
            If c.keys(i) = lk AndAlso Len(lk) > 0 Then Return i
        Next
        VBRaise(5)
        Return -1
    End If
    Dim i As Long = CLng(RV_ToD(k))
    If i < 1 OrElse i > c.count Then VBRaise(9): Return -1
    Return i - 1
End Function

Private Sub VBColAdd(ByRef c As VBCollection, ByRef item As RVar, ByRef key As String, _
                     ByRef before As RVar, ByRef after As RVar)
    Dim lk As String = LCase(key)
    If Len(lk) Then
        For i As Long = 0 To c.count - 1
            If c.keys(i) = lk Then VBRaise(457): Exit Sub
        Next
    End If
    Dim at As Long = c.count
    If before.vt <> vbvEmpty Then
        at = VBColIndex(c, before)
        If at < 0 Then Exit Sub
    ElseIf after.vt <> vbvEmpty Then
        at = VBColIndex(c, after)
        If at < 0 Then Exit Sub
        at += 1
    End If
    If c.count = 0 Then
        ReDim c.items(0 To 7)
        ReDim c.keys(0 To 7)
    ElseIf c.count > UBound(c.items) Then
        ReDim Preserve c.items(0 To c.count * 2)
        ReDim Preserve c.keys(0 To c.count * 2)
    End If
    For i As Long = c.count To at + 1 Step -1
        c.items(i) = c.items(i - 1)
        c.keys(i) = c.keys(i - 1)
    Next
    c.items(at) = item
    c.keys(at) = lk
    c.count += 1
End Sub

Private Function VBColItem(ByRef c As VBCollection, ByRef k As RVar) As RVar
    Dim i As Long = VBColIndex(c, k)
    If i < 0 Then Return RV_Empty()
    Return c.items(i)
End Function

Private Sub VBColRemove(ByRef c As VBCollection, ByRef k As RVar)
    Dim i As Long = VBColIndex(c, k)
    If i < 0 Then Exit Sub
    For j As Long = i To c.count - 2
        c.items(j) = c.items(j + 1)
        c.keys(j) = c.keys(j + 1)
    Next
    c.count -= 1
    c.items(c.count) = RV_Empty()
    c.keys(c.count) = ""
End Sub

Private Sub VBColClear(ByRef c As VBCollection)
    c.count = 0
    Erase c.items
    Erase c.keys
End Sub

' ------------------------------------------------------------------------------ program start / end
Dim Shared vbOnEnd As Sub()

Private Sub VBEnd()
    VBCloseAll()
    If Len(vbDebugPending) Then VBDebugOut("")
    If vbOnEnd Then vbOnEnd()
    ExitProcess(0)
End Sub

Private Sub VBInitCore(ByRef title As String)
    vbAppTitle = title
    Dim buf As WString * 1024
    Dim n As Long = GetModuleFileNameW(0, @buf, 1024)
    Dim p As String = VBFromWide(@buf, n)
    vbAppPath = Left(p, InStrRev(p, "\") - 1)
    Dim w As WString Ptr = VBWide(vbAppPath)
    SetCurrentDirectoryW(w)                ' like the IDE: relative paths are relative to the program folder
    Deallocate(w)
    VBRandomize()
    vbRndSeed = 327680
End Sub
