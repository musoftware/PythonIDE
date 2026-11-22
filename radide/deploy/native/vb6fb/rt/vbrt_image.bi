' ============================================================================================
' vbrt_image.bi - pictures for PictureBox.Picture / Form.Icon through GDI+ (a Windows system DLL).
' Included only by programs that use pictures.  Images embedded in the exe (RCDATA resources
' named after the file, see vbImageRes) are found first, then files next to the program.
' Part of RAD IDE (MIT).
' ============================================================================================
#inclib "gdiplus"
#inclib "ole32"

Type VBGdipInput
    version As ULong
    callback As Any Ptr
    noThread As Long
    noCodecs As Long
End Type

Extern "Windows"
Declare Function GdiplusStartup Lib "gdiplus" (ByVal token As ULONG_PTR Ptr, ByVal gin As VBGdipInput Ptr, ByVal outp As Any Ptr) As Long
Declare Function GdipLoadImageFromStream Lib "gdiplus" (ByVal stream As Any Ptr, ByVal img As Any Ptr Ptr) As Long
Declare Function GdipLoadImageFromFile Lib "gdiplus" (ByVal file As WString Ptr, ByVal img As Any Ptr Ptr) As Long
Declare Function GdipCreateFromHDC Lib "gdiplus" (ByVal dc As HDC, ByVal g As Any Ptr Ptr) As Long
Declare Function GdipDeleteGraphics Lib "gdiplus" (ByVal g As Any Ptr) As Long
Declare Function GdipDrawImageRectI Lib "gdiplus" (ByVal g As Any Ptr, ByVal img As Any Ptr, ByVal x As Long, ByVal y As Long, ByVal w As Long, ByVal h As Long) As Long
Declare Function GdipGetImageWidth Lib "gdiplus" (ByVal img As Any Ptr, ByVal w As ULong Ptr) As Long
Declare Function GdipGetImageHeight Lib "gdiplus" (ByVal img As Any Ptr, ByVal h As ULong Ptr) As Long
Declare Function GdipCreateHICONFromBitmap Lib "gdiplus" (ByVal img As Any Ptr, ByVal ic As HICON Ptr) As Long
End Extern

Dim Shared vbGdipToken As ULONG_PTR

Private Function VBImageRes(ByRef path As String) As Any Ptr    ' embedded copy -> IStream
    Dim nm As String = "IMG_" & UCase(VBReplace(path, "/", "\"))
    For i As Long = 4 To Len(nm) - 1
        Dim c As Long = nm[i]
        If Not ((c >= 48 AndAlso c <= 57) OrElse (c >= 65 AndAlso c <= 90)) Then nm[i] = 95
    Next
    Dim w As WString Ptr = VBWide(nm)
    Dim hr As HRSRC = FindResourceW(0, w, MAKEINTRESOURCEW(10))
    Deallocate(w)
    If hr = 0 Then Return 0
    Dim size As DWORD = SizeofResource(0, hr)
    Dim src As Any Ptr = LockResource(LoadResource(0, hr))
    Dim hm As HGLOBAL = GlobalAlloc(GMEM_MOVEABLE, size)
    CopyMemory(GlobalLock(hm), src, size)
    GlobalUnlock(hm)
    Dim stream As IStream Ptr
    If CreateStreamOnHGlobal(hm, -1, @stream) <> 0 Then Return 0
    Return stream
End Function

Private Function VBGdipLoad(ByRef path As String) As Any Ptr
    If vbGdipToken = 0 Then
        Dim gin As VBGdipInput
        gin.version = 1
        GdiplusStartup(@vbGdipToken, @gin, 0)
    End If
    Dim img As Any Ptr = 0
    Dim stream As IStream Ptr = VBImageRes(path)
    If stream Then
        GdipLoadImageFromStream(stream, @img)
        Return img
    End If
    Dim w As WString Ptr = VBWide(path)
    GdipLoadImageFromFile(w, @img)
    Deallocate(w)
    Return img
End Function

' like the IDE's PictureBox: the picture at its own size, centred in the control
Private Sub VBGdipDraw(ByVal img As Any Ptr, ByVal dc As HDC, ByRef rc As RECT)
    Dim g As Any Ptr
    If GdipCreateFromHDC(dc, @g) <> 0 Then Exit Sub
    Dim As ULong iw, ih
    GdipGetImageWidth(img, @iw)
    GdipGetImageHeight(img, @ih)
    Dim As Long w = VBS(iw), h = VBS(ih)
    GdipDrawImageRectI(g, img, rc.left + ((rc.right - rc.left) - w) \ 2, rc.top + ((rc.bottom - rc.top) - h) \ 2, w, h)
    GdipDeleteGraphics(g)
End Sub

Private Function VBGdipIcon(ByRef path As String) As HICON
    Dim img As Any Ptr = VBGdipLoad(path)
    If img = 0 Then Return 0
    Dim ic As HICON
    GdipCreateHICONFromBitmap(img, @ic)
    Return ic
End Function

Private Sub VBUseImages()
    vbImageLoader = @VBGdipLoad
    vbImageDraw = @VBGdipDraw
    vbIconLoader = @VBGdipIcon
End Sub
