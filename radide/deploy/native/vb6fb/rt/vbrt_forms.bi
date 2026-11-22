' ============================================================================================
' vbrt_forms.bi - RAD IDE VB6 runtime for FreeBASIC: forms and controls on plain Win32
' (comctl32 v6 visual styles, system-DPI aware, Unicode/Arabic text).  Part of RAD IDE (MIT).
'
' The generated program describes every form, control and menu item in the vbCtls() table
' (VBDefForm / VBDef / VBDefMenu + direct field assignments) and binds event procedures with
' VBOn(id, event, @handler).  Forms are created the first time they are needed (Load / Show /
' a property of one of their controls), like VB6.
' ============================================================================================
#include once "vbrt_core.bi"
#include once "win/commctrl.bi"
#include once "win/commdlg.bi"
#include once "win/shlobj.bi"
#include once "win/uxtheme.bi"
#inclib "comctl32"
#inclib "uxtheme"

Enum VBKind
    vbkForm = 1
    vbkButton
    vbkLabel
    vbkTextBox
    vbkCheckBox
    vbkOption
    vbkListBox
    vbkComboBox
    vbkFrame
    vbkPanel
    vbkPicture
    vbkProgress
    vbkUpDown
    vbkSlider
    vbkTimer
    vbkMenu
    vbkLink
    vbkStatus
    vbkTab
    vbkDate
    vbkDlgOpen
    vbkDlgSave
    vbkDlgColor
    vbkDlgFont
    vbkDlgFolder
End Enum

Enum VBEvent
    vbeClick = 0
    vbeDblClick
    vbeChange
    vbeGotFocus
    vbeLostFocus
    vbeKeyPress
    vbeKeyDown
    vbeKeyUp
    vbeMouseDown
    vbeMouseUp
    vbeMouseMove
    vbeTimer
    vbeLoad
    vbeActivate
    vbeDeactivate
    vbeResize
    vbeQueryUnload
    vbeUnload
    vbeTerminate
    vbeMouseEnter
    vbeMouseLeave
    vbeInitialize
    vbeValidate
    vbeSizeVariantChanged        ' layout variants (rt/vbrt_motion.bi)
    vbeCount
End Enum

Enum VBProp
    vbpText = 1
    vbpValue
    vbpLeft
    vbpTop
    vbpWidth
    vbpHeight
    vbpEnabled
    vbpVisible
    vbpBackColor
    vbpForeColor
    vbpListIndex
    vbpListCount
    vbpNewIndex
    vbpSelStart
    vbpSelLength
    vbpSelText
    vbpLocked
    vbpMaxLength
    vbpMin
    vbpMax
    vbpInterval
    vbpFontName
    vbpFontSize
    vbpFontBold
    vbpFontItalic
    vbpFontUnderline
    vbpToolTipText
    vbpTag
    vbpHwnd
    vbpTabIndex
    vbpPicture
    vbpChecked
    vbpFileName
    vbpFileTitle
    vbpFilter
    vbpDialogTitle
    vbpInitDir
    vbpColor
    vbpCancelError
    vbpWindowState
    vbpScaleWidth
    vbpScaleHeight
    vbpName
    vbpMultiLine
    vbpPasswordChar
    vbpIndex
    vbpTab
    vbpTabs
    vbpAlignment
    vbpLinkColor
    vbpTabStop
    vbpYear
    vbpMonth
    vbpDay
    vbpHour
    vbpMinute
    vbpSecond
    vbpFormat
End Enum

Type VBEventArgs
    index As Long
    keyAscii As Long
    keyCode As Long
    shift As Long
    button As Long
    x As Single
    y As Single
    cancel As Long
    unloadMode As Long
    prevTab As Long
End Type
Type VBHandler As Sub(ByRef e As VBEventArgs)

Type VBPlace
    As Single x, y, w, h, rx, ry, rw, rh
End Type

Type VBCtl
    kind As Long
    form As Long                 ' owning form (a form is its own owner)
    parent As Long               ' container control (0 = the form's client area); menus: parent menu
    page As Long                 ' tab page when the parent is a TabControl
    hwnd As HWND
    inner As HWND                ' container: the window children live in (GroupBox: the box window)
    buddy As HWND                ' up-down arrows / group-box frame
    name As String
    arrIndex As Long             ' Index in a control array (-1 = none)
    pl As VBPlace                ' Anchor / Dock geometry (design pixels)
    px As Long                   ' current geometry in design pixels, relative to the container
    py As Long
    pw As Long
    ph As Long
    text As String
    items As String              ' "a;b;c"
    align As Long                ' 0 left, 1 right, 2 center
    fontName As String
    fontSize As Single
    bold As Long
    italic As Long
    underline As Long
    hfont As HFONT
    fore As Long                 ' &hBBGGRR, -1 = default
    back As Long
    hbrush As HBRUSH
    enabled As Long
    visible As Long
    tabIndex As Long
    tabStop As Long
    tooltip As String
    multiline As Long
    readonly As Long
    maxlen As Long
    password As String
    style As Long                ' ComboBox: 0 DropDownList, 1 DropDown, 2 Simple
    vmin As Long
    vmax As Long
    value As Long
    interval As Long
    timerOn As Long
    tag As String
    picture As String
    image As Any Ptr             ' GDI+ image
    title As String
    filter As String
    filename As String
    filetitle As String
    initdir As String
    colour As Long
    cancelErr As Long
    hmenu As HMENU               ' menu: the menu that holds the item / the item's popup
    checked As Long
    pages(0 To 31) As HWND       ' TabControl pages
    npages As Long
    curTab As Long
    ' forms
    loaded As Long
    startPos As Long             ' 0 manual, 1 center screen
    border As Long               ' 0 sizable, 1 fixed single
    topMost As Long
    winState As Long             ' 0 normal, 1 minimized, 2 maximized
    twips As Long                ' ScaleMode = Twip (15 per pixel)
    icon As String
    menuBar As HMENU
    hicon As HICON
    accel As HACCEL
    linkColor As Long
    newIndex As Long
    ev(0 To vbeCount - 1) As VBHandler
End Type

Dim Shared vbCtls(Any) As VBCtl
Dim Shared vbCtlCount As Long
Dim Shared vbScale As Long = 96                 ' screen DPI
Dim Shared vbCreating As Long                    ' no events while controls are being created
Dim Shared vbFireDepth As Long                   ' event handlers running (nested)
Dim Shared vbRefocus As Long                     ' Validate Cancel: the focus goes back to this control (no events)
Const VB_WM_REFOCUS = WM_APP + 77
Dim Shared vbStartForm As Long
Dim Shared vbTooltip As HWND
Dim Shared vbImageLoader As Function(ByRef path As String) As Any Ptr
Dim Shared vbImageDraw As Sub(ByVal img As Any Ptr, ByVal dc As HDC, ByRef rc As RECT)
Dim Shared vbIconLoader As Function(ByRef path As String) As HICON
Dim Shared vbHandCursor As HCURSOR
' animations / visual states / layout variants: rt/vbrt_motion.bi (included only by programs that use them)
' sets these hooks; vbFxQuiet > 0 while it writes properties itself
Dim Shared vbFxQuiet As Long
Dim Shared vbFxHot As Long                      ' the control under the mouse (MouseEnter / MouseLeave)
Dim Shared vbFxOnEvent As Sub(ByVal id As Long, ByVal ev As Long)
Dim Shared vbFxOnSet As Function(ByVal id As Long, ByVal p As Long, ByVal v As Long) As Long
Dim Shared vbFxOnForm As Sub(ByVal f As Long, ByVal what As Long, ByVal wp As WPARAM, ByVal lp As LPARAM)
Const VB_WM_FX = WM_APP + 78
Const VB_FX_TIMER0 = 20000                       ' timer ids of the motion runtime (VB Timers: 1000 + id)
Const VB_HOVER_TIMER = 19999                     ' watches the cursor after a WM_MOUSELEAVE that came too early

#define VBS(v) MulDiv((v), vbScale, 96)          ' design pixels -> screen pixels
#define VBU(v) MulDiv((v), 96, vbScale)          ' screen pixels -> design pixels

' ------------------------------------------------------------------------------ table
Private Sub VBEnsure(ByVal id As Long)
    If id > UBound(vbCtls) Then ReDim Preserve vbCtls(0 To id + 32)
    If id > vbCtlCount Then vbCtlCount = id
End Sub

Private Sub VBDefForm(ByVal id As Long, ByRef nm As String, ByRef caption As String, ByVal w As Long, ByVal h As Long)
    VBEnsure(id)
    With vbCtls(id)
        .kind = vbkForm: .form = id: .name = nm: .text = caption
        .pw = w: .ph = h: .pl.w = w: .pl.h = h
        .fore = -1: .back = -1: .enabled = -1: .visible = 0: .arrIndex = -1
        .startPos = 1: .fontName = "Segoe UI": .fontSize = 9
    End With
End Sub

Private Sub VBDef(ByVal id As Long, ByVal frm As Long, ByVal parent As Long, ByVal kind As Long, ByRef nm As String, _
                  ByRef txt As String, ByVal x As Long, ByVal y As Long, ByVal w As Long, ByVal h As Long)
    VBEnsure(id)
    With vbCtls(id)
        .kind = kind: .form = frm: .parent = parent: .name = nm: .text = txt
        .px = x: .py = y: .pw = w: .ph = h
        .pl.x = x: .pl.y = y: .pl.w = w: .pl.h = h
        .fore = -1: .back = -1: .enabled = -1: .visible = -1: .arrIndex = -1: .tabStop = -1
        .fontName = "Segoe UI": .fontSize = 9: .vmax = 100: .interval = 100: .linkColor = &hCC6600
        .colour = 0
        If kind = vbkButton Then .align = 2
    End With
End Sub

Private Sub VBDefMenu(ByVal id As Long, ByVal frm As Long, ByVal parentMenu As Long, ByRef nm As String, ByRef txt As String)
    VBEnsure(id)
    With vbCtls(id)
        .kind = vbkMenu: .form = frm: .parent = parentMenu: .name = nm: .text = txt
        .enabled = -1: .visible = -1: .arrIndex = -1
    End With
End Sub

Private Sub VBPlaceSet(ByVal id As Long, ByVal x As Single, ByVal y As Single, ByVal w As Single, ByVal h As Single, _
                       ByVal rx As Single, ByVal ry As Single, ByVal rw As Single, ByVal rh As Single)
    With vbCtls(id).pl
        .x = x: .y = y: .w = w: .h = h: .rx = rx: .ry = ry: .rw = rw: .rh = rh
    End With
End Sub

Private Sub VBFontSet(ByVal id As Long, ByRef nm As String, ByVal size As Single, ByVal bold As Long, ByVal italic As Long)
    With vbCtls(id)
        .fontName = nm: .fontSize = size: .bold = bold: .italic = italic
    End With
End Sub

Private Sub VBOn(ByVal id As Long, ByVal ev As Long, ByVal h As VBHandler)
    vbCtls(id).ev(ev) = h
End Sub

Private Function VBUnit(ByVal id As Long) As Long        ' 15 when the form's ScaleMode is Twip
    Return IIf(vbCtls(vbCtls(id).form).twips, 15, 1)
End Function

' ------------------------------------------------------------------------------ errors in events
Private Sub VBUnhandled()
    Dim msg As String = "Run-time error '" & Str(VBErr.Number) & "':" & Chr(13, 10, 13, 10) & VBErr.Description
    Dim h As HANDLE = GetStdHandle(STD_ERROR_HANDLE)
    If h <> 0 AndAlso h <> INVALID_HANDLE_VALUE Then
        Dim t As String = vbErrFile & "(" & Str(vbErrLine) & "): Run-time error " & Str(VBErr.Number) & ": " & VBErr.Description & Chr(13, 10)
        Dim written As DWORD
        WriteFile(h, StrPtr(t), Len(t), @written, 0)
    End If
    vbErrPending = 0
    vbErrLine = 0
    Dim w As WString Ptr = VBWide(msg)
    Dim tt As WString Ptr = VBWide(vbAppTitle)
    MessageBoxW(GetActiveWindow(), w, tt, MB_ICONERROR)
    Deallocate(w): Deallocate(tt)
End Sub

Private Function VBFire(ByVal id As Long, ByVal ev As Long, ByRef e As VBEventArgs) As Long
    If id <= 0 OrElse id > vbCtlCount OrElse vbCreating Then Return 0
    If vbFxOnEvent <> 0 Then vbFxOnEvent(id, ev)       ' triggers / automatic visual states
    Dim h As VBHandler = vbCtls(id).ev(ev)
    If h = 0 Then Return 0
    e.index = vbCtls(id).arrIndex
    vbFireDepth += 1
    h(e)
    vbFireDepth -= 1
    If vbErrPending Then VBUnhandled()
    Return -1
End Function

Private Sub VBFire0(ByVal id As Long, ByVal ev As Long)
    Dim e As VBEventArgs
    VBFire(id, ev, e)
End Sub

' the mouse came over control id (only tracked when the motion runtime is in): MouseLeave of the previous one,
' TME_LEAVE for this window, MouseEnter
Private Sub VBHoverEnter(ByVal h As HWND, ByVal id As Long)
    If vbFxHot = id Then Exit Sub
    If vbFxHot > 0 Then
        Dim old As Long = vbFxHot
        vbFxHot = 0
        VBFire0(old, vbeMouseLeave)
    End If
    Dim t As TRACKMOUSEEVENT
    t.cbSize = SizeOf(t)
    t.dwFlags = TME_LEAVE
    t.hwndTrack = h
    TrackMouseEvent(@t)
    vbFxHot = id
    VBFire0(id, vbeMouseEnter)
End Sub

Private Function VBHoverOver(ByVal id As Long) As Long
    Dim cp As POINT
    GetCursorPos(@cp)
    Dim w As HWND = WindowFromPoint(cp)
    Return w <> 0 AndAlso (w = vbCtls(id).hwnd OrElse w = vbCtls(id).inner)
End Function

Private Sub VBHoverLeave(ByVal id As Long)
    If vbFxHot <> id OrElse id = 0 Then Exit Sub
    ' a WM_MOUSELEAVE while the cursor is still over the control (themed buttons track the mouse themselves and
    ' end our tracking): the cursor is watched instead (VBHoverPoll)
    Dim f As Long = vbCtls(id).form
    If vbCtls(f).hwnd <> 0 AndAlso VBHoverOver(id) Then
        SetTimer(vbCtls(f).hwnd, VB_HOVER_TIMER, 60, 0)
        Exit Sub
    End If
    vbFxHot = 0
    VBFire0(id, vbeMouseLeave)
End Sub

Private Sub VBHoverPoll(ByVal f As Long)
    Dim id As Long = vbFxHot
    If id > 0 AndAlso id <= vbCtlCount AndAlso vbCtls(id).hwnd <> 0 AndAlso VBHoverOver(id) Then Exit Sub
    KillTimer(vbCtls(f).hwnd, VB_HOVER_TIMER)
    If id > 0 Then
        vbFxHot = 0
        VBFire0(id, vbeMouseLeave)
    End If
End Sub

' ------------------------------------------------------------------------------ helpers
Private Function VBIdOf(ByVal h As HWND) As Long
    If h = 0 Then Return 0
    Dim id As Long = CLng(GetWindowLongPtrW(h, GWLP_USERDATA))
    If id > 0 AndAlso id <= vbCtlCount Then
        If vbCtls(id).hwnd = h OrElse vbCtls(id).buddy = h OrElse vbCtls(id).inner = h Then Return id
    End If
    Return 0
End Function

Private Sub VBSetTextW(ByVal h As HWND, ByRef s As String)
    Dim w As WString Ptr = VBWide(s)
    SetWindowTextW(h, w)
    Deallocate(w)
End Sub

Private Function VBGetTextW(ByVal h As HWND) As String
    Dim n As Long = GetWindowTextLengthW(h)
    If n = 0 Then Return ""
    Dim w As WString Ptr = Allocate((n + 2) * 2)
    n = GetWindowTextW(h, w, n + 1)
    Function = VBFromWide(w, n)
    Deallocate(w)
End Function

' right-to-left reading order when the text starts with a Hebrew / Arabic letter (like Qt's auto direction)
Private Function VBIsRtl(ByRef s As String) As Long
    Dim As Long i = 0, n = Len(s)
    While i < n
        Dim b As Long = s[i]
        If b < &h80 Then
            If (b >= 65 AndAlso b <= 90) OrElse (b >= 97 AndAlso b <= 122) Then Return 0
            i += 1
        Else
            Dim cp As Long = VBDecodeFirst(Mid(s, i + 1, 4))
            If (cp >= &h590 AndAlso cp <= &h8FF) OrElse (cp >= &hFB1D AndAlso cp <= &hFEFC) Then Return -1
            If cp >= &hC0 Then Return 0
            i += IIf(b < &hE0, 2, IIf(b < &hF0, 3, 4))
        End If
    Wend
    Return 0
End Function

Private Sub VBSetRtl(ByVal h As HWND, ByRef s As String)
    Dim ex As Long = GetWindowLongW(h, GWL_EXSTYLE)
    Dim want As Long = IIf(VBIsRtl(s), ex Or WS_EX_RTLREADING, ex And Not WS_EX_RTLREADING)
    If want <> ex Then SetWindowLongW(h, GWL_EXSTYLE, want): InvalidateRect(h, 0, -1)
End Sub

Private Function VBMakeFont(ByVal id As Long) As HFONT
    With vbCtls(id)
        Dim w As WString Ptr = VBWide(.fontName)
        Dim f As HFONT = CreateFontW(-MulDiv(CLng(.fontSize * 100), vbScale, 7200), 0, 0, 0, IIf(.bold, FW_BOLD, FW_NORMAL), _
                                     IIf(.italic, 1, 0), IIf(.underline, 1, 0), 0, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, _
                                     CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH Or FF_DONTCARE, w)
        Deallocate(w)
        Return f
    End With
End Function

Private Sub VBApplyFont(ByVal id As Long)
    With vbCtls(id)
        If .hwnd = 0 Then Exit Sub
        Dim old As HFONT = .hfont
        .hfont = VBMakeFont(id)
        SendMessageW(.hwnd, WM_SETFONT, Cast(WPARAM, .hfont), 1)
        If .buddy AndAlso .kind = vbkFrame Then SendMessageW(.buddy, WM_SETFONT, Cast(WPARAM, .hfont), 1)
        If old Then DeleteObject(old)
    End With
End Sub

Private Sub VBApplyBrush(ByVal id As Long)
    With vbCtls(id)
        If .hbrush Then DeleteObject(.hbrush): .hbrush = 0
        If .back >= 0 Then .hbrush = CreateSolidBrush(.back)
    End With
End Sub

' the background a transparent control shows: its own colour, else the nearest container's / form's
Private Function VBEffBack(ByVal id As Long) As Long
    Dim i As Long = id
    While i > 0
        If vbCtls(i).back >= 0 Then Return i
        If vbCtls(i).kind = vbkForm Then Exit While
        If vbCtls(i).kind = vbkTab Then Exit While
        i = IIf(vbCtls(i).parent > 0, vbCtls(i).parent, vbCtls(i).form)
    Wend
    Return 0
End Function

' the window that hosts the children of container id (0 = form client)
Private Function VBHost(ByVal id As Long) As HWND
    With vbCtls(id)
        If .parent = 0 Then Return vbCtls(.form).hwnd
        Dim p As Long = .parent
        If vbCtls(p).kind = vbkTab Then
            If .page >= 0 AndAlso .page < vbCtls(p).npages Then Return vbCtls(p).pages(.page)
            Return vbCtls(p).inner
        End If
        Return vbCtls(p).inner
    End With
End Function

' client size of the area a control lives in, in design pixels
Private Sub VBContainerSize(ByVal id As Long, ByRef cw As Long, ByRef ch As Long)
    Dim p As Long = vbCtls(id).parent
    If p = 0 Then
        Dim rc As RECT
        GetClientRect(vbCtls(vbCtls(id).form).hwnd, @rc)
        cw = VBU(rc.right): ch = VBU(rc.bottom)
        Return
    End If
    If vbCtls(p).kind = vbkTab Then
        cw = vbCtls(p).pw - 4: ch = vbCtls(p).ph - 26
    Else
        cw = vbCtls(p).pw: ch = vbCtls(p).ph
    End If
    If cw < 0 Then cw = 0
    If ch < 0 Then ch = 0
End Sub

Declare Sub VBLayoutChildren(ByVal container As Long, ByVal frm As Long)

Private Sub VBPlaceNow(ByVal id As Long)
    With vbCtls(id)
        If .hwnd = 0 Then Exit Sub
        Dim h As Long = .ph
        If .kind = vbkComboBox Then h = .ph + 200
        If .kind = vbkUpDown Then
            MoveWindow(.hwnd, VBS(.px), VBS(.py), VBS(.pw), VBS(.ph), -1)
            SendMessageW(.buddy, UDM_SETBUDDY, Cast(WPARAM, .hwnd), 0)
        ElseIf .kind = vbkFrame Then
            MoveWindow(.hwnd, VBS(.px), VBS(.py), VBS(.pw), VBS(.ph), -1)
            MoveWindow(.buddy, 0, 0, VBS(.pw), VBS(.ph), -1)
        ElseIf .kind = vbkTab Then
            MoveWindow(.hwnd, VBS(.px), VBS(.py), VBS(.pw), VBS(.ph), -1)
            MoveWindow(.inner, 0, 0, VBS(.pw), VBS(.ph), -1)
            For i As Long = 0 To .npages - 1
                MoveWindow(.pages(i), VBS(2), VBS(24), VBS(.pw - 4), VBS(.ph - 26), -1)
            Next
        Else
            MoveWindow(.hwnd, VBS(.px), VBS(.py), VBS(.pw), VBS(h), -1)
        End If
    End With
End Sub

Private Sub VBRelayout(ByVal id As Long)
    Dim As Long cw, ch
    VBContainerSize(id, cw, ch)
    With vbCtls(id)
        .px = CLng(.pl.x + .pl.rx * cw)
        .py = CLng(.pl.y + .pl.ry * ch)
        .pw = CLng(.pl.w + .pl.rw * cw): If .pw < 0 Then .pw = 0
        .ph = CLng(.pl.h + .pl.rh * ch): If .ph < 0 Then .ph = 0
    End With
    VBPlaceNow(id)
End Sub

Private Sub VBLayoutChildren(ByVal container As Long, ByVal frm As Long)
    For i As Long = 1 To vbCtlCount
        With vbCtls(i)
            If .form = frm AndAlso .kind <> vbkForm AndAlso .kind <> vbkMenu AndAlso .hwnd <> 0 AndAlso .parent = container Then
                If .pl.rx <> 0 OrElse .pl.ry <> 0 OrElse .pl.rw <> 0 OrElse .pl.rh <> 0 Then
                    VBRelayout(i)
                    If .inner Then VBLayoutChildren(i, frm)
                End If
            End If
        End With
    Next
End Sub

' a control's geometry was changed by code: keep it (with its anchors) from now on
Private Sub VBMoved(ByVal id As Long)
    Dim As Long cw, ch
    VBContainerSize(id, cw, ch)
    With vbCtls(id)
        .pl.x = .px - .pl.rx * cw
        .pl.y = .py - .pl.ry * ch
        .pl.w = .pw - .pl.rw * cw
        .pl.h = .ph - .pl.rh * ch
    End With
    VBPlaceNow(id)
    If vbCtls(id).inner Then VBLayoutChildren(id, vbCtls(id).form)
End Sub

' ------------------------------------------------------------------------------ window procedures
Declare Function VBFormProc(ByVal hwnd As HWND, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM) As LRESULT
Declare Sub VBFormUnload(ByVal f As Long, ByVal mode As Long = 1)
Declare Function VBHandleCommon(ByVal hwnd As HWND, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM, ByRef handled As Long) As LRESULT

Private Function VBShiftState() As Long
    Dim s As Long = 0
    If GetKeyState(VK_SHIFT) < 0 Then s Or= 1
    If GetKeyState(VK_CONTROL) < 0 Then s Or= 2
    If GetKeyState(VK_MENU) < 0 Then s Or= 4
    Return s
End Function

Private Function VBMouseArgs(ByVal id As Long, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM, ByRef e As VBEventArgs) As Long
    Dim u As Long = VBUnit(id)
    e.x = VBU(CShort(LoWord(lp))) * u
    e.y = VBU(CShort(HiWord(lp))) * u
    e.shift = VBShiftState()
    Select Case msg
    Case WM_LBUTTONDOWN, WM_LBUTTONUP: e.button = 1
    Case WM_RBUTTONDOWN, WM_RBUTTONUP: e.button = 2
    Case WM_MBUTTONDOWN, WM_MBUTTONUP: e.button = 4
    Case Else
        e.button = IIf(wp And MK_LBUTTON, 1, 0) Or IIf(wp And MK_RBUTTON, 2, 0) Or IIf(wp And MK_MBUTTON, 4, 0)
    End Select
    Return 0
End Function

' keyboard / mouse / focus events of a control (subclass procedure)
Private Function VBCtlSub(ByVal hwnd As HWND, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM, _
                          ByVal uid As UINT_PTR, ByVal ref As DWORD_PTR) As LRESULT
    Dim id As Long = CLng(ref)
    Dim e As VBEventArgs
    Select Case msg
    Case WM_CHAR
        If vbCtls(id).ev(vbeKeyPress) Then
            e.keyAscii = wp
            VBFire(id, vbeKeyPress, e)
            If e.keyAscii = 0 Then Return 0
            wp = e.keyAscii
        End If
    Case WM_KEYDOWN, WM_SYSKEYDOWN
        If vbCtls(id).ev(vbeKeyDown) Then
            e.keyCode = wp: e.shift = VBShiftState()
            VBFire(id, vbeKeyDown, e)
            If e.keyCode = 0 Then Return 0
        End If
    Case WM_KEYUP, WM_SYSKEYUP
        If vbCtls(id).ev(vbeKeyUp) Then
            e.keyCode = wp: e.shift = VBShiftState()
            VBFire(id, vbeKeyUp, e)
        End If
    Case WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN
        If vbCtls(id).ev(vbeMouseDown) <> 0 OrElse vbFxOnEvent <> 0 Then VBMouseArgs(id, msg, wp, lp, e): VBFire(id, vbeMouseDown, e)
    Case WM_LBUTTONUP, WM_RBUTTONUP, WM_MBUTTONUP
        If vbCtls(id).ev(vbeMouseUp) <> 0 OrElse vbFxOnEvent <> 0 Then VBMouseArgs(id, msg, wp, lp, e): VBFire(id, vbeMouseUp, e)
        ' Label / LinkLabel / PictureBox: Click after MouseUp, released over the control (VB6 order; the STATIC
        ' control's STN_CLICKED comes with the button press)
        Select Case vbCtls(id).kind
        Case vbkLabel, vbkLink, vbkPicture
            If msg = WM_LBUTTONUP Then
                Dim rc As RECT
                GetClientRect(hwnd, @rc)
                Dim As Long mx = CShort(LoWord(lp)), my = CShort(HiWord(lp))
                If mx >= 0 AndAlso my >= 0 AndAlso mx < rc.right AndAlso my < rc.bottom Then VBFire0(id, vbeClick)
            End If
        End Select
    Case WM_MOUSEMOVE
        If vbFxOnEvent <> 0 AndAlso vbFxHot <> id Then VBHoverEnter(hwnd, id)
        If vbCtls(id).ev(vbeMouseMove) Then VBMouseArgs(id, msg, wp, lp, e): VBFire(id, vbeMouseMove, e)
    Case WM_MOUSELEAVE
        VBHoverLeave(id)
    Case WM_SETFOCUS
        If vbRefocus = 0 Then VBFire0(id, vbeGotFocus)
    Case WM_KILLFOCUS
        If vbRefocus = 0 Then
            ' VB6 Validate: the focus goes to another control of the same form - before LostFocus; Cancel keeps
            ' the focus here (the other control gets no GotFocus, this one no LostFocus)
            Dim nh As HWND = Cast(HWND, wp)
            Dim fh As HWND = vbCtls(vbCtls(id).form).hwnd
            If vbCtls(id).ev(vbeValidate) AndAlso nh <> 0 AndAlso fh <> 0 AndAlso GetAncestor(nh, GA_ROOT) = fh Then
                e.cancel = 0
                VBFire(id, vbeValidate, e)
                If e.cancel Then
                    vbRefocus = id
                    PostMessageW(fh, VB_WM_REFOCUS, id, 0)
                    Return DefSubclassProc(hwnd, msg, wp, lp)
                End If
            End If
            VBFire0(id, vbeLostFocus)
        End If
    Case WM_SETCURSOR
        If vbCtls(id).kind = vbkLink Then SetCursor(vbHandCursor): Return -1
    Case WM_LBUTTONDBLCLK
        If vbCtls(id).kind = vbkTextBox OrElse vbCtls(id).kind = vbkPicture Then VBFire0(id, vbeDblClick)
    End Select
    Return DefSubclassProc(hwnd, msg, wp, lp)
End Function

' container windows (Panel / Frame / TabControl pages): forward notifications to the form
Private Function VBBoxProc(ByVal hwnd As HWND, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM) As LRESULT
    Select Case msg
    Case WM_COMMAND, WM_NOTIFY, WM_CTLCOLORSTATIC, WM_CTLCOLOREDIT, WM_CTLCOLORLISTBOX, WM_CTLCOLORBTN, _
         WM_DRAWITEM, WM_HSCROLL, WM_VSCROLL
        Dim handled As Long
        Dim r As LRESULT = VBHandleCommon(hwnd, msg, wp, lp, handled)
        If handled Then Return r
    Case WM_ERASEBKGND
        Dim id As Long = VBIdOf(hwnd)
        Dim b As Long = VBEffBack(id)
        Dim rc As RECT
        GetClientRect(hwnd, @rc)
        If b > 0 AndAlso vbCtls(b).hbrush Then
            FillRect(Cast(HDC, wp), @rc, vbCtls(b).hbrush)
        ElseIf id > 0 AndAlso vbCtls(id).kind = vbkTab Then
            Return DefWindowProcW(hwnd, msg, wp, lp)
        Else
            FillRect(Cast(HDC, wp), @rc, GetSysColorBrush(COLOR_BTNFACE))
        End If
        Return 1
    Case WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_LBUTTONUP, WM_RBUTTONUP, WM_MOUSEMOVE
        Dim id As Long = VBIdOf(hwnd)
        If id > 0 Then
            Dim e As VBEventArgs
            VBMouseArgs(id, msg, wp, lp, e)
            Select Case msg
            Case WM_LBUTTONDOWN, WM_RBUTTONDOWN: VBFire(id, vbeMouseDown, e)
            Case WM_LBUTTONUP, WM_RBUTTONUP
                VBFire(id, vbeMouseUp, e)
                If msg = WM_LBUTTONUP Then VBFire0(id, vbeClick)
            Case Else
                If vbFxOnEvent <> 0 AndAlso vbFxHot <> id Then VBHoverEnter(hwnd, id)
                VBFire(id, vbeMouseMove, e)
            End Select
        End If
    Case WM_MOUSELEAVE
        VBHoverLeave(VBIdOf(hwnd))
    Case WM_LBUTTONDBLCLK
        VBFire0(VBIdOf(hwnd), vbeDblClick)
    End Select
    Return DefWindowProcW(hwnd, msg, wp, lp)
End Function

Private Sub VBDrawButton(ByVal id As Long, ByVal di As DRAWITEMSTRUCT Ptr)
    Dim rc As RECT = di->rcItem
    Dim dc As HDC = di->hDC
    Dim pressed As Long = (di->itemState And ODS_SELECTED) <> 0
    Dim back As Long = IIf(vbCtls(id).back >= 0, vbCtls(id).back, GetSysColor(COLOR_BTNFACE))
    If (di->itemState And ODS_DISABLED) Then back = GetSysColor(COLOR_BTNFACE)
    Dim br As HBRUSH = CreateSolidBrush(back)
    FillRect(dc, @rc, br)
    DeleteObject(br)
    DrawEdge(dc, @rc, IIf(pressed, EDGE_SUNKEN, EDGE_RAISED), BF_RECT)
    If pressed Then OffsetRect(@rc, 1, 1)
    SetBkMode(dc, TRANSPARENT)
    SetTextColor(dc, IIf((di->itemState And ODS_DISABLED), GetSysColor(COLOR_GRAYTEXT), IIf(vbCtls(id).fore >= 0, vbCtls(id).fore, GetSysColor(COLOR_BTNTEXT))))
    Dim old As HGDIOBJ = SelectObject(dc, vbCtls(id).hfont)
    Dim cap As String = VBGetTextW(vbCtls(id).hwnd)
    Dim w As WString Ptr = VBWide(cap)
    Dim fl As UINT = DT_SINGLELINE Or DT_VCENTER Or IIf(VBIsRtl(cap), DT_RTLREADING, 0)
    Select Case vbCtls(id).align
    Case 0: fl Or= DT_LEFT: rc.left += 4
    Case 1: fl Or= DT_RIGHT: rc.right -= 4
    Case Else: fl Or= DT_CENTER
    End Select
    DrawTextW(dc, w, -1, @rc, fl)
    Deallocate(w)
    SelectObject(dc, old)
    If (di->itemState And ODS_FOCUS) Then
        Dim fr As RECT = di->rcItem
        InflateRect(@fr, -4, -4)
        DrawFocusRect(dc, @fr)
    End If
End Sub

Private Sub VBDrawPicture(ByVal id As Long, ByVal di As DRAWITEMSTRUCT Ptr)
    Dim rc As RECT = di->rcItem
    Dim b As Long = VBEffBack(id)
    FillRect(di->hDC, @rc, IIf(b > 0 AndAlso vbCtls(b).hbrush <> 0, vbCtls(b).hbrush, GetSysColorBrush(COLOR_BTNFACE)))
    If vbCtls(id).image <> 0 AndAlso vbImageDraw <> 0 Then vbImageDraw(vbCtls(id).image, di->hDC, rc)
End Sub

Private Sub VBOptionClicked(ByVal id As Long, ByVal fire As Long)
    Dim was As Long = SendMessageW(vbCtls(id).hwnd, BM_GETCHECK, 0, 0) = BST_CHECKED
    For i As Long = 1 To vbCtlCount
        With vbCtls(i)
            If i <> id AndAlso .kind = vbkOption AndAlso .form = vbCtls(id).form AndAlso .parent = vbCtls(id).parent _
               AndAlso .page = vbCtls(id).page AndAlso .hwnd <> 0 Then
                SendMessageW(.hwnd, BM_SETCHECK, BST_UNCHECKED, 0)
                .value = 0
            End If
        End With
    Next
    SendMessageW(vbCtls(id).hwnd, BM_SETCHECK, BST_CHECKED, 0)
    vbCtls(id).value = -1
    If fire AndAlso was = 0 Then VBFire0(id, vbeClick)
End Sub

Private Sub VBTabShow(ByVal id As Long)
    With vbCtls(id)
        Dim cur As Long = SendMessageW(.hwnd, TCM_GETCURSEL, 0, 0)
        For i As Long = 0 To .npages - 1
            ShowWindow(.pages(i), IIf(i = cur, SW_SHOW, SW_HIDE))
        Next
    End With
End Sub

' notifications that reach the form (directly or through a container window)
Private Function VBHandleCommon(ByVal hwnd As HWND, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM, ByRef handled As Long) As LRESULT
    handled = 0
    Select Case msg
    Case WM_COMMAND
        Dim code As Long = HiWord(wp)
        If lp = 0 Then                                   ' menu / accelerator
            Dim id As Long = LoWord(wp) - 1000
            If id > 0 AndAlso id <= vbCtlCount AndAlso vbCtls(id).kind = vbkMenu Then VBFire0(id, vbeClick): handled = -1
            Return 0
        End If
        Dim id As Long = VBIdOf(Cast(HWND, lp))
        If id = 0 Then Return 0
        handled = -1
        Select Case vbCtls(id).kind
        Case vbkButton
            If code = BN_CLICKED Then VBFire0(id, vbeClick)
        Case vbkCheckBox
            If code = BN_CLICKED Then
                Dim st As Long = SendMessageW(vbCtls(id).hwnd, BM_GETCHECK, 0, 0)
                SendMessageW(vbCtls(id).hwnd, BM_SETCHECK, IIf(st = BST_CHECKED, BST_UNCHECKED, BST_CHECKED), 0)
                vbCtls(id).value = IIf(st = BST_CHECKED, 0, 1)
                VBFire0(id, vbeClick)
            End If
        Case vbkOption
            If code = BN_CLICKED Then VBOptionClicked(id, -1)
        Case vbkTextBox
            If code = EN_CHANGE Then VBFire0(id, vbeChange)
        Case vbkUpDown
            If code = EN_CHANGE AndAlso vbCreating = 0 Then
                vbCtls(id).value = SendMessageW(vbCtls(id).buddy, UDM_GETPOS32, 0, 0)
                VBFire0(id, vbeChange)
            End If
        Case vbkListBox
            If code = LBN_SELCHANGE Then VBFire0(id, vbeClick)
            If code = LBN_DBLCLK Then VBFire0(id, vbeDblClick)
        Case vbkComboBox
            If code = CBN_SELCHANGE Then VBFire0(id, vbeClick)
            If code = CBN_EDITCHANGE Then VBFire0(id, vbeChange)
            If code = CBN_DBLCLK Then VBFire0(id, vbeDblClick)
        Case vbkLabel, vbkLink, vbkPicture, vbkPanel
            If code = STN_CLICKED AndAlso vbCtls(id).kind = vbkPanel Then VBFire0(id, vbeClick)   ' others: on WM_LBUTTONUP
            If code = STN_DBLCLK Then VBFire0(id, vbeDblClick)
        End Select
        Return 0
    Case WM_NOTIFY
        Dim nh As NMHDR Ptr = Cast(NMHDR Ptr, lp)
        Dim id As Long = VBIdOf(nh->hwndFrom)
        If id > 0 AndAlso vbCtls(id).kind = vbkTab Then
            If nh->code = TCN_SELCHANGE Then
                handled = -1
                VBTabShow(id)
                Dim e As VBEventArgs
                e.prevTab = vbCtls(id).curTab
                vbCtls(id).curTab = SendMessageW(vbCtls(id).hwnd, TCM_GETCURSEL, 0, 0)
                VBFire(id, vbeClick, e)
            End If
        End If
        If id > 0 AndAlso vbCtls(id).kind = vbkStatus AndAlso nh->code = NM_CLICK Then VBFire0(id, vbeClick)
        If id > 0 AndAlso vbCtls(id).kind = vbkDate AndAlso nh->code = DTN_DATETIMECHANGE Then handled = -1: VBFire0(id, vbeChange)
        Return 0
    Case WM_HSCROLL, WM_VSCROLL
        Dim id As Long = VBIdOf(Cast(HWND, lp))
        If id > 0 AndAlso vbCtls(id).kind = vbkSlider Then
            handled = -1
            Dim v As Long = SendMessageW(vbCtls(id).hwnd, TBM_GETPOS, 0, 0)
            If v <> vbCtls(id).value Then vbCtls(id).value = v: VBFire0(id, vbeChange)
        End If
        Return 0
    Case WM_CTLCOLORSTATIC, WM_CTLCOLOREDIT, WM_CTLCOLORLISTBOX, WM_CTLCOLORBTN
        Dim id As Long = VBIdOf(Cast(HWND, lp))
        If id = 0 Then Return 0
        Dim dc As HDC = Cast(HDC, wp)
        With vbCtls(id)
            If .fore >= 0 Then SetTextColor(dc, .fore)
            If .kind = vbkLink Then SetTextColor(dc, IIf(.fore >= 0, .fore, .linkColor))
            If .back >= 0 Then
                handled = -1
                SetBkColor(dc, .back)
                Return Cast(LRESULT, .hbrush)
            End If
            Select Case .kind
            Case vbkLabel, vbkCheckBox, vbkOption, vbkLink, vbkSlider, vbkPanel, vbkFrame, vbkPicture
                Dim b As Long = VBEffBack(id)
                If b > 0 AndAlso vbCtls(b).hbrush <> 0 Then
                    handled = -1
                    SetBkColor(dc, vbCtls(b).back)
                    Return Cast(LRESULT, vbCtls(b).hbrush)
                End If
                If .fore >= 0 OrElse .kind = vbkLink Then
                    handled = -1
                    SetBkColor(dc, GetSysColor(COLOR_BTNFACE))
                    Return Cast(LRESULT, GetSysColorBrush(COLOR_BTNFACE))
                End If
            Case Else
                If .fore >= 0 Then
                    handled = -1
                    SetBkColor(dc, GetSysColor(COLOR_WINDOW))
                    Return Cast(LRESULT, GetSysColorBrush(COLOR_WINDOW))
                End If
            End Select
        End With
        Return 0
    Case WM_DRAWITEM
        Dim di As DRAWITEMSTRUCT Ptr = Cast(DRAWITEMSTRUCT Ptr, lp)
        Dim id As Long = VBIdOf(di->hwndItem)
        If id = 0 Then Return 0
        handled = -1
        If vbCtls(id).kind = vbkButton Then VBDrawButton(id, di)
        If vbCtls(id).kind = vbkPicture Then VBDrawPicture(id, di)
        Return -1
    End Select
    Return 0
End Function

Private Function VBFormProc(ByVal hwnd As HWND, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM) As LRESULT
    Dim f As Long = CLng(GetWindowLongPtrW(hwnd, GWLP_USERDATA))
    If f <= 0 OrElse f > vbCtlCount Then Return DefWindowProcW(hwnd, msg, wp, lp)
    Dim handled As Long
    Select Case msg
    Case WM_COMMAND, WM_NOTIFY, WM_CTLCOLORSTATIC, WM_CTLCOLOREDIT, WM_CTLCOLORLISTBOX, WM_CTLCOLORBTN, _
         WM_DRAWITEM, WM_HSCROLL, WM_VSCROLL
        Dim r As LRESULT = VBHandleCommon(hwnd, msg, wp, lp, handled)
        If handled Then Return r
    Case WM_TIMER
        If wp >= VB_FX_TIMER0 AndAlso vbFxOnForm <> 0 Then vbFxOnForm(f, 3, wp, 0): Return 0
        If wp = VB_HOVER_TIMER Then VBHoverPoll(f): Return 0
        Dim id As Long = CLng(wp) - 1000
        If id > 0 AndAlso id <= vbCtlCount AndAlso vbCtls(id).kind = vbkTimer Then
            If vbCtls(id).timerOn Then VBFire0(id, vbeTimer)
        End If
        Return 0
    Case WM_ERASEBKGND
        If vbCtls(f).hbrush Then
            Dim rc As RECT
            GetClientRect(hwnd, @rc)
            FillRect(Cast(HDC, wp), @rc, vbCtls(f).hbrush)
            Return 1
        End If
    Case WM_SIZE
        If vbCtls(f).loaded AndAlso wp <> SIZE_MINIMIZED Then
            vbCtls(f).pw = VBU(LoWord(lp)): vbCtls(f).ph = VBU(HiWord(lp))
            VBLayoutChildren(0, f)
            If vbFxOnForm <> 0 Then vbFxOnForm(f, 4, 0, 0)      ' layout variants
            If IsWindowVisible(hwnd) Then VBFire0(f, vbeResize)
        End If
    Case VB_WM_FX                                     ' <storyboard>_Completed / Form_SizeVariantChanged
        If vbFxOnForm <> 0 Then vbFxOnForm(f, 6, wp, lp)
        Return 0
    Case WM_ACTIVATE
        If LoWord(wp) = WA_INACTIVE Then VBFire0(f, vbeDeactivate) Else VBFire0(f, vbeActivate)
    Case WM_CLOSE
        VBFormUnload(f, 0)
        Return 0
    Case VB_WM_REFOCUS                                ' after Validate Cancel: back to the control, no events
        Dim id As Long = CLng(wp)
        If id > 0 AndAlso id <= vbCtlCount AndAlso vbCtls(id).hwnd Then SetFocus(vbCtls(id).hwnd)
        vbRefocus = 0
        Return 0
    Case WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN
        Dim e As VBEventArgs
        VBMouseArgs(f, msg, wp, lp, e)
        VBFire(f, vbeMouseDown, e)
    Case WM_LBUTTONUP, WM_RBUTTONUP, WM_MBUTTONUP
        Dim e As VBEventArgs
        VBMouseArgs(f, msg, wp, lp, e)
        VBFire(f, vbeMouseUp, e)
        If msg = WM_LBUTTONUP Then VBFire0(f, vbeClick)
    Case WM_MOUSEMOVE
        Dim e As VBEventArgs
        VBMouseArgs(f, msg, wp, lp, e)
        VBFire(f, vbeMouseMove, e)
    Case WM_LBUTTONDBLCLK
        VBFire0(f, vbeDblClick)
    Case WM_CHAR
        Dim e As VBEventArgs
        e.keyAscii = wp
        VBFire(f, vbeKeyPress, e)
    Case WM_KEYDOWN
        Dim e As VBEventArgs
        e.keyCode = wp: e.shift = VBShiftState()
        VBFire(f, vbeKeyDown, e)
    Case WM_KEYUP
        Dim e As VBEventArgs
        e.keyCode = wp: e.shift = VBShiftState()
        VBFire(f, vbeKeyUp, e)
    End Select
    Return DefWindowProcW(hwnd, msg, wp, lp)
End Function

' ------------------------------------------------------------------------------ creation
Dim Shared vbClassesDone As Long

Private Sub VBInitGui()
    If vbClassesDone Then Exit Sub
    vbClassesDone = -1
    Dim icc As INITCOMMONCONTROLSEX
    icc.dwSize = SizeOf(icc)
    icc.dwICC = ICC_WIN95_CLASSES Or ICC_STANDARD_CLASSES Or ICC_TAB_CLASSES Or ICC_BAR_CLASSES Or ICC_UPDOWN_CLASS Or ICC_PROGRESS_CLASS Or ICC_DATE_CLASSES
    InitCommonControlsEx(@icc)
    Dim dc As HDC = GetDC(0)
    vbScale = GetDeviceCaps(dc, LOGPIXELSY)
    ReleaseDC(0, dc)
    vbHandCursor = LoadCursor(0, IDC_HAND)
    Dim wc As WNDCLASSEXW
    wc.cbSize = SizeOf(wc)
    wc.style = CS_DBLCLKS
    wc.lpfnWndProc = @VBFormProc
    wc.hInstance = GetModuleHandleW(0)
    wc.hCursor = LoadCursor(0, IDC_ARROW)
    wc.hbrBackground = Cast(HBRUSH, COLOR_BTNFACE + 1)
    wc.lpszClassName = @WStr("RADVBForm")
    wc.hIcon = LoadIconW(wc.hInstance, MAKEINTRESOURCEW(1))
    RegisterClassExW(@wc)
    wc.lpfnWndProc = @VBBoxProc
    wc.hIcon = 0
    wc.lpszClassName = @WStr("RADVBBox")
    wc.hbrBackground = 0
    RegisterClassExW(@wc)
End Sub

Private Sub VBDateToCtl(ByVal id As Long, ByVal dv As Double)
    Dim As Long y, m, d, h, n, sec
    VBDateParts(dv, y, m, d, h, n, sec)
    Dim st As SYSTEMTIME
    st.wYear = y: st.wMonth = m: st.wDay = d: st.wHour = h: st.wMinute = n: st.wSecond = sec
    st.wDayOfWeek = VBWeekday(dv) - 1
    SendMessageW(vbCtls(id).hwnd, DTM_SETSYSTEMTIME, GDT_VALID, Cast(LPARAM, @st))
End Sub

Private Function VBDateFromCtl(ByVal id As Long) As Double
    Dim st As SYSTEMTIME
    SendMessageW(vbCtls(id).hwnd, DTM_GETSYSTEMTIME, 0, Cast(LPARAM, @st))
    Return VBDateSerial(st.wYear, st.wMonth, st.wDay) + VBTimeSerial(st.wHour, st.wMinute, st.wSecond)
End Function

Private Function VBCreateCtl(ByVal id As Long) As HWND
    Dim clsName As WString * 32
    Dim As DWORD st = WS_CHILD Or WS_CLIPSIBLINGS, ex = 0
    Dim host As HWND = VBHost(id)
    Dim inst As HINSTANCE = GetModuleHandleW(0)
    With vbCtls(id)
        If .visible Then st Or= WS_VISIBLE
        If .enabled = 0 Then st Or= WS_DISABLED
        Select Case .kind
        Case vbkButton
            clsName = "BUTTON": st Or= BS_PUSHBUTTON Or WS_TABSTOP
            If .back >= 0 OrElse .fore >= 0 Then st Or= BS_OWNERDRAW
            If .align = 0 Then st Or= BS_LEFT
            If .align = 1 Then st Or= BS_RIGHT
        Case vbkCheckBox
            clsName = "BUTTON": st Or= BS_CHECKBOX Or WS_TABSTOP
        Case vbkOption
            clsName = "BUTTON": st Or= BS_RADIOBUTTON Or WS_TABSTOP
        Case vbkLabel, vbkLink
            clsName = "STATIC": st Or= SS_NOTIFY
            If .align = 1 Then
                st Or= SS_RIGHT
            ElseIf .align = 2 Then
                st Or= SS_CENTER
            Else
                st Or= SS_LEFTNOWORDWRAP
            End If
            If InStr(.text, Chr(10)) = 0 Then st Or= SS_CENTERIMAGE
        Case vbkPicture
            clsName = "STATIC": st Or= SS_NOTIFY Or SS_OWNERDRAW
        Case vbkTextBox
            clsName = "EDIT": st Or= WS_TABSTOP Or ES_AUTOHSCROLL: ex = WS_EX_CLIENTEDGE
            If .multiline Then st Or= ES_MULTILINE Or ES_AUTOVSCROLL Or WS_VSCROLL Or ES_WANTRETURN: st And= Not ES_AUTOHSCROLL
            If .readonly Then st Or= ES_READONLY
            If Len(.password) Then st Or= ES_PASSWORD
            If .align = 1 Then st Or= ES_RIGHT
            If .align = 2 Then st Or= ES_CENTER
        Case vbkListBox
            clsName = "LISTBOX": st Or= WS_TABSTOP Or LBS_NOTIFY Or WS_VSCROLL Or LBS_NOINTEGRALHEIGHT: ex = WS_EX_CLIENTEDGE
        Case vbkComboBox
            clsName = "COMBOBOX": st Or= WS_TABSTOP Or WS_VSCROLL
            st Or= IIf(.style = 0, CBS_DROPDOWNLIST, IIf(.style = 2, CBS_SIMPLE, CBS_DROPDOWN Or CBS_AUTOHSCROLL))
        Case vbkFrame
            clsName = "RADVBBox": ex = WS_EX_CONTROLPARENT
        Case vbkPanel
            clsName = "RADVBBox": ex = WS_EX_CONTROLPARENT
        Case vbkTab
            clsName = "RADVBBox": ex = WS_EX_CONTROLPARENT
        Case vbkProgress
            clsName = PROGRESS_CLASS
        Case vbkUpDown
            clsName = "EDIT": st Or= WS_TABSTOP Or ES_NUMBER Or ES_AUTOHSCROLL: ex = WS_EX_CLIENTEDGE
        Case vbkSlider
            clsName = TRACKBAR_CLASS: st Or= WS_TABSTOP Or TBS_HORZ Or TBS_AUTOTICKS
        Case vbkStatus
            clsName = STATUSCLASSNAME: st Or= CCS_NOPARENTALIGN Or CCS_NORESIZE
        Case vbkDate
            clsName = DATETIMEPICK_CLASS: st Or= WS_TABSTOP Or IIf(.style = 2, DTS_TIMEFORMAT, 0)
        Case Else
            Return 0
        End Select
        If .tabStop = 0 Then st And= Not WS_TABSTOP
        If VBIsRtl(.text) Then ex Or= WS_EX_RTLREADING
        Dim h As Long = .ph
        If .kind = vbkComboBox Then h = .ph + 200
        Dim wt As WString Ptr = VBWide(.text)
        .hwnd = CreateWindowExW(ex, @clsName, IIf(.kind = vbkFrame OrElse .kind = vbkTab, @WStr(""), wt), st, VBS(.px), VBS(.py), _
                                VBS(.pw), VBS(h), host, Cast(HMENU, Cast(INT_PTR, 1000 + id)), inst, 0)
        Deallocate(wt)
        SetWindowLongPtrW(.hwnd, GWLP_USERDATA, id)
        .hfont = VBMakeFont(id)
        SendMessageW(.hwnd, WM_SETFONT, Cast(WPARAM, .hfont), 0)
        VBApplyBrush(id)
        Select Case .kind
        Case vbkFrame
            .inner = .hwnd
            Dim wt2 As WString Ptr = VBWide(.text)
            .buddy = CreateWindowExW(WS_EX_TRANSPARENT, "BUTTON", wt2, WS_CHILD Or WS_VISIBLE Or BS_GROUPBOX Or WS_CLIPSIBLINGS, _
                                     0, 0, VBS(.pw), VBS(.ph), .hwnd, Cast(HMENU, Cast(INT_PTR, 1000 + id)), inst, 0)
            Deallocate(wt2)
            SetWindowLongPtrW(.buddy, GWLP_USERDATA, id)
            SendMessageW(.buddy, WM_SETFONT, Cast(WPARAM, .hfont), 0)
            If .fore >= 0 Then SetWindowTheme(.buddy, @WStr(""), @WStr(""))
        Case vbkPanel
            .inner = .hwnd
        Case vbkTab
            .inner = CreateWindowExW(0, WC_TABCONTROL, "", WS_CHILD Or WS_VISIBLE Or WS_CLIPSIBLINGS Or WS_TABSTOP, 0, 0, VBS(.pw), VBS(.ph), _
                                     .hwnd, Cast(HMENU, Cast(INT_PTR, 1000 + id)), inst, 0)
            Swap .hwnd, .inner           ' hwnd = the tab control (notifications), inner = the outer box
            SetWindowLongPtrW(.hwnd, GWLP_USERDATA, id)
            SetWindowLongPtrW(.inner, GWLP_USERDATA, id)
            SendMessageW(.hwnd, WM_SETFONT, Cast(WPARAM, .hfont), 0)
            ' the outer box is what is placed in the container; the tab control fills it
            MoveWindow(.inner, VBS(.px), VBS(.py), VBS(.pw), VBS(.ph), 0)
            Dim tabs As String = .items
            Dim As Long k = 0, p = 1
            While Len(tabs) > 0 AndAlso k < 32
                Dim q As Long = InStr(tabs, ";")
                Dim one As String = IIf(q, Left(tabs, q - 1), tabs)
                tabs = IIf(q, Mid(tabs, q + 1), "")
                one = Trim(one)
                If Len(one) = 0 Then Continue While
                Dim ti As TCITEMW
                ti.mask = TCIF_TEXT
                Dim wt3 As WString Ptr = VBWide(one)
                ti.pszText = wt3
                SendMessageW(.hwnd, TCM_INSERTITEMW, k, Cast(LPARAM, @ti))
                Deallocate(wt3)
                .pages(k) = CreateWindowExW(WS_EX_CONTROLPARENT, "RADVBBox", "", WS_CHILD Or WS_CLIPSIBLINGS, VBS(2), VBS(24), _
                                            VBS(.pw - 4), VBS(.ph - 26), .inner, 0, inst, 0)
                SetWindowLongPtrW(.pages(k), GWLP_USERDATA, id)
                SetWindowPos(.pages(k), HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE Or SWP_NOSIZE)
                k += 1
            Wend
            .npages = k
            SendMessageW(.hwnd, TCM_SETCURSEL, .curTab, 0)
            If .curTab >= 0 AndAlso .curTab < k Then ShowWindow(.pages(.curTab), SW_SHOW)
        Case vbkTextBox
            If .maxlen > 0 Then SendMessageW(.hwnd, EM_LIMITTEXT, .maxlen, 0)
            If Len(.password) Then SendMessageW(.hwnd, EM_SETPASSWORDCHAR, VBDecodeFirst(.password), 0)
        Case vbkCheckBox
            SendMessageW(.hwnd, BM_SETCHECK, IIf(.value = 1, BST_CHECKED, IIf(.value = 2, BST_INDETERMINATE, BST_UNCHECKED)), 0)
            If .fore >= 0 Then SetWindowTheme(.hwnd, @WStr(""), @WStr(""))
        Case vbkOption
            If .value Then SendMessageW(.hwnd, BM_SETCHECK, BST_CHECKED, 0)
            If .fore >= 0 Then SetWindowTheme(.hwnd, @WStr(""), @WStr(""))
        Case vbkListBox, vbkComboBox
            Dim its As String = .items
            While Len(its) > 0
                Dim q As Long = InStr(its, ";")
                Dim one As String = Trim(IIf(q, Left(its, q - 1), its))
                its = IIf(q, Mid(its, q + 1), "")
                If Len(one) = 0 Then Continue While
                Dim wi As WString Ptr = VBWide(one)
                SendMessageW(.hwnd, IIf(.kind = vbkListBox, LB_ADDSTRING, CB_ADDSTRING), 0, Cast(LPARAM, wi))
                Deallocate(wi)
            Wend
            If .kind = vbkComboBox AndAlso .style <> 0 Then VBSetTextW(.hwnd, .text)
        Case vbkProgress
            SendMessageW(.hwnd, PBM_SETRANGE32, .vmin, .vmax)
            SendMessageW(.hwnd, PBM_SETPOS, .value, 0)
        Case vbkUpDown
            .buddy = CreateWindowExW(0, UPDOWN_CLASS, "", WS_CHILD Or WS_VISIBLE Or UDS_SETBUDDYINT Or UDS_ALIGNRIGHT Or UDS_ARROWKEYS Or UDS_NOTHOUSANDS, _
                                     0, 0, 0, 0, host, 0, inst, 0)
            SetWindowLongPtrW(.buddy, GWLP_USERDATA, id)
            SendMessageW(.buddy, UDM_SETBUDDY, Cast(WPARAM, .hwnd), 0)
            SendMessageW(.buddy, UDM_SETRANGE32, .vmin, .vmax)
            SendMessageW(.buddy, UDM_SETPOS32, 0, .value)
            If .visible = 0 Then ShowWindow(.buddy, SW_HIDE)
        Case vbkSlider
            SendMessageW(.hwnd, TBM_SETRANGEMIN, 0, .vmin)
            SendMessageW(.hwnd, TBM_SETRANGEMAX, 0, .vmax)
            SendMessageW(.hwnd, TBM_SETPOS, -1, .value)
        Case vbkStatus
            SendMessageW(.hwnd, SB_SIMPLE, 1, 0)
            Dim ws As WString Ptr = VBWide(.text)
            SendMessageW(.hwnd, SB_SETTEXTW, 255, Cast(LPARAM, ws))
            SendMessageW(.hwnd, SB_SETTEXTW, 0, Cast(LPARAM, ws))
            Deallocate(ws)
        Case vbkLink
            .underline = -1
            DeleteObject(.hfont)
            .hfont = VBMakeFont(id)
            SendMessageW(.hwnd, WM_SETFONT, Cast(WPARAM, .hfont), 0)
        Case vbkPicture
            If Len(.picture) AndAlso vbImageLoader <> 0 Then .image = vbImageLoader(.picture)
        Case vbkDate
            ' the IDE's formats: Short 2024-01-31, Long Wednesday, 31 January 2024, Time 13:45:00
            Dim fmt As WString Ptr = VBWide(IIf(.style = 1, "dddd, d MMMM yyyy", IIf(.style = 2, "HH:mm:ss", "yyyy-MM-dd")))
            SendMessageW(.hwnd, DTM_SETFORMATW, 0, Cast(LPARAM, fmt))
            Deallocate(fmt)
            Dim dv As Double = VBNow()
            If Len(.text) Then
                Dim t As String = .text
                Dim dd As Double = VBDateSerial(ValInt(Left(t, 4)), ValInt(Mid(t, 6, 2)), ValInt(Mid(t, 9, 2)))
                If Len(t) >= 19 Then dd += VBTimeSerial(ValInt(Mid(t, 12, 2)), ValInt(Mid(t, 15, 2)), ValInt(Mid(t, 18, 2)))
                If Mid(t, 3, 1) = ":" Then dd = Int(VBNow()) + VBTimeSerial(ValInt(Left(t, 2)), ValInt(Mid(t, 4, 2)), ValInt(Mid(t, 7, 2)))
                dv = dd
            End If
            VBDateToCtl(id, dv)
        End Select
        If Len(.tooltip) AndAlso vbTooltip <> 0 Then
            Dim ti As TTTOOLINFOW
            ti.cbSize = SizeOf(ti)
            ti.uFlags = TTF_IDISHWND Or TTF_SUBCLASS
            ti.hwnd = vbCtls(.form).hwnd
            ti.uId = Cast(UINT_PTR, .hwnd)
            Dim wt4 As WString Ptr = VBWide(.tooltip)
            ti.lpszText = wt4
            SendMessageW(vbTooltip, TTM_ADDTOOLW, 0, Cast(LPARAM, @ti))
            Deallocate(wt4)
        End If
        If .kind <> vbkFrame AndAlso .kind <> vbkPanel AndAlso .kind <> vbkTab Then
            SetWindowSubclass(.hwnd, @VBCtlSub, 1, id)
        End If
        If .kind = vbkTab Then Return .inner
        Return .hwnd
    End With
End Function

' menu shortcuts: "Save" & Chr(9) & "Ctrl+S" in a caption -> an accelerator of the form
Dim Shared vbAccForm(0 To 255) As Long
Dim Shared vbAccKey(0 To 255) As ACCEL
Dim Shared vbAccCount As Long

Private Sub VBAccelAdd(ByVal f As Long, ByRef spec As String, ByVal id As Long)
    If vbAccCount > 255 Then Exit Sub
    Dim As String rest = UCase(spec), k
    Dim fl As Long = FVIRTKEY
    Do
        If Left(rest, 5) = "CTRL+" Then
            fl Or= FCONTROL: rest = Mid(rest, 6)
        ElseIf Left(rest, 6) = "SHIFT+" Then
            fl Or= FSHIFT: rest = Mid(rest, 7)
        ElseIf Left(rest, 4) = "ALT+" Then
            fl Or= FALT: rest = Mid(rest, 5)
        Else
            Exit Do
        End If
    Loop
    Dim vk As Long = 0
    If Len(rest) = 1 Then
        vk = Asc(rest)
    ElseIf Left(rest, 1) = "F" AndAlso Val(Mid(rest, 2)) >= 1 AndAlso Val(Mid(rest, 2)) <= 24 Then
        vk = VK_F1 + Val(Mid(rest, 2)) - 1
    Else
        Select Case rest
        Case "DEL", "DELETE": vk = VK_DELETE
        Case "INS", "INSERT": vk = VK_INSERT
        Case "ENTER": vk = VK_RETURN
        Case "ESC", "ESCAPE": vk = VK_ESCAPE
        Case "TAB": vk = VK_TAB
        Case "HOME": vk = VK_HOME
        Case "END": vk = VK_END
        Case "PGUP": vk = VK_PRIOR
        Case "PGDN": vk = VK_NEXT
        Case "BACKSPACE", "BKSP": vk = VK_BACK
        End Select
    End If
    If vk = 0 Then Exit Sub
    vbAccForm(vbAccCount) = f
    vbAccKey(vbAccCount).fVirt = fl
    vbAccKey(vbAccCount).key = vk
    vbAccKey(vbAccCount).cmd = 1000 + id
    vbAccCount += 1
End Sub

Private Sub VBBuildMenus(ByVal f As Long)
    Dim bar As HMENU = 0
    For i As Long = 1 To vbCtlCount
        With vbCtls(i)
            If .kind <> vbkMenu OrElse .form <> f Then Continue For
            If bar = 0 Then bar = CreateMenu()
            Dim owner As HMENU = IIf(.parent = 0, bar, vbCtls(.parent).hmenu)
            If owner = 0 Then Continue For
            ' an item with children owns a popup
            Dim hasKids As Long = 0
            For j As Long = i + 1 To vbCtlCount
                If vbCtls(j).kind = vbkMenu AndAlso vbCtls(j).parent = i Then hasKids = -1: Exit For
            Next
            Dim wt As WString Ptr = VBWide(.text)
            If .text = "-" Then
                AppendMenuW(owner, MF_SEPARATOR, 0, 0)
            ElseIf hasKids Then
                .hmenu = CreatePopupMenu()
                AppendMenuW(owner, MF_POPUP, Cast(UINT_PTR, .hmenu), wt)
            Else
                AppendMenuW(owner, MF_STRING Or IIf(.enabled, 0, MF_GRAYED) Or IIf(.checked, MF_CHECKED, 0), 1000 + i, wt)
            End If
            Deallocate(wt)
        End With
    Next
    If bar Then vbCtls(f).menuBar = bar
    Dim acc(0 To 255) As ACCEL
    Dim na As Long = 0
    For i As Long = 0 To vbAccCount - 1
        If vbAccForm(i) = f Then acc(na) = vbAccKey(i): na += 1
    Next
    If na Then vbCtls(f).accel = CreateAcceleratorTableW(@acc(0), na)
End Sub

Private Function VBMenuOwner(ByVal id As Long) As HMENU
    Dim p As Long = vbCtls(id).parent
    If p = 0 Then Return vbCtls(vbCtls(id).form).menuBar
    Return vbCtls(p).hmenu
End Function

' VB6 Load: create the form window and its controls (hidden), then Form_Load
Private Sub VBFormLoad(ByVal f As Long)
    If f <= 0 OrElse vbCtls(f).loaded Then Exit Sub
    VBFire0(f, vbeInitialize)
    VBInitGui()
    vbCreating += 1
    With vbCtls(f)
        .loaded = -1
        VBApplyBrush(f)
        VBBuildMenus(f)
        Dim st As DWORD = WS_OVERLAPPEDWINDOW Or WS_CLIPCHILDREN
        If .border = 1 Then st = WS_OVERLAPPED Or WS_CAPTION Or WS_SYSMENU Or WS_MINIMIZEBOX Or WS_CLIPCHILDREN
        Dim ex As DWORD = WS_EX_CONTROLPARENT Or IIf(.topMost, WS_EX_TOPMOST, 0)
        Dim rc As RECT = Type(0, 0, VBS(.pl.w), VBS(.pl.h))
        AdjustWindowRectEx(@rc, st, IIf(.menuBar, 1, 0), ex)
        Dim As Long ww = rc.right - rc.left, wh = rc.bottom - rc.top, x = CW_USEDEFAULT, y = CW_USEDEFAULT
        If .startPos = 1 Then
            Dim wa As RECT
            SystemParametersInfoW(SPI_GETWORKAREA, 0, @wa, 0)
            x = wa.left + ((wa.right - wa.left) - VBS(.pl.w)) \ 2 + rc.left
            y = wa.top + ((wa.bottom - wa.top) - VBS(.pl.h)) \ 3 + rc.top
            If x < wa.left Then x = wa.left
            If y < wa.top Then y = wa.top
        End If
        Dim wt As WString Ptr = VBWide(.text)
        .hwnd = CreateWindowExW(ex, "RADVBForm", wt, st, x, y, ww, wh, 0, .menuBar, GetModuleHandleW(0), 0)
        Deallocate(wt)
        SetWindowLongPtrW(.hwnd, GWLP_USERDATA, f)
        If .menuBar Then
            ' the menu bar can wrap onto two lines: keep the client area at the designed size
            Dim cr As RECT
            GetClientRect(.hwnd, @cr)
            If cr.bottom <> VBS(.pl.h) Then
                Dim wr As RECT
                GetWindowRect(.hwnd, @wr)
                SetWindowPos(.hwnd, 0, 0, 0, wr.right - wr.left, (wr.bottom - wr.top) + VBS(.pl.h) - cr.bottom, SWP_NOMOVE Or SWP_NOZORDER)
            End If
        End If
        .pw = .pl.w: .ph = .pl.h
        If Len(.icon) AndAlso vbIconLoader <> 0 Then
            .hicon = vbIconLoader(.icon)
            If .hicon Then
                SendMessageW(.hwnd, WM_SETICON, ICON_BIG, Cast(LPARAM, .hicon))
                SendMessageW(.hwnd, WM_SETICON, ICON_SMALL, Cast(LPARAM, .hicon))
            End If
        End If
        .hfont = VBMakeFont(f)
    End With
    If vbTooltip = 0 Then
        vbTooltip = CreateWindowExW(WS_EX_TOPMOST, TOOLTIPS_CLASS, 0, WS_POPUP Or TTS_ALWAYSTIP, 0, 0, 0, 0, vbCtls(f).hwnd, 0, GetModuleHandleW(0), 0)
    End If
    ' containers first so that their windows exist when their children are created
    Dim todo As Long = -1
    Dim pass As Long = 0
    While todo AndAlso pass < 16
        todo = 0
        For i As Long = 1 To vbCtlCount
            With vbCtls(i)
                If .form <> f OrElse .kind = vbkForm OrElse .kind = vbkMenu OrElse .hwnd <> 0 Then Continue For
                If .kind = vbkTimer OrElse .kind >= vbkDlgOpen Then Continue For
                If .parent > 0 AndAlso vbCtls(.parent).hwnd = 0 Then todo = -1: Continue For
                VBCreateCtl(i)
            End With
        Next
        pass += 1
    Wend
    ' timers
    For i As Long = 1 To vbCtlCount
        With vbCtls(i)
            If .form = f AndAlso .kind = vbkTimer AndAlso .timerOn AndAlso .interval > 0 Then
                SetTimer(vbCtls(f).hwnd, 1000 + i, .interval, 0)
            End If
        End With
    Next
    If vbCtls(f).winState = 2 Then
        ' applied when shown
    End If
    vbCreating -= 1
    If vbFxOnForm <> 0 Then vbFxOnForm(f, 1, 0, 0)      ' animations / states / variants of the form
    VBFire0(f, vbeLoad)
End Sub

' ------------------------------------------------------------------------------ show / hide / unload / message loop
Declare Sub VBMessageLoop(ByVal untilForm As Long)

Private Sub VBFormShow(ByVal f As Long, ByVal modal As Long = 0)
    If vbCtls(f).loaded = 0 Then VBFormLoad(f)
    If vbCtls(f).loaded = 0 Then Exit Sub            ' unloaded by its own Form_Load
    Dim hw As HWND = vbCtls(f).hwnd
    Dim first As Long = (vbCtls(f).visible = 0)
    vbCtls(f).visible = -1
    If modal Then
        Dim owner As HWND = GetActiveWindow()
        Dim disabled(0 To 63) As HWND
        Dim nd As Long = 0
        For i As Long = 1 To vbCtlCount
            If vbCtls(i).kind = vbkForm AndAlso i <> f AndAlso vbCtls(i).loaded AndAlso IsWindowEnabled(vbCtls(i).hwnd) AndAlso nd < 64 Then
                EnableWindow(vbCtls(i).hwnd, 0)
                disabled(nd) = vbCtls(i).hwnd
                nd += 1
            End If
        Next
        If owner Then SetWindowLongPtrW(hw, GWLP_HWNDPARENT, Cast(LONG_PTR, owner))
        ShowWindow(hw, IIf(vbCtls(f).winState = 2, SW_SHOWMAXIMIZED, SW_SHOW))
        If first Then VBFire0(f, vbeResize)
        If first AndAlso vbFxOnForm <> 0 Then vbFxOnForm(f, 2, 0, 0)    ' "On load" animations, timers
        SetForegroundWindow(hw)
        VBMessageLoop(f)
        For i As Long = 0 To nd - 1
            If IsWindow(disabled(i)) Then EnableWindow(disabled(i), -1)
        Next
        If owner AndAlso IsWindow(owner) Then SetActiveWindow(owner)
        Exit Sub
    End If
    ShowWindow(hw, IIf(vbCtls(f).winState = 2, SW_SHOWMAXIMIZED, IIf(vbCtls(f).winState = 1, SW_SHOWMINIMIZED, SW_SHOW)))
    If first Then VBFire0(f, vbeResize)
    If first AndAlso vbFxOnForm <> 0 Then vbFxOnForm(f, 2, 0, 0)        ' "On load" animations, timers
    SetForegroundWindow(hw)
End Sub

Private Sub VBFormHide(ByVal f As Long)
    If vbCtls(f).loaded = 0 Then Exit Sub
    vbCtls(f).visible = 0
    ShowWindow(vbCtls(f).hwnd, SW_HIDE)
End Sub

Private Function VBAnyFormLoaded() As Long
    For i As Long = 1 To vbCtlCount
        If vbCtls(i).kind = vbkForm AndAlso vbCtls(i).loaded Then Return -1
    Next
    Return 0
End Function

Private Sub VBFormUnload(ByVal f As Long, ByVal mode As Long = 1)
    If f <= 0 OrElse vbCtls(f).loaded = 0 Then Exit Sub
    Dim e As VBEventArgs
    e.unloadMode = mode
    VBFire(f, vbeQueryUnload, e)
    If e.cancel Then Exit Sub
    e.cancel = 0
    VBFire(f, vbeUnload, e)
    If e.cancel Then Exit Sub
    If vbCtls(f).loaded = 0 Then Exit Sub
    If vbFxOnForm <> 0 Then vbFxOnForm(f, 5, 0, 0)      ' animations stop
    For i As Long = 1 To vbCtlCount
        With vbCtls(i)
            If .form = f AndAlso i <> f Then
                If vbFxHot = i Then vbFxHot = 0
                If .kind = vbkTimer Then KillTimer(vbCtls(f).hwnd, 1000 + i)
                .hwnd = 0: .inner = 0: .buddy = 0
                If .hfont Then DeleteObject(.hfont): .hfont = 0
                If .kind = vbkMenu Then .hmenu = 0
            End If
        End With
    Next
    With vbCtls(f)
        .loaded = 0
        .visible = 0
        Dim hw As HWND = .hwnd
        .hwnd = 0
        .menuBar = 0
        DestroyWindow(hw)
    End With
    VBFire0(f, vbeTerminate)
    ' VB6 ends the program when no form is loaded AND no code runs: "Unload Me" inside a handler goes on with the
    ' rest of the handler; the message loop ends the program afterwards (it stops when no form is loaded)
    If VBAnyFormLoaded() = 0 AndAlso vbFireDepth = 0 Then VBEnd()
End Sub

Private Sub VBPump(ByRef m As MSG)
    Dim root As HWND = GetAncestor(m.hwnd, GA_ROOT)
    If root Then
        Dim f As Long = CLng(GetWindowLongPtrW(root, GWLP_USERDATA))
        If f > 0 AndAlso f <= vbCtlCount AndAlso vbCtls(f).kind = vbkForm AndAlso vbCtls(f).hwnd = root Then
            If vbCtls(f).accel AndAlso TranslateAcceleratorW(root, vbCtls(f).accel, @m) Then Exit Sub
            If IsDialogMessageW(root, @m) Then Exit Sub
        End If
    End If
    TranslateMessage(@m)
    DispatchMessageW(@m)
End Sub

Private Sub VBMessageLoop(ByVal untilForm As Long)
    Dim m As MSG
    Do
        If untilForm > 0 Then
            If vbCtls(untilForm).loaded = 0 OrElse vbCtls(untilForm).visible = 0 Then Exit Do
        Else
            If VBAnyFormLoaded() = 0 Then Exit Do
        End If
        If GetMessageW(@m, 0, 0, 0) <= 0 Then VBEnd()
        VBPump(m)
    Loop
End Sub

Private Sub VBDoEvents()
    Dim m As MSG
    While PeekMessageW(@m, 0, 0, 0, PM_REMOVE)
        If m.message = WM_QUIT Then VBEnd()
        VBPump(m)
    Wend
End Sub

Private Sub VBRun()
    VBMessageLoop(0)
    VBEnd()
End Sub

' ------------------------------------------------------------------------------ properties
Private Sub VBNeed(ByVal id As Long)                    ' VB6: touching a control loads its form
    If vbCtls(vbCtls(id).form).loaded = 0 Then VBFormLoad(vbCtls(id).form)
End Sub

Private Function VBListText(ByVal id As Long, ByVal i As Long) As String
    With vbCtls(id)
        Dim isList As Long = (.kind = vbkListBox)
        Dim n As Long = SendMessageW(.hwnd, IIf(isList, LB_GETTEXTLEN, CB_GETLBTEXTLEN), i, 0)
        If n < 0 Then Return ""
        Dim w As WString Ptr = Allocate((n + 2) * 2)
        SendMessageW(.hwnd, IIf(isList, LB_GETTEXT, CB_GETLBTEXT), i, Cast(LPARAM, w))
        Function = VBFromWide(w, n)
        Deallocate(w)
    End With
End Function

Private Function VBGetS(ByVal id As Long, ByVal p As Long) As String
    If vbCtls(id).kind <> vbkForm AndAlso vbCtls(id).kind < vbkDlgOpen AndAlso vbCtls(id).kind <> vbkTimer Then VBNeed(id)
    With vbCtls(id)
        Select Case p
        Case vbpText
            Select Case .kind
            Case vbkForm
                If .loaded Then Return VBGetTextW(.hwnd)
                Return .text
            Case vbkListBox
                Dim i As Long = SendMessageW(.hwnd, LB_GETCURSEL, 0, 0)
                If i < 0 Then Return ""
                Return VBListText(id, i)
            Case vbkMenu, vbkFrame, vbkTimer, vbkStatus
                Return .text
            Case vbkTab
                Dim i As Long = SendMessageW(.hwnd, TCM_GETCURSEL, 0, 0)
                Return Str(i)
            Case vbkDlgOpen, vbkDlgSave
                Return .filename
            Case Else
                If .hwnd Then Return VBGetTextW(.hwnd)
                Return .text
            End Select
        Case vbpName: Return .name
        Case vbpTag: Return .tag
        Case vbpToolTipText: Return .tooltip
        Case vbpFontName: Return .fontName
        Case vbpSelText
            Dim As DWORD a, b
            SendMessageW(.hwnd, EM_GETSEL, Cast(WPARAM, @a), Cast(LPARAM, @b))
            Dim w As String = VBGetTextW(.hwnd)
            Dim ww As WString Ptr = VBWide(w)
            Function = VBFromWide(ww + a, b - a)
            Deallocate(ww)
            Exit Function
        Case vbpFileName: Return .filename
        Case vbpFileTitle: Return .filetitle
        Case vbpFilter: Return .filter
        Case vbpDialogTitle: Return .title
        Case vbpInitDir: Return .initdir
        Case vbpPasswordChar: Return .password
        Case vbpPicture: Return .picture
        End Select
    End With
    VBRaise(438)
    Return ""
End Function

Private Function VBGetN(ByVal id As Long, ByVal p As Long) As Double
    If vbCtls(id).kind <> vbkForm AndAlso vbCtls(id).kind < vbkDlgOpen AndAlso vbCtls(id).kind <> vbkTimer AndAlso vbCtls(id).kind <> vbkMenu Then VBNeed(id)
    Dim u As Long = VBUnit(id)
    With vbCtls(id)
        Select Case p
        Case vbpValue
            Select Case .kind
            Case vbkCheckBox
                Dim st As Long = SendMessageW(.hwnd, BM_GETCHECK, 0, 0)
                Return IIf(st = BST_CHECKED, 1, IIf(st = BST_INDETERMINATE, 2, 0))
            Case vbkOption: Return IIf(SendMessageW(.hwnd, BM_GETCHECK, 0, 0) = BST_CHECKED, -1, 0)
            Case vbkProgress: Return SendMessageW(.hwnd, PBM_GETPOS, 0, 0)
            Case vbkUpDown: Return SendMessageW(.buddy, UDM_GETPOS32, 0, 0)
            Case vbkSlider: Return SendMessageW(.hwnd, TBM_GETPOS, 0, 0)
            Case vbkDate: Return VBDateFromCtl(id)
            End Select
        Case vbpYear: Return VBYear(VBDateFromCtl(id))
        Case vbpMonth: Return VBMonth(VBDateFromCtl(id))
        Case vbpDay: Return VBDay(VBDateFromCtl(id))
        Case vbpHour: Return VBHour(VBDateFromCtl(id))
        Case vbpMinute: Return VBMinute(VBDateFromCtl(id))
        Case vbpSecond: Return VBSecond(VBDateFromCtl(id))
        Case vbpFormat: Return IIf(.style = 1, 0, IIf(.style = 2, 2, 1))
        Case vbpLeft
            If .kind = vbkForm Then
                Dim r As RECT
                If .loaded Then GetWindowRect(.hwnd, @r)
                Return VBU(r.left) * u
            End If
            Return .px * u
        Case vbpTop
            If .kind = vbkForm Then
                Dim r As RECT
                If .loaded Then GetWindowRect(.hwnd, @r)
                Return VBU(r.top) * u
            End If
            Return .py * u
        Case vbpWidth: Return .pw * u
        Case vbpHeight: Return .ph * u
        Case vbpScaleWidth: Return .pw * u
        Case vbpScaleHeight: Return .ph * u
        Case vbpEnabled: Return .enabled
        Case vbpVisible
            If .kind = vbkForm Then Return IIf(.loaded, IsWindowVisible(.hwnd) <> 0, 0)
            Return .visible
        Case vbpBackColor
            If .back >= 0 Then Return .back
            Return &h8000000F
        Case vbpForeColor
            If .fore >= 0 Then Return .fore
            Return &h80000012
        Case vbpListIndex
            If .kind = vbkListBox Then Return SendMessageW(.hwnd, LB_GETCURSEL, 0, 0)
            If .kind = vbkComboBox Then Return SendMessageW(.hwnd, CB_GETCURSEL, 0, 0)
        Case vbpListCount
            If .kind = vbkListBox Then Return SendMessageW(.hwnd, LB_GETCOUNT, 0, 0)
            If .kind = vbkComboBox Then Return SendMessageW(.hwnd, CB_GETCOUNT, 0, 0)
        Case vbpNewIndex: Return .newIndex
        Case vbpSelStart, vbpSelLength
            Dim As DWORD a, b
            If .kind = vbkComboBox Then
                SendMessageW(.hwnd, CB_GETEDITSEL, Cast(WPARAM, @a), Cast(LPARAM, @b))
            Else
                SendMessageW(.hwnd, EM_GETSEL, Cast(WPARAM, @a), Cast(LPARAM, @b))
            End If
            Return IIf(p = vbpSelStart, a, b - a)
        Case vbpLocked: Return .readonly
        Case vbpMaxLength: Return .maxlen
        Case vbpMin: Return .vmin
        Case vbpMax: Return .vmax
        Case vbpInterval: Return .interval
        Case vbpFontSize: Return .fontSize
        Case vbpFontBold: Return .bold
        Case vbpFontItalic: Return .italic
        Case vbpFontUnderline: Return .underline
        Case vbpHwnd: Return CLng(Cast(INT_PTR, .hwnd))
        Case vbpTabIndex: Return .tabIndex
        Case vbpTabStop: Return .tabStop
        Case vbpChecked: Return .checked
        Case vbpColor: Return .colour
        Case vbpCancelError: Return .cancelErr
        Case vbpMultiLine: Return .multiline
        Case vbpIndex: Return .arrIndex
        Case vbpAlignment: Return .align
        Case vbpTab: Return SendMessageW(.hwnd, TCM_GETCURSEL, 0, 0)
        Case vbpTabs: Return .npages
        Case vbpLinkColor: Return .linkColor
        Case vbpWindowState
            If .loaded = 0 Then Return .winState
            Return IIf(IsIconic(.hwnd), 1, IIf(IsZoomed(.hwnd), 2, 0))
        End Select
    End With
    VBRaise(438)
    Return 0
End Function

Private Sub VBSetS(ByVal id As Long, ByVal p As Long, ByRef s As String)
    If vbCtls(id).kind <> vbkForm AndAlso vbCtls(id).kind < vbkDlgOpen AndAlso vbCtls(id).kind <> vbkTimer AndAlso vbCtls(id).kind <> vbkMenu Then VBNeed(id)
    With vbCtls(id)
        Select Case p
        Case vbpText
            Select Case .kind
            Case vbkForm
                .text = s
                If .loaded Then VBSetTextW(.hwnd, s)
            Case vbkListBox
                Dim w As WString Ptr = VBWide(s)
                Dim i As Long = SendMessageW(.hwnd, LB_FINDSTRINGEXACT, -1, Cast(LPARAM, w))
                Deallocate(w)
                If i >= 0 Then SendMessageW(.hwnd, LB_SETCURSEL, i, 0): VBFire0(id, vbeClick)
            Case vbkComboBox
                If .style = 0 Then
                    Dim w As WString Ptr = VBWide(s)
                    Dim i As Long = SendMessageW(.hwnd, CB_FINDSTRINGEXACT, -1, Cast(LPARAM, w))
                    Deallocate(w)
                    If i >= 0 Then SendMessageW(.hwnd, CB_SETCURSEL, i, 0) Else VBRaise(383, "'Text' property is read-only")
                Else
                    VBSetTextW(.hwnd, s)
                    VBFire0(id, vbeChange)
                End If
            Case vbkMenu
                .text = s
                Dim owner As HMENU = VBMenuOwner(id)
                If owner Then
                    Dim w As WString Ptr = VBWide(s)
                    ModifyMenuW(owner, 1000 + id, MF_BYCOMMAND Or MF_STRING Or IIf(.checked, MF_CHECKED, 0) Or IIf(.enabled, 0, MF_GRAYED), 1000 + id, w)
                    Deallocate(w)
                    DrawMenuBar(vbCtls(.form).hwnd)
                End If
            Case vbkFrame
                .text = s
                VBSetTextW(.buddy, s)
            Case vbkStatus
                .text = s
                Dim w As WString Ptr = VBWide(s)
                SendMessageW(.hwnd, SB_SETTEXTW, 255, Cast(LPARAM, w))
                SendMessageW(.hwnd, SB_SETTEXTW, 0, Cast(LPARAM, w))
                Deallocate(w)
            Case vbkTextBox
                VBSetRtl(.hwnd, s)
                Dim t As String = s
                If .multiline Then t = VBReplace(VBReplace(s, Chr(13, 10), Chr(10)), Chr(10), Chr(13, 10))
                VBSetTextW(.hwnd, t)
            Case vbkDlgOpen, vbkDlgSave
                .filename = s
            Case Else
                .text = s
                If .hwnd Then
                    VBSetRtl(.hwnd, s)
                    VBSetTextW(.hwnd, s)
                    If .kind = vbkLabel OrElse .kind = vbkLink Then InvalidateRect(.hwnd, 0, -1)
                End If
            End Select
            Exit Sub
        Case vbpTag: .tag = s: Exit Sub
        Case vbpToolTipText
            .tooltip = s
            If vbTooltip AndAlso .hwnd Then
                Dim ti As TTTOOLINFOW
                ti.cbSize = SizeOf(ti)
                ti.uFlags = TTF_IDISHWND Or TTF_SUBCLASS
                ti.hwnd = vbCtls(.form).hwnd
                ti.uId = Cast(UINT_PTR, .hwnd)
                Dim w As WString Ptr = VBWide(s)
                ti.lpszText = w
                SendMessageW(vbTooltip, TTM_DELTOOLW, 0, Cast(LPARAM, @ti))
                SendMessageW(vbTooltip, TTM_ADDTOOLW, 0, Cast(LPARAM, @ti))
                Deallocate(w)
            End If
            Exit Sub
        Case vbpFontName: .fontName = s: VBApplyFont(id): Exit Sub
        Case vbpSelText
            Dim w As WString Ptr = VBWide(s)
            SendMessageW(.hwnd, EM_REPLACESEL, 1, Cast(LPARAM, w))
            Deallocate(w)
            Exit Sub
        Case vbpFileName: .filename = s: Exit Sub
        Case vbpFilter: .filter = s: Exit Sub
        Case vbpDialogTitle: .title = s: Exit Sub
        Case vbpInitDir: .initdir = s: Exit Sub
        Case vbpPasswordChar
            .password = s
            SendMessageW(.hwnd, EM_SETPASSWORDCHAR, VBDecodeFirst(s), 0)
            InvalidateRect(.hwnd, 0, -1)
            Exit Sub
        Case vbpPicture
            .picture = s
            If vbImageLoader Then .image = IIf(Len(s), vbImageLoader(s), 0)
            If .hwnd Then InvalidateRect(.hwnd, 0, -1)
            Exit Sub
        End Select
    End With
    VBRaise(438)
End Sub

Private Sub VBSetN(ByVal id As Long, ByVal p As Long, ByVal v As Double)
    If vbCtls(id).kind <> vbkForm AndAlso vbCtls(id).kind < vbkDlgOpen AndAlso vbCtls(id).kind <> vbkTimer AndAlso vbCtls(id).kind <> vbkMenu Then VBNeed(id)
    Dim u As Long = VBUnit(id)
    Dim iv As Long = CLng(v)
    With vbCtls(id)
        Select Case p
        Case vbpValue
            Select Case .kind
            Case vbkCheckBox
                If iv < 0 OrElse iv > 2 Then VBRaise(380): Exit Sub
                Dim old As Long = .value
                .value = iv
                SendMessageW(.hwnd, BM_SETCHECK, IIf(iv = 1, BST_CHECKED, IIf(iv = 2, BST_INDETERMINATE, BST_UNCHECKED)), 0)
                If old <> iv Then VBFire0(id, vbeClick)
            Case vbkOption
                If iv Then VBOptionClicked(id, -1) Else SendMessageW(.hwnd, BM_SETCHECK, BST_UNCHECKED, 0): .value = 0
            Case vbkProgress
                .value = iv
                SendMessageW(.hwnd, PBM_SETPOS, iv, 0)
            Case vbkUpDown
                Dim old As Long = SendMessageW(.buddy, UDM_GETPOS32, 0, 0)
                .value = iv
                SendMessageW(.buddy, UDM_SETPOS32, 0, iv)
            Case vbkSlider
                Dim old As Long = .value
                .value = iv
                SendMessageW(.hwnd, TBM_SETPOS, -1, iv)
                If old <> iv Then VBFire0(id, vbeChange)
            Case vbkDate
                Dim old As Double = VBDateFromCtl(id)
                VBDateToCtl(id, v)
                If old <> v Then VBFire0(id, vbeChange)
            Case Else
                VBRaise(438)
            End Select
            Exit Sub
        Case vbpLeft, vbpTop, vbpWidth, vbpHeight
            Dim px As Long = CLng(v / u)
            If .kind = vbkForm Then
                If .loaded = 0 Then VBFormLoad(id)
                Dim r As RECT
                GetWindowRect(.hwnd, @r)
                Select Case p
                Case vbpLeft: SetWindowPos(.hwnd, 0, VBS(px), r.top, 0, 0, SWP_NOSIZE Or SWP_NOZORDER Or SWP_NOACTIVATE)
                Case vbpTop: SetWindowPos(.hwnd, 0, r.left, VBS(px), 0, 0, SWP_NOSIZE Or SWP_NOZORDER Or SWP_NOACTIVATE)
                Case Else
                    ' Width / Height are the client size (like the designer)
                    Dim cr As RECT
                    GetClientRect(.hwnd, @cr)
                    Dim As Long dw = (r.right - r.left) - cr.right, dh = (r.bottom - r.top) - cr.bottom
                    Dim As Long nw = cr.right, nh = cr.bottom
                    If p = vbpWidth Then nw = VBS(px) Else nh = VBS(px)
                    SetWindowPos(.hwnd, 0, 0, 0, nw + dw, nh + dh, SWP_NOMOVE Or SWP_NOZORDER Or SWP_NOACTIVATE)
                End Select
                Exit Sub
            End If
            Select Case p
            Case vbpLeft: .px = px
            Case vbpTop: .py = px
            Case vbpWidth: .pw = px
            Case Else: .ph = px
            End Select
            VBMoved(id)
            Exit Sub
        Case vbpEnabled
            .enabled = IIf(iv, -1, 0)
            If .kind = vbkMenu Then
                Dim owner As HMENU = VBMenuOwner(id)
                If owner Then EnableMenuItem(owner, 1000 + id, MF_BYCOMMAND Or IIf(iv, MF_ENABLED, MF_GRAYED)): DrawMenuBar(vbCtls(.form).hwnd)
            ElseIf .kind = vbkTimer Then
                .timerOn = .enabled
                Dim fh As HWND = vbCtls(.form).hwnd
                If fh Then
                    If .timerOn AndAlso .interval > 0 Then SetTimer(fh, 1000 + id, .interval, 0) Else KillTimer(fh, 1000 + id)
                End If
            ElseIf .hwnd Then
                EnableWindow(IIf(.kind = vbkTab, .inner, .hwnd), iv <> 0)
                If .buddy Then EnableWindow(.buddy, iv <> 0)
                If .kind = vbkTab Then EnableWindow(.hwnd, iv <> 0)
            End If
            If vbFxOnSet <> 0 AndAlso vbFxQuiet = 0 Then vbFxOnSet(id, vbpEnabled, iv)    ' Disabled state
            Exit Sub
        Case vbpVisible
            If .kind = vbkForm Then
                If iv Then VBFormShow(id) Else VBFormHide(id)
                Exit Sub
            End If
            ' "On show" / "On hide" animations: shown at once, hidden at the end of the animation
            If vbFxOnSet <> 0 AndAlso vbFxQuiet = 0 AndAlso .kind <> vbkMenu Then
                If vbFxOnSet(id, vbpVisible, iv) Then Exit Sub
            End If
            .visible = IIf(iv, -1, 0)
            If .kind = vbkMenu Then Exit Sub
            If .hwnd Then
                ShowWindow(IIf(.kind = vbkTab, .inner, .hwnd), IIf(iv, SW_SHOWNA, SW_HIDE))
                If .buddy AndAlso .kind = vbkUpDown Then ShowWindow(.buddy, IIf(iv, SW_SHOWNA, SW_HIDE))
            End If
            Exit Sub
        Case vbpBackColor, vbpForeColor
            If p = vbpBackColor Then .back = iv And &hFFFFFF Else .fore = iv And &hFFFFFF
            If (iv And &h80000000) Then
                If p = vbpBackColor Then .back = -1 Else .fore = -1
            End If
            If p = vbpBackColor Then VBApplyBrush(id)
            If .kind = vbkForm Then
                If .hwnd Then InvalidateRect(.hwnd, 0, -1)
            ElseIf .hwnd Then
                If .kind = vbkButton AndAlso (GetWindowLongW(.hwnd, GWL_STYLE) And BS_TYPEMASK) <> BS_OWNERDRAW Then
                    SetWindowLongW(.hwnd, GWL_STYLE, (GetWindowLongW(.hwnd, GWL_STYLE) And Not BS_TYPEMASK) Or BS_OWNERDRAW)
                End If
                If p = vbpForeColor AndAlso (.kind = vbkCheckBox OrElse .kind = vbkOption) Then SetWindowTheme(.hwnd, @WStr(""), @WStr(""))
                InvalidateRect(.hwnd, 0, -1)
                If .inner AndAlso .inner <> .hwnd Then InvalidateRect(.inner, 0, -1)
                If .buddy Then InvalidateRect(.buddy, 0, -1)
                RedrawWindow(IIf(.kind = vbkTab, .inner, .hwnd), 0, 0, RDW_INVALIDATE Or RDW_ERASE Or RDW_ALLCHILDREN)
            End If
            Exit Sub
        Case vbpListIndex
            If .kind = vbkListBox Then
                SendMessageW(.hwnd, LB_SETCURSEL, iv, 0)
            ElseIf .kind = vbkComboBox Then
                SendMessageW(.hwnd, CB_SETCURSEL, iv, 0)
            Else
                VBRaise(438): Exit Sub
            End If
            VBFire0(id, vbeClick)
            Exit Sub
        Case vbpSelStart
            SendMessageW(.hwnd, EM_SETSEL, iv, iv)
            Exit Sub
        Case vbpSelLength
            Dim As DWORD a, b
            SendMessageW(.hwnd, EM_GETSEL, Cast(WPARAM, @a), Cast(LPARAM, @b))
            SendMessageW(.hwnd, EM_SETSEL, a, a + iv)
            Exit Sub
        Case vbpLocked
            .readonly = iv
            SendMessageW(.hwnd, EM_SETREADONLY, iv <> 0, 0)
            Exit Sub
        Case vbpMaxLength
            .maxlen = iv
            SendMessageW(.hwnd, EM_LIMITTEXT, iv, 0)
            Exit Sub
        Case vbpMin, vbpMax
            If p = vbpMin Then .vmin = iv Else .vmax = iv
            Select Case .kind
            Case vbkProgress: SendMessageW(.hwnd, PBM_SETRANGE32, .vmin, .vmax)
            Case vbkUpDown: SendMessageW(.buddy, UDM_SETRANGE32, .vmin, .vmax)
            Case vbkSlider: SendMessageW(.hwnd, IIf(p = vbpMin, TBM_SETRANGEMIN, TBM_SETRANGEMAX), -1, iv)
            End Select
            Exit Sub
        Case vbpInterval
            .interval = iv
            Dim fh As HWND = vbCtls(.form).hwnd
            If fh Then
                If .timerOn AndAlso iv > 0 Then SetTimer(fh, 1000 + id, iv, 0) Else KillTimer(fh, 1000 + id)
            End If
            Exit Sub
        Case vbpFontSize: .fontSize = v: VBApplyFont(id): Exit Sub
        Case vbpFontBold: .bold = iv: VBApplyFont(id): Exit Sub
        Case vbpFontItalic: .italic = iv: VBApplyFont(id): Exit Sub
        Case vbpFontUnderline: .underline = iv: VBApplyFont(id): Exit Sub
        Case vbpTabIndex: .tabIndex = iv: Exit Sub
        Case vbpTabStop
            .tabStop = iv
            If .hwnd Then SetWindowLongW(.hwnd, GWL_STYLE, IIf(iv, GetWindowLongW(.hwnd, GWL_STYLE) Or WS_TABSTOP, GetWindowLongW(.hwnd, GWL_STYLE) And Not WS_TABSTOP))
            Exit Sub
        Case vbpChecked
            .checked = iv
            Dim owner As HMENU = VBMenuOwner(id)
            If owner Then CheckMenuItem(owner, 1000 + id, MF_BYCOMMAND Or IIf(iv, MF_CHECKED, MF_UNCHECKED))
            Exit Sub
        Case vbpColor: .colour = iv: Exit Sub
        Case vbpCancelError: .cancelErr = iv: Exit Sub
        Case vbpAlignment: .align = iv: Exit Sub
        Case vbpLinkColor: .linkColor = iv: If .hwnd Then InvalidateRect(.hwnd, 0, -1)
            Exit Sub
        Case vbpTab
            If iv < 0 OrElse iv >= .npages Then VBRaise(380): Exit Sub
            Dim e As VBEventArgs
            e.prevTab = SendMessageW(.hwnd, TCM_GETCURSEL, 0, 0)
            SendMessageW(.hwnd, TCM_SETCURSEL, iv, 0)
            VBTabShow(id)
            .curTab = iv
            If e.prevTab <> iv Then VBFire(id, vbeClick, e)
            Exit Sub
        Case vbpWindowState
            .winState = iv
            If .loaded AndAlso IsWindowVisible(.hwnd) Then ShowWindow(.hwnd, IIf(iv = 2, SW_MAXIMIZE, IIf(iv = 1, SW_MINIMIZE, SW_RESTORE)))
            Exit Sub
        End Select
    End With
    VBRaise(438)
End Sub

' ------------------------------------------------------------------------------ methods
Private Sub VBAddItem(ByVal id As Long, ByRef s As String, ByVal index As Long = -1)
    VBNeed(id)
    With vbCtls(id)
        Dim w As WString Ptr = VBWide(s)
        If .kind = vbkListBox Then
            .newIndex = SendMessageW(.hwnd, LB_INSERTSTRING, index, Cast(LPARAM, w))
        ElseIf .kind = vbkComboBox Then
            .newIndex = SendMessageW(.hwnd, CB_INSERTSTRING, index, Cast(LPARAM, w))
        Else
            VBRaise(438)
        End If
        Deallocate(w)
    End With
End Sub

Private Sub VBRemoveItem(ByVal id As Long, ByVal index As Long)
    VBNeed(id)
    With vbCtls(id)
        Dim n As Long = SendMessageW(.hwnd, IIf(.kind = vbkListBox, LB_GETCOUNT, CB_GETCOUNT), 0, 0)
        If index < 0 OrElse index >= n Then VBRaise(5): Exit Sub
        SendMessageW(.hwnd, IIf(.kind = vbkListBox, LB_DELETESTRING, CB_DELETESTRING), index, 0)
    End With
End Sub

Private Sub VBClear(ByVal id As Long)
    VBNeed(id)
    With vbCtls(id)
        Select Case .kind
        Case vbkListBox: SendMessageW(.hwnd, LB_RESETCONTENT, 0, 0)
        Case vbkComboBox: SendMessageW(.hwnd, CB_RESETCONTENT, 0, 0)
        Case vbkTextBox: VBSetTextW(.hwnd, "")
        Case Else: VBRaise(438)
        End Select
    End With
End Sub

Private Function VBListGet(ByVal id As Long, ByVal i As Long) As String
    VBNeed(id)
    Dim n As Long = SendMessageW(vbCtls(id).hwnd, IIf(vbCtls(id).kind = vbkListBox, LB_GETCOUNT, CB_GETCOUNT), 0, 0)
    If i < 0 OrElse i >= n Then Return ""
    Return VBListText(id, i)
End Function

Private Sub VBListSet(ByVal id As Long, ByVal i As Long, ByRef s As String)
    VBNeed(id)
    With vbCtls(id)
        Dim isList As Long = (.kind = vbkListBox)
        Dim n As Long = SendMessageW(.hwnd, IIf(isList, LB_GETCOUNT, CB_GETCOUNT), 0, 0)
        If i < 0 OrElse i >= n Then VBRaise(5): Exit Sub
        Dim sel As Long = SendMessageW(.hwnd, IIf(isList, LB_GETCURSEL, CB_GETCURSEL), 0, 0)
        SendMessageW(.hwnd, IIf(isList, LB_DELETESTRING, CB_DELETESTRING), i, 0)
        Dim w As WString Ptr = VBWide(s)
        SendMessageW(.hwnd, IIf(isList, LB_INSERTSTRING, CB_INSERTSTRING), i, Cast(LPARAM, w))
        Deallocate(w)
        If sel = i Then SendMessageW(.hwnd, IIf(isList, LB_SETCURSEL, CB_SETCURSEL), i, 0)
    End With
End Sub

Private Sub VBSetFocus(ByVal id As Long)
    If vbCtls(id).kind = vbkForm Then
        If vbCtls(id).loaded Then SetForegroundWindow(vbCtls(id).hwnd)
        Exit Sub
    End If
    VBNeed(id)
    If vbCtls(id).enabled = 0 OrElse vbCtls(id).visible = 0 Then VBRaise(5): Exit Sub
    SetFocus(vbCtls(id).hwnd)
End Sub

Private Sub VBMove(ByVal id As Long, ByVal l As Double, ByVal t As Double = -1e300, ByVal w As Double = -1e300, ByVal h As Double = -1e300)
    VBSetN(id, vbpLeft, l)
    If t > -1e299 Then VBSetN(id, vbpTop, t)
    If w > -1e299 Then VBSetN(id, vbpWidth, w)
    If h > -1e299 Then VBSetN(id, vbpHeight, h)
End Sub

Private Sub VBRefresh(ByVal id As Long)
    If vbCtls(id).hwnd Then UpdateWindow(vbCtls(id).hwnd)
End Sub

Private Sub VBZOrder(ByVal id As Long, ByVal where As Long = 0)
    If vbCtls(id).hwnd Then SetWindowPos(IIf(vbCtls(id).kind = vbkTab, vbCtls(id).inner, vbCtls(id).hwnd), IIf(where = 0, HWND_TOP, HWND_BOTTOM), 0, 0, 0, 0, SWP_NOMOVE Or SWP_NOSIZE)
End Sub

Private Function VBTabCaption(ByVal id As Long, ByVal i As Long) As String
    VBNeed(id)
    Dim buf As WString * 260
    Dim ti As TCITEMW
    ti.mask = TCIF_TEXT
    ti.pszText = @buf
    ti.cchTextMax = 259
    SendMessageW(vbCtls(id).hwnd, TCM_GETITEMW, i, Cast(LPARAM, @ti))
    Return VBFromWide(@buf)
End Function

Private Sub VBTabCaptionSet(ByVal id As Long, ByVal i As Long, ByRef s As String)
    VBNeed(id)
    Dim ti As TCITEMW
    ti.mask = TCIF_TEXT
    Dim w As WString Ptr = VBWide(s)
    ti.pszText = w
    SendMessageW(vbCtls(id).hwnd, TCM_SETITEMW, i, Cast(LPARAM, @ti))
    Deallocate(w)
End Sub

' ------------------------------------------------------------------------------ MsgBox / InputBox
Private Function VBMsgBox(ByRef prompt As String, ByVal buttons As Long = 0, ByRef title As String = "") As Long
    Dim w As WString Ptr = VBWide(prompt)
    Dim t As WString Ptr = VBWide(IIf(Len(title), title, vbAppTitle))
    Dim owner As HWND = GetActiveWindow()
    Function = MessageBoxW(owner, w, t, buttons Or IIf(buttons And &h1000, 0, MB_TASKMODAL))
    Deallocate(w): Deallocate(t)
End Function

Dim Shared vbIbResult As String
Dim Shared vbIbDone As Long
Dim Shared vbIbEdit As HWND

Private Function VBInputProc(ByVal hwnd As HWND, ByVal msg As UINT, ByVal wp As WPARAM, ByVal lp As LPARAM) As LRESULT
    Select Case msg
    Case WM_COMMAND
        If LoWord(wp) = IDOK Then vbIbResult = VBGetTextW(vbIbEdit): vbIbDone = 1: Return 0
        If LoWord(wp) = IDCANCEL Then vbIbResult = "": vbIbDone = 2: Return 0
    Case WM_CLOSE
        vbIbResult = "": vbIbDone = 2
        Return 0
    End Select
    Return DefWindowProcW(hwnd, msg, wp, lp)
End Function

Private Function VBInputBox(ByRef prompt As String, ByRef title As String = "", ByRef def As String = "") As String
    VBInitGui()
    Static registered As Long
    Dim inst As HINSTANCE = GetModuleHandleW(0)
    If registered = 0 Then
        Dim wc As WNDCLASSEXW
        wc.cbSize = SizeOf(wc)
        wc.lpfnWndProc = @VBInputProc
        wc.hInstance = inst
        wc.hCursor = LoadCursor(0, IDC_ARROW)
        wc.hbrBackground = Cast(HBRUSH, COLOR_BTNFACE + 1)
        wc.lpszClassName = @WStr("RADVBInput")
        RegisterClassExW(@wc)
        registered = -1
    End If
    Dim owner As HWND = GetActiveWindow()
    Dim st As DWORD = WS_POPUP Or WS_CAPTION Or WS_SYSMENU
    Dim rc As RECT = Type(0, 0, VBS(372), VBS(132))
    AdjustWindowRectEx(@rc, st, 0, WS_EX_DLGMODALFRAME Or WS_EX_CONTROLPARENT)
    Dim wa As RECT
    SystemParametersInfoW(SPI_GETWORKAREA, 0, @wa, 0)
    Dim As Long ww = rc.right - rc.left, wh = rc.bottom - rc.top
    Dim t As WString Ptr = VBWide(IIf(Len(title), title, vbAppTitle))
    Dim dlg As HWND = CreateWindowExW(WS_EX_DLGMODALFRAME Or WS_EX_CONTROLPARENT, "RADVBInput", t, st, _
                                      wa.left + (wa.right - wa.left - ww) \ 2, wa.top + (wa.bottom - wa.top - wh) \ 3, ww, wh, owner, 0, inst, 0)
    Deallocate(t)
    Dim f As Long = 0
    Dim tmpF As VBCtl
    Dim font As HFONT
    Dim ncm As NONCLIENTMETRICSW
    ncm.cbSize = SizeOf(ncm)
    SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, SizeOf(ncm), @ncm, 0)
    font = CreateFontIndirectW(@ncm.lfMessageFont)
    Dim p As WString Ptr = VBWide(prompt)
    Dim lbl As HWND = CreateWindowExW(0, "STATIC", p, WS_CHILD Or WS_VISIBLE, VBS(10), VBS(10), VBS(270), VBS(80), dlg, 0, inst, 0)
    Deallocate(p)
    Dim ok As HWND = CreateWindowExW(0, "BUTTON", "OK", WS_CHILD Or WS_VISIBLE Or WS_TABSTOP Or BS_DEFPUSHBUTTON, VBS(290), VBS(10), VBS(72), VBS(24), dlg, Cast(HMENU, IDOK), inst, 0)
    Dim cn As HWND = CreateWindowExW(0, "BUTTON", "Cancel", WS_CHILD Or WS_VISIBLE Or WS_TABSTOP, VBS(290), VBS(40), VBS(72), VBS(24), dlg, Cast(HMENU, IDCANCEL), inst, 0)
    Dim d As WString Ptr = VBWide(def)
    vbIbEdit = CreateWindowExW(WS_EX_CLIENTEDGE, "EDIT", d, WS_CHILD Or WS_VISIBLE Or WS_TABSTOP Or ES_AUTOHSCROLL, VBS(10), VBS(98), VBS(352), VBS(22), dlg, 0, inst, 0)
    Deallocate(d)
    For Each_ As Long = 0 To 3
        Dim hh As HWND = IIf(Each_ = 0, lbl, IIf(Each_ = 1, ok, IIf(Each_ = 2, cn, vbIbEdit)))
        SendMessageW(hh, WM_SETFONT, Cast(WPARAM, font), 0)
    Next
    SendMessageW(vbIbEdit, EM_SETSEL, 0, -1)
    If owner Then EnableWindow(owner, 0)
    ShowWindow(dlg, SW_SHOW)
    SetForegroundWindow(dlg)
    SetFocus(vbIbEdit)
    vbIbDone = 0
    Dim m As MSG
    While vbIbDone = 0
        If GetMessageW(@m, 0, 0, 0) <= 0 Then Exit While
        If IsDialogMessageW(dlg, @m) = 0 Then
            TranslateMessage(@m)
            DispatchMessageW(@m)
        End If
    Wend
    If owner Then EnableWindow(owner, -1): SetActiveWindow(owner)
    DestroyWindow(dlg)
    DeleteObject(font)
    Return vbIbResult
End Function

' ------------------------------------------------------------------------------ common dialogs
Private Function VBDlgCancel(ByVal id As Long) As Long
    If vbCtls(id).cancelErr Then VBRaise(32755)
    Return 0
End Function

Private Function VBShowFile(ByVal id As Long, ByVal save As Long) As Long
    With vbCtls(id)
        Dim buf As WString * 4096
        Dim fnw As WString Ptr = VBWide(.filename)
        lstrcpynW(@buf, fnw, 4095)
        Deallocate(fnw)
        ' "Text files|*.txt|All files|*.*" -> double-NUL separated list
        Dim flt As String = .filter
        If Len(flt) = 0 Then flt = "All files|*.*"
        Dim fw As WString Ptr = VBWide(flt & "||")
        For i As Long = 0 To lstrlenW(fw) - 1
            If (*fw)[i] = Asc("|") Then (*fw)[i] = 0
        Next
        Dim tw As WString Ptr = VBWide(.title)
        Dim dw As WString Ptr = VBWide(.initdir)
        Dim ofn As OPENFILENAMEW
        ofn.lStructSize = SizeOf(ofn)
        ofn.hwndOwner = GetActiveWindow()
        ofn.lpstrFilter = fw
        ofn.lpstrFile = @buf
        ofn.nMaxFile = 4096
        If Len(.title) Then ofn.lpstrTitle = tw
        If Len(.initdir) Then ofn.lpstrInitialDir = dw
        ofn.Flags = OFN_EXPLORER Or OFN_HIDEREADONLY Or IIf(save, OFN_OVERWRITEPROMPT, OFN_FILEMUSTEXIST)
        Dim ok As Long = IIf(save, GetSaveFileNameW(@ofn), GetOpenFileNameW(@ofn))
        Deallocate(fw): Deallocate(tw): Deallocate(dw)
        If ok = 0 Then Return VBDlgCancel(id)
        .filename = VBFromWide(@buf)
        .filetitle = Mid(.filename, InStrRev(.filename, "\") + 1)
        Return -1
    End With
End Function

Private Function VBShowColor(ByVal id As Long) As Long
    Static custom(0 To 15) As COLORREF
    Dim cc As CHOOSECOLORW
    cc.lStructSize = SizeOf(cc)
    cc.hwndOwner = GetActiveWindow()
    cc.rgbResult = vbCtls(id).colour
    cc.lpCustColors = @custom(0)
    cc.Flags = CC_RGBINIT Or CC_FULLOPEN
    If ChooseColorW(@cc) = 0 Then Return VBDlgCancel(id)
    vbCtls(id).colour = cc.rgbResult
    Return -1
End Function

Private Function VBShowFont(ByVal id As Long) As Long
    Dim lf As LOGFONTW
    Dim w As WString Ptr = VBWide(vbCtls(id).fontName)
    lstrcpynW(@lf.lfFaceName, w, 32)
    Deallocate(w)
    lf.lfHeight = -MulDiv(CLng(vbCtls(id).fontSize), vbScale, 72)
    lf.lfWeight = IIf(vbCtls(id).bold, FW_BOLD, FW_NORMAL)
    lf.lfItalic = IIf(vbCtls(id).italic, 1, 0)
    Dim cf As CHOOSEFONTW
    cf.lStructSize = SizeOf(cf)
    cf.hwndOwner = GetActiveWindow()
    cf.lpLogFont = @lf
    cf.Flags = CF_SCREENFONTS Or CF_INITTOLOGFONTSTRUCT Or CF_EFFECTS
    If ChooseFontW(@cf) = 0 Then Return VBDlgCancel(id)
    vbCtls(id).fontName = VBFromWide(@lf.lfFaceName)
    vbCtls(id).fontSize = cf.iPointSize / 10
    vbCtls(id).bold = IIf(lf.lfWeight >= FW_BOLD, -1, 0)
    vbCtls(id).italic = IIf(lf.lfItalic, -1, 0)
    vbCtls(id).colour = cf.rgbColors
    Return -1
End Function

Private Function VBShowFolder(ByVal id As Long) As Long
    Dim bi As BROWSEINFOW
    Dim buf As WString * 1024
    bi.hwndOwner = GetActiveWindow()
    bi.pszDisplayName = @buf
    Dim tw As WString Ptr = VBWide(vbCtls(id).title)
    bi.lpszTitle = tw
    bi.ulFlags = BIF_RETURNONLYFSDIRS Or BIF_NEWDIALOGSTYLE
    CoInitialize(0)
    Dim pidl As Any Ptr = SHBrowseForFolderW(@bi)
    Deallocate(tw)
    If pidl = 0 Then Return VBDlgCancel(id)
    SHGetPathFromIDListW(pidl, @buf)
    CoTaskMemFree(pidl)
    vbCtls(id).filename = VBFromWide(@buf)
    Return -1
End Function

' ShowDialog(): "OK" / "Cancel" by the dialog's kind
Private Function VBShowDialog(ByVal id As Long) As String
    Dim ok As Long
    Select Case vbCtls(id).kind
    Case vbkDlgOpen: ok = VBShowFile(id, 0)
    Case vbkDlgSave: ok = VBShowFile(id, -1)
    Case vbkDlgColor: ok = VBShowColor(id)
    Case vbkDlgFont: ok = VBShowFont(id)
    Case vbkDlgFolder: ok = VBShowFolder(id)
    End Select
    Return IIf(ok, "OK", "Cancel")
End Function

' ------------------------------------------------------------------------------ App / Screen / Clipboard
Private Function VBScreenW() As Long
    Return VBU(GetSystemMetrics(SM_CXSCREEN)) * 15
End Function
Private Function VBScreenH() As Long
    Return VBU(GetSystemMetrics(SM_CYSCREEN)) * 15
End Function

Private Sub VBClipSet(ByRef s As String)
    If OpenClipboard(0) = 0 Then Exit Sub
    EmptyClipboard()
    Dim w As WString Ptr = VBWide(s)
    Dim n As Long = (lstrlenW(w) + 1) * 2
    Dim hm As HGLOBAL = GlobalAlloc(GMEM_MOVEABLE, n)
    CopyMemory(GlobalLock(hm), w, n)
    GlobalUnlock(hm)
    SetClipboardData(CF_UNICODETEXT, hm)
    CloseClipboard()
    Deallocate(w)
End Sub

Private Function VBClipGet() As String
    If OpenClipboard(0) = 0 Then Return ""
    Dim hm As HANDLE = GetClipboardData(CF_UNICODETEXT)
    If hm Then
        Function = VBFromWide(Cast(WString Ptr, GlobalLock(hm)))
        GlobalUnlock(hm)
    End If
    CloseClipboard()
End Function

Private Sub VBClipClear()
    If OpenClipboard(0) Then EmptyClipboard(): CloseClipboard()
End Sub

Private Sub VBBeep()
    MessageBeep(MB_OK)
End Sub
